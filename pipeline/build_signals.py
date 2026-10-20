"""Build data/processed/signals.csv from the two Indeed Hiring Lab repos.

Usage:
    python pipeline/build_signals.py --raw data/raw --out data/processed

Expects two git clones inside --raw:
    jpt_repo/  = https://github.com/hiring-lab/job_postings_tracker
    ait_repo/  = https://github.com/hiring-lab/ai-tracker

Output: one row per series x geo x sector x month (contract in member1_data_signals.md).
Series:
    job_postings_index  sector-level and national (sector blank), monthly mean of the
                        daily seasonally-adjusted index (1 Feb 2020 = 100)
    ai_postings_share   country-level, monthly mean of the daily % of postings mentioning AI

Flags:
    is_partial          month has fewer daily observations than calendar days
                        (usually the latest month). Kept, but flagged: drop before modelling.
    is_carried_forward  AI share copied from the previous month because the source has
                        not published that month yet (only for months where postings data exist).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SECTOR_GEOS = ["US", "GB", "AU", "CA", "DE", "FR"]  # countries with sector-level data
JPT_URL = "https://github.com/hiring-lab/job_postings_tracker"
AIT_URL = "https://github.com/hiring-lab/ai-tracker"
JPT_SOURCE = "Indeed Hiring Lab job_postings_tracker (CC-BY-4.0)"
AIT_SOURCE = "Indeed Hiring Lab ai-tracker (CC-BY-4.0)"

COLUMNS = ["series", "geo", "sector", "month", "value", "source", "source_url",
           "as_of_date", "is_partial", "is_carried_forward"]


def monthly_mean(df: pd.DataFrame, keys: list[str], value: str) -> pd.DataFrame:
    """Average daily values to months and flag months with incomplete daily coverage."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    g = df.groupby(keys + ["month"], as_index=False).agg(value=(value, "mean"), n_days=("date", "nunique"))
    g["is_partial"] = g["n_days"] < g["month"].dt.days_in_month
    g["month"] = g["month"].astype(str)
    return g.drop(columns="n_days")


def load_sectors(jpt: Path, geo: str) -> pd.DataFrame:
    d = pd.read_csv(jpt / geo / f"job_postings_by_sector_{geo}.csv")
    as_of = d["date"].max()
    d = d[d["variable"] == "total postings"]
    m = monthly_mean(d.rename(columns={"display_name": "sector"}), ["sector"], "indeed_job_postings_index")
    m["geo"], m["as_of_date"] = geo, as_of
    return m


def load_national(jpt: Path, geo: str) -> pd.DataFrame:
    d = pd.read_csv(jpt / geo / f"aggregate_job_postings_{geo}.csv")
    as_of = d["date"].max()
    if "variable" in d.columns:
        d = d[d["variable"] == "total postings"]
    m = monthly_mean(d, [], "indeed_job_postings_index_SA")
    m["geo"], m["sector"], m["as_of_date"] = geo, "", as_of
    return m


def load_ai(ait: Path) -> pd.DataFrame:
    d = pd.read_csv(ait / "AI_posting.csv").rename(columns={"jobcountry": "geo"})
    out = []
    for geo, gd in d.groupby("geo"):
        m = monthly_mean(gd, [], "AI_share_postings")
        m["geo"], m["as_of_date"] = geo, gd["date"].max()
        out.append(m)
    m = pd.concat(out, ignore_index=True)
    m["sector"] = ""
    return m


def carry_ai_forward(ai: pd.DataFrame, postings_months: dict[str, set[str]]) -> pd.DataFrame:
    """Add rows for months that have postings data but no AI data yet."""
    ai = ai.assign(is_carried_forward=False)
    extra = []
    for geo, months in postings_months.items():
        g = ai[ai["geo"] == geo].sort_values("month")
        if g.empty:
            continue
        last = g.iloc[-1]
        for mo in sorted(m for m in months if m > last["month"]):
            row = last.copy()
            row["month"], row["is_partial"], row["is_carried_forward"] = mo, False, True
            extra.append(row)
    return pd.concat([ai, pd.DataFrame(extra)], ignore_index=True) if extra else ai


def build(raw: Path) -> pd.DataFrame:
    jpt, ait = raw / "jpt_repo", raw / "ait_repo"
    parts, months_by_geo = [], {}
    for geo in SECTOR_GEOS:
        s, n = load_sectors(jpt, geo), load_national(jpt, geo)
        months_by_geo[geo] = set(s["month"])
        for p in (s, n):
            p["series"], p["source"], p["source_url"] = "job_postings_index", JPT_SOURCE, JPT_URL
            parts.append(p)

    ai = carry_ai_forward(load_ai(ait), months_by_geo)
    ai["series"], ai["source"], ai["source_url"] = "ai_postings_share", AIT_SOURCE, AIT_URL
    parts.append(ai)

    out = pd.concat(parts, ignore_index=True)
    out["is_carried_forward"] = out["is_carried_forward"].fillna(False).astype(bool)
    out["is_partial"] = out["is_partial"].astype(bool)
    out["value"] = out["value"].round(4)
    out = out[COLUMNS].sort_values(["series", "geo", "sector", "month"]).reset_index(drop=True)

    # Integrity checks
    key = ["series", "geo", "sector", "month"]
    assert not out.duplicated(key).any(), "duplicate keys in signals"
    assert out["value"].notna().all(), "missing values in signals"
    per_sector = out[(out.series == "job_postings_index") & (out.sector != "")].groupby(["geo", "sector"]).size()
    assert per_sector.groupby(level=0).nunique().eq(1).all(), "sectors have unequal month counts"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    a = ap.parse_args()
    out = build(Path(a.raw))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    out.to_csv(Path(a.out) / "signals.csv", index=False)
    print(f"signals.csv: {len(out):,} rows")
    print(out.groupby(["series", "geo"]).agg(months=("month", "nunique"), first=("month", "min"),
                                             last=("month", "max"), as_of=("as_of_date", "max")).to_string())


if __name__ == "__main__":
    main()
