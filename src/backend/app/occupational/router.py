from fastapi import APIRouter, HTTPException, Query

from app.occupational import service

router = APIRouter(prefix="/occupational", tags=["occupational"])


def _run(fn, *args):
    try:
        return fn(*args)
    except service.NotBuilt as e:
        raise HTTPException(status_code=503, detail=f"occupational pipeline output missing ({e}); run "
                                                    "`python -m occupational.run` from src/backend")


@router.get("/meta")
def get_meta():
    """Run, data and model versions, filters the data supports, headline test scores, source health."""
    return _run(service.meta)


# Example: http://127.0.0.1:8000/occupational/skills?country=US&occupation=software_engineer&h=6
@router.get("/skills")
def get_skills(country: str = Query(..., description="e.g. US"), occupation: str = Query(..., description="e.g. data_scientist"),
               h: int = Query(6, description="Horizon in months: 3, 6 or 12"),
               origin: str | None = Query(None, description="An earlier origin month (YYYY-MM) to see that forecast vs what happened")):
    """Every modelled skill in one country x occupation: latest share, forecast, range, evidence, test accuracy."""
    return _run(service.skills, country, occupation, h, origin)


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str, country: str = Query(...), occupation: str = Query(...)):
    """One skill's monthly history, forecasts, past test forecasts, Adzuna snapshot counts and example ads."""
    try:
        return _run(service.skill_detail, skill_id, country, occupation)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown skill: {skill_id}")


@router.get("/emerging")
def get_emerging(country: str = Query(...), occupation: str = Query(...)):
    """Skills ranked by the lower bound of their share increase, with taxonomy status, O*NET coverage and evidence."""
    return _run(service.emerging, country, occupation)


@router.get("/adoption")
def get_adoption(occupation: str = Query(...)):
    """Worker AI usage (measured), employer-side proxy and task exposure, kept separate, with their sources."""
    return _run(service.adoption, occupation)


@router.get("/evaluation")
def get_evaluation():
    """Full evaluation of the served run: split, every method's scores, interval coverage, cell accuracy."""
    return _run(service.evaluation)
