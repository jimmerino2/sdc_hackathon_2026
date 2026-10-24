"""Real-Time Population Survey: % of employed US adults using generative AI for their job, per SOC major group,
quarterly (Bick, Blandin & Deming, via FRED). Target worker_genai_use_rate (occupation adoption).

This measures *workers*, by occupation group, directly. It is the only occupation-level adoption evidence in the
platform; BTOS (firms) is never used in its place.

Point in time, two ways:
  alfred    with FRED_API_KEY set, every published vintage of every series comes from ALFRED, and a value is
            available from its vintage's realtime_start
  assumed   without a key, the current values only, each assumed available 21 days after its quarter ends (the
            2026-Q3 value was already on FRED on 2026-10-22). Revisions are unknown, so origins built this way are
            labelled "current_only". Every download is kept under raw/rps/snapshots/<date>/, so real vintages build
            up from now on even without a key.

Raw    data/raw/rps/fred/*.csv (latest), data/raw/rps/snapshots/<date>/
Output data/processed/forecasting/rps_observations.csv   (columns in data/documentation/STRUCTURE.md section 11)

Usage:
    python -m forecasting.rps             # download (ALFRED if FRED_API_KEY is set), rebuild
    python -m forecasting.rps --no-pull
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
from pathlib import Path

import pandas as pd

from .vintages import OUT, ROOT

RAW = ROOT / "data" / "raw" / "rps"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
ALFRED_API = ("https://api.stlouisfed.org/fred/series/observations?series_id={}&realtime_start=1776-07-04"
              "&realtime_end=9999-12-31&file_type=json&api_key={}")
# FRED series number -> 2018 SOC major group, in the order of the FRED release (checked against the series titles
# in pipeline/build_ai_adoption.py on feat/ai-adoption-mc; reused as is).
MAJORS = ["11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31",
          "33", "35", "37", "39", "41", "43", "45", "47", "49", "51", "53"]
SERIES = {f"RPSGENAIUSAGESHAREOCC{i}": m for i, m in enumerate(MAJORS, start=1)} | {"RPSGENAIUSAGESHAREWORK": "00"}
NAMES = {"00": "All workers", "11": "Management", "13": "Business and financial operations",
         "15": "Computer and mathematical", "17": "Architecture and engineering",
         "19": "Life, physical and social science", "21": "Community and social service", "23": "Legal",
         "25": "Educational instruction and library", "27": "Arts, design, entertainment, sports and media",
         "29": "Healthcare practitioners and technical", "31": "Healthcare support", "33": "Protective service",
         "35": "Food preparation and serving", "37": "Building and grounds cleaning and maintenance",
         "39": "Personal care and service", "41": "Sales and related", "43": "Office and administrative support",
         "45": "Farming, fishing and forestry", "47": "Construction and extraction",
         "49": "Installation, maintenance and repair", "51": "Production", "53": "Transportation and material moving"}
ASSUMED_LAG = pd.Timedelta(days=21)  # after quarter end, when no ALFRED vintage dates are available
COLUMNS = ["series_id", "unit", "unit_name", "quarter", "value_pct", "available_at", "availability_basis",
           "fetched_at", "source_file"]


ENV_FILE = ROOT / "src" / "backend" / ".env"


def fred_key() -> str | None:
    """FRED_API_KEY from the environment, else from src/backend/.env (gitignored). Never printed or logged."""
    if os.environ.get("FRED_API_KEY"):
        return os.environ["FRED_API_KEY"].strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip().removeprefix("export ").strip() == "FRED_API_KEY":
                return value.strip().strip('"').strip("'") or None
    return None


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sdc-hackathon-2026 pipeline)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def pull() -> None:
    """Download every series (and ALFRED vintages with a key). Failures keep the previous files."""
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    snap = RAW / "snapshots" / stamp
    snap.mkdir(parents=True, exist_ok=True)
    (RAW / "fred").mkdir(parents=True, exist_ok=True)
    key = fred_key()
    for sid in SERIES:
        try:
            body = _get(FRED_CSV.format(sid))
            (snap / f"{sid}.csv").write_bytes(body)
            tmp = RAW / "fred" / f".{sid}.tmp"
            tmp.write_bytes(body)
            tmp.replace(RAW / "fred" / f"{sid}.csv")
            if key:
                (snap / f"{sid}.alfred.json").write_bytes(_get(ALFRED_API.format(sid, key)))
        except OSError as e:
            print(f"warning: could not download {sid} ({e}); keeping the previous file")


def snapshot_existing() -> None:
    """Keep a dated copy of files downloaded before snapshots existed (dated by modification time)."""
    for f in (RAW / "fred").glob("RPS*.csv"):
        stamp = pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC").strftime("%Y-%m-%d")
        dst = RAW / "snapshots" / stamp / f.name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)


def parse_alfred(sid: str, payload: dict, source: str, fetched_at: pd.Timestamp) -> pd.DataFrame:
    """ALFRED observations -> one row per (quarter, vintage). "." (no value in that vintage) is skipped, not 0."""
    rows = [{"series_id": sid, "quarter": pd.Period(o["date"], freq="Q"), "value_pct": float(o["value"]),
             "available_at": pd.Timestamp(o["realtime_start"], tz="UTC"), "availability_basis": "alfred",
             "fetched_at": fetched_at, "source_file": source}
            for o in payload["observations"] if o["value"] != "."]
    return pd.DataFrame(rows)


def parse_csv(sid: str, path: Path, fetched_at: pd.Timestamp) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d[pd.to_numeric(d[sid], errors="coerce").notna()]
    q = pd.PeriodIndex(pd.to_datetime(d["observation_date"]), freq="Q")
    return pd.DataFrame({"series_id": sid, "quarter": q, "value_pct": d[sid].astype(float).to_numpy(),
                         "available_at": (q.end_time.normalize() + ASSUMED_LAG).tz_localize("UTC"),
                         "availability_basis": "assumed", "fetched_at": fetched_at, "source_file": path.name})


def build() -> pd.DataFrame:
    parts = []
    snaps = sorted((RAW / "snapshots").glob("*")) if (RAW / "snapshots").exists() else []
    alfred = {f.name.split(".")[0]: f for s in snaps for f in s.glob("*.alfred.json")}  # latest snapshot wins
    for sid in SERIES:
        if sid in alfred:
            f = alfred[sid]
            fetched = pd.Timestamp(f.parent.name, tz="UTC")
            parts.append(parse_alfred(sid, json.loads(f.read_text()), f"snapshots/{f.parent.name}/{f.name}", fetched))
            continue
        f = RAW / "fred" / f"{sid}.csv"
        if f.exists():
            parts.append(parse_csv(sid, f, pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC").floor("s")))
    d = pd.concat(parts, ignore_index=True)
    d["unit"] = d["series_id"].map(SERIES)
    d["unit_name"] = d["unit"].map(NAMES)
    # A value is never available before we could have fetched it if the date is only assumed and lies in the future
    d["available_at"] = d[["available_at", "fetched_at"]].min(axis=1).where(
        d["availability_basis"] == "assumed", d["available_at"])
    return d[COLUMNS].sort_values(["unit", "quarter", "available_at"]).reset_index(drop=True)


def validate(d: pd.DataFrame) -> None:
    if d.duplicated(["series_id", "quarter", "available_at"]).any():
        raise ValueError("duplicate RPS observations")
    if not d["value_pct"].between(0, 100).all():
        raise ValueError("RPS value outside 0-100")
    if set(d["unit"]) != set(SERIES.values()):
        raise ValueError(f"RPS series missing: {set(SERIES.values()) - set(d['unit'])}")


def load() -> pd.DataFrame:
    d = pd.read_csv(OUT / "rps_observations.csv", dtype={"unit": str})
    d["quarter"] = pd.PeriodIndex(d["quarter"], freq="Q")
    for c in ("available_at", "fetched_at"):
        d[c] = pd.to_datetime(d[c], utc=True, format="ISO8601")
    return d


def ingest(pull_first: bool) -> None:
    snapshot_existing()
    if pull_first:
        pull()
    d = build()
    validate(d)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / ".rps_observations.csv.tmp"
    d.to_csv(tmp, index=False)
    tmp.replace(OUT / "rps_observations.csv")
    print(f"rps: {len(d):,} rows, {d['unit'].nunique()} groups, quarters {d['quarter'].min()}..{d['quarter'].max()}, "
          f"basis {d['availability_basis'].value_counts().to_dict()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ingest(not ap.parse_args().no_pull)


if __name__ == "__main__":
    main()
