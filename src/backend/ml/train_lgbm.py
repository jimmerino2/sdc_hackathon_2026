"""Train a LightGBM model that forecasts each sector's job-postings index 12 months ahead.

Input : data/processed/model_table_US.csv  (one row per sector x month, already lagged)
Output: ml/output/forecast_output.csv   12-month-ahead forecast per sector and scenario.
                                        index_pred/low/high = headline (yoy: last year's growth
                                        repeats); index_model* = LightGBM; index_baseline = constant
        ml/output/lgbm_model.txt        the trained model
        ml/output/model_meta.json       data as-of dates, settings, seed, holdout scores

Notes on the data (see data/documentation/):
  * The US stands in for Malaysia (Indeed has no MY data), so the output is flagged is_proxy_geo.
  * The target is `target_index_12m_ahead`; we predict the growth over 12 months
    (target / index - 1) so sectors with different index levels share one model.
  * The AI features are national (the same for every sector in a month).
"""
import argparse
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

import build_training_table
import job_forecast

HERE = Path(__file__).parent
DATA_DIR = HERE.parents[2] / "data" / "processed"
HORIZONS = [3, 6, 9, 12]  # months ahead the app shows; one model is trained per horizon
SEED = 42

CATS = ["sector", "period"]
NUMERIC = [
    "index",  # sector postings index now (1 Feb 2020 = 100)
    "mom",  # index / index_lag1 - 1
    "chg3",  # index / index_lag3 - 1
    "index_yoy",  # index / index_lag12 - 1
    "rel_nat",  # sector index vs national index, both last month
    "ai_share_lag1",  # % of US postings mentioning AI, last month
    "ai_chg3_lag1",
    "ai_chg12_lag1",
]
FEATURES = NUMERIC + CATS

# Scenario assumption (NOT learned from data): shift in 12-month growth, per unit of a sector's
# AI exposure above/below the average sector. Rapid AI: exposed sectors post less than average,
# unexposed ones more. Slow: the reverse. Baseline: no shift. Change these to tune the spread.
SCENARIO_EFFECT = {"Slow": +0.10, "Baseline": 0.0, "Rapid AI": -0.10}

# Small, heavily regularised trees: ~1.5-2.6k rows from 47 series with overlapping targets.
PARAMS = dict(
    objective="regression",
    learning_rate=0.03,
    num_leaves=4,
    min_child_samples=30,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=5.0,
    random_state=SEED,
    verbose=-1,
)


def load_table(path: Path) -> pd.DataFrame:
    """Read model_table_US.csv, parse `month` to a date and sort by sector and month."""
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"] + "-01")
    return df.sort_values(["sector", "month"]).reset_index(drop=True)


def add_features(df: pd.DataFrame, target_col: str = "target_index_12m_ahead") -> pd.DataFrame:
    """Add the scale-free features and the training target `y` to the model table.

    The table already holds the lags (so no leakage: AI and national values are last month's).
    We only turn levels into changes so one model can learn across sectors:
      mom      this month vs last month
      chg3     this month vs 3 months ago
      rel_nat  sector index / national index (is the sector outperforming the market?)
      y        target: growth over the horizon = target / index - 1, where the target column holds
               the index `horizon` months later (NaN for the latest months, whose future isn't known)
    """
    out = df.copy()
    out["mom"] = out["index"] / out["index_lag1"] - 1
    out["chg3"] = out["index"] / out["index_lag3"] - 1
    out["rel_nat"] = out["index_lag1"] / out["national_lag1"]
    out["y"] = out[target_col] / out["index"] - 1
    return out


def sector_exposure(processed_dir: Path) -> pd.Series:
    """Average AI exposure (0-1) per Indeed sector, weighted by crosswalk.weight.

    Jobs map to sectors through crosswalk.csv; a job spanning two sectors counts by its weight.
    Sectors with no job in the crosswalk get the mean exposure, so scenarios leave them unshifted.
    """
    cw = pd.read_csv(processed_dir / "crosswalk.csv")
    ex = pd.read_csv(processed_dir / "ai_exposure.csv")[["onet_code", "exposure"]]
    m = cw.merge(ex, on="onet_code", how="left")
    m["w_exp"] = m["weight"] * m["exposure"]
    grouped = m.groupby("indeed_sector")
    return grouped["w_exp"].sum() / grouped["weight"].sum()


def set_categories(df: pd.DataFrame, cats: dict) -> pd.DataFrame:
    """Mark sector and period as categorical with a fixed list of allowed values.

    The same lists must be used when training and when predicting, otherwise LightGBM's
    internal codes would point at different sectors. They are saved in model_meta.json.
    """
    out = df.copy()
    for c in CATS:
        out[c] = pd.Categorical(out[c], categories=cats[c])
    return out


def fit(train: pd.DataFrame, n_trees: int) -> lgb.LGBMRegressor:
    """Train the regressor on FEATURES -> y (growth over the horizon) with a fixed number of trees.

    No early stopping on purpose: with so little data, stopping on the holdout would make the
    holdout score look better than it really is.
    """
    model = lgb.LGBMRegressor(n_estimators=n_trees, **PARAMS)
    model.fit(train[FEATURES], train["y"])
    return model


def score(actual: pd.Series, pred: pd.Series, base: pd.Series) -> dict:
    """Error metrics in index space.

    MAPE       mean absolute % error of the predicted index (lower is better)
    MAE        mean absolute error in index points
    direction  % of cases where we got up-vs-down right relative to today's index
               (what the quadrant's "growing or shrinking" needs); blank if the method
               never predicts a change (the "flat" baseline)
    """
    err = (actual - pred).abs()
    moves = (pred != base).all()
    direction = float((np.sign(pred - base) == np.sign(actual - base)).mean() * 100) if moves else np.nan
    return {
        "MAPE %": round(float((err / actual.abs()).mean() * 100), 2),
        "MAE": round(float(err.mean()), 2),
        "direction %": round(direction, 1),
    }


def run_horizon(h: int, args, exposure: pd.Series, manifest: dict) -> tuple[pd.DataFrame, lgb.LGBMRegressor, dict]:
    """Validate, refit and forecast one horizon `h` (months ahead). Returns (rows, model, meta).

    1. Holdout: the last `--holdout` origin months with a known target are held out. Training uses
       only origins whose h-month target was already known when the holdout began (an h-month
       gap), so nothing from the future leaks in.
    2. Baselines: "flat", "yoy" (last year's pace, scaled to h months) and "constant" (every sector
       moves by the average training growth).
    3. Refit on all labelled rows and forecast from the latest month. The headline forecast is the
       yoy pace shifted by the scenario; the LightGBM forecast is given next to it.
    The scenario shift is defined for 12 months and scaled by h/12.
    """
    scale = h / 12
    tbl = build_training_table.build_training_table(DATA_DIR, horizon=h)
    tbl = tbl[tbl["geo"] == "US"].drop(columns="geo").reset_index(drop=True)
    df = add_features(tbl, target_col="target_index_ahead")
    cats = {c: sorted(df[c].unique().tolist()) for c in CATS}
    df = set_categories(df, cats)

    labelled = df.dropna(subset=NUMERIC + ["y"])
    if args.post_only:
        labelled = labelled[labelled["period"] == "post"]
    latest = df["month"].max()

    last_origin = labelled["month"].max()
    hold_start = last_origin - pd.DateOffset(months=args.holdout - 1)
    train_end = hold_start - pd.DateOffset(months=h)
    train = labelled[labelled["month"] <= train_end]
    hold = labelled[labelled["month"] >= hold_start]
    print(f"\n=== horizon {h} months === {len(labelled):,} labelled rows | holdout origins "
          f"{hold_start:%Y-%m} -> {last_origin:%Y-%m} ({len(hold)} rows) | train origins up to "
          f"{train_end:%Y-%m} ({len(train)} rows)")

    model = fit(train, args.trees)
    growth = pd.Series(model.predict(hold[FEATURES]), index=hold.index)
    actual, base = hold["target_index_ahead"], hold["index"]
    yoy_g = (1 + hold["index_yoy"]) ** scale - 1
    preds = {
        "LightGBM": base * (1 + growth),
        "flat (index unchanged)": base,
        "yoy (last year's pace repeats)": base * (1 + yoy_g),
        "constant (mean train growth)": base * (1 + train["y"].mean()),
    }
    table = pd.DataFrame({name: score(actual, p, base) for name, p in preds.items()}).T
    print(table.to_string())
    print(f"({(hold['y'] < 0).mean() * 100:.1f}% of holdout sectors fell, so always guessing 'down' scores that for direction)")

    # rough ranges: 10th-90th percentile of holdout errors in growth space, for the model and for yoy
    q_lo, q_hi = (float((hold["y"] - growth).quantile(q)) for q in (0.10, 0.90))
    qy_lo, qy_hi = (float((hold["y"] - yoy_g).quantile(q)) for q in (0.10, 0.90))
    beats = table.loc["LightGBM", "MAPE %"] < table.loc["constant (mean train growth)", "MAPE %"]
    status = "validated" if beats else "indicative"
    base_growth = float(labelled["y"].mean())

    # ---- final: refit on everything with a known target, forecast from the latest month ----
    final = fit(labelled, args.trees)
    origin = df[df["month"] == latest].dropna(subset=NUMERIC).copy()
    g = final.predict(origin[FEATURES])
    sectors = origin["sector"].astype(str)
    sec_exp = sectors.map(exposure)
    centred = (sec_exp - exposure.mean()).fillna(0.0).to_numpy()  # 0 for sectors with no job
    as_of = manifest.get("signals_as_of", {}).get("job_postings_index")

    frames = []
    for scenario, effect in SCENARIO_EFFECT.items():
        shift = effect * centred * scale  # scenario's AI-exposure assumption, scaled to the horizon
        gm = g + shift  # LightGBM growth, shifted
        gh = ((1 + origin["index_yoy"].to_numpy()) ** scale - 1) + shift  # headline: yoy pace, shifted
        frames.append(pd.DataFrame({
            "sector": sectors.to_numpy(),
            "geo": manifest.get("default_geo", "US"),
            "is_proxy_geo": manifest.get("is_proxy_geo", True),
            "scenario": scenario,
            "horizon_m": h,
            "origin_month": latest.strftime("%Y-%m"),
            "target_month": (latest + pd.DateOffset(months=h)).strftime("%Y-%m"),
            "index_now": origin["index"].round(2).to_numpy(),
            "index_pred": (origin["index"] * (1 + gh)).round(2).to_numpy(),
            "index_low": (origin["index"] * (1 + gh + qy_lo)).round(2).to_numpy(),
            "index_high": (origin["index"] * (1 + gh + qy_hi)).round(2).to_numpy(),
            "headline_method": "yoy",
            "index_model": (origin["index"] * (1 + gm)).round(2).to_numpy(),
            "index_model_low": (origin["index"] * (1 + gm + q_lo)).round(2).to_numpy(),
            "index_model_high": (origin["index"] * (1 + gm + q_hi)).round(2).to_numpy(),
            "index_baseline": (origin["index"] * (1 + base_growth)).round(2).to_numpy(),
            "ai_exposure": sec_exp.round(3).to_numpy(),
            "model_status": status,
            "as_of_date": as_of,
        }))
    meta = {
        "train_rows": int(len(labelled)),
        "holdout": {"origins": [f"{hold_start:%Y-%m}", f"{last_origin:%Y-%m}"], "scores": table.to_dict(orient="index")},
        "interval_growth_q10_q90": {"model": [q_lo, q_hi], "yoy_headline": [qy_lo, qy_hi]},
        "baseline_growth": base_growth,
        "model_status": status,
        "categories": cats,
    }
    return pd.concat(frames, ignore_index=True), final, meta


def main():
    """Train one model per horizon (3, 6, 9, 12 months) and write the forecasts, models and metadata.

    Outputs in --out-dir: forecast_output.csv (all horizons, long format), lgbm_model_h{h}.txt per
    horizon, and model_meta.json (shared settings plus per-horizon holdout scores and ranges).
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_DIR / "model_table_US.csv"), help="folder of this file is used for manifest/crosswalk")
    ap.add_argument("--holdout", type=int, default=12, help="months of origins held out for validation")
    ap.add_argument("--trees", type=int, default=300)
    ap.add_argument("--post-only", action="store_true", help="drop rows from the pandemic period")
    ap.add_argument("--out-dir", default=str(HERE / "output"))
    args = ap.parse_args()

    data_dir = Path(args.data).parent
    manifest_path = data_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    exposure = sector_exposure(data_dir)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, horizons_meta = [], {}
    for h in HORIZONS:
        rows, model, hmeta = run_horizon(h, args, exposure, manifest)
        frames.append(rows)
        model.booster_.save_model(str(out_dir / f"lgbm_model_h{h}.txt"))
        horizons_meta[str(h)] = {k: v for k, v in hmeta.items() if k != "categories"}
        categories = hmeta["categories"]
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(out_dir / "forecast_output.csv", index=False)
    jobs = job_forecast.build_job_forecast(out, data_dir, SCENARIO_EFFECT)
    jobs.to_csv(out_dir / "job_forecast.csv", index=False)

    meta = {
        "data_file": Path(args.data).name,
        "data_as_of": manifest.get("signals_as_of"),
        "ai_exposure_as_of": manifest.get("ai_exposure_as_of"),
        "is_proxy_geo": manifest.get("is_proxy_geo", True),
        "target": "growth of the sector postings index over each horizon (months ahead)",
        "horizons": HORIZONS,
        "features": FEATURES,
        "categories": categories,
        "params": {**PARAMS, "n_estimators": args.trees},
        "post_only": args.post_only,
        "headline_method": "yoy (last year's pace repeats, scaled to the horizon); chosen because the LightGBM model "
                           "did not beat simple baselines across rolling-window backtests run during development",
        "scenario_effect_assumption_12m": SCENARIO_EFFECT,
        "by_horizon": horizons_meta,
    }
    (out_dir / "model_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"\nwrote job_forecast.csv ({len(jobs)} rows = {jobs['onet_code'].nunique()} jobs x {len(SCENARIO_EFFECT)} scenarios x {len(HORIZONS)} horizons)")
    print(f"wrote forecast_output.csv ({len(out)} rows = {out['sector'].nunique()} sectors x "
          f"{len(SCENARIO_EFFECT)} scenarios x {len(HORIZONS)} horizons), lgbm_model_h*.txt, model_meta.json -> {out_dir}")
    for h in HORIZONS:
        print(f"  horizon {h:>2}m: model_status {horizons_meta[str(h)]['model_status']}")


if __name__ == "__main__":
    main()
