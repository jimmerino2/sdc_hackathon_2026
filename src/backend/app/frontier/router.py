from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.frontier import runner, service
from app.frontier.schemas import (
    EvaluateIn,
    EvaluationResult,
    GameActionIn,
    GameActionResult,
    GameState,
    RequestIn,
    RequestResult,
    RunnerHealth,
)
from app.frontier.simulator import GameSimulator
from app.frontier.store import JsonFileStore

runner_router = APIRouter(prefix="/runner", tags=["frontier runner"])
game_router = APIRouter(prefix="/game", tags=["frontier game"])


@lru_cache
def get_simulator() -> GameSimulator:
    return GameSimulator(JsonFileStore(), service.send_request)


def _unavailable(e: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(e))


def _check_mission(mission_id: str):
    if mission_id not in runner.KNOWN_MISSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown mission {mission_id!r}")


@runner_router.get("/health", response_model=RunnerHealth)
def runner_health():
    """503 with an actionable message when learner code can't be run in isolation."""
    try:
        info = runner.health()
    except runner.RunnerUnavailable as e:
        raise _unavailable(e)
    return RunnerHealth(status="ok", isolation=info["isolation"])


@runner_router.post("/missions/{mission_id}/evaluate", response_model=EvaluationResult)
def evaluate(mission_id: str, payload: EvaluateIn):
    """Run the mission's tests against the submitted code inside the sandbox."""
    _check_mission(mission_id)
    try:
        return service.evaluate(mission_id, payload.code)
    except runner.RunnerUnavailable as e:
        raise _unavailable(e)
    except runner.RunnerFailure as e:
        raise HTTPException(status_code=502, detail=str(e))


@runner_router.post("/missions/{mission_id}/request", response_model=RequestResult)
def send_request(mission_id: str, payload: RequestIn):
    """Send one HTTP request to the learner's FastAPI app inside the sandbox."""
    _check_mission(mission_id)
    try:
        return service.send_request(mission_id, payload.code, payload.request)
    except runner.RunnerUnavailable as e:
        raise _unavailable(e)
    except runner.RunnerFailure as e:
        raise HTTPException(status_code=502, detail=str(e))


@game_router.get("/state", response_model=GameState)
def game_state():
    return get_simulator().get_state()


@game_router.post("/actions", response_model=GameActionResult)
def game_action(payload: GameActionIn):
    """Ask the trusted simulator to perform an action. `mine` consults the learner's route."""
    try:
        return get_simulator().act(payload.command, payload.target, payload.code)
    except runner.RunnerUnavailable as e:
        raise _unavailable(e)
    except runner.RunnerFailure as e:
        raise HTTPException(status_code=502, detail=str(e))


@game_router.post("/reset", response_model=GameState)
def game_reset():
    """Development helper: restore the world to its starting state."""
    return get_simulator().reset()
