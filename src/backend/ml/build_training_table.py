"""Build the training table for any forecast horizon from data/processed/signals.csv.

model_table_US.csv only has the 12-month target; this rebuilds the same table with the target
`horizon` months ahead (3, 6, 9, 12 ...). Same columns and the same 1-month publication lag as
pipeline/build_model_table.py. It covers every geo (US, GB, AU, CA, DE, FR) with a `geo` column,
each with its own national index and AI-share series; train_lgbm.py keeps only the US rows.
Partial months are dropped.
"""
import pandas as pd

GEOS = ["US", "GB", "AU", "CA", "DE", "FR"]


def build_geo_table(s: pd.DataFrame, geo: str, horizon: int = 12) -> pd.DataFrame:
    """One geo's table: per-sector index lags, lagged national and AI features, and the target.

    The target `target_index_ahead` is the sector index `horizon` months later (also stored as
    `target_index_12m_ahead` when horizon is 12, the name train_lgbm.add_features expects).
    """
    g = s[(s.geo == geo) & (~s.is_partial.astype(str).eq("True"))]
    idx = g[(g.series == "job_postings_index") & (g.sector != "")][["sector", "month", "value"]]
    idx = idx.rename(columns={"value": "index"})
    nat = g[(g.series == "job_postings_index") & (g.sector == "")][["month", "value"]]
    nat = nat.rename(columns={"value": "national"}).sort_values("month")
    ai = g[g.series == "ai_postings_share"].sort_values("month")[["month", "value"]]
    ai = ai.rename(columns={"value": "ai_share"})
    ai["ai_chg3"] = ai.ai_share - ai.ai_share.shift(3)
    ai["ai_chg12"] = ai.ai_share - ai.ai_share.shift(12)

    # publication lag: features for month m only use national / AI data up to m-1
    for frame, cols in ((nat, ["national"]), (ai, ["ai_share", "ai_chg3", "ai_chg12"])):
        for c in cols:
            frame[f"{c}_lag1"] = frame[c].shift(1)
    nat = nat[["month", "national_lag1"]]
    ai = ai[["month", "ai_share_lag1", "ai_chg3_lag1", "ai_chg12_lag1"]]

    parts = []
    for sector, d in idx.groupby("sector"):
        d = d.sort_values("month").reset_index(drop=True)
        months = pd.PeriodIndex(d["month"], freq="M")
        assert (months[1:] - months[:-1]).map(lambda x: x.n).isin([1]).all(), f"month gap in {geo}/{sector}"
        for k in (1, 3, 12):
            d[f"index_lag{k}"] = d["index"].shift(k)
        d["index_yoy"] = d["index"] / d["index_lag12"] - 1
        d["target_index_ahead"] = d["index"].shift(-horizon)
        if horizon == 12:
            d["target_index_12m_ahead"] = d["target_index_ahead"]
        parts.append(d)
    out = pd.concat(parts, ignore_index=True)
    out = out.merge(nat, on="month", how="left").merge(ai, on="month", how="left")
    out["geo"] = geo
    return out


def build_training_table(processed_dir, horizon: int = 12) -> pd.DataFrame:
    """All geos stacked for one horizon, with `period` added and `month` parsed to a date; ready for add_features."""
    s = pd.read_csv(processed_dir / "signals.csv", keep_default_na=False)
    out = pd.concat([build_geo_table(s, g, horizon) for g in GEOS], ignore_index=True)
    out["period"] = (out["month"] < "2022-01").map({True: "pandemic", False: "post"})
    out["month"] = pd.to_datetime(out["month"] + "-01")
    return out.sort_values(["geo", "sector", "month"]).reset_index(drop=True)


if __name__ == "__main__":
    import train_lgbm as t

    tbl = build_training_table(t.DATA_DIR)
    print(tbl.groupby("geo").agg(rows=("index", "size"), sectors=("sector", "nunique"),
                                 first=("month", "min"), last=("month", "max")))
    # sanity: US rows should match the team's model_table_US.csv
    us = tbl[tbl.geo == "US"]
    ref = t.load_table(t.DATA_DIR / "model_table_US.csv")
    m = us.merge(ref, on=["sector", "month"], suffixes=("", "_ref"))
    for c in ("index", "index_lag12", "national_lag1", "ai_share_lag1", "ai_chg12_lag1", "target_index_12m_ahead"):
        diff = (m[c] - m[f"{c}_ref"]).abs().max()
        print(f"US vs model_table_US  {c:24s} max abs diff {diff:.6f}")
    print("US rows pooled", len(us), "| reference rows", len(ref))
