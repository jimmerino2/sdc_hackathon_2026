import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.forecast.schemas import DataSource, ForecastRow, HistoryPoint, HorizonOutlook, JobForecast, JobHorizon, Projection, Range, Reliability

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "ml" / "output"
PROCESSED_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
HISTORY_MONTHS = 12  # how far back the role chart looks
MANIFEST = Path(__file__).resolve().parents[4] / "data" / "processed" / "manifest.json"
FLAT_BAND_PCT = 2.0  # changes within +-2% count as "stable"

NOTES = {
    "indicative": "Indicative trend, not a precise prediction: in historical tests the machine-learning "
                  "model did not beat simple baselines, so the main forecast repeats last year's trend "
                  "(typical error about 10%). Scenarios are what-if assumptions.",
    "validated": "The machine-learning model beat the simple baselines in historical testing.",
}


@lru_cache
def _meta() -> dict:
    """model_meta.json: feature order, category lists, error ranges (written by ml/train_lgbm.py)."""
    return json.loads((OUTPUT_DIR / "model_meta.json").read_text())


@lru_cache
def _table() -> pd.DataFrame:
    """The precomputed forecast table (forecast_output.csv), read once."""
    return pd.read_csv(OUTPUT_DIR / "forecast_output.csv")


@lru_cache
def _jobs() -> pd.DataFrame:
    """The job-level forecast table (job_forecast.csv), read once."""
    return pd.read_csv(OUTPUT_DIR / "job_forecast.csv")


@lru_cache
def _sector_index() -> pd.DataFrame:
    """Monthly postings index per sector (rows = month, columns = sector), from the model table."""
    t = pd.read_csv(PROCESSED_DIR / "model_table_US.csv", usecols=["sector", "month", "index"])
    return t.pivot(index="month", columns="sector", values="index").sort_index()


@lru_cache
def _crosswalk() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "crosswalk.csv", usecols=["onet_code", "indeed_sector", "weight"])


def _history(onet_code: str, forecast_from: str) -> list[HistoryPoint]:
    """The job's past months as a percent change vs `forecast_from`, blended over its sectors like the forecast is."""
    cw = _crosswalk()
    cw = cw[cw["onet_code"] == onet_code]
    idx = _sector_index()
    idx = idx[idx.index <= forecast_from]
    if cw.empty or idx.empty or forecast_from not in idx.index:
        return []
    change = pd.Series(0.0, index=idx.index)
    for _, r in cw.iterrows():
        col = idx[r["indeed_sector"]]
        change += r["weight"] * (col / col.loc[forecast_from] - 1)
    change = (change * 100).round(1).dropna().tail(HISTORY_MONTHS + 1)
    return [HistoryPoint(month=m, change_pct=float(v)) for m, v in change.items()]


JOB_NOTE = ("A job has no postings history of its own: its number is its sector's trend (blended if it spans "
            "two sectors). Jobs in the same sector differ only under the Slow and Rapid AI scenarios.")


def _manifest() -> dict:
    """data/processed/manifest.json (written by pipeline/refresh.py). Read on each call so a refresh shows without a restart."""
    try:
        return json.loads(MANIFEST.read_text())
    except (OSError, ValueError):
        return {}


def sources() -> list[DataSource]:
    """The datasets behind the trends, with the date each was last published.

    Names and links are fixed (see data/documentation/SOURCES.md); dates and months come from the data files.
    """
    t = _table().iloc[0]
    asof = _manifest().get("signals_as_of", {})
    return [
        DataSource(
            id="indeed_postings",
            name="Indeed Job Postings Index",
            publisher="Indeed Hiring Lab",
            url="https://github.com/hiring-lab/job_postings_tracker",
            license="CC-BY-4.0",
            used_for="Rising and declining roles",
            as_of=asof.get("job_postings_index") or str(t["as_of_date"]),
            latest_month=str(t["origin_month"]),
            is_proxy_for_malaysia=bool(t["is_proxy_geo"]),
        ),
        DataSource(
            id="indeed_ai_tracker",
            name="Indeed AI Tracker",
            publisher="Indeed Hiring Lab",
            url="https://github.com/hiring-lab/ai-tracker",
            license="CC-BY-4.0",
            used_for="Slow, Baseline and Rapid AI scenarios",
            as_of=asof.get("ai_postings_share"),
            is_proxy_for_malaysia=bool(t["is_proxy_geo"]),
        ),
    ]


def sectors() -> list[str]:
    """Sector names that appear in the forecasts."""
    return _meta()["categories"]["sector"]


def _trend(change_pct: float, horizon: int = 12) -> str:
    """Label a percent change as growing / stable / shrinking; the +-2% band is scaled to the horizon."""
    band = FLAT_BAND_PCT * horizon / 12
    if change_pct > band:
        return "growing"
    if change_pct < -band:
        return "shrinking"
    return "stable"


def _projection(method: str, now: float, pred: float, low: float, high: float) -> Projection:
    """Bundle a predicted index, its percent change from now, and its range."""
    return Projection(
        method=method,
        index=round(pred, 2),
        change_pct=round((pred / now - 1) * 100, 1),
        range=Range(low=round(low, 2), high=round(high, 2)),
    )


def _reliability(status: str) -> Reliability:
    """Status plus the plain-language caveat that goes with it."""
    return Reliability(status=status, note=NOTES[status])


def list_forecasts(sector: str | None, scenario: str | None, horizon: int | None) -> list[ForecastRow]:
    """Precomputed forecasts in readable form: one entry per sector and scenario, each holding its horizons.

    Optionally filtered by sector, scenario and/or horizon (3, 6, 9 or 12).
    """
    df = _table()
    if sector:
        df = df[df["sector"].str.lower() == sector.strip().lower()]
    if scenario:
        df = df[df["scenario"].str.lower() == scenario.strip().lower()]
    if horizon:
        df = df[df["horizon_m"] == horizon]
    rows = []
    for (sec, scen), grp in df.sort_values("horizon_m").groupby(["sector", "scenario"], sort=False):
        recs = grp.replace({np.nan: None}).to_dict(orient="records")
        outlook = []
        for r in recs:
            h = int(r["horizon_m"])
            proj = _projection("Last year's pace repeats", r["index_now"], r["index_pred"], r["index_low"], r["index_high"])
            model = _projection("Machine-learning model (LightGBM)", r["index_now"], r["index_model"],
                                r["index_model_low"], r["index_model_high"])
            outlook.append(HorizonOutlook(
                horizon_months=h,
                forecast_for=r["target_month"],
                trend=_trend(proj.change_pct, h),
                forecast=proj,
                model_forecast=model,
                average_change_index=r["index_baseline"],
                reliability=_reliability(r["model_status"]),
            ))
        first = recs[0]
        rows.append(ForecastRow(
            sector=sec,
            scenario=scen,
            country=first["geo"],
            is_proxy_for_malaysia=bool(first["is_proxy_geo"]),
            forecast_from=first["origin_month"],
            current_index=first["index_now"],
            ai_exposure=first["ai_exposure"],
            data_as_of=first["as_of_date"],
            outlook=outlook,
        ))
    return rows


def list_jobs(
    onet_code: str | None, title: str | None, scenario: str | None, horizon: int | None
) -> list[JobForecast]:
    """Job-level forecasts, optionally filtered by O*NET code, part of the title, scenario and/or horizon."""
    df = _jobs()
    if onet_code:
        df = df[df["onet_code"] == onet_code]
    if title:
        df = df[df["title"].str.contains(title, case=False, regex=False)]
    if scenario:
        df = df[df["scenario"].str.lower() == scenario.strip().lower()]
    if horizon:
        df = df[df["horizon_m"] == horizon]
    out = []
    for (code, scen), grp in df.sort_values("horizon_m").groupby(["onet_code", "scenario"], sort=False):
        recs = grp.replace({np.nan: None}).to_dict(orient="records")
        first = recs[0]
        outlook = [JobHorizon(
            horizon_months=int(r["horizon_m"]),
            forecast_for=r["forecast_for"],
            trend=_trend(r["change_pct"], int(r["horizon_m"])),
            change_pct=r["change_pct"],
            range=Range(low=r["change_low_pct"], high=r["change_high_pct"]),
            model_change_pct=r["model_change_pct"],
            model_range=Range(low=r["model_change_low_pct"], high=r["model_change_high_pct"]),
            reliability=_reliability(r["model_status"]),
        ) for r in recs]
        out.append(JobForecast(
            onet_code=code,
            title=first["title"],
            scenario=scen,
            sectors=first["sectors"],
            country=first["country"],
            is_proxy_for_malaysia=bool(first["is_proxy_geo"]),
            forecast_from=first["forecast_from"],
            ai_exposure=first["ai_exposure"],
            automation_share=first["automation_share"],
            augmentation_share=first["augmentation_share"],
            ai_exposure_low_sample=bool(first["ai_exposure_low_sample"]),
            note=JOB_NOTE,
            data_as_of=first["as_of_date"],
            history=_history(code, first["forecast_from"]),
            outlook=outlook,
        ))
    return out
