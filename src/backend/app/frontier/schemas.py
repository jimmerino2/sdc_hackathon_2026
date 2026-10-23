"""Mirrors src/game-frontend/src/api/types.ts."""

from typing import Any, Literal

from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
ErrorCategory = Literal[
    "syntax", "name", "type", "missing_return", "wrong_value", "wrong_status",
    "validation", "runtime", "timeout", "resource_limit",
]


class RunnerHealth(BaseModel):
    status: Literal["ok", "degraded"]
    isolation: str
    simulated: bool = False


class CodeError(BaseModel):
    type: str
    message: str
    line: int | None = None
    category: ErrorCategory


class TestOutcome(BaseModel):
    id: str
    name: str
    passed: bool
    message: str | None = None
    category: ErrorCategory | None = None


class EvaluateIn(BaseModel):
    code: str = Field(max_length=20_000)


class EvaluationResult(BaseModel):
    run_id: str
    mission_id: str
    status: Literal["passed", "failed", "error", "timeout"]
    tests: list[TestOutcome]
    stdout: str = ""
    stderr: str = ""
    error: CodeError | None = None
    duration_ms: int


class RouteRequest(BaseModel):
    method: HttpMethod
    path: str = Field(pattern=r"^/[^\s]*$", max_length=200)
    query: dict[str, str] = {}
    headers: dict[str, str] = {}
    body: Any = None


class RouteResponse(BaseModel):
    status_code: int
    headers: dict[str, str] = {}
    body: Any = None


class RequestIn(BaseModel):
    code: str = Field(max_length=20_000)
    request: RouteRequest


class RequestResult(BaseModel):
    run_id: str
    request: RouteRequest
    response: RouteResponse | None = None
    error: CodeError | None = None
    logs: str = ""
    duration_ms: int


class ResourceNodeState(BaseModel):
    id: str
    resource: str
    remaining: int


class GameState(BaseModel):
    inventory: dict[str, int]
    equipped: str | None
    nodes: dict[str, ResourceNodeState]
    version: int


GameCommand = Literal["mine", "pickup", "equip"]
GameActionCode = Literal[
    "OK", "REJECTED_BY_ROUTE", "ROUTE_ERROR", "INVALID_RESPONSE", "NODE_DEPLETED", "MISSION_LOCKED", "NOT_ALLOWED",
]


class GameEffect(BaseModel):
    type: Literal["inventory_add", "inventory_remove", "node_update", "equip"]
    item: str | None = None
    qty: int | None = None
    node_id: str | None = None


class Reward(BaseModel):
    xp: int
    achievement_ids: list[str]
    granted: bool


class GameActionIn(BaseModel):
    command: GameCommand
    target: str = Field(max_length=64)
    mission_id: str | None = None
    code: str | None = Field(default=None, max_length=20_000)


class GameActionResult(BaseModel):
    action_id: str
    command: GameCommand
    target: str
    accepted: bool
    code: GameActionCode
    reason: str
    trace: RequestResult | None = None
    effects: list[GameEffect] = []
    state: GameState
    reward: Reward | None = None
