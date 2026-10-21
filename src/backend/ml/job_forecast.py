"""Turn the sector forecasts into job-level forecasts (one row per job x scenario x horizon).

A job has no postings history of its own, so it inherits its sectors' trend:
  * sector trend: the job's sectors' Baseline growth, blended by crosswalk.weight (weights sum to 1);
  * scenario: Slow / Rapid AI shift the growth by the JOB's own AI exposure (ai_exposure.csv), so two
    jobs in the same sector can differ under the AI scenarios. Baseline is the plain sector blend.
The scenario effect is the same assumption as in train_lgbm.SCENARIO_EFFECT (not learned from data).
"""
from pathlib import Path

import pandas as pd


def build_job_forecast(forecast: pd.DataFrame, processed_dir: Path, scenario_effect: dict) -> pd.DataFrame:
    """Return the job-level table from forecast_output rows (all scenarios and horizons).

    Growth is in percent change from the sector index now. Ranges blend the sectors' low/high the
    same way. `ai_exposure_low_sample` flags jobs whose exposure is a fallback or a tied floor.
    """
    cw = pd.read_csv(processed_dir / "crosswalk.csv")
    ex = pd.read_csv(processed_dir / "ai_exposure.csv").set_index("onet_code")
    det = pd.read_csv(processed_dir / "ai_exposure_detail.csv")
    low_sample = set(det.loc[det["low_sample"].astype(str).str.lower() == "true", "onet_code"]) if "low_sample" in det else set()
    mean_exposure = float(ex["exposure"].mean())

    base = forecast[forecast["scenario"] == "Baseline"].copy()
    for col, name in (("index_pred", "g"), ("index_low", "g_low"), ("index_high", "g_high"), ("index_model", "gm"),
                      ("index_model_low", "gm_low"), ("index_model_high", "gm_high")):
        base[name] = base[col] / base["index_now"] - 1
    cols = ["sector", "horizon_m", "origin_month", "target_month", "g", "g_low", "g_high", "gm", "gm_low", "gm_high",
            "model_status", "geo", "is_proxy_geo", "as_of_date"]
    j = cw.merge(base[cols], left_on="indeed_sector", right_on="sector")
    for c in ("g", "g_low", "g_high", "gm", "gm_low", "gm_high"):
        j[c] = j[c] * j["weight"]
    key = ["onet_code", "title", "horizon_m"]
    agg = j.groupby(key).agg(
        g=("g", "sum"), g_low=("g_low", "sum"), g_high=("g_high", "sum"),
        gm=("gm", "sum"), gm_low=("gm_low", "sum"), gm_high=("gm_high", "sum"),
        origin_month=("origin_month", "first"), target_month=("target_month", "first"),
        model_status=("model_status", "first"), geo=("geo", "first"),
        is_proxy_geo=("is_proxy_geo", "first"), as_of_date=("as_of_date", "first"),
    ).reset_index()

    mix = (cw.sort_values("weight", ascending=False)
             .assign(part=lambda d: d["indeed_sector"] + " (" + (d["weight"] * 100).round(0).astype(int).astype(str) + "%)")
             .groupby("onet_code")["part"].agg(", ".join).rename("sectors"))
    agg = agg.merge(mix, on="onet_code")
    agg["ai_exposure"] = agg["onet_code"].map(ex["exposure"])
    agg["automation_share"] = agg["onet_code"].map(ex["automation_share"])
    agg["augmentation_share"] = agg["onet_code"].map(ex["augmentation_share"])
    agg["ai_exposure_low_sample"] = agg["onet_code"].isin(low_sample) | agg["ai_exposure"].isin([0.0, 0.117])

    frames = []
    for scenario, effect in scenario_effect.items():
        d = agg.copy()
        shift = effect * (d["ai_exposure"] - mean_exposure) * (d["horizon_m"] / 12)  # scaled to the horizon
        d["scenario"] = scenario
        for c in ("g", "g_low", "g_high", "gm", "gm_low", "gm_high"):
            d[c] = d[c] + shift
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    for c in ("g", "g_low", "g_high", "gm", "gm_low", "gm_high"):
        out[c] = (out[c] * 100).round(1)
    out = out.rename(columns={"g": "change_pct", "g_low": "change_low_pct", "g_high": "change_high_pct",
                              "gm": "model_change_pct", "gm_low": "model_change_low_pct",
                              "gm_high": "model_change_high_pct", "geo": "country", "target_month": "forecast_for",
                              "origin_month": "forecast_from"})
    order = ["onet_code", "title", "scenario", "horizon_m", "forecast_from", "forecast_for", "change_pct",
             "change_low_pct", "change_high_pct", "model_change_pct", "model_change_low_pct", "model_change_high_pct",
             "sectors", "ai_exposure", "automation_share", "augmentation_share", "ai_exposure_low_sample",
             "model_status", "country", "is_proxy_geo", "as_of_date"]
    return out[order].sort_values(["onet_code", "scenario", "horizon_m"]).reset_index(drop=True)
