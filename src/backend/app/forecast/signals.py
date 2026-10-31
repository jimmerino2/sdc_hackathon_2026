"""The monthly series the forecast is trained on: job-postings indexes per sector and the AI share of postings.

Read from the Supabase table `forecast_signals` (migrations/0025_forecast_signals.sql, filled by
pipeline/load_forecast_signals.py) so a changed row changes the next retrain. Where that table is missing or empty
the same rows come from data/processed/signals.csv, so the app works before the migration is applied.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.supabase import get_admin_client, get_client

PROCESSED_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
TABLE = "forecast_signals"
PAGE = 1000  # PostgREST returns at most this many rows per request
COLUMNS = ["series", "geo", "sector", "month", "value", "source", "source_url", "as_of_date", "is_partial", "is_carried_forward"]


def year_quarter(month: str) -> str:
    """'2026-09' -> '2026-Q3'."""
    year, m = month.split("-")
    return f"{year}-Q{(int(m) - 1) // 3 + 1}"


def _from_supabase() -> pd.DataFrame | None:
    """The US rows from Supabase, or None if it can't be read or holds none."""
    settings = get_settings()
    if not settings.supabase_url or not (settings.supabase_service_key or settings.supabase_key):
        return None
    try:
        client = get_admin_client() if settings.supabase_service_key else get_client()
        rows: list[dict] = []
        while True:
            page = (client.table(TABLE).select(",".join(COLUMNS)).eq("geo", "US")
                    .order("series").order("sector").order("month").range(len(rows), len(rows) + PAGE - 1).execute().data)
            rows += page
            if len(page) < PAGE:
                break
    except Exception as e:  # table not created yet, no network...
        print(f"could not read {TABLE} from Supabase ({type(e).__name__}); using signals.csv")
        return None
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["sector"] = df["sector"].fillna("")
    return df


@lru_cache
def load_signals() -> tuple[pd.DataFrame, str]:
    """(the US signals table in signals.csv's layout, where it came from: 'supabase' or 'csv'). Read once; see clear()."""
    df = _from_supabase()
    if df is not None:
        return df, "supabase"
    csv = pd.read_csv(PROCESSED_DIR / "signals.csv", keep_default_na=False)
    return csv[csv["geo"] == "US"].reset_index(drop=True), "csv"


def clear() -> None:
    """Forget what was read, so the next call reads the data again."""
    load_signals.cache_clear()


def sector_months(df: pd.DataFrame) -> pd.DataFrame:
    """The finished (not partial) monthly index rows per sector: columns sector, month, value."""
    rows = df[(df["series"] == "job_postings_index") & (df["sector"] != "") & (~df["is_partial"].astype(str).eq("True"))]
    return rows[["sector", "month", "value"]]
