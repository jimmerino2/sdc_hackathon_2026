from fastapi import APIRouter, HTTPException, Query

from app.forecast import service
from app.forecast.schemas import DataSource, ForecastRow, JobForecast

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
