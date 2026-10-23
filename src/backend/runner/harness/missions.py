"""Evaluation tests for each mission. Test ids match src/game-frontend/src/content/missions.ts.

Each test receives the learner module's namespace and raises TestFailure with a
learner-readable message when the behaviour is wrong. Tests check behaviour,
not a specific solution, and use more than one input where hard-coding is tempting.
"""

from dataclasses import dataclass
from typing import Callable


class TestFailure(Exception):
    def __init__(self, message, category="wrong_value"):
        super().__init__(message)
        self.category = category


@dataclass
class Test:
    id: str
    name: str
    fn: Callable


def need(ns, name, kind="variable"):
    if name not in ns:
        raise TestFailure(f"Couldn't find a {kind} called `{name}`. Check the spelling.", "name")
    return ns[name]


def need_function(ns, name):
    fn = need(ns, name, "function")
    if not callable(fn):
        raise TestFailure(f"`{name}` exists but isn't a function.", "type")
    return fn


def expect_equal(actual, expected, call):
    if actual is None and expected is not None:
        raise TestFailure(f"{call} returned None — did you forget `return`?", "missing_return")
    if actual != expected or type(actual) is not type(expected):
        raise TestFailure(f"{call} returned {actual!r}, expected {expected!r}.")


# ---------- w1-satchel ----------

def name_is_text(ns):
    v = need(ns, "explorer_name")
    if not isinstance(v, str):
        raise TestFailure(f"explorer_name is {v!r}, which isn't text. Put it in quotes.", "type")
    if not v.strip():
        raise TestFailure("explorer_name is an empty string. Put your name between the quotes.")


def rations_is_three(ns):
    v = need(ns, "rations")
    if isinstance(v, str):
        raise TestFailure(f"rations is the text {v!r}. Remove the quotes to make it a number.", "type")
    if type(v) is not int or v != 3:
        raise TestFailure(f"rations is {v!r}, expected the number 3.")


def has_map_true(ns):
    v = need(ns, "has_map")
    if v is not True:
        raise TestFailure(f"has_map is {v!r}, expected True.")


# ---------- w1-rocks ----------

def _can_mine(ns, resource, tool, expected):
    fn = need_function(ns, "can_mine")
    expect_equal(fn(resource, tool), expected, f"can_mine({resource!r}, {tool!r})")


# ---------- w1-ledger ----------

def copper_lookup(ns):
    fn = need_function(ns, "required_tool")
    expect_equal(fn("copper"), "stone_pickaxe", "required_tool('copper')")


def tin_added(ns):
    ledger = need(ns, "REQUIRED_TOOL")
    if not isinstance(ledger, dict):
        raise TestFailure("REQUIRED_TOOL should be a dictionary.", "type")
    if ledger.get("tin") != "stone_pickaxe":
        raise TestFailure(f"REQUIRED_TOOL['tin'] is {ledger.get('tin')!r}, expected 'stone_pickaxe'.")
    expect_equal(need_function(ns, "required_tool")("tin"), "stone_pickaxe", "required_tool('tin')")


def unknown_is_none(ns):
    fn = need_function(ns, "required_tool")
    try:
        got = fn("mithril")
    except KeyError:
        raise TestFailure("required_tool('mithril') crashed with KeyError. Use .get() or check `in` first.", "runtime")
    if got is not None:
        raise TestFailure(f"required_tool('mithril') returned {got!r}, expected None.")


# ---------- w1-signal ----------

def _handle(ns, method, path, status, body=None):
    fn = need_function(ns, "handle")
    got = fn(method, path)
    call = f"handle({method!r}, {path!r})"
    if got is None:
        raise TestFailure(f"{call} returned None — did you forget `return`?", "missing_return")
    if not isinstance(got, dict) or "status" not in got:
        raise TestFailure(f"{call} should return a dictionary with a 'status' key, got {got!r}.")
    if got["status"] != status:
        raise TestFailure(f"{call} returned status {got['status']!r}, expected {status}.", "wrong_status")
    if body is not None and got.get("body") != body:
        raise TestFailure(f"{call} returned body {got.get('body')!r}, expected {body!r}.")


# ---------- FastAPI helpers ----------

def client(ns):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = need(ns, "app")
    if not isinstance(app, FastAPI):
        raise TestFailure("`app` should be created with `FastAPI()`.", "type")
    return TestClient(app, raise_server_exceptions=False)


def expect_status(resp, status, call):
    if resp.status_code == 500:
        raise TestFailure(f"{call} crashed the server (500). Check the route's code.", "runtime")
    if resp.status_code == 404 and status != 404:
        raise TestFailure(f"{call} → 404: no route matched. Check the decorator's method and path.", "wrong_status")
    if resp.status_code != status:
        raise TestFailure(f"{call} → {resp.status_code}, expected {status}.", "wrong_status")


def body(resp):
    try:
        return resp.json()
    except ValueError:
        return resp.text


# ---------- w1-first-route ----------

def app_loads(ns):
    client(ns)


def status_route_200(ns):
    expect_status(client(ns).get("/status"), 200, "GET /status")


def status_body(ns):
    resp = client(ns).get("/status")
    expect_status(resp, 200, "GET /status")
    got = body(resp)
    if got is None:
        raise TestFailure("GET /status returned null — did you forget `return`?", "missing_return")
    if got != {"camp": "online"}:
        raise TestFailure(f"GET /status returned {got!r}, expected {{'camp': 'online'}}.")


# ---------- w1-copper-rights ----------

def _mine(ns, payload):
    return client(ns).post("/mine", json=payload)


def mine_success(ns):
    for resource in ("copper", "tin"):
        payload = {"resource": resource, "tool": "stone_pickaxe"}
        resp = _mine(ns, payload)
        call = f"POST /mine {payload}"
        expect_status(resp, 200, call)
        got = body(resp)
        if got is None:
            raise TestFailure(f"{call} returned null — your route needs to `return` a result.", "missing_return")
        expected = {"mined": True, "resource": resource, "amount": 1}
        if got != expected:
            raise TestFailure(f"{call} returned {got!r}, expected {expected!r}.")


def mine_wrong_tool(ns):
    for tool in ("hands", "wooden_spoon"):
        payload = {"resource": "copper", "tool": tool}
        expect_status(_mine(ns, payload), 403, f"POST /mine {payload}")


def mine_unknown(ns):
    for resource in ("dragonglass", "cheese"):
        payload = {"resource": resource, "tool": "stone_pickaxe"}
        expect_status(_mine(ns, payload), 400, f"POST /mine {payload}")


def mine_bad_body(ns):
    expect_status(_mine(ns, {"resource": "copper"}), 422, "POST /mine without a tool")


def mine_amount_fixed(ns):
    resp = _mine(ns, {"resource": "copper", "tool": "stone_pickaxe"})
    got = body(resp)
    if not isinstance(got, dict) or "amount" not in got:
        raise TestFailure("A successful mine should include an `amount`.", "missing_return" if got is None else "wrong_value")
    if got["amount"] != 1 or type(got["amount"]) is not int:
        raise TestFailure(f"amount is {got['amount']!r}; it must be exactly 1.")


MISSIONS = {
    "w1-satchel": {
        "tests": [
            Test("name_is_text", "explorer_name is a string", name_is_text),
            Test("rations_is_three", "rations equals 3", rations_is_three),
            Test("has_map_true", "has_map is True", has_map_true),
        ]
    },
    "w1-rocks": {
        "tests": [
            Test("copper_with_pickaxe", "copper + stone_pickaxe → True", lambda ns: _can_mine(ns, "copper", "stone_pickaxe", True)),
            Test("copper_with_hands", "copper + hands → False", lambda ns: _can_mine(ns, "copper", "hands", False)),
            Test(
                "other_resource",
                "unknown rock → False",
                lambda ns: (_can_mine(ns, "diamond", "stone_pickaxe", False), _can_mine(ns, "stone", "hands", False)),
            ),
        ]
    },
    "w1-ledger": {
        "tests": [
            Test("copper_lookup", "copper needs a stone_pickaxe", copper_lookup),
            Test("tin_added", "tin is in the ledger", tin_added),
            Test("unknown_is_none", "unknown ore returns None", unknown_is_none),
        ]
    },
    "w1-signal": {
        "tests": [
            Test("get_status_200", "GET /status → 200", lambda ns: _handle(ns, "GET", "/status", 200, {"camp": "online"})),
            Test(
                "post_status_405",
                "POST /status → 405",
                lambda ns: (_handle(ns, "POST", "/status", 405), _handle(ns, "DELETE", "/status", 405)),
            ),
            Test(
                "unknown_path_404",
                "GET /treasure → 404",
                lambda ns: (_handle(ns, "GET", "/treasure", 404), _handle(ns, "POST", "/mine", 404)),
            ),
        ]
    },
    "w1-first-route": {
        "tests": [
            Test("app_loads", "the app starts", app_loads),
            Test("status_route_200", "GET /status → 200", status_route_200),
            Test("status_body", 'body is {"camp": "online"}', status_body),
        ]
    },
    "w1-copper-rights": {
        "tests": [
            Test("mine_success", "copper + stone_pickaxe → 200", mine_success),
            Test("mine_wrong_tool", "copper + hands → 403", mine_wrong_tool),
            Test("mine_unknown", "unknown ore → 400", mine_unknown),
            Test("mine_bad_body", "missing field → 422", mine_bad_body),
            Test("mine_amount_fixed", "amount is exactly 1", mine_amount_fixed),
        ]
    },
}
