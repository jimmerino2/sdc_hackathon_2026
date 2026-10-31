from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.forecast import retrain as retraining
from app.forecast import service, signals
from app.forecast.schemas import DataSource, ForecastRow, JobForecast, QuarterInfo, Quarters, RetrainOut, RetrainRequest

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=list[ForecastRow])
def list_forecasts(sector: str | None = None, scenario: str | None = None, horizon: int | None = Query(None, description="3, 6, 9 or 12 months ahead")):
    """Precomputed forecasts at 3, 6, 9 and 12 months. Filter with ?sector=Marketing&scenario=Rapid AI&horizon=6."""
    if horizon is not None and horizon not in (3, 6, 9, 12):
        raise HTTPException(status_code=422, detail="horizon must be 3, 6, 9 or 12")
    return service.list_forecasts(sector, scenario, horizon)

# Example API for job title Marketing Managers: http://127.0.0.1:8000/forecast/jobs?title=marketing managers
@router.get("/jobs", response_model=list[JobForecast])
def list_jobs(
    onet_code: str | None = Query(None, description="O*NET code, e.g. 15-2051.00"),
    title: str | None = Query(None, description="Part of a job title, e.g. 'data'"),
    scenario: str | None = None,
    horizon: int | None = Query(None, description="3, 6, 9 or 12 months ahead"),
):
    """Job-level forecasts (the job inherits its sector's trend). Filter by code, title, scenario or horizon."""
    if horizon is not None and horizon not in (3, 6, 9, 12):
        raise HTTPException(status_code=422, detail="horizon must be 3, 6, 9 or 12")
    return service.list_jobs(onet_code, title, scenario, horizon)


@router.get("/sectors", response_model=list[str])
def list_sectors():
    """Sector names that appear in GET /forecast."""
    return service.sectors()


@router.get("/sources", response_model=list[DataSource])
def list_sources():
    """The datasets behind the role trends: name, publisher, link, and the date each was last published."""
    return service.sources()


@router.get("/quarters", response_model=Quarters)
def list_quarters():
    """The quarters of data the model can be trained on, oldest first, for the quarter picker."""
    df, source = signals.load_signals()
    done = retraining.cached_default()
    return Quarters(
        quarters=[QuarterInfo(**q) for q in retraining.quarters(df)],
        latest_quarter=signals.year_quarter(max(retraining.sector_months_set(df))),
        source=source,
        refresh_enabled=get_settings().forecast_refresh_enabled,
        default_trained_rows=done.trained_rows if done else service.default_trained_rows(),
    )


@router.post("/retrain", response_model=RetrainOut)
def retrain_forecast(body: RetrainRequest):
    """A job's forecast from the model retrained without the quarters in excluded_quarters.

    The excluded quarters are left out of the data and so is every sample that touches one of their months (a lag, an
    AI change or a target), then the model is trained again (the same code as ml/train_lgbm.py). It takes 2-3 seconds
    the first time for a set of quarters and is instant after that. 422 if a quarter isn't valid or too little data
    is left; 404 if the job has no forecast.
    """
    try:
        result, cached = retraining.retrain(body.excluded_quarters)
    except retraining.RetrainError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    forecasts = service.list_jobs(body.onet_code, None, None, None, jobs=result.jobs, sector_index=result.sector_index)
    if not forecasts:
        raise HTTPException(status_code=404, detail=f"no forecast for {body.onet_code!r}")
    done = retraining.cached_default()
    return RetrainOut(
        excluded_quarters=result.excluded, forecast_from=result.forecast_from, trained_rows=result.trained_rows,
        default_trained_rows=done.trained_rows if done else service.default_trained_rows(),
        holdout_origins=result.holdout_origins, model_status=result.model_status, source=result.source,
        seconds=result.seconds, cached=cached, forecasts=forecasts,
    )


@router.post("/refresh", status_code=204)
def refresh_forecast_data():
    """Forget the stored retrains and re-read the series (and the forecast tables) on the next request.

    Use it after changing rows in Supabase so the next retrain sees them. Off unless FORECAST_REFRESH_ENABLED=true.
    """
    if not get_settings().forecast_refresh_enabled:
        raise HTTPException(status_code=403, detail="refreshing is turned off (set FORECAST_REFRESH_ENABLED=true)")
    retraining.clear()
    service.clear_caches()
