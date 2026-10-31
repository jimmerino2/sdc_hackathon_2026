"""Helpers for the point-in-time tables in data/processed/forecasting: dates, checks, atomic writes and as-of lookups.

A forecast made at time T may only use the latest vintage with available_at <= T.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "vintages"
OUT = ROOT / "data" / "processed" / "forecasting"
COLUMNS = ["source_id", "vintage_id", "blob_sha", "available_at", "source_file", "schema_version",
           "geo", "month", "value", "numerator", "denominator", "n_days", "is_partial"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def parse_dates(s: pd.Series, geo: pd.Series | None = None) -> pd.Series:
    """One date format per file. Early files are day-first ("29/3/24"), so "1/2/19" is ambiguous: the
    format chosen is the one under which every value parses and each geo's dates run day by day."""
    for fmt in ("%Y-%m-%d", "%d/%m/%y", "%m/%d/%y"):
        d = pd.to_datetime(s, format=fmt, errors="coerce")
        if d.isna().any():
            continue
        steps = d.groupby(geo.to_numpy() if geo is not None else 0).diff().dropna()
        if steps.eq(pd.Timedelta(days=1)).all():
            return d
    return pd.Series(pd.NaT, index=s.index)


def monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily geo/date/value -> monthly mean, with day counts. A month short of days is flagged partial."""
    d = daily.dropna(subset=["date", "value"]).copy()
    d["month"] = d["date"].dt.to_period("M")
    agg = {"value": ("value", "mean"), "n_days": ("date", "nunique")}
    for c in ("numerator", "denominator"):  # published counts are summed; absent -> blank, never 0
        if c in d.columns:
            agg[c] = (c, "sum")
    g = d.groupby(["geo", "month"], as_index=False).agg(**agg)
    for c in ("numerator", "denominator"):
        g[c] = g[c] if c in g.columns else pd.NA
    g["is_partial"] = g["n_days"] < g["month"].dt.days_in_month
    g["month"] = g["month"].astype(str)
    return g


def validate(df: pd.DataFrame, lo: float, hi: float) -> None:
    """Checks every vintage table must pass before it replaces the previous one."""
    key = ["vintage_id", "geo", "month"]
    if df.duplicated(key).any():
        raise ValueError("duplicate vintage x geo x month rows")
    if df["value"].isna().any() or not df["value"].between(lo, hi).all():
        raise ValueError(f"values missing or outside [{lo}, {hi}]")
    if (df["n_days"] <= 0).any():
        raise ValueError("months with no days")


def write(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f".{name}.tmp"
    df.assign(available_at=df["available_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
              value=df["value"].round(5)).to_csv(tmp, index=False)
    tmp.replace(OUT / name)  # only after the full table was written


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(OUT / name, dtype={"vintage_id": str, "blob_sha": str})
    df["available_at"] = pd.to_datetime(df["available_at"], utc=True)
    return df


def as_of(vintages: pd.DataFrame, when: pd.Timestamp, per_geo: bool = False) -> pd.DataFrame:
    """Rows of the latest vintage published at or before `when` (empty if none was).

    per_geo=False: one vintage for all geos (the AI tracker is one file; a country it drops is gone, not stale).
    per_geo=True: the latest vintage of each geo (the postings tracker has one file per country)."""
    v = vintages[vintages["available_at"] <= when]
    if v.empty:
        return v
    latest = v.groupby("geo")["available_at"].transform("max") if per_geo else v["available_at"].max()
    return v[v["available_at"] == latest]
