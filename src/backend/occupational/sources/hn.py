"""Hacker News "Ask HN: Who is hiring?" threads: one thread a month since 2011, one top-level comment per hiring
company, full ad text. The only free job-ad text source with real multi-year history, so the skill-demand models
train on it.

Population: tech companies that post on HN (startup-heavy, US-heavy, software-heavy). It is not the whole labour
market; every output says so.
Dates: a post's own created_at is its posting date; it is attributed to its thread's month. A month's thread keeps
collecting posts for weeks, so a month counts as observed (available) from the first day of the next month.
Revisions: comments fetched today reflect later edits and deletions (small; no vintages exist). retrieved_at is kept.
API: hn.algolia.com (public, no key). Raw threads are cached in raw/hn/; a completed month is not fetched again.
"""
from __future__ import annotations

import gzip
import json
import re
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from .. import store, taxonomy as T

SOURCE = "hn_whoishiring"
SEARCH = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1000&page={page}"
ITEM = "https://hn.algolia.com/api/v1/items/{id}"
TITLE = re.compile(r"^Ask HN: Who is hiring\? \(([A-Za-z]+),? (\d{4})\)\s*$")
FIRST_MONTH = pd.Period("2014-01", freq="M")
GAP_S = 0.5


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "occupational-forecasting-research/0.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def list_threads() -> pd.DataFrame:
    hits, page = [], 0
    while True:
        d = _get(SEARCH.format(page=page))
        hits += d["hits"]
        page += 1
        if page >= d.get("nbPages", 1):
            break
    rows = []
    for h in hits:
        m = TITLE.match(h.get("title") or "")
        if m:
            month = pd.Period(f"{m.group(1)[:3]} {m.group(2)}", freq="M")
            rows.append({"thread_id": str(h["objectID"]), "month": str(month), "title": h["title"],
                         "created_at": h["created_at"], "num_comments": h.get("num_comments")})
    t = pd.DataFrame(rows).drop_duplicates("month", keep="first")  # newest first: keep the official repost if any
    return t[pd.PeriodIndex(t["month"], freq="M") >= FIRST_MONTH].sort_values("month").reset_index(drop=True)


def _raw(thread_id: str):
    return store.path("raw", "hn", "items", f"{thread_id}.json.gz")


def fetch(pull: bool = True, now: datetime | None = None) -> dict:
    """Download threads not yet cached, and re-download the current month's (still collecting posts).
    Returns a health record. Without pull, only the cache is used."""
    now = now or datetime.now(timezone.utc)
    log_rel = "raw/hn/threads.csv"
    prev = store.read_table(log_rel, dtype=str) if store.exists(log_rel) else pd.DataFrame(
        columns=["thread_id", "month", "title", "created_at", "num_comments", "retrieved_at"])
    if not pull:
        return {"source": SOURCE, "status": "cache_only" if len(prev) else "missing", "threads": len(prev)}
    try:
        threads = list_threads()
    except Exception as e:  # keep the cache
        return {"source": SOURCE, "status": "fetch_failed", "error": str(e)[:200], "threads": len(prev)}
    done = dict(zip(prev["thread_id"], prev["retrieved_at"]))
    fetched, failed = 0, []
    for t in threads.itertuples():
        complete_after = (pd.Period(t.month, freq="M") + 1).to_timestamp().tz_localize("UTC") + pd.Timedelta(days=7)
        r = done.get(t.thread_id)
        if r and _raw(t.thread_id).exists() and pd.Timestamp(r) >= complete_after:
            continue  # fetched after the month closed: final
        try:
            item = _get(ITEM.format(id=t.thread_id))
        except Exception as e:
            failed.append(f"{t.month}: {str(e)[:80]}")
            continue
        kids = [{"id": c.get("id"), "author": c.get("author"), "created_at": c.get("created_at"),
                 "text": c.get("text")} for c in item.get("children", []) if c.get("parent_id") == item.get("id")]
        p = _raw(t.thread_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(gzip.compress(json.dumps(kids).encode(), mtime=0))
        done[t.thread_id] = now.isoformat()
        fetched += 1
        time.sleep(GAP_S)
    threads["retrieved_at"] = threads["thread_id"].map(done)
    store.write_table(log_rel, threads[threads["retrieved_at"].notna()])
    return {"source": SOURCE, "status": "ok" if not failed else "partial", "threads": int(threads["retrieved_at"].notna().sum()),
            "fetched_now": fetched, "failed": failed[:10]}


def load_ads() -> pd.DataFrame:
    """Every cached post as one raw ad row (not yet classified or deduplicated)."""
    if not store.exists("raw/hn/threads.csv"):
        return pd.DataFrame()
    threads = store.read_table("raw/hn/threads.csv", dtype=str)
    rows = []
    for t in threads.itertuples():
        p = _raw(t.thread_id)
        if not p.exists():
            continue
        for c in json.loads(gzip.decompress(p.read_bytes())):
            text = T.clean_html(c.get("text"))
            header = text.split("\n", 1)[0][:400]
            rows.append({
                "source": SOURCE, "source_id": str(c["id"]), "thread_id": t.thread_id, "month": t.month,
                "posted_at": c.get("created_at"), "retrieved_at": t.retrieved_at, "author": c.get("author") or "",
                "employer": header.split("|", 1)[0].strip()[:120] if "|" in header else "",
                "title_raw": header, "location_raw": header, "text": text,
                "url": f"https://news.ycombinator.com/item?id={c['id']}"})
    return pd.DataFrame(rows)
