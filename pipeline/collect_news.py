"""Collect AI-adoption news from the GDELT DOC 2.0 API into data/processed/news_articles.csv (appended).

Usage:
    python pipeline/collect_news.py                 # last 7 days
    python pipeline/collect_news.py --days 14

Only article metadata is stored (URL, title, domain, country, date); GDELT does not return article text.
Each query is one request, spaced QUERY_GAP_S apart (GDELT allows one request every 5 seconds).

Validation before an article is kept:
  * the domain is on the trusted list (news_sources.csv, with a tier); everything else is dropped
  * one row per URL, and one per normalised title + domain within the window (syndicated copies)
The LLM reading of each article happens later, in src/backend/ml/ai_signal_score.py.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "news_articles.csv"
SOURCES = Path(__file__).parent / "news_sources.csv"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERY_GAP_S = 6
RETRIES = 4
BACKOFF_S = 30
MAX_RECORDS = 75
USER_AGENT = "Mozilla/5.0 (sdc-hackathon-2026 data pipeline)"
AI = '("generative AI" OR "artificial intelligence" OR "AI agents" OR "AI tools" OR ChatGPT OR Copilot OR LLM)'
QUERIES = {
    "adoption": f'{AI} (adoption OR rollout OR deploy OR "at work" OR employees OR workforce) sourcelang:english',
    "cost_capability": f'{AI} ("price cut" OR cheaper OR "new model" OR launch OR release) sourcelang:english',
    "regulation": f'{AI} (regulation OR ban OR restrict OR lawsuit OR "AI Act" OR moratorium) sourcelang:english',
    "jobs": f'{AI} (layoffs OR "job cuts" OR hiring OR "replaced by") sourcelang:english',
    "malaysia": f"{AI} sourcecountry:malaysia",
}
COLS = ["url", "title", "domain", "source_country", "seen_date", "query", "tier", "fetched_at"]


def gdelt(query: str, days: int) -> list[dict]:
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": MAX_RECORDS,
              "timespan": f"{days}d", "sort": "datedesc"}
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                body = res.read().decode("utf-8", "replace")
            if body.lstrip().startswith("{"):
                return json.loads(body).get("articles", [])
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
        wait = BACKOFF_S * 2 ** attempt  # throttled: HTTP 429 or the plain-text "limit requests" reply
        print(f"  GDELT throttled (attempt {attempt + 1}), waiting {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"GDELT kept refusing the query: {query[:60]}")


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    tiers = pd.read_csv(SOURCES).set_index("domain")["tier"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows, failed = [], []
    for i, (name, q) in enumerate(QUERIES.items()):
        if i:
            time.sleep(QUERY_GAP_S)
        try:
            arts = gdelt(q, a.days)
        except Exception as e:  # one failed query must not stop the others
            failed.append(name)
            print(f"WARNING: query {name} failed: {e}")
            continue
        for art in arts:
            domain = art.get("domain", "").lower().removeprefix("www.")
            rows.append({"url": art["url"], "title": art.get("title", "").strip(), "domain": domain,
                         "source_country": art.get("sourcecountry", ""),
                         "seen_date": pd.to_datetime(art["seendate"], format="%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d"),
                         "query": name, "tier": tiers.get(domain), "fetched_at": now})
        print(f"  {name}: {len(arts)} articles")
    if len(failed) == len(QUERIES):
        raise SystemExit("every GDELT query failed; news_articles.csv left as it was")
    new = pd.DataFrame(rows, columns=COLS)
    kept = new[new["tier"].notna() & new["title"].ne("")].copy()
    print(f"fetched {len(new)}, from trusted sources {len(kept)}")

    old = pd.read_csv(OUT, dtype=str) if OUT.exists() else pd.DataFrame(columns=COLS)
    allr = pd.concat([old, kept.astype(str)], ignore_index=True).drop_duplicates("url", keep="first")
    allr["_t"] = allr["title"].map(norm_title)
    allr = allr.drop_duplicates(["_t", "domain"], keep="first").drop(columns="_t")
    allr["tier"] = pd.to_numeric(allr["tier"]).astype(int)
    allr.sort_values("seen_date", ascending=False)[COLS].to_csv(OUT, index=False)
    print(f"news_articles.csv: {len(allr)} rows ({len(allr) - len(old)} new)")


if __name__ == "__main__":
    main()
