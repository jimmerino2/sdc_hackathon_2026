"""Weekly Adzuna snapshot: share of live ads mentioning AI per category, and ad counts for each job's skills.

Usage (free tier, 25 calls a day: all runs together stay within DAILY_BUDGET calls per day):
    python pipeline/collect_adzuna.py --check       # 1 call: are the keys working?
    python pipeline/collect_adzuna.py               # weekly: AI share for 22 US categories (22 calls, plus 22
                                                    #   every 4 weeks to refresh category totals); a week that
                                                    #   needs more than the day's budget finishes the next day
    python pipeline/collect_adzuna.py --skills      # monthly: also 1 software tool per job (46 calls, over 3 days)

Keys: ADZUNA_APP_ID and ADZUNA_APP_KEY from the environment or src/backend/.env (never commit them).
Adzuna has no Malaysia site, so these are signals from the countries chosen, not Malaysian demand.

Each call asks for one result page and reads the total `count` of matching live ads:
  data/processed/adzuna_ai_share.csv  week x country x category: total_ads, ai_ads, ai_share
                                      (feeds the structured part of ml/ai_signal_score.py once 6+ weeks exist)
  data/processed/skill_demand.csv     week x country x job x skill: ads, share of the category's ads
How calls are saved:
  * data/raw/adzuna/calls_log.csv counts calls per day across runs; a run stops at DAILY_BUDGET for the day.
  * A run skips categories (and skills) already collected this week, so rerunning the next day resumes.
  * Category totals change slowly: reused for TOTALS_MAX_AGE_DAYS before being fetched again.
  * The category list is kept for 30 days; a query already made today is read from data/raw/adzuna/<date>/.
AI share is fetched before skills; skills (only with --skills) use what is left of the day's budget.
Categories come from adzuna_category_map.csv; skills are each job's top software tools and skill phrases
from onet_role_skills.csv, searched as exact phrases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "adzuna"
ENV = ROOT / "src" / "backend" / ".env"
API = "https://api.adzuna.com/v1/api/jobs/{country}/{endpoint}"
CALL_GAP_S = 2.5  # stay well under Adzuna's per-minute limit
DAILY_BUDGET = 20  # free tier allows 25 a day; keep 5 spare for --check and retries
TOTALS_MAX_AGE_DAYS = 28
CATEGORIES_MAX_AGE_DAYS = 30
CALLS_LOG = RAW / "calls_log.csv"
AI_TERMS = "ai llm chatgpt copilot genai openai"  # what_or: any of these words
SKILLS_PER_JOB = {"tech": 1, "skill": 0}  # free tier: one software tool per job
MIN_SKILL_LEN = 3  # "C", "R" are not searchable as keywords


class AdzunaError(RuntimeError):
    pass


def keys() -> tuple[str, str]:
    env = dict(os.environ)
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    app_id, app_key = env.get("ADZUNA_APP_ID", ""), env.get("ADZUNA_APP_KEY", "")
    if not (app_id and app_key):
        raise SystemExit("ADZUNA_APP_ID / ADZUNA_APP_KEY are not set (environment or src/backend/.env)")
    return app_id, app_key


def calls_today(day: str) -> int:
    if not CALLS_LOG.exists():
        return 0
    log = pd.read_csv(CALLS_LOG, dtype={"date": str})
    return int(log.loc[log.date == day, "calls"].sum())


def log_call(day: str) -> None:
    log = pd.read_csv(CALLS_LOG, dtype={"date": str}) if CALLS_LOG.exists() else pd.DataFrame(columns=["date", "calls"])
    if (log.date == day).any():
        log.loc[log.date == day, "calls"] += 1
    else:
        log = pd.concat([log, pd.DataFrame([{"date": day, "calls": 1}])], ignore_index=True)
    log.to_csv(CALLS_LOG, index=False)


class Client:
    def __init__(self, app_id: str, app_key: str, daily_budget: int, day: str):
        self.auth, self.day, self.calls = {"app_id": app_id, "app_key": app_key}, day, 0
        self.left = daily_budget - calls_today(day)  # earlier runs today count too
        self.cache = RAW / day
        self.cache.mkdir(parents=True, exist_ok=True)

    def get(self, country: str, endpoint: str, **params) -> dict:
        key = hashlib.sha1(json.dumps([country, endpoint, params], sort_keys=True).encode()).hexdigest()[:16]
        cached = self.cache / f"{key}.json"
        if cached.exists():  # same query today: no call spent
            return json.loads(cached.read_text())
        if self.left <= 0:
            raise AdzunaError("the day's call budget is used up; rerun tomorrow to continue")
        url = API.format(country=country, endpoint=endpoint) + "?" + urllib.parse.urlencode(
            {**self.auth, **params, "content-type": "application/json"})
        for attempt in range(3):
            if self.calls:
                time.sleep(CALL_GAP_S * (attempt + 1))
            self.calls += 1
            self.left -= 1
            log_call(self.day)
            try:
                with urllib.request.urlopen(url, timeout=60) as res:
                    data = json.loads(res.read())
                cached.write_text(json.dumps(data))
                return data
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise SystemExit(f"Adzuna rejected the keys ({e.code}); check ADZUNA_APP_ID / ADZUNA_APP_KEY")
                if e.code != 429 and e.code < 500:
                    raise AdzunaError(f"{e.code} for {endpoint} {params}")
                print(f"  Adzuna {e.code}, retrying")
        raise AdzunaError(f"gave up on {endpoint} {params}")

    def count(self, country: str, **params) -> int:
        return int(self.get(country, "search/1", results_per_page=1, **params).get("count", 0))


def skill_terms(n_tech: int, n_skill: int) -> pd.DataFrame:
    """Each job's top software tools and skill phrases, as search terms."""
    s = pd.read_csv(PROCESSED / "onet_role_skills.csv").dropna(subset=["skill_name", "importance"])
    s["term"] = s["skill_name"].str.replace(r"\s+software$", "", regex=True).str.strip()
    s = s[s["term"].str.len() >= MIN_SKILL_LEN].sort_values("importance", ascending=False)
    parts = [s[s.skill_type == t].groupby("onet_code").head(n) for t, n in (("tech", n_tech), ("skill", n_skill))]
    return pd.concat(parts)[["onet_code", "term"]].drop_duplicates()


def upsert(path: Path, rows: pd.DataFrame, keys: list[str]) -> None:
    """Add rows, replacing any existing row with the same keys (so a week can be filled over several days)."""
    old = pd.read_csv(path, dtype={"onet_code": str}) if path.exists() else pd.DataFrame()
    pd.concat([old, rows], ignore_index=True).drop_duplicates(keys, keep="last").to_csv(path, index=False)


def categories(client: "Client", country: str) -> set[str]:
    """Category tags of a country's site, kept on disk for CATEGORIES_MAX_AGE_DAYS."""
    path = RAW / f"categories_{country}.json"
    if path.exists() and (time.time() - path.stat().st_mtime) < CATEGORIES_MAX_AGE_DAYS * 86400:
        return set(json.loads(path.read_text()))
    tags = sorted(r["tag"] for r in client.get(country, "categories").get("results", []))
    path.write_text(json.dumps(tags))
    return set(tags)


def recent_totals(today: date) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], str]]:
    """Latest total_ads per (country, category) fetched within TOTALS_MAX_AGE_DAYS, and when it was fetched."""
    path = PROCESSED / "adzuna_ai_share.csv"
    if not path.exists():
        return {}, {}
    d = pd.read_csv(path)
    if "totals_fetched_at" not in d:
        d["totals_fetched_at"] = d["fetched_at"]
    d["totals_fetched_at"] = d["totals_fetched_at"].fillna(d["fetched_at"])
    d = d[pd.to_datetime(d.totals_fetched_at).dt.date >= today - timedelta(days=TOTALS_MAX_AGE_DAYS)]
    d = d.sort_values("week").drop_duplicates(["country", "category"], keep="last")
    keys = list(zip(d.country, d.category))
    return dict(zip(keys, d.total_ads.astype(int))), dict(zip(keys, d.totals_fetched_at))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="us", help="comma-separated Adzuna country codes")
    ap.add_argument("--daily-budget", type=int, default=DAILY_BUDGET, help="max calls per day, all runs together")
    ap.add_argument("--skills", action="store_true", help="also count each job's skills (monthly)")
    ap.add_argument("--check", action="store_true", help="one test call per country, then stop")
    a = ap.parse_args()
    today = date.today()
    y, w, _ = today.isocalendar()
    week = f"{y}-W{w:02d}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    countries = [c.strip().lower() for c in a.countries.split(",") if c.strip()]
    client = Client(*keys(), a.daily_budget, today.isoformat())
    print(f"calls left today: {max(client.left, 0)} of {a.daily_budget}")

    if a.check:
        for c in countries:
            print(f"{c}: {client.count(c):,} live ads")
        return

    cmap = pd.read_csv(Path(__file__).parent / "adzuna_category_map.csv", dtype={"soc_major": str})
    share_path = PROCESSED / "adzuna_ai_share.csv"
    prev = pd.read_csv(share_path) if share_path.exists() else pd.DataFrame(columns=["week", "country", "category"])
    done = set(zip(prev.loc[prev.week == week, "country"], prev.loc[prev.week == week, "category"]))
    totals, totals_at = recent_totals(today)
    ai_rows, stopped = [], False
    for c in countries:
        try:
            tags = categories(client, c)
        except AdzunaError as e:
            print(f"  stopped before {c}: {e}")
            stopped = True
            break
        for cat in sorted(set(cmap.category) & tags):
            if (c, cat) in done:
                continue
            try:
                if (c, cat) not in totals:
                    totals[(c, cat)], totals_at[(c, cat)] = client.count(c, category=cat), now
                ai = client.count(c, category=cat, what_or=AI_TERMS)
            except AdzunaError as e:
                print(f"  stopped AI share at {c}/{cat}: {e}")
                stopped = True
                break
            total = totals[(c, cat)]
            ai_rows.append({"week": week, "country": c, "category": cat, "total_ads": total, "ai_ads": ai,
                            "ai_share": round(ai / total, 5) if total else None, "fetched_at": now,
                            "totals_fetched_at": totals_at[(c, cat)]})
        if stopped:
            break
    if ai_rows:
        upsert(share_path, pd.DataFrame(ai_rows), ["week", "country", "category"])
    todo = len(set(cmap.category)) * len(countries) - len(done) - len(ai_rows)
    print(f"week {week}: {len(ai_rows)} category AI shares added, {max(todo, 0)} still to do this week")

    if a.skills and not stopped:
        roles = pd.read_csv(PROCESSED / "onet_roles.csv", dtype=str)[["onet_code", "title"]]
        main_cat = cmap.sort_values("weight", ascending=False).drop_duplicates("soc_major").set_index("soc_major")["category"]
        terms = skill_terms(SKILLS_PER_JOB["tech"], SKILLS_PER_JOB["skill"]).merge(roles, on="onet_code")
        terms["category"] = terms["onet_code"].str[:2].map(main_cat)
        skill_path = PROCESSED / "skill_demand.csv"
        sd = pd.read_csv(skill_path, dtype={"onet_code": str}) if skill_path.exists() else pd.DataFrame(columns=["week", "country", "onet_code", "skill"])
        this = sd[sd.week == week]
        sdone = set(zip(this.country, this.onet_code, this.skill))
        tasks = [(c, r) for c in countries for r in terms.dropna(subset=["category"]).itertuples()
                 if (c, r.category) in totals and (c, r.onet_code, r.term) not in sdone]
        skill_rows = []
        for c, r in tasks:
            try:
                ads = client.count(c, category=r.category, what_phrase=r.term.lower())
            except AdzunaError as e:
                print(f"  stopped skills: {e}")
                break
            total = totals[(c, r.category)]
            skill_rows.append({"week": week, "country": c, "onet_code": r.onet_code, "title": r.title,
                               "category": r.category, "skill": r.term, "ads": ads,
                               "share": round(ads / total, 5) if total else 0.0, "fetched_at": now})
        if skill_rows:
            upsert(skill_path, pd.DataFrame(skill_rows), ["week", "country", "onet_code", "skill"])
        print(f"skills: {len(skill_rows)} added, {len(tasks) - len(skill_rows)} still to do this week")
    print(f"{client.calls} API calls this run; {max(client.left, 0)} left today")


if __name__ == "__main__":
    main()
