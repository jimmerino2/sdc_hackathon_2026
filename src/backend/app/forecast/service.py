import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.forecast.schemas import (AdoptionExpected, AdoptionOutlook, AdoptionPoint, AdoptionScenario, AdoptionScore,
                                  AdoptionSignal, ForecastRow, HorizonOutlook, JobForecast, JobHorizon, OddsWeek,
                                  Projection, Range, Reliability, SkillDemandPoint)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "ml" / "output"
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


JOB_NOTE = ("A job has no postings history of its own: its number is its sector's trend (blended if it spans "
            "two sectors). Jobs in the same sector differ only under the Slow and Rapid AI scenarios.")


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
            outlook=outlook,
        ))
    return out


# ---------- AI adoption scenarios (ml/ai_adoption_mc.py + ml/ai_signal_score.py) ----------
# These files change every week, so they are re-read when they change on disk instead of once per process.

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
SCENARIO_ORDER = ["AI accelerates", "AI holds", "AI declines"]
ODDS_COLS = {"AI accelerates": "p_accelerates", "AI holds": "p_holds", "AI declines": "p_declines"}
PRIOR_ODDS = {"AI accelerates": 0.25, "AI holds": 0.5, "AI declines": 0.25}  # before the first scoring run
ADOPTION_NOTE = ("Share of US workers who say they use AI for their job (Real-Time Population Survey), simulated "
                 "under three scenarios. The scenarios are assumptions; the odds are updated weekly from job ads, "
                 "business surveys and validated news, and are not a tested prediction. Not a measure of job loss.")
_files: dict[Path, tuple[float, pd.DataFrame]] = {}


def _fresh(path: Path) -> pd.DataFrame:
    """Read a CSV, again only if it changed since the last read. Missing file -> empty frame."""
    if not path.exists():
        return pd.DataFrame()
    mtime = path.stat().st_mtime
    if path not in _files or _files[path][0] != mtime:
        _files[path] = (mtime, pd.read_csv(path, dtype={"soc_major": str, "onet_code": str}))
    return _files[path][1]


def _latest_week(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["week"] == df["week"].max()] if len(df) else df


def _num(v) -> float | None:
    return None if pd.isna(v) else float(v)


def _score(row: pd.Series) -> AdoptionScore:
    return AdoptionScore(week=row["week"], score=float(row["score"]), structured_part=_num(row["structured_part"]),
                         news_part=_num(row["news_part"]), news_items=int(row["news_items"]),
                         signals=[AdoptionSignal(**sig) for sig in json.loads(row["signals"])])


def _outlook(rows: pd.DataFrame, odds: dict[str, float], code: str, group: str, score: AdoptionScore | None,
             onet_code: str | None = None, title: str | None = None) -> AdoptionOutlook:
    rows = rows.sort_values("horizon_m")
    scenarios = []
    for name in SCENARIO_ORDER:
        sc = rows[rows["scenario"] == name]
        scenarios.append(AdoptionScenario(scenario=name, probability=odds[name], outlook=[
            AdoptionPoint(horizon_months=int(r.horizon_m), forecast_for=r.forecast_for, p10=r.p10, p25=r.p25,
                          p50=r.p50, p75=r.p75, p90=r.p90) for r in sc.itertuples()]))
    expected = []
    for h, g in rows.groupby("horizon_m"):
        p50 = g.set_index("scenario")["p50"]
        expected.append(AdoptionExpected(horizon_months=int(h), forecast_for=g["forecast_for"].iloc[0],
                                         rate=round(sum(odds[s] * p50[s] for s in SCENARIO_ORDER), 4)))
    first = rows.iloc[0]
    return AdoptionOutlook(soc_major=code, group=group, onet_code=onet_code, title=title, country="US",
                           is_proxy_for_malaysia=True, forecast_from=first["forecast_from"],
                           current_rate=float(first["rate_now"]), expected=expected, scenarios=scenarios,
                           score=score, data_as_of=str(first["as_of_date"]), note=ADOPTION_NOTE)


def _odds_and_scores() -> tuple[dict[str, dict[str, float]], dict[str, AdoptionScore]]:
    odds = _latest_week(_fresh(OUTPUT_DIR / "scenario_odds_history.csv"))
    scores = _latest_week(_fresh(OUTPUT_DIR / "ai_signal_score.csv"))
    o = {r["soc_major"]: {s: float(r[c]) for s, c in ODDS_COLS.items()} for _, r in odds.iterrows()}
    return o, {r["soc_major"]: _score(r) for _, r in scores.iterrows()}


def list_ai_adoption(group: str | None, horizon: int | None) -> list[AdoptionOutlook]:
    """AI adoption scenarios per SOC major group. `group` matches the code ('15') or part of the name."""
    df = _fresh(OUTPUT_DIR / "ai_adoption_mc.csv")
    if df.empty:
        return []
    if group:
        g = group.strip()
        df = df[(df["soc_major"] == g) | df["soc_major_name"].str.contains(g, case=False, regex=False)]
    if horizon:
        df = df[df["horizon_m"] == horizon]
    odds, scores = _odds_and_scores()
    return [_outlook(rows, odds.get(code, PRIOR_ODDS), code, rows["soc_major_name"].iloc[0], scores.get(code))
            for code, rows in df.groupby("soc_major", sort=True)]


def list_job_ai_adoption(onet_code: str | None, title: str | None, horizon: int | None) -> list[AdoptionOutlook]:
    """AI adoption scenarios per job; the odds and score are those of the job's SOC major group."""
    df = _fresh(OUTPUT_DIR / "ai_adoption_mc_jobs.csv")
    if df.empty:
        return []
    if onet_code:
        df = df[df["onet_code"] == onet_code]
    if title:
        df = df[df["title"].str.contains(title, case=False, regex=False)]
    if horizon:
        df = df[df["horizon_m"] == horizon]
    names = _fresh(OUTPUT_DIR / "ai_adoption_mc.csv").drop_duplicates("soc_major").set_index("soc_major")["soc_major_name"]
    odds, scores = _odds_and_scores()
    out = []
    for code, rows in df.groupby("onet_code", sort=True):
        g = rows["soc_major"].iloc[0]
        out.append(_outlook(rows, odds.get(g, PRIOR_ODDS), g, names.get(g, ""), scores.get(g), code,
                            rows["title"].iloc[0]))
    return out


def odds_history(group: str) -> list[OddsWeek]:
    """Weekly odds of the three scenarios for one SOC major group."""
    df = _fresh(OUTPUT_DIR / "scenario_odds_history.csv")
    if df.empty:
        return []
    df = df[df["soc_major"] == group.strip()].sort_values("week")
    return [OddsWeek(week=r.week, p_accelerates=r.p_accelerates, p_holds=r.p_holds, p_declines=r.p_declines)
            for r in df.itertuples()]


def skill_demand(onet_code: str, country: str | None) -> list[SkillDemandPoint]:
    """Weekly Adzuna ad counts for a job's skills (empty until pipeline/collect_adzuna.py has run)."""
    df = _fresh(DATA_DIR / "skill_demand.csv")
    if df.empty:
        return []
    df = df[df["onet_code"] == onet_code]
    if country:
        df = df[df["country"].str.lower() == country.strip().lower()]
    return [SkillDemandPoint(week=r.week, skill=r.skill, country=r.country, ads=int(r.ads), share=float(r.share))
            for r in df.sort_values(["skill", "week"]).itertuples()]
