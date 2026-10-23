"""Turns raw sandbox output into the API contract. Nothing here executes learner code."""

import uuid

from app.frontier import runner
from app.frontier.schemas import CodeError, EvaluationResult, RequestResult, RouteRequest

TIMEOUT_ERROR = CodeError(
    type="Timeout",
    message="Your code ran out of time. Is something looping forever?",
    category="timeout",
)
OOM_ERROR = CodeError(
    type="MemoryLimit",
    message="Your code used more memory than the sandbox allows.",
    category="resource_limit",
)


def evaluate(mission_id: str, code: str) -> EvaluationResult:
    run_id = uuid.uuid4().hex
    raw = runner.run_job({"mode": "evaluate", "mission_id": mission_id, "code": code})
    if raw.get("timeout") or raw.get("oom"):
        return EvaluationResult(
            run_id=run_id,
            mission_id=mission_id,
            status="timeout" if raw.get("timeout") else "error",
            tests=[],
            error=TIMEOUT_ERROR if raw.get("timeout") else OOM_ERROR,
            duration_ms=runner.WALL_TIMEOUT_S * 1000 if raw.get("timeout") else 0,
        )
    return EvaluationResult(run_id=run_id, mission_id=mission_id, **raw)


def send_request(mission_id: str, code: str, request: RouteRequest) -> RequestResult:
    run_id = uuid.uuid4().hex
    raw = runner.run_job({"mode": "request", "mission_id": mission_id, "code": code, "request": request.model_dump()})
    if raw.get("timeout") or raw.get("oom"):
        return RequestResult(
            run_id=run_id,
            request=request,
            error=TIMEOUT_ERROR if raw.get("timeout") else OOM_ERROR,
            duration_ms=0,
        )
    return RequestResult(run_id=run_id, request=request, **raw)
