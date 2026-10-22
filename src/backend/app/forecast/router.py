from fastapi import APIRouter, HTTPException, Query

from app.forecast import service
from app.forecast.schemas import AdoptionOutlook, ForecastRow, JobForecast, OddsWeek, SkillDemandPoint

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


def _check_horizon(horizon: int | None) -> None:
    if horizon is not None and horizon not in (3, 6, 9, 12):
        raise HTTPException(status_code=422, detail="horizon must be 3, 6, 9 or 12")


@router.get("/ai-adoption", response_model=list[AdoptionOutlook])
def list_ai_adoption(
    group: str | None = Query(None, description="SOC major group code ('15') or part of its name; '00' = all workers"),
    horizon: int | None = Query(None, description="3, 6, 9 or 12 months ahead"),
):
    """AI adoption at work per occupation group under AI accelerates / holds / declines, with this week's odds."""
    _check_horizon(horizon)
    return service.list_ai_adoption(group, horizon)


@router.get("/ai-adoption/jobs", response_model=list[AdoptionOutlook])
def list_job_ai_adoption(
    onet_code: str | None = Query(None, description="O*NET code, e.g. 15-1252.00"),
    title: str | None = Query(None, description="Part of a job title, e.g. 'software'"),
    horizon: int | None = Query(None, description="3, 6, 9 or 12 months ahead"),
):
    """The same per job, starting from the job's own adoption rate; odds are its occupation group's."""
    _check_horizon(horizon)
    return service.list_job_ai_adoption(onet_code, title, horizon)


@router.get("/ai-adoption/odds-history", response_model=list[OddsWeek])
def odds_history(group: str = Query("00", description="SOC major group code; '00' = all workers")):
    """How the odds of the three scenarios moved, week by week."""
    return service.odds_history(group)


@router.get("/skill-demand", response_model=list[SkillDemandPoint])
def skill_demand(
    onet_code: str = Query(..., description="O*NET code, e.g. 15-1252.00"),
    country: str | None = Query(None, description="Adzuna country code, e.g. 'gb'"),
):
    """Weekly live-ad counts for the job's key skills (Adzuna). Empty until the collector has run."""
    return service.skill_demand(onet_code, country)
