"""POST /roadmap/stream, with the build replaced so nothing touches the database or the model."""
import json
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.deps import get_supabase_admin
from app.main import app
from app.roadmap import service
from app.roadmap.schemas import Roadmap

client = TestClient(app)
BODY = {"profile_id": str(uuid4()), "onet_code": "15-1252.00"}


def _events(res) -> list[dict]:
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def _roadmap() -> Roadmap:
    return Roadmap(profile_id=BODY["profile_id"], onet_code=BODY["onet_code"], title="Software Developers", description=None,
                   roadmap_id=None, status=None, current=None, sections=[])


def setup_function():
    app.dependency_overrides[get_supabase_admin] = lambda: object()


def teardown_function():
    app.dependency_overrides.clear()


def test_stream_reports_progress_then_the_result(monkeypatch):
    def fake(db, profile_id, onet_code, replace, priority_skills=None, on_event=None, skills=None):
        on_event({"type": "role", "title": "Software Developers", "onet_code": onet_code})
        on_event({"type": "plan", "reused": True})
        on_event({"type": "roadmap", "roadmap": _roadmap().model_dump(mode="json")})
        return _roadmap()

    monkeypatch.setattr(service, "create_roadmap", fake)
    res = client.post("/roadmap/stream", json=BODY)
    assert res.headers["content-type"].startswith("text/event-stream")
    events = _events(res)
    assert [e["type"] for e in events] == ["role", "plan", "roadmap", "result"]
    assert events[-1]["title"] == "Software Developers"


def test_stream_turns_an_http_error_into_a_failed_event(monkeypatch):
    def fake(*args, **kwargs):
        raise HTTPException(status_code=409, detail="already built")

    monkeypatch.setattr(service, "create_roadmap", fake)
    assert _events(client.post("/roadmap/stream", json=BODY)) == [{"type": "failed", "status": 409, "message": "already built"}]


def test_stream_passes_the_priority_skills_on(monkeypatch):
    seen = {}

    def fake(db, profile_id, onet_code, replace, priority_skills=None, on_event=None, skills=None):
        seen["priority"] = priority_skills
        return _roadmap()

    monkeypatch.setattr(service, "create_roadmap", fake)
    _events(client.post("/roadmap/stream", json={**BODY, "priority_skills": ["Python"]}))
    assert seen["priority"] == ["Python"]


def test_stream_passes_the_chosen_skills_on(monkeypatch):
    seen = {}

    def fake(db, profile_id, onet_code, replace, priority_skills=None, on_event=None, skills=None):
        seen["skills"] = skills
        return _roadmap()

    monkeypatch.setattr(service, "create_roadmap", fake)
    _events(client.post("/roadmap/stream", json={**BODY, "skills": ["Python", "SQL"]}))
    assert seen["skills"] == ["Python", "SQL"]


def test_the_skill_list_endpoint_returns_the_selection(monkeypatch):
    from app.roadmap.schemas import SelectedSkill, SkillSelection
    monkeypatch.setattr(service, "suggest_skills", lambda db, profile_id, onet_code: SkillSelection(
        onet_code=onet_code, title="Software Developers", source="ai", skills=[SelectedSkill(skill_id="a", skill_name="Python", skill_type="tech")]))
    res = client.post("/roadmap/skills", json=BODY)
    assert res.status_code == 200 and res.json()["skills"][0]["skill_name"] == "Python" and res.json()["source"] == "ai"
