"""Frontier runner + simulator tests.

Simulator tests use a fake runner. Sandbox tests run real code through Docker
and are skipped when Docker or the runner image is unavailable.
"""

import pytest
from fastapi.testclient import TestClient

from app.frontier import runner, service
from app.frontier.schemas import RequestResult, RouteRequest, RouteResponse
from app.frontier.simulator import GameSimulator
from app.frontier.store import MemoryStore

# ---------- reference code ----------

STARTER_MINE = '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
REQUIRED_TOOL = {"copper": "stone_pickaxe", "tin": "stone_pickaxe"}

class MineRequest(BaseModel):
    resource: str
    tool: str

@app.post("/mine")
def mine(req: MineRequest):
    pass
'''

GOOD_MINE = '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
REQUIRED_TOOL = {"copper": "stone_pickaxe", "tin": "stone_pickaxe"}

class MineRequest(BaseModel):
    resource: str
    tool: str

@app.post("/mine")
def mine(req: MineRequest):
    if req.resource not in REQUIRED_TOOL:
        raise HTTPException(status_code=400, detail="Unknown resource")
    if req.tool != REQUIRED_TOOL[req.resource]:
        raise HTTPException(status_code=403, detail="Wrong tool")
    return {"mined": True, "resource": req.resource, "amount": 1}
'''

# Approves everything — passes the happy path only.
GREEDY_MINE = '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class MineRequest(BaseModel):
    resource: str
    tool: str

@app.post("/mine")
def mine(req: MineRequest):
    return {"mined": True, "resource": "copper", "amount": 1}
'''

SOLUTIONS = {
    "w1-satchel": 'explorer_name = "Robin"\nrations = 3\nhas_map = True\n',
    "w1-rocks": 'def can_mine(resource, tool):\n    return resource == "copper" and tool == "stone_pickaxe"\n',
    "w1-ledger": (
        'REQUIRED_TOOL = {"copper": "stone_pickaxe", "tin": "stone_pickaxe"}\n'
        "def required_tool(resource):\n    return REQUIRED_TOOL.get(resource)\n"
    ),
    "w1-signal": (
        "def handle(method, path):\n"
        '    if path == "/status":\n'
        '        if method == "GET":\n'
        '            return {"status": 200, "body": {"camp": "online"}}\n'
        '        return {"status": 405, "body": {}}\n'
        '    return {"status": 404, "body": {}}\n'
    ),
    "w1-first-route": (
        "from fastapi import FastAPI\napp = FastAPI()\n"
        '@app.get("/status")\ndef status():\n    return {"camp": "online"}\n'
    ),
    "w1-copper-rights": GOOD_MINE,
}


# ---------- simulator (no Docker) ----------


def fake_route(status: int, body=None, crash: bool = False):
    calls = []

    def send(mission_id: str, code: str, request: RouteRequest) -> RequestResult:
        calls.append(request)
        if crash:
            return RequestResult(run_id="x", request=request, duration_ms=0,
                                 error={"type": "KeyError", "message": "'copper'", "category": "runtime"})
        return RequestResult(run_id="x", request=request, duration_ms=0,
                             response=RouteResponse(status_code=status, body=body))

    send.calls = calls
    return send


OK_BODY = {"mined": True, "resource": "copper", "amount": 1}


def make_sim(send):
    return GameSimulator(MemoryStore(), send)


def test_mine_sends_trusted_tool_and_awards_one_copper():
    send = fake_route(200, OK_BODY)
    sim = make_sim(send)
    sim.act("pickup", "crate-1", None)
    r = sim.act("mine", "copper-1", "code")
    assert r.accepted and r.code == "OK"
    assert send.calls[-1].body == {"resource": "copper", "tool": "stone_pickaxe"}
    assert r.state.inventory["copper"] == 1
    assert r.state.nodes["copper-1"].remaining == 2
    assert r.reward and r.reward.granted


def test_reward_is_granted_once():
    sim = make_sim(fake_route(200, OK_BODY))
    sim.act("pickup", "crate-1", None)
    first = sim.act("mine", "copper-1", "code")
    second = sim.act("mine", "copper-1", "code")
    assert first.reward is not None
    assert second.reward is None
    assert second.state.inventory["copper"] == 2


def test_route_cannot_inflate_amount():
    sim = make_sim(fake_route(200, {"mined": True, "resource": "copper", "amount": 99}))
    sim.act("pickup", "crate-1", None)
    r = sim.act("mine", "copper-1", "code")
    assert not r.accepted and r.code == "INVALID_RESPONSE"
    assert "copper" not in r.state.inventory


def test_route_approving_bare_hands_is_rejected_by_simulator():
    sim = make_sim(fake_route(200, OK_BODY))
    r = sim.act("mine", "copper-1", "code")  # no pickaxe picked up
    assert not r.accepted and r.code == "INVALID_RESPONSE"
    assert r.state.inventory == {}


def test_route_refusal_and_crash_change_nothing():
    sim = make_sim(fake_route(403, {"detail": "Wrong tool"}))
    r = sim.act("mine", "copper-1", "code")
    assert r.code == "REJECTED_BY_ROUTE" and "Correct" in r.reason
    sim = make_sim(fake_route(0, crash=True))
    r = sim.act("mine", "copper-1", "code")
    assert r.code == "ROUTE_ERROR"
    assert r.state.nodes["copper-1"].remaining == 3


def test_null_body_is_explained():
    sim = make_sim(fake_route(200, None))
    sim.act("pickup", "crate-1", None)
    r = sim.act("mine", "copper-1", "code")
    assert r.code == "INVALID_RESPONSE" and "null" in r.reason


def test_node_depletes():
    sim = make_sim(fake_route(200, OK_BODY))
    sim.act("pickup", "crate-1", None)
    for _ in range(3):
        assert sim.act("mine", "copper-1", "code").accepted
    r = sim.act("mine", "copper-1", "code")
    assert r.code == "NODE_DEPLETED"
    assert r.state.inventory["copper"] == 3


def test_pickup_only_once():
    sim = make_sim(fake_route(200, OK_BODY))
    assert sim.act("pickup", "crate-1", None).accepted
    again = sim.act("pickup", "crate-1", None)
    assert not again.accepted
    assert again.state.inventory["stone_pickaxe"] == 1


# ---------- sandbox (Docker) ----------


def docker_ready():
    try:
        runner.health()
        return True
    except runner.RunnerUnavailable:
        return False


sandbox = pytest.mark.skipif(not docker_ready(), reason="Docker or frontier-runner image unavailable")


@sandbox
@pytest.mark.parametrize("mission_id", list(SOLUTIONS))
def test_reference_solutions_pass(mission_id):
    r = service.evaluate(mission_id, SOLUTIONS[mission_id])
    failing = [t for t in r.tests if not t.passed]
    assert r.status == "passed", failing


@sandbox
def test_starter_code_fails_meaningfully():
    r = service.evaluate("w1-copper-rights", STARTER_MINE)
    assert r.status == "failed"
    by_id = {t.id: t for t in r.tests}
    assert by_id["mine_success"].category == "missing_return"
    assert by_id["mine_wrong_tool"].category == "wrong_status"
    assert by_id["mine_bad_body"].passed  # Pydantic handles this one for free


@sandbox
def test_hardcoded_route_does_not_pass():
    r = service.evaluate("w1-copper-rights", GREEDY_MINE)
    by_id = {t.id: t for t in r.tests}
    assert not by_id["mine_success"].passed  # tin returns the wrong resource
    assert not by_id["mine_wrong_tool"].passed
    assert not by_id["mine_unknown"].passed


@sandbox
def test_unfilled_blank_reports_name_error_with_line():
    starter = "explorer_name = ___\nrations = ___\nhas_map = ___\n"
    r = service.evaluate("w1-satchel", starter)
    assert r.status == "error"
    assert r.error.category == "name" and r.error.line == 1


@sandbox
def test_syntax_error_has_line():
    r = service.evaluate("w1-rocks", "def can_mine(resource, tool)\n    return True\n")
    assert r.error.category == "syntax" and r.error.line == 1


@sandbox
def test_infinite_loop_times_out():
    r = service.evaluate("w1-rocks", "def can_mine(resource, tool):\n    while True:\n        pass\n")
    assert r.status == "failed"
    assert all(t.category == "timeout" for t in r.tests)


@sandbox
def test_sandbox_has_no_network():
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 80), timeout=2)\n"
        "    explorer_name = 'online'\n"
        "except OSError:\n"
        "    explorer_name = 'offline'\n"
        "rations = 3\nhas_map = True\n"
        "print(explorer_name)\n"
    )
    r = service.evaluate("w1-satchel", code)
    assert r.stdout.strip() == "offline"


@sandbox
def test_sandbox_runs_as_non_root_with_readonly_fs():
    code = (
        "import os\n"
        "try:\n"
        "    open('/harness/pwned', 'w')\n"
        "    w = 'writable'\n"
        "except OSError:\n"
        "    w = 'readonly'\n"
        "print(os.getuid(), w)\n"
        "explorer_name = 'x'\nrations = 3\nhas_map = True\n"
    )
    r = service.evaluate("w1-satchel", code)
    assert r.stdout.strip() == "10001 readonly"


@sandbox
def test_request_returns_real_response_and_crash_as_500():
    req = RouteRequest(method="POST", path="/mine", body={"resource": "copper", "tool": "hands"})
    r = service.send_request("w1-copper-rights", GOOD_MINE, req)
    assert r.response.status_code == 403 and r.response.body == {"detail": "Wrong tool"}

    crashing = GOOD_MINE.replace('if req.resource not in REQUIRED_TOOL:\n        raise HTTPException(status_code=400, detail="Unknown resource")\n    ', "")
    req = RouteRequest(method="POST", path="/mine", body={"resource": "dragonglass", "tool": "x"})
    r = service.send_request("w1-copper-rights", crashing, req)
    assert r.response.status_code == 500
    assert r.error.type == "KeyError" and r.error.line is not None


@sandbox
def test_end_to_end_game_mining_through_api(tmp_path, monkeypatch):
    from app.frontier import router as frontier_router
    from app.frontier.store import JsonFileStore
    from app.main import create_app

    frontier_router.get_simulator.cache_clear()
    monkeypatch.setattr(frontier_router, "JsonFileStore", lambda: JsonFileStore(tmp_path / "s.json"))
    client = TestClient(create_app())

    r = client.post("/game/actions", json={"command": "mine", "target": "copper-1", "code": GOOD_MINE}).json()
    assert r["code"] == "REJECTED_BY_ROUTE" and r["trace"]["response"]["status_code"] == 403

    client.post("/game/actions", json={"command": "pickup", "target": "crate-1"})
    r = client.post("/game/actions", json={"command": "mine", "target": "copper-1", "code": GOOD_MINE}).json()
    assert r["accepted"] and r["state"]["inventory"]["copper"] == 1

    r = client.post("/game/actions", json={"command": "mine", "target": "copper-1", "code": STARTER_MINE}).json()
    assert r["code"] == "INVALID_RESPONSE" and r["state"]["inventory"]["copper"] == 1

    assert client.get("/game/state").json()["inventory"]["copper"] == 1
    frontier_router.get_simulator.cache_clear()
