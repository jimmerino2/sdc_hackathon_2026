from fastapi import APIRouter, HTTPException, Query

from app.outlook import service
from app.outlook.schemas import OutlookRow, TargetSummary

router = APIRouter(prefix="/outlook", tags=["outlook"])


def _check(target: str) -> None:
    if target not in service.targets():
        raise HTTPException(status_code=404, detail=f"unknown target or no forecast run yet: {target}")


@router.get("", response_model=list[TargetSummary])
def list_targets():
    """The four rebuilt forecast targets (skill demand, business adoption, occupation adoption, AI capability):
    what each measures, which horizons are served, their status and data freshness."""
    return [service.summary(t) for t in service.targets()]


# Example: http://127.0.0.1:8000/outlook/ai_mention_share?unit=US
@router.get("/{target}", response_model=list[OutlookRow])
def get_forecast(target: str, unit: str | None = Query(None, description="e.g. US, 54|new, 15, v1.1"),
                 h: int | None = Query(None, description="Horizon in the target's periods")):
    """Promoted forecasts for one target. Every row carries its status, range and warnings; read them."""
    _check(target)
    return service.rows(target, unit, h)


@router.get("/{target}/evaluation")
def get_evaluation(target: str):
    """The newest run's evaluation: split, selection table, holdout scores, coverage, ablations, regimes."""
    _check(target)
    return service.evaluation(target)
