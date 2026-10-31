"""Load the US rows of data/processed/signals.csv into Supabase (table from migrations/0025_forecast_signals.sql).

    python pipeline/load_forecast_signals.py              # upsert the rows
    python pipeline/load_forecast_signals.py --dry-run    # parse and validate only, no network

The backend reads this table to retrain the forecast on the data up to a chosen quarter. Needs the SERVICE ROLE key. SUPABASE_URL and SUPABASE_SERVICE_KEY are read from the shell, else from
src/backend/.env (which is not committed).

Adds year_quarter (2026-Q3) and is_tech to each row. Rows are upserted on (series, geo, sector, month), so re-running is
safe; rows that disappear from the CSV are not deleted.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / "data" / "processed" / "signals.csv"
BACKEND_ENV = ROOT / "src" / "backend" / ".env"
BATCH = 500
GEO = "US"  # the only geo the app trains on
SERIES = {"job_postings_index", "ai_postings_share"}
# The Indeed sectors that are tech work; everything else (Accounting, Therapy...) is not. Change this list to change the flag.
TECH_SECTORS = {
    "Software Development",
    "Data & Analytics",
    "IT Infrastructure, Operations & Support",
    "IT Systems & Solutions",
}


def year_quarter(month: str) -> str:
    year, m = month.split("-")
    return f"{year}-Q{(int(m) - 1) // 3 + 1}"


def read_rows() -> list[dict]:
    rows = []
    with open(SIGNALS, encoding="utf-8", newline="") as f:
        for n, raw in enumerate(csv.DictReader(f), start=2):
            if raw["geo"] != GEO or raw["series"] not in SERIES:
                continue
            try:
                rows.append({
                    "series": raw["series"],
                    "geo": raw["geo"],
                    "sector": raw["sector"],
                    "month": raw["month"],
                    "year_quarter": year_quarter(raw["month"]),
                    "value": float(raw["value"]),
                    "source": raw["source"] or None,
                    "source_url": raw["source_url"] or None,
                    "as_of_date": raw["as_of_date"] or None,
                    "is_partial": raw["is_partial"] == "True",
                    "is_carried_forward": raw["is_carried_forward"] == "True",
                    "is_tech": raw["sector"] in TECH_SECTORS,
                })
            except (ValueError, KeyError) as e:
                raise SystemExit(f"signals.csv line {n}: {e}")
    keys = [(r["series"], r["geo"], r["sector"], r["month"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise SystemExit("signals.csv has duplicate (series, geo, sector, month) rows")
    return rows


def env_value(name: str) -> str | None:
    """The setting from the shell, else from src/backend/.env (the file the backend reads)."""
    if os.environ.get(name):
        return os.environ[name]
    if BACKEND_ENV.exists():
        for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"\'') or None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="parse and validate the CSV, do not connect")
    args = ap.parse_args()

    rows = read_rows()
    sectors = {r["sector"] for r in rows if r["sector"]}
    tech = {r["sector"] for r in rows if r["is_tech"]}
    print(f"{len(rows)} rows parsed: {len(sectors)} sectors ({len(tech)} tech), months {min(r['month'] for r in rows)} to {max(r['month'] for r in rows)}")
    missing = TECH_SECTORS - sectors
    if missing:
        print(f"warning: tech sectors not in the data: {sorted(missing)}", file=sys.stderr)
    if args.dry_run:
        return 0

    url, key = env_value("SUPABASE_URL"), env_value("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in src/backend/.env or your shell.", file=sys.stderr)
        return 1
    from supabase import create_client  # imported late so --dry-run needs no dependency

    client = create_client(url, key)
    for i in range(0, len(rows), BATCH):
        client.table("forecast_signals").upsert(rows[i:i + BATCH], on_conflict="series,geo,sector,month").execute()
    print(f"forecast_signals: {len(rows)} rows upserted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
