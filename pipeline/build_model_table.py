"""Build a leakage-safe monthly modelling table for Member 2 from signals.csv.

Replaces the join logic of the old real_data_pipeline.py, with the agreed fixes:
  1. AI-change features are computed on the FULL AI series (from 2019) BEFORE joining,
     so the first sector months still get 3- and 12-month AI changes.
  2. Partial months (e.g. a month with only 9 days of data) are dropped.
  3. The latest AI value is carried forward when the source has not published yet
     (flag kept as ai_carried_forward).
  4. A 1-month publication lag: features for month t only use AI and national data up to t-1.
  5. Row counts and key uniqueness are asserted after every join.

Usage:
    python pipeline/build_model_table.py --geo US
Output: data/processed/model_table_<geo>.csv

Columns:
  sector, month
  index                      sector postings index in month t (target-side; do not use as a same-month feature for t+h without lagging)
  index_lag1/3/12            sector index 1/3/12 months earlier
  index_yoy                  index / index_lag12 - 1
  national_lag1              national postings index, month t-1
  ai_share_lag1              % of postings mentioning AI, month t-1 (publication lag)
  ai_chg3_lag1, ai_chg12_lag1  change in AI share over 3 / 12 months, ending t-1
  ai_carried_forward         True if ai_share_lag1 was carried forward
  period                     "pandemic" (before 2022-01) or "post" -- use to filter or as a flag
  target_index_12m_ahead     sector index at t+12 (blank when not yet known)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build(signals: Path, geo: str) -> pd.DataFrame:
    s = pd.read_csv(signals, dtype={"sector": str}, keep_default_na=False)
    s = s[s.geo == geo]

    # 1. AI features on the full AI series, before any join
    ai = s[s.series == "ai_postings_share"].sort_values("month")[["month", "value", "is_carried_forward"]]
    ai = ai.rename(columns={"value": "ai_share", "is_carried_forward": "ai_carried_forward"})
    ai["ai_chg3"] = ai.ai_share - ai.ai_share.shift(3)
    ai["ai_chg12"] = ai.ai_share - ai.ai_share.shift(12)

    nat = s[(s.series == "job_postings_index") & (s.sector == "")][["month", "value"]].rename(columns={"value": "national"})

    sec = s[(s.series == "job_postings_index") & (s.sector != "")]
    # 2. drop partial months
    n_partial = int(sec.is_partial.astype(str).str.lower().eq("true").sum())
    sec = sec[~sec.is_partial.astype(str).str.lower().eq("true")]
    sec = sec[["sector", "month", "value"]].rename(columns={"value": "index"}).sort_values(["sector", "month"])

    # sector lags and target (within sector)
    g = sec.groupby("sector")["index"]
    for k in (1, 3, 12):
        sec[f"index_lag{k}"] = g.shift(k)
    sec["index_yoy"] = sec["index"] / sec["index_lag12"] - 1
    sec["target_index_12m_ahead"] = g.shift(-12)

    # 4. publication lag: shift AI and national by one month
    def lag_month(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        out = df[["month"] + cols].copy()
        out["month"] = (pd.PeriodIndex(out["month"], freq="M") + 1).astype(str)
        return out.rename(columns={c: f"{c}_lag1" for c in cols})

    ai_l = lag_month(ai, ["ai_share", "ai_chg3", "ai_chg12", "ai_carried_forward"])
    ai_l = ai_l.rename(columns={"ai_carried_forward_lag1": "ai_carried_forward"})
    nat_l = lag_month(nat, ["national"])

    # 5. joins with integrity checks
    n0 = len(sec)
    t = sec.merge(ai_l, on="month", how="left", validate="many_to_one")
    assert len(t) == n0, "row count changed after AI join"
    t = t.merge(nat_l, on="month", how="left", validate="many_to_one")
    assert len(t) == n0, "row count changed after national join"
    assert not t.duplicated(["sector", "month"]).any(), "duplicate sector-month keys"

    missing_ai = t["ai_share_lag1"].isna().sum()
    assert missing_ai == 0, f"{missing_ai} rows without lagged AI share"

    t["period"] = (t["month"] < "2022-01").map({True: "pandemic", False: "post"})
    print(f"{geo}: {len(t):,} rows, {t.sector.nunique()} sectors, {t.month.min()}..{t.month.max()}, "
          f"dropped {n_partial} partial sector-months, "
          f"{t.target_index_12m_ahead.notna().sum():,} rows with known 12m-ahead target")
    cols = ["sector", "month", "index", "index_lag1", "index_lag3", "index_lag12", "index_yoy",
            "national_lag1", "ai_share_lag1", "ai_chg3_lag1", "ai_chg12_lag1", "ai_carried_forward",
            "period", "target_index_12m_ahead"]
    return t[cols]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--geo", default="US")
    a = ap.parse_args()
    out = build(Path(a.processed) / "signals.csv", a.geo)
    out.to_csv(Path(a.processed) / f"model_table_{a.geo}.csv", index=False)


if __name__ == "__main__":
    main()
