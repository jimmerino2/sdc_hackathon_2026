"""Load data/processed/*.csv into Supabase (tables from migrations/0001_initial_schema.sql).

    python pipeline/load_supabase.py              # upsert every table
    python pipeline/load_supabase.py --dry-run    # parse and validate only, no network
    python pipeline/load_supabase.py --tables onet_roles crosswalk

Needs the SERVICE ROLE key (the anon/publishable key is read-only by design):
    SUPABASE_URL            falls back to src/backend/.env
    SUPABASE_SERVICE_KEY    set in your shell only, never commit it

Rows are upserted on each table's primary key, so re-running is safe. Rows that
disappear from a CSV are NOT deleted; truncate the table first if you need that.
Blank CSV cells are loaded as NULL. Tables load in foreign-key order.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
BACKEND_ENV = ROOT / "src" / "backend" / ".env"
BATCH = 500

# table -> (primary key, int columns, float columns, bool columns, smallint columns)
# Everything not listed stays text/date, which PostgREST casts from ISO strings.
TABLES: dict[str, dict] = {
    "onet_roles": dict(key=["onet_code"], int=["job_zone"]),
    "onet_role_skills": dict(key=["onet_code", "skill_id"], float=["importance", "level"]),
    "ai_exposure": dict(key=["onet_code"], float=["exposure", "automation_share", "augmentation_share"]),
    "ai_exposure_detail": dict(key=["onet_code"], bool=["low_sample"], float=[
        "pct_claude_ai", "collaboration_bucket_automation_pct_claude_ai",
        "collaboration_bucket_augmentation_pct_claude_ai", "use_case_work_pct_claude_ai",
        "ai_autonomy_mean_claude_ai", "pct_api", "collaboration_bucket_automation_pct_api",
        "collaboration_bucket_augmentation_pct_api", "use_case_work_pct_api", "ai_autonomy_mean_api",
        "work_pct_claude_ai", "work_pct_api", "usage_share", "exposure", "automation_share",
        "augmentation_share"]),
    "crosswalk": dict(key=["onet_code", "indeed_sector"], float=["weight"]),
    "onet_to_my_group": dict(key=["onet_code"]),
    "my_vacancies": dict(key=["freq", "period", "group_type", "group"], int=["vacancies"], bool=["is_partial"]),
}


def to_bool(v: str) -> bool:
    if v.lower() in ("true", "1"):
        return True
    if v.lower() in ("false", "0"):
        return False
    raise ValueError(f"not a boolean: {v!r}")


def read_rows(table: str) -> list[dict]:
    spec = TABLES[table]
    casts = {}
    for col in spec.get("int", []):
        casts[col] = lambda v: int(float(v))
    for col in spec.get("float", []):
        casts[col] = float
    for col in spec.get("bool", []):
        casts[col] = to_bool
    rows = []
    with open(PROCESSED / f"{table}.csv", encoding="utf-8", newline="") as f:
        for n, raw in enumerate(csv.DictReader(f), start=2):
            row = {}
            for col, val in raw.items():
                if val == "":
                    row[col] = None
                    continue
                try:
                    row[col] = casts[col](val) if col in casts else val
                except ValueError as e:
                    raise SystemExit(f"{table}.csv line {n}, column {col}: {e}")
            rows.append(row)
    keys = [tuple(r[k] for k in spec["key"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise SystemExit(f"{table}.csv has duplicate primary keys")
    return rows


def env_url() -> str | None:
    if os.environ.get("SUPABASE_URL"):
        return os.environ["SUPABASE_URL"]
    if BACKEND_ENV.exists():
        for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("SUPABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"\'')
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="parse and validate the CSVs, do not connect")
    ap.add_argument("--tables", nargs="+", choices=list(TABLES), help="subset to load (default: all)")
    args = ap.parse_args()

    todo = [t for t in TABLES if not args.tables or t in args.tables]
    data = {t: read_rows(t) for t in todo}
    for t, rows in data.items():
        print(f"{t:20s} {len(rows):6d} rows parsed")
    if args.dry_run:
        return 0

    url, key = env_url(), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL (or src/backend/.env) and SUPABASE_SERVICE_KEY.", file=sys.stderr)
        return 1
    from supabase import create_client  # imported late so --dry-run needs no dependency

    client = create_client(url, key)
    for t, rows in data.items():
        on_conflict = ",".join(TABLES[t]["key"])
        for i in range(0, len(rows), BATCH):
            client.table(t).upsert(rows[i:i + BATCH], on_conflict=on_conflict).execute()
        print(f"{t:20s} {len(rows):6d} rows upserted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
