"""Emerging-skill discovery: find skill-like terms in ad text that the curated vocabulary does not know, decide which
have enough evidence to track, and keep a versioned registry of every skill and its status.

1. Extract   tech-shaped terms (PyTorch, Next.js, GPT-4, RAG) and capitalised terms or 2-3 word phrases that are
             not sentence-initial (Claude Code, Vertex AI), from eligible, classified HN ads.
2. Normalise spelling (taxonomy.key: 'Next.js' = 'NextJS' = 'next js'); a term whose key is a known skill's is an
             alias of it (status merged, counted under the known skill).
3. Filter    generic words (used in lower case in >= GENERIC_LOWER_SHARE of their occurrences), places, months,
             the posting company's own name, and job-title words.
4. Evidence  per country x occupation, and per occupation over all countries (a term's novelty does not depend
             on the country; demand figures stay per country): ads naming the term in the last 6 complete months vs the 12 before, distinct
             employers, months present. A term is newly_detected only with >= STRONG support and a first
             appearance within NEW_MONTHS; weaker support, or an established term the vocabulary lacks, is
             under_review; below that it is noise and not registered. One-off mentions never qualify.
5. Registry  taxonomy/skill_registry.json, versioned; the previous version is archived on every change.
             Statuses: known, newly_detected, under_review, merged, deprecated. Reviewer decisions in
             taxonomy/registry_overrides.csv win over the rules.

Ranking uses a lower bound on the increase in share (growth_lb), so a term going from 1 to 3 ads cannot top the
list on percentage growth.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import store, taxonomy as T

RECENT, BASE = 6, 12  # months
NEW_MONTHS = 36  # newly_detected only for terms first seen in the last 36 months; older ones are not new
STRONG = {"recent_ads": 10, "employers": 6, "months_present": 3}
WEAK = {"recent_ads": 5, "employers": 3, "months_present": 2}
GENERIC_LOWER_SHARE = 0.25
ALL = "ALL"  # pooled over countries: discovery evidence only, never a demand estimate
Z10 = 1.2816  # one-sided 90%: growth_lb is the 10th percentile of the share increase

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[.\-+#][A-Za-z0-9+#]+)*[+#]*")
_TECH = re.compile(r"[a-z][A-Z]|[A-Za-z]\d|\d[A-Za-z]|[.+#]")
_STOP = set("""
a an and or the we our us you your they their it its is are be this that with for from to of in on at by as
i me my he she his her who what when where why how which all any each more most other some such no not only own same so
than too very can will just should now also if then there here about after again against before between into through
during above below up down out off over under further once both few many much one two three four five new great best
hiring hire join apply email contact please send resume cv salary equity benefits visa sponsorship remote onsite on-site
hybrid full time part fulltime parttime contract intern internship internships senior junior staff principal lead head
director manager engineer engineers engineering developer developers development software scientist scientists data
analyst analysts science team teams role roles position positions job jobs company companies startup startups series seed
founded founding founder founders ceo cto vp inc llc ltd gmbh corp yc office offices location locations based us usa
uk eu europe america american north south east west global worldwide anywhere timezone timezones est pst cet utc gmt
january february march april may june july august september october november december
california texas colorado washington florida massachusetts oregon virginia georgia illinois ohio michigan utah arizona
minnesota pennsylvania jersey carolina york francisco angeles diego jose bay area valley city county state states
university college school phd bsc msc degree bachelor bachelors master masters stanford mit berkeley
jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday
k m usd eur gbp year years yr yrs month months week weeks day days hour hours experience
http https www com io org net html href nofollow rel
api apis ui uis ux saas b2b b2c sdk sdks os json fullstack frontend backend objective coordinator managers
google amazon microsoft facebook meta apple netflix
""".split())
_STOP_KEYS = {k.replace("-", "") for k in _STOP} | {"fulltime", "parttime", "vcfunded", "vcbacked", "aipowered"}


def _is_tech(tok: str) -> bool:
    return bool(_TECH.search(tok)) or (tok.isupper() and 2 <= len(tok) <= 6)


def _sentence_starts(text: str) -> set[int]:
    starts = {0}
    for m in re.finditer(r"(?:^|[.!?:;\n•\-–|*(]\s*)(?=[A-Za-z])", text, flags=re.M):
        starts.add(m.end())
    return starts


_DOMAIN = re.compile(r"(^www\.)|\.(com|io|co|org|net|ai|app|dev|me|ly|so|us|uk|de|sh|xyz|gg|careers|jobs|html?)$", re.I)
_SEGMENTS = re.compile(r"(?<=[.!?;:])\s+|\n")
MIN_STACK_KNOWN = 2  # a term counts only in a segment that also names >= 2 known skills (a tech-stack list)


def _plausible(tok: str) -> bool:
    low = tok.lower()
    return not (low in _STOP or T.key(tok) in _STOP_KEYS or _DOMAIN.search(tok) or tok.isdigit() or
                (len(tok) <= 2 and not tok.isupper()) or
                (len(tok) > 6 and re.search(r"\d", tok) and not re.search(r"[.\-]", tok)))  # ids, hashes


def terms(text: str, employer: str = "", known_keys: set[str] | None = None) -> dict[str, str]:
    """key -> surface form of the candidate terms in one ad (at most once each). Only segments (sentences or lines)
    that name at least MIN_STACK_KNOWN known skills are read: skills are listed next to other skills, while company
    names, schools and places mostly sit in prose."""
    known_keys = known_key_set() if known_keys is None else known_keys
    emp = {T.key(w) for w in re.findall(r"[A-Za-z0-9]+", employer)}
    out: dict[str, str] = {}
    for seg in _SEGMENTS.split(text):
        toks = [(m.group(0), m.start()) for m in _TOKEN.finditer(seg)]
        if len(toks) < 3:
            continue
        keys = [T.key(t) for t, _ in toks]
        hits = sum(k in known_keys for k in keys) + sum(
            T.key(a + b) in known_keys for a, b in zip(keys, keys[1:]))
        if hits < MIN_STACK_KNOWN:
            continue
        starts = _sentence_starts(seg)
        for i, (tok, pos) in enumerate(toks):
            k = keys[i]
            if _plausible(tok) and k not in emp and (
                    _is_tech(tok) or (tok[0].isupper() and len(tok) >= 3 and pos not in starts)):
                out.setdefault(k, tok)
            for n in (2, 3):  # phrases: adjacent capitalised / tech tokens separated by one space
                group = toks[i:i + n]
                if len(group) < n:
                    break
                words = [t for t, _ in group]
                if not all(seg[group[j][1] + len(words[j]):group[j + 1][1]] == " " for j in range(n - 1)):
                    break
                if not all(w[0].isupper() or _is_tech(w) for w in words) or \
                        (pos in starts and not _is_tech(tok)) or any(w.lower() in _ROLE for w in words) or \
                        not all(_plausible(w) or w.lower() in _JOINERS for w in words[1:]) or not _plausible(words[0]):
                    continue
                pk = T.key(" ".join(words))
                if pk not in emp:
                    out.setdefault(pk, " ".join(words))
    return out


_ROLE = set("""engineer engineers developer developers designer designers manager managers scientist scientists analyst
analysts researcher researchers intern interns architect architects consultant consultants specialist specialists
executive executives officer officers director directors lead leads head recruiter administrator admin technician
""".split())
_JOINERS = {"ai", "ml", "api", "sdk", "cloud", "code", "data", "db"}


def known_key_set() -> set[str]:
    return set(known_key_map())


def _generic_keys(texts: list[str], keys: set[str]) -> set[str]:
    """Single words that are mostly written in lower case: ordinary English, not names."""
    singles = {k for k in keys if k.isalpha()}
    lower, total = Counter(), Counter()
    for text in texts:
        for w in re.findall(r"[A-Za-z]+", text):
            k = w.lower()
            if k in singles:
                total[k] += 1
                if w.islower():
                    lower[k] += 1
    return {k for k in singles if total[k] and lower[k] / total[k] >= GENERIC_LOWER_SHARE}


def _place_keys() -> set[str]:
    g = store.read_json("taxonomy/geo.json")["countries"]
    out = set()
    for v in g.values():
        out.add(T.key(v["name"]))
        for p in v["patterns"]:
            out |= {T.key(c) for c in re.findall(r"\b[A-Z]{2}\b", p)}  # state / province codes in alternations
            plain = re.sub(r"\\b|\\\.|\?|\(.*?\)|[,\\]", " ", p).strip()
            for part in [plain, *plain.split()]:
                if part and re.fullmatch(r"[A-Za-zÀ-ÿ .]+", part):
                    out.add(T.key(part))
    return out


def extract(ads: pd.DataFrame, text: pd.Series) -> pd.DataFrame:
    """(ad_id, key, surface) for candidate terms in eligible, classified HN ads, after the generic/place/known filters."""
    rel = ads[ads["eligible"] & ads["occupations"].ne("") & (ads["source"] == "hn_whoishiring")]
    texts = text.reindex(rel["ad_id"]).fillna("").tolist()
    kk = known_key_set()
    rows = [(aid, k, s) for aid, t, emp in zip(rel["ad_id"], texts, rel["employer"].fillna(""))
            for k, s in terms(t, emp, kk).items()]
    c = pd.DataFrame(rows, columns=["ad_id", "key", "surface"])
    if c.empty:
        return c
    support = c.groupby("key")["ad_id"].nunique()
    c = c[c["key"].isin(support[support >= WEAK["recent_ads"]].index)]
    drop = _generic_keys(texts, set(c["key"])) | _place_keys() | {k for k in c["key"] if len(k) < 2}
    return c[~c["key"].isin(drop)].reset_index(drop=True)


def known_key_map() -> dict[str, str]:
    m = {}
    for s in T.curated():
        for k in s.keys:
            m.setdefault(k, s.id)
    return m


def window_stats(counts: pd.DataFrame, totals: pd.DataFrame, last: pd.Period) -> pd.DataFrame:
    """Per country x occupation x skill: recent (6 months to `last`) vs base (the 12 before) ads and shares.
    counts: month, country, occupation, skill_id, n_ads_skill [, employers]; totals: month, country, occupation, n_ads."""
    rec = (last - RECENT + 1, last)
    base = (last - RECENT - BASE + 1, last - RECENT)
    m = pd.PeriodIndex(counts["month"], freq="M")
    tm = pd.PeriodIndex(totals["month"], freq="M")
    cell = ["country", "occupation"]
    nR = totals[(tm >= rec[0]) & (tm <= rec[1])].groupby(cell)["n_ads"].sum().rename("n_recent")
    nB = totals[(tm >= base[0]) & (tm <= base[1])].groupby(cell)["n_ads"].sum().rename("n_base")
    cr = counts[(m >= rec[0]) & (m <= rec[1])]
    kR = cr.groupby(cell + ["skill_id"]).agg(k_recent=("n_ads_skill", "sum"), months_present=("month", "nunique"))
    kB = counts[(m >= base[0]) & (m <= base[1])].groupby(cell + ["skill_id"])["n_ads_skill"].sum().rename("k_base")
    first = counts[counts["n_ads_skill"] > 0].groupby(cell + ["skill_id"])["month"].min().rename("first_seen")
    total = counts.groupby(cell + ["skill_id"])["n_ads_skill"].sum().rename("k_total")
    s = pd.concat([kR, kB, first, total], axis=1).reset_index()
    s = s.merge(nR.reset_index(), on=cell, how="left").merge(nB.reset_index(), on=cell, how="left")
    s[["k_recent", "k_base", "months_present", "n_recent", "n_base"]] = \
        s[["k_recent", "k_base", "months_present", "n_recent", "n_base"]].fillna(0).astype(int)
    pR = (s["k_recent"] + 0.5) / (s["n_recent"] + 1)
    pB = (s["k_base"] + 0.5) / (s["n_base"] + 1)
    s["share_recent"] = np.where(s["n_recent"] > 0, s["k_recent"] / s["n_recent"].clip(lower=1), np.nan)
    s["share_base"] = np.where(s["n_base"] > 0, s["k_base"] / s["n_base"].clip(lower=1), np.nan)
    s["change_pp"] = (s["share_recent"] - s["share_base"]) * 100
    sd = np.sqrt(pR * (1 - pR) / (s["n_recent"] + 1) + pB * (1 - pB) / (s["n_base"] + 1))
    s["growth_lb_pp"] = ((pR - pB) - Z10 * sd) * 100
    s["growth_ub_pp"] = ((pR - pB) + Z10 * sd) * 100  # < 0: a decline at the same confidence
    s["growth_ratio"] = pR / pB
    s["recent_window"] = f"{rec[0]}..{rec[1]}"
    s["base_window"] = f"{base[0]}..{base[1]}"
    return s


def confidence(k: int, employers: int, months: int) -> str:
    if k >= 30 and employers >= 15 and months >= 5:
        return "high"
    if k >= 15 and employers >= 8 and months >= 4:
        return "medium"
    return "low"


def _snippet(text: str, surface: str, width: int = 90) -> str:
    i = text.find(surface)
    if i < 0:
        return ""
    a, b = max(0, i - width), min(len(text), i + len(surface) + width)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def build_registry(ads: pd.DataFrame, text: pd.Series, cands: pd.DataFrame, last: pd.Period,
                   data_version: str, withheld: tuple[str, ...] = (), versioned: bool = True) -> tuple[dict, pd.DataFrame]:
    """Registry of all skills, and (ad_id, skill_id) rows for the candidates registered for tracking.
    withheld: curated skill ids to treat as unknown (the back-check); versioned=False writes nothing."""
    known = {k: s for k, s in known_key_map().items() if s not in withheld}
    prev = store.read_json("taxonomy/skill_registry.json", default={"version": 0, "skills": []}) if versioned else \
        {"version": 0, "skills": []}
    overrides = _overrides()
    meta = ads.set_index("ad_id")
    cands = cands.assign(key=fold_suffixes(cands["key"], set(known) | set(cands["key"])))
    entries: dict[str, dict] = {}
    for s in T.curated():
        if s.id in withheld:
            continue
        entries[s.id] = {"skill_id": s.id, "name": s.name, "category": s.category, "status": "known",
                         "origin": "curated", "in_onet": T.in_onet(s.keys), "aliases_seen": [], "merged_into": None,
                         "evidence": None, "reason": "seed vocabulary (curated; O*NET coverage checked)"}

    # aliases of known skills seen in text -> merged
    surf = cands.groupby(["key", "surface"]).size().reset_index(name="n").sort_values("n", ascending=False)
    for k, g in surf.groupby("key"):
        if k in known:
            sid = known[k]
            forms = [f for f in g["surface"].tolist() if f != entries[sid]["name"]][:5]
            entries[sid]["aliases_seen"] = sorted(set(entries[sid]["aliases_seen"]) | set(forms))
    unknown = cands[~cands["key"].isin(known)]

    # evidence per candidate x cell
    x = unknown.merge(meta[["month", "countries", "occupations", "employer_key"]], left_on="ad_id", right_index=True)
    x = x.assign(country=x["countries"].str.split("|"), occupation=x["occupations"].str.split("|"))
    x = x.explode("occupation")
    # novelty is a property of the language, so evidence is also judged per occupation over all ads (country
    # "ALL", including ads with no country). Demand figures elsewhere stay per country.
    pooled = x.drop_duplicates(["ad_id", "key", "occupation"]).assign(country=ALL)
    x = pd.concat([x.explode("country").pipe(lambda d: d[d["country"].ne("") & d["country"].notna()]), pooled])
    totals = pd.concat([_totals(ads), _totals(ads, pooled=True)])
    counts = x.groupby(["month", "country", "occupation", "key"]).agg(
        n_ads_skill=("ad_id", "nunique")).reset_index().rename(columns={"key": "skill_id"})
    stats = window_stats(counts, totals, last) if len(counts) else pd.DataFrame()
    rec_lo = last - RECENT + 1
    xr = x[pd.PeriodIndex(x["month"], freq="M") >= rec_lo]
    emp = xr.groupby(["country", "occupation", "key"])["employer_key"].nunique().rename("employers").reset_index()
    if len(stats):
        stats = stats.merge(emp.rename(columns={"key": "skill_id"}), on=["country", "occupation", "skill_id"], how="left")
        stats["employers"] = stats["employers"].fillna(0).astype(int)
    onet_all = T.onet_keys()
    best_form = surf.drop_duplicates("key").set_index("key")["surface"]
    first_global = pooled.groupby("key")["month"].min()
    for k, g in (stats.groupby("skill_id") if len(stats) else []):
        def passes(t):
            return (g["k_recent"] >= t["recent_ads"]) & (g["employers"] >= t["employers"]) & \
                (g["months_present"] >= t["months_present"]) & (g["growth_lb_pp"] > 0)
        strong, weak = g[passes(STRONG)], g[passes(WEAK)]
        if weak.empty:
            continue
        top = (strong if len(strong) else weak).sort_values("growth_lb_pp", ascending=False).iloc[0]
        alias_of = _near_alias(k, known)
        first = pd.Period(first_global[k], freq="M") if k in first_global else last
        is_new = first > last - NEW_MONTHS
        status = "newly_detected" if len(strong) and is_new and not alias_of else "under_review"
        where = f"all countries, {top.occupation}; discovery evidence only" if top.country == ALL else \
            f"{top.country}, {top.occupation}"
        reason = (f"{int(top.k_recent)} ads from {int(top.employers)} employers in {int(top.months_present)} of the "
                  f"last {RECENT} months ({where}); share up at least "
                  f"{top.growth_lb_pp:.2f} pp (90% lower bound)")
        if alias_of:
            reason += f"; spelling close to known skill '{alias_of}', so it needs review before tracking separately"
        elif not is_new:
            reason += (f"; first seen {first}, so not new: an established term missing from the vocabulary, "
                       f"proposed for adding")
        elif not len(strong):
            reason += "; below the evidence needed to call it a new skill"
        ex = unknown[unknown["key"] == k].merge(meta[["month", "employer", "employer_key", "url"]], left_on="ad_id",
                                               right_index=True)
        ex = ex.sort_values("month", ascending=False).drop_duplicates("employer_key").head(3)
        entries[f"cand:{k}"] = {
            "skill_id": f"cand:{k}", "name": best_form.get(k, k), "category": "discovered", "status": status,
            "origin": "discovered", "in_onet": k in onet_all, "aliases_seen": [], "merged_into": None,
            "possible_alias_of": alias_of, "first_seen": str(first_global.get(k, "")),
            "confidence": confidence(int(top.k_recent), int(top.employers), int(top.months_present)),
            "reason": reason,
            "evidence": [{"ad_id": r.ad_id, "month": r.month, "employer": r.employer, "url": r.url,
                          "snippet": _snippet(text.get(r.ad_id, ""), r.surface)} for r in ex.itertuples()]}

    # reviewer decisions win over the rules (mark_deprecated leaves them alone too)
    for sid, e in entries.items():
        o = overrides.get(sid) or overrides.get(T.key(e["name"]))
        if o:
            e["status"], e["reason"] = o["status"], f"reviewer: {o.get('note') or o['status']}"
            if o.get("merged_into"):
                e["merged_into"] = o["merged_into"]
    reg = {"built_at": datetime.now(timezone.utc).isoformat(), "data_version": data_version,
           "last_complete_month": str(last), "thresholds": {"strong": STRONG, "weak": WEAK, "recent_months": RECENT,
                                                            "base_months": BASE, "new_months": NEW_MONTHS},
           "skills": sorted(entries.values(), key=lambda e: e["skill_id"])}
    if versioned:
        reg = _version(reg, prev)
    tracked = {e["skill_id"][5:] for e in entries.values()
               if e["origin"] == "discovered" and e["status"] in ("newly_detected", "under_review")}
    rows = unknown[unknown["key"].isin(tracked)].assign(skill_id=lambda d: "cand:" + d["key"])[["ad_id", "skill_id"]]
    return reg, rows.drop_duplicates()


# Recent skills in the curated vocabulary, withheld for the back-check: could the detector have found them?
WITHHELD = ("llm", "generative_ai", "rag", "langchain", "vector_db", "ai_agents", "mcp", "openai_api",
            "anthropic_claude", "ai_assisted_dev", "prompt_engineering", "llm_evals", "huggingface", "nextjs",
            "fastapi", "svelte")


def backcheck(ads: pd.DataFrame, text: pd.Series, cands: pd.DataFrame, months: list[pd.Period]) -> pd.DataFrame:
    """Replay discovery at past month ends with WITHHELD treated as unknown, using only ads up to that month.
    One row per withheld skill x as-of month: was any of its spellings registered, with what status and evidence."""
    rows = []
    month = ads.set_index("ad_id")["month"]
    for last in months:
        a = ads[pd.PeriodIndex(ads["month"], freq="M") <= last]
        c = cands[pd.PeriodIndex(cands["ad_id"].map(month), freq="M") <= last]
        reg, _ = build_registry(a, text, c, last, "backcheck", withheld=WITHHELD, versioned=False)
        found = {e["skill_id"][5:]: e for e in reg["skills"] if e["origin"] == "discovered"}
        for s in T.curated():
            if s.id not in WITHHELD:
                continue
            hit = next((found[k] for k in sorted(s.keys) if k in found), None)
            rows.append({"skill_id": s.id, "name": s.name, "as_of": str(last), "detected": hit is not None,
                         "status": hit["status"] if hit else None, "term": hit["name"] if hit else None,
                         "first_seen": hit["first_seen"] if hit else None,
                         "confidence": hit["confidence"] if hit else None,
                         "reason": hit["reason"] if hit else None})
    return pd.DataFrame(rows)


SUFFIXES = ("apis", "api", "sdk", "js")


def fold_suffixes(keys: pd.Series, pool: set[str]) -> pd.Series:
    """'reactjs' -> 'react', 'graphqlapi' -> 'graphql' when the shorter form is itself a known or candidate term."""
    def fold(k: str) -> str:
        for s in SUFFIXES:
            if k.endswith(s) and len(k) > len(s) + 2 and k[:-len(s)] in pool:
                return k[:-len(s)]
        return k
    return keys.map(fold)


def mark_deprecated(reg: dict, counts: pd.DataFrame, last: pd.Period, months: int = 24) -> None:
    m = pd.PeriodIndex(counts["month"], freq="M")
    recent = set(counts.loc[(m > last - months) & (counts["n_ads_skill"] > 0), "skill_id"])
    ever = set(counts.loc[counts["n_ads_skill"] > 0, "skill_id"])
    for e in reg["skills"]:
        if e["status"] == "known" and e["skill_id"] in ever and e["skill_id"] not in recent                 and not e["reason"].startswith("reviewer:"):
            e["status"], e["reason"] = "deprecated", f"no ads named it in the last {months} months"


def _near_alias(k: str, known: dict[str, str]) -> str | None:
    if len(k) < 5:
        return None
    for kk, sid in known.items():
        if len(kk) >= 5 and (kk.startswith(k) or k.startswith(kk) or _lev1(k, kk)):
            return sid
    return None


def _lev1(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def _totals(ads: pd.DataFrame, pooled: bool = False) -> pd.DataFrame:
    e = ads[ads["eligible"] & ads["occupations"].ne("") & (ads["source"] == "hn_whoishiring")]
    if pooled:
        e = e.assign(country=ALL, occupation=e["occupations"].str.split("|")).explode("occupation")
    else:
        e = e[e["countries"].ne("")]
        e = e.assign(country=e["countries"].str.split("|"), occupation=e["occupations"].str.split("|"))
        e = e.explode("country").explode("occupation")
    return e.groupby(["month", "country", "occupation"])["ad_id"].nunique().rename("n_ads").reset_index()


def _overrides() -> dict:
    if not store.exists("taxonomy/registry_overrides.csv"):
        return {}
    o = store.read_table("taxonomy/registry_overrides.csv", dtype=str, keep_default_na=False)
    return {r["skill"]: r for r in o.to_dict("records")}


def _version(new: dict, prev: dict) -> dict:
    """Bump the version when any skill's status, name or evidence level changed; archive the previous version."""
    sig = lambda r: {e["skill_id"]: (e["status"], e.get("confidence"), e.get("merged_into")) for e in r.get("skills", [])}
    a, b = sig(prev), sig(new)
    changes = [{"skill_id": k, "from": a.get(k, (None,))[0], "to": b.get(k, (None,))[0]}
               for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    if prev.get("version") and not changes:
        new["version"], new["changes"] = prev["version"], prev.get("changes", [])
        new["previous_version"] = prev.get("previous_version")
        return new
    if prev.get("version"):
        store.write_json(f"taxonomy/registry_history/v{prev['version']}.json", prev)
    new["version"], new["previous_version"] = prev.get("version", 0) + 1, prev.get("version") or None
    new["changes"] = changes[:500]
    return new


def tally(reg: dict) -> dict:
    return dict(Counter(e["status"] for e in reg["skills"]))

