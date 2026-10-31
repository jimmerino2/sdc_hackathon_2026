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


# Example: http://127.0.0.1:8000/outlook/worker_genai_use_rate?unit=00
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


# Example: http://127.0.0.1:8000/outlook/frontier_time_horizon/regime?unit=v1.1
@router.get("/{target}/regime")
def get_regime(target: str, unit: str = Query(..., description="e.g. v1.1")):
    """How the faster / same pace / slower chances were worked out, step by step (capability only)."""
    _check(target)
    return service.regime_explained(target, unit)


# Example: http://127.0.0.1:8000/outlook/frontier_time_horizon/engine
@router.get("/{target}/engine")
def get_engine(target: str):
    """Capability engine detail for the served run: measured and bridged models, the frontier, the forecast fan
    (10-90%), per-horizon pace chances, backtest scores against the baselines, and data limitations."""
    _check(target)
    return service.engine(target)



@router.get("/capability/success-curves")
def get_success_curves():
    """Task lengths the measured models complete at 95%, 90%, 80%, 75%, 50%, 25% and 10% success (display only)."""
    return service.success_curves()
