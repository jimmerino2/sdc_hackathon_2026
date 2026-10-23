"""Trusted game simulation. The only place that changes inventory or world state.

Learner code is consulted (through the sandbox) about whether an action is
allowed, but its answer is validated against the game's own rules before any
effect is applied. A route can refuse an action; it can never invent one.
"""

import threading
import time
import uuid
from collections.abc import Callable

from app.frontier.schemas import (
    GameActionResult,
    GameEffect,
    GameState,
    RequestResult,
    Reward,
    RouteRequest,
)
from app.frontier.store import StateStore

GAME_MISSION_ID = "w1-copper-rights"
REQUIRED_TOOL = {"copper": "stone_pickaxe", "tin": "stone_pickaxe"}
NODE_CAPACITY = 3
REGROW_SECONDS = 60
FIRST_ORE_REWARD = Reward(xp=25, achievement_ids=["first-ore"], granted=True)

SendRequest = Callable[[str, str, RouteRequest], RequestResult]


def initial_state() -> dict:
    return {
        "inventory": {},
        "equipped": None,
        "nodes": {
            nid: {"id": nid, "resource": "copper", "remaining": NODE_CAPACITY, "depleted_at": None}
            for nid in ("copper-1", "copper-2")
        },
        "version": 1,
        "rewards": [],
    }


def detail_of(body) -> str:
    if isinstance(body, dict) and "detail" in body:
        d = body["detail"]
        return d if isinstance(d, str) else str(d)
    return ""


class GameSimulator:
    def __init__(self, store: StateStore, send_request: SendRequest):
        self.store = store
        self.send_request = send_request
        self.lock = threading.Lock()

    # ---------- state ----------

    def _load(self) -> dict:
        state = self.store.load() or initial_state()
        now = time.time()
        for node in state["nodes"].values():
            if node["remaining"] <= 0 and node["depleted_at"] and now - node["depleted_at"] >= REGROW_SECONDS:
                node["remaining"] = NODE_CAPACITY
                node["depleted_at"] = None
        return state

    @staticmethod
    def public(state: dict) -> GameState:
        return GameState(
            inventory={k: v for k, v in state["inventory"].items() if v > 0},
            equipped=state["equipped"],
            nodes={
                nid: {"id": n["id"], "resource": n["resource"], "remaining": n["remaining"]}
                for nid, n in state["nodes"].items()
            },
            version=state["version"],
        )

    def get_state(self) -> GameState:
        with self.lock:
            return self.public(self._load())

    def reset(self) -> GameState:
        with self.lock:
            state = initial_state()
            self.store.save(state)
            return self.public(state)

    # ---------- actions ----------

    def act(self, command: str, target: str, code: str | None) -> GameActionResult:
        # One action at a time: a double-click can't mine the same ore twice.
        with self.lock:
            state = self._load()
            handler = {"mine": self._mine, "pickup": self._pickup, "equip": self._equip}[command]
            result = handler(state, target, code)
            if result.accepted:
                state["version"] += 1
                self.store.save(state)
            result.state = self.public(state)
            return result

    def _result(self, command, target, accepted, code, reason, **extra) -> GameActionResult:
        return GameActionResult(
            action_id=uuid.uuid4().hex,
            command=command,
            target=target,
            accepted=accepted,
            code=code,
            reason=reason,
            state=GameState(inventory={}, equipped=None, nodes={}, version=0),  # replaced in act()
            **extra,
        )

    def _pickup(self, state, target, _code):
        if target != "crate-1":
            return self._result("pickup", target, False, "NOT_ALLOWED", "There's nothing to pick up there.")
        if state["inventory"].get("stone_pickaxe"):
            return self._result("pickup", target, False, "NOT_ALLOWED", "The crate is empty.")
        state["inventory"]["stone_pickaxe"] = 1
        state["equipped"] = "stone_pickaxe"
        return self._result(
            "pickup", target, True, "OK", "You found a stone pickaxe and equipped it.",
            effects=[GameEffect(type="inventory_add", item="stone_pickaxe", qty=1), GameEffect(type="equip", item="stone_pickaxe")],
        )

    def _equip(self, state, target, _code):
        if target == "none":
            state["equipped"] = None
            return self._result("equip", target, True, "OK", "Hands free.", effects=[GameEffect(type="equip")])
        if not state["inventory"].get(target):
            return self._result("equip", target, False, "NOT_ALLOWED", f"You don't have a {target}.")
        state["equipped"] = target
        return self._result("equip", target, True, "OK", f"Equipped {target}.", effects=[GameEffect(type="equip", item=target)])

    def _mine(self, state, target, code):
        node = state["nodes"].get(target)
        if node is None:
            return self._result("mine", target, False, "NOT_ALLOWED", "There's nothing to mine there.")
        if not code or not code.strip():
            return self._result("mine", target, False, "MISSION_LOCKED", "No mining route has been written yet.")
        if node["remaining"] <= 0:
            return self._result("mine", target, False, "NODE_DEPLETED", "This deposit is tapped out. It will regrow in a minute.")

        resource = node["resource"]
        tool = state["equipped"] or "hands"
        request = RouteRequest(method="POST", path="/mine", body={"resource": resource, "tool": tool})
        trace = self.send_request(GAME_MISSION_ID, code, request)

        verdict = self._judge(trace, resource, tool)
        if verdict is not None:
            code_, reason = verdict
            return self._result("mine", target, False, code_, reason, trace=trace)

        state["inventory"][resource] = state["inventory"].get(resource, 0) + 1
        node["remaining"] -= 1
        if node["remaining"] == 0:
            node["depleted_at"] = time.time()
        reward = None
        if "first-ore" not in state["rewards"]:
            state["rewards"].append("first-ore")
            reward = FIRST_ORE_REWARD
        return self._result(
            "mine", target, True, "OK", f"Your route approved it: +1 {resource}.",
            trace=trace,
            effects=[GameEffect(type="inventory_add", item=resource, qty=1), GameEffect(type="node_update", node_id=target)],
            reward=reward,
        )

    @staticmethod
    def _judge(trace: RequestResult, resource: str, tool: str) -> tuple[str, str] | None:
        """None means the route's answer is valid and the action may proceed."""
        resp = trace.response
        if resp is None or resp.status_code >= 500:
            why = trace.error.message if trace.error else "the server crashed"
            return "ROUTE_ERROR", f"Your route crashed: {why}"
        status = resp.status_code
        allowed = REQUIRED_TOOL.get(resource) == tool

        if status in (404, 405):
            return "ROUTE_ERROR", f"No POST /mine route answered ({status}). Check your decorator."
        if status == 422:
            return "REJECTED_BY_ROUTE", "Your route rejected the rig's request body (422). The rig sends {resource, tool} — check MineRequest's fields."
        if 400 <= status < 500:
            detail = detail_of(resp.body)
            suffix = f' ("{detail}")' if detail else ""
            if allowed:
                return "REJECTED_BY_ROUTE", f"Your route refused with {status}{suffix} — but a stone pickaxe should be allowed to mine {resource}."
            return "REJECTED_BY_ROUTE", f"Your route refused mining {resource} with {tool.replace('_', ' ')} ({status}){suffix}. Correct — you need a pickaxe."
        if not 200 <= status < 300:
            return "INVALID_RESPONSE", f"Unexpected status {status}."

        if not allowed:
            return "INVALID_RESPONSE", f"Your route approved mining {resource} with {tool.replace('_', ' ')}. The rig refuses — {resource} needs a {REQUIRED_TOOL.get(resource, 'proper tool')}."
        body = resp.body
        if body is None:
            return "INVALID_RESPONSE", "Your route answered 200 with an empty body (null). Did you forget to return the result?"
        if not isinstance(body, dict):
            return "INVALID_RESPONSE", f"The rig expected a JSON object, got {body!r}."
        if body.get("mined") is not True:
            return "INVALID_RESPONSE", f'Expected "mined": true, got {body.get("mined")!r}.'
        if body.get("resource") != resource:
            return "INVALID_RESPONSE", f'Expected "resource": "{resource}", got {body.get("resource")!r}.'
        amount = body.get("amount")
        if type(amount) is not int or amount != 1:
            return "INVALID_RESPONSE", f'Expected "amount": 1, got {amount!r}. No route gets to hand out free ore.'
        return None
