"""Monthly package downloads (PyPI and npm) for the adoption indicators in taxonomy/skill_signals.json.

  pypi  ClickPy, ClickHouse's public mirror of the PyPI BigQuery download logs, queried read-only over HTTP (one
        query for every package). History from 2016-01 (some early months are incomplete).
  npm   the npm registry's download-counts API, one package at a time in ranges of up to 18 months (its limit).
        History from 2015-12-30.
Cached in raw/packages/monthly.csv (source, package, month, downloads, days, retrieved_at). A month that was
complete when fetched is never fetched again; failures leave the cache as it was and are reported in the health
record. Only complete calendar months are kept; a month with fewer than MIN_DAY_SHARE of its days reported is
marked incomplete and treated as missing downstream, not as zero.
Counts are taken as published today (no vintages): neither source normally revises past days.
"""
from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

import pandas as pd

from .. import store

SOURCE = "packages"
CACHE = "raw/packages/monthly.csv"
CLICKHOUSE = "https://sql-clickhouse.clickhouse.com/?user=demo"
NPM = "https://api.npmjs.org/downloads/range/{start}:{end}/{pkg}"
NPM_START = date(2015, 12, 30)
NPM_GAP_S = 0.4
MIN_DAY_SHARE = 0.8
COLS = ["source", "package", "month", "downloads", "days", "retrieved_at"]


def config() -> dict:
    return store.read_json("taxonomy/skill_signals.json")


def packages(cfg: dict | None = None) -> dict[str, set[str]]:
    """Every package to fetch, per source: the skills' indicators and the reference basket."""
    cfg = cfg or config()
    out = {"pypi": set(cfg["reference"]["pypi"]), "npm": set(cfg["reference"]["npm"])}
    for s in cfg["skills"].values():
        for src in out:
            out[src].update(s.get(src, []))
    return out


TRACKED = "datasets/package_downloads.csv"


def load() -> pd.DataFrame:
    """The raw cache, else the tracked copy the last run published (a fresh clone has no raw/)."""
    for rel in (CACHE, TRACKED):
        if store.exists(rel):
            return store.read_table(rel, dtype={"month": str})
    return pd.DataFrame(columns=COLS)


def _http(url: str, data: bytes | None = None, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "jobee-occupational-forecasting"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _pypi(pkgs: set[str], since: str, now: str) -> pd.DataFrame:
    names = ",".join("'" + p.replace("'", "") + "'" for p in sorted(pkgs))
    q = (f"SELECT project, toStartOfMonth(date) AS m, sum(count) AS downloads, uniqExact(date) AS days "
         f"FROM pypi.pypi_downloads_per_day WHERE project IN ({names}) AND date >= '{since}-01' "
         f"GROUP BY project, m ORDER BY project, m FORMAT CSVWithNames")
    df = pd.read_csv(io.BytesIO(_http(CLICKHOUSE, q.encode(), timeout=120)))
    df["month"] = df["m"].str[:7]
    return df.rename(columns={"project": "package"}).assign(source="pypi", retrieved_at=now)[COLS]


def _npm(pkg: str, since: date, until: date, now: str) -> pd.DataFrame:
    rows = []
    start = since
    while start <= until:
        end = min(until, date(start.year + (start.month + 17) // 12, (start.month + 17) % 12 + 1, 1) - pd.Timedelta(days=1))
        url = NPM.format(start=start.isoformat(), end=end.isoformat(), pkg=urllib.parse.quote(pkg, safe="@/"))
        for attempt in range(2):
            try:
                rows += json.loads(_http(url)).get("downloads", [])
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and not attempt:
                    time.sleep(30)
                    continue
                raise
        time.sleep(NPM_GAP_S)
        start = end + pd.Timedelta(days=1)
    if not rows:
        return pd.DataFrame(columns=COLS)
    d = pd.DataFrame(rows)
    d["month"] = d["day"].str[:7]
    g = d.groupby("month").agg(downloads=("downloads", "sum"), days=("day", "nunique")).reset_index()
    return g.assign(source="npm", package=pkg, retrieved_at=now)[COLS]


def fetch(pull: bool = True) -> dict:
    """Bring the cache up to the last complete month. Returns a health record."""
    cache = load()
    want = packages()
    today = datetime.now(timezone.utc).date()
    last = (pd.Period(today, "M") - 1)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    failed, fetched = [], {"pypi": 0, "npm": 0}
    if pull:
        for src in ("pypi", "npm"):
            have = cache[cache["source"] == src]
            done = have.groupby("package")["month"].max().to_dict()
            todo = {p for p in want[src] if done.get(p, "") < str(last)}
            if not todo:
                continue
            try:
                if src == "pypi":
                    since = min((done.get(p) or "2015-12") for p in todo)
                    new = _pypi(todo, since, now)
                    fetched["pypi"] = new["package"].nunique()
                    cache = _merge(cache, new[new["month"] <= str(last)])
                else:
                    for p in sorted(todo):
                        try:
                            since = (pd.Period(done[p], "M") + 1).start_time.date() if p in done else NPM_START
                            new = _npm(p, since, last.end_time.date(), now)
                            cache = _merge(cache, new[new["month"] <= str(last)])
                            fetched["npm"] += 1
                        except Exception as e:
                            failed.append(f"npm {p}: {str(e)[:80]}")
            except Exception as e:
                failed.append(f"{src}: {str(e)[:120]}")
        store.write_table(CACHE, cache, allow_empty=True)
    have = {src: sorted(set(cache.loc[cache["source"] == src, "package"])) for src in ("pypi", "npm")}
    missing = {src: sorted(want[src] - set(have[src])) for src in want}
    latest = cache["month"].max() if len(cache) else None
    return {"source": SOURCE, "status": "ok" if not failed and latest == str(last) else
            ("partial" if len(cache) else "missing"),
            "latest_month": latest, "fetched_packages": fetched, "failed": failed[:20], "missing_packages": missing}


def _merge(cache: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if new.empty:
        return cache
    k = ["source", "package", "month"]
    out = pd.concat([cache[~cache.set_index(k).index.isin(new.set_index(k).index)], new], ignore_index=True)
    return out.sort_values(k).reset_index(drop=True)


def monthly(cache: pd.DataFrame | None = None) -> pd.DataFrame:
    """Complete months only: source, package, month, downloads (incomplete months dropped, i.e. missing)."""
    c = load() if cache is None else cache
    if c.empty:
        return c
    dim = pd.PeriodIndex(c["month"], freq="M").days_in_month
    return c[c["days"] >= MIN_DAY_SHARE * dim].reset_index(drop=True)
