"""Occupations, countries and the skill vocabulary, and the text rules that apply them.

Inputs (hand-written, in data/occupational_forecasting/taxonomy/):
  occupations.json     sector -> occupation, title patterns, O*NET codes, Adzuna search, SO survey dev types
  geo.json             country patterns for location text
  curated_skills.csv   seed vocabulary: skill_id, name, category, patterns (case-insensitive), cs_patterns
                       (case-sensitive), each a ';;'-separated list of regexes
O*NET 31.0 software_skills.csv (raw/onet/) says which skills O*NET already covers: per occupation and overall.
The vocabulary is a starting point, not a limit: emerging.py adds skills found in ad text.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from . import store

# A term's edges: not glued to a letter or digit on either side (so 'java' does not match 'javascript').
_L, _R = r"(?<![A-Za-z0-9])", r"(?![A-Za-z0-9])"


@dataclass(frozen=True)
class Occupation:
    id: str
    name: str
    sector_id: str
    sector_name: str
    onet_codes: tuple[str, ...]
    onet_note: str
    title_re: re.Pattern
    header_only_re: re.Pattern | None
    adzuna_search: str
    so_devtypes: dict
    so_note: str = ""


@dataclass
class Skill:
    id: str
    name: str
    category: str
    regex: re.Pattern | None
    cs_regex: re.Pattern | None
    origin: str = "curated"
    keys: set[str] = field(default_factory=set)

    def find(self, text: str) -> bool:
        return bool((self.regex and self.regex.search(text)) or (self.cs_regex and self.cs_regex.search(text)))


def _alt(parts: list[str], flags=0) -> re.Pattern | None:
    parts = [p.strip() for p in parts if p.strip()]
    return re.compile(_L + "(?:" + "|".join(f"(?:{p})" for p in parts) + ")" + _R, flags) if parts else None


@lru_cache(maxsize=1)
def _occ_json() -> dict:
    return store.read_json("taxonomy/occupations.json")


def occupations() -> list[Occupation]:
    out = []
    for sec in _occ_json()["sectors"]:
        for o in sec["occupations"]:
            out.append(Occupation(
                o["id"], o["name"], sec["id"], sec["name"], tuple(o["onet_codes"]), o.get("onet_note", ""),
                _alt(o["title_patterns"], re.I), _alt(o.get("title_patterns_header_only", []), re.I),
                o["adzuna_search"], o.get("so_devtypes", {}), o.get("so_note", "")))
    return out


def taxonomy_version() -> str:
    return _occ_json()["version"]


@lru_cache(maxsize=1)
def countries() -> dict[str, dict]:
    g = store.read_json("taxonomy/geo.json")["countries"]
    return {c: {"name": v["name"], "re": re.compile("|".join(f"(?:{p})" for p in v["patterns"]))} for c, v in g.items()}


def countries_in(location: str) -> list[str]:
    return [c for c, v in countries().items() if v["re"].search(location)]


def occupations_in(header: str, body: str = "") -> list[str]:
    """Occupations named as job titles: anywhere in the header; in the body only in the singular form (so 'work with
    our data scientists' in a software post does not count)."""
    out = []
    for o in occupations():
        if o.title_re.search(header) or (o.header_only_re and o.header_only_re.search(header)) or \
                (body and o.title_re.search(body) and _singular_in(o, body)):
            out.append(o.id)
    return out


def _singular_in(o: Occupation, body: str) -> bool:
    return any(not m.group(0).lower().endswith("s") for m in o.title_re.finditer(body))


# ---------- text ----------

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def clean_html(s: str | None) -> str:
    """HN/Adzuna HTML to plain text; paragraph tags become newlines."""
    if not s:
        return ""
    s = re.sub(r"<p>|<br\s*/?>|</li>", "\n", s, flags=re.I)
    s = html.unescape(_TAG.sub(" ", s))
    s = s.replace("…", "...").replace("�", " ")
    return "\n".join(_WS.sub(" ", line).strip() for line in s.split("\n")).strip()


def key(term: str) -> str:
    """Normalised form used to merge spellings: 'Next.js', 'NextJS', 'next js' -> 'nextjs'; 'Agents' -> 'agent'."""
    k = re.sub(r"[\s.\-_/]+", "", term.lower())
    if len(k) > 4 and k.endswith("s") and not k.endswith(("ss", "us", "is", "js", "os", "as")):
        k = k[:-1]
    return k


# ---------- skills ----------

@lru_cache(maxsize=1)
def curated() -> list[Skill]:
    df = store.read_table("taxonomy/curated_skills.csv", dtype=str, keep_default_na=False)
    out = []
    for r in df.itertuples():
        ci, cs = r.patterns.split(";;") if r.patterns else [], r.cs_patterns.split(";;") if r.cs_patterns else []
        s = Skill(r.skill_id, r.name, r.category, _alt(ci, re.I), _alt(cs))
        s.keys = {key(r.name), key(r.skill_id)} | {k for p in ci + cs for k in literal_keys(p)}
        out.append(s)
    return out


def _strip_lookarounds(p: str) -> str:
    out, i = [], 0
    while i < len(p):
        if p.startswith(("(?=", "(?!", "(?<=", "(?<!"), i):
            depth, j, in_class = 0, i, False
            while j < len(p):
                ch = p[j]
                if ch == "\\":
                    j += 2
                    continue
                if in_class:
                    in_class = ch != "]"
                elif ch == "[":
                    in_class = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            i = j + 1
            continue
        out.append(p[i])
        i += 1
    return "".join(out)


def literal_keys(pattern: str, limit: int = 32) -> set[str]:
    r"""Plain spellings a pattern stands for, for alias matching: 'postgres(ql)?' -> postgres, postgresql;
    'react(\.js|js)?' -> react, reactjs; 'hugging ?face' -> huggingface; '\bml\b' -> ml. Lookarounds are dropped;
    patterns too complex to expand give nothing."""
    p = _strip_lookarounds(pattern).replace(r"\b", "")
    p = re.sub(r"\[([^\]])[^\]]*\]", r"\1", p)  # a character class -> its first character
    variants = [""]
    for tok in re.findall(r"\(([^()]*)\)(\?)?|(\\.|.)(\?)?", p):
        group, gopt, ch, copt = tok
        if group or gopt:
            opts = group.split("|") + ([""] if gopt else [])
        else:
            opts = [ch.lstrip("\\")] + ([""] if copt else [])
        variants = [v + o for v in variants for o in opts][:limit]
    return {key(v) for v in variants if v and re.fullmatch(r"[\w .+#/-]+", v)}


def _onet_name_keys(name: str) -> set[str]:
    """Keys an O*NET software example covers: the name without 'software', and acronyms/words in it."""
    base = re.sub(r"\b(software|platform|programming language|language|framework)\b", "", name, flags=re.I).strip()
    out = {key(base)} if base else set()
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", base):
        if (tok.isupper() and len(tok) >= 2) or re.search(r"[a-z][A-Z]|[0-9+#.]", tok):
            out.add(key(tok))
    return {k for k in out if k}


@lru_cache(maxsize=1)
def onet_software() -> pd.DataFrame:
    """O*NET 31.0 software skills (raw/onet/software_skills.csv) with the keys each example covers."""
    p = store.path("raw", "onet", "software_skills.csv")
    if not p.exists():
        return pd.DataFrame(columns=["onet_code", "example", "hot", "in_demand", "keys"])
    d = pd.read_csv(p, dtype=str)
    d = d.rename(columns={"O*NET-SOC Code": "onet_code", "Workplace Example": "example", "Hot Technology": "hot",
                          "In Demand": "in_demand"})
    d["keys"] = d["example"].map(_onet_name_keys)
    return d[["onet_code", "example", "hot", "in_demand", "keys"]]


def onet_keys(codes: tuple[str, ...] | None = None) -> set[str]:
    d = onet_software()
    if codes is not None:
        d = d[d["onet_code"].isin(codes)]
    return set().union(*d["keys"]) if len(d) else set()


def in_onet(skill_keys: set[str], codes: tuple[str, ...] | None = None) -> bool:
    return bool(skill_keys & onet_keys(codes))


def match_skills(text: str, skills: list[Skill] | None = None) -> list[str]:
    return [s.id for s in (skills or curated()) if s.find(text)]


def onet_available() -> bool:
    return store.path("raw", "onet", "software_skills.csv").exists()


def save_onet(files: dict[str, bytes]) -> None:
    for name, data in files.items():
        p = store.path("raw", "onet", name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    onet_software.cache_clear()


def describe() -> dict:
    """Taxonomy summary for the API."""
    return {"version": taxonomy_version(),
            "sectors": [{"id": s["id"], "name": s["name"], "occupations": [
                {"id": o["id"], "name": o["name"], "onet_codes": o["onet_codes"], "onet_note": o.get("onet_note", "")}
                for o in s["occupations"]]} for s in _occ_json()["sectors"]],
            "countries": {c: v["name"] for c, v in countries().items()},
            "curated_skills": len(curated()), "onet_release": "O*NET 31.0" if onet_available() else None}


def reset_caches() -> None:
    for f in (_occ_json, countries, curated, onet_software):
        f.cache_clear()

