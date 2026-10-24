from fastapi import APIRouter, HTTPException, Query

from app.outlook import service
from app.outlook.schemas import OutlookRow, TargetSummary, UnitAccuracy

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


# Example: http://127.0.0.1:8000/outlook/btos_ai_use_rate/accuracy?unit=62|new
@router.get("/{target}/accuracy", response_model=list[UnitAccuracy])
def get_accuracy(target: str, unit: str = Query(..., description="e.g. US, 62|new, 15, v1.1")):
    """For one unit: how every method did on the held-back test data, per published horizon, and whether the
    published forecast beat 'no change' there."""
    _check(target)
    return service.accuracy(target, unit)
