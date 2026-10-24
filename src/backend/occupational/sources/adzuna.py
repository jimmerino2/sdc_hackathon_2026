"""Adzuna job-ads API: dated snapshots of live ads per country x occupation.

Free tier: 25 calls a day. Calls are counted in data/raw/adzuna/calls_log.csv, the log the earlier collector used,
so all Adzuna use on this machine shares one daily budget (DAILY_BUDGET, 5 spare for retries).
What a snapshot is: the newest live ads (sort_by=date, last 30 days) whose title matches the occupation's search
term, one page of 50 per country x occupation. Description is a ~500-character snippet, so skill counts are lower
than in full ads: never mix these counts with the HN series. The API gives no past ads, so history only exists
from the snapshots saved here; nothing is back-filled.
Also read: responses already cached in data/raw/adzuna/<date>/ by the earlier collector (same API, real ads).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from .. import store, taxonomy as T

SOURCE = "adzuna"
API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
COUNTRIES = ("us", "gb", "ca", "au")
DAILY_BUDGET = 20
CALL_GAP_S = 13  # 5 calls a minute allowed
SHARED_LOG = store.REPO / "data" / "raw" / "adzuna" / "calls_log.csv"
LEGACY_CACHE = store.REPO / "data" / "raw" / "adzuna"
ENV = store.REPO / "src" / "backend" / ".env"


def _keys() -> tuple[str, str] | None:
    env = dict(os.environ)
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    a, b = env.get("ADZUNA_APP_ID", ""), env.get("ADZUNA_APP_KEY", "")
    return (a, b) if a and b else None


def calls_today(day: str) -> int:
    if not SHARED_LOG.exists():
        return 0
    log = pd.read_csv(SHARED_LOG, dtype={"date": str})
    return int(log.loc[log["date"] == day, "calls"].sum())


def _log_call(day: str) -> None:
    SHARED_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = pd.read_csv(SHARED_LOG, dtype={"date": str}) if SHARED_LOG.exists() else pd.DataFrame(columns=["date", "calls"])
    if (log["date"] == day).any():
        log.loc[log["date"] == day, "calls"] += 1
    else:
        log = pd.concat([log, pd.DataFrame([{"date": day, "calls": 1}])], ignore_index=True)
    log.to_csv(SHARED_LOG, index=False)


def collect(max_calls: int = 16, now: datetime | None = None) -> dict:
    """Take today's snapshot for every country x occupation not yet collected today, within the budget."""
    now = now or datetime.now(timezone.utc)
    day = now.date().isoformat()
    keys = _keys()
    if not keys:
        return {"source": SOURCE, "status": "no_credentials", "detail": "ADZUNA_APP_ID / ADZUNA_APP_KEY not set"}
    left = min(max_calls, DAILY_BUDGET - calls_today(day))
    out_dir = store.path("raw", "adzuna", day)
    out_dir.mkdir(parents=True, exist_ok=True)
    made, skipped, errors = 0, 0, []
    for c in COUNTRIES:
        for o in T.occupations():
            params = {"results_per_page": 50, "title_only": o.adzuna_search, "max_days_old": 30, "sort_by": "date"}
            name = hashlib.sha1(json.dumps([c, params], sort_keys=True).encode()).hexdigest()[:16]
            f = out_dir / f"{name}.json"
            if f.exists():
                continue
            if left <= 0:
                skipped += 1
                continue
            url = API.format(country=c) + "?" + urllib.parse.urlencode(
                {"app_id": keys[0], "app_key": keys[1], **params, "content-type": "application/json"})
            if made:
                time.sleep(CALL_GAP_S)
            left -= 1
            made += 1
            _log_call(day)
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.loads(r.read())
            except urllib.error.HTTPError as e:
                errors.append(f"{c}/{o.id}: HTTP {e.code}")
                if e.code in (401, 403):
                    break
                continue
            except Exception as e:
                errors.append(f"{c}/{o.id}: {str(e)[:80]}")
                continue
            data["_query"] = {"country": c, "occupation_search": o.id, **params, "retrieved_at": now.isoformat()}
            f.write_text(json.dumps(data))
    status = "ok" if not errors and not skipped else ("budget_exhausted" if skipped else "partial")
    return {"source": SOURCE, "status": status, "calls_made": made, "pending_for_budget": skipped,
            "errors": errors[:10], "calls_today": calls_today(day), "daily_budget": DAILY_BUDGET}


def _responses():
    """(retrieval date, response) for our snapshots and the earlier collector's cached search responses."""
    for base in (store.path("raw", "adzuna"), LEGACY_CACHE):
        if not base.exists():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            for f in sorted(d.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(data, dict) and data.get("results"):
                    yield d.name, data


def load_ads() -> pd.DataFrame:
    rows = []
    for day, data in _responses():
        for a in data["results"]:
            if "title" not in a or "id" not in a:
                continue
            area = (a.get("location") or {}).get("area") or []
            title = T.clean_html(a.get("title"))
            rows.append({
                "source": SOURCE, "source_id": str(a["id"]), "thread_id": "", "posted_at": a.get("created"),
                "month": a["created"][:7] if a.get("created") else None,
                "retrieved_at": day, "author": "", "employer": ((a.get("company") or {}).get("display_name") or "")[:120],
                "title_raw": title, "location_raw": ", ".join(area), "country_hint": (area[0] if area else "").upper(),
                "text": title + "\n" + T.clean_html(a.get("description")), "url": a.get("redirect_url", "")})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # the same ad seen in several snapshots: keep the first sighting (it was live from then)
    return df.sort_values("retrieved_at").drop_duplicates(["source_id"], keep="first").reset_index(drop=True)
