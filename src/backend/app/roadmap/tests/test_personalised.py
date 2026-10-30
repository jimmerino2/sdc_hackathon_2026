from types import SimpleNamespace

from app.roadmap import planner, service
from app.roadmap.planner import PlanNode, PlanSection

PLAN = [
    PlanSection("Basics", [[PlanNode("a"), PlanNode("b", ["a"], True)], [PlanNode("c")]]),
    PlanSection("More", [[PlanNode("d", [], True)]]),
]


def _by_skill(rows):
    return {r["skill_id"]: r for r in rows}


def test_new_learner_starts_at_the_first_unit_with_no_required_prerequisite_open():
    rows = _by_skill(service.detail_rows(PLAN, "r", "x"))
    assert [rows[k]["status"] for k in "abcd"] == ["available", "locked", "locked", "locked"]


def test_skills_the_learner_has_start_completed_and_the_start_moves_on():
    rows = _by_skill(service.detail_rows(PLAN, "r", "x", {"a": "t0", "b": "t0"}))
    assert rows["a"]["status"] == rows["b"]["status"] == "completed" and rows["a"]["completed_at"] == "t0"
    assert rows["c"]["status"] == "available" and rows["d"]["status"] == "locked"
    assert rows["c"]["completed_at"] is None


def test_a_prerequisite_the_learner_has_unlocks_what_needs_it():
    rows = _by_skill(service.detail_rows(PLAN, "r", "x", {"a": "t0"}))
    assert rows["b"]["status"] == "available"


def test_levels_count_close_equivalents_and_use_the_three_steps():
    profile = SimpleNamespace(skills=[SimpleNamespace(name="Git", score=0.7), SimpleNamespace(name="Python", score=0.3)])
    levels = service.learner_levels(profile)
    assert levels["github"] == 0.67 and levels["python"] == 0.33 and levels["programming"] == 0.33
    assert levels["github"] >= planner.OWNED_LEVEL > levels["python"]


def test_the_planner_tells_the_model_about_the_learner(monkeypatch):
    sent = {}
    monkeypatch.setattr(planner, "_complete", lambda messages: sent.update(m=messages) or '{"sections":[{"title":"T","units":[{"nodes":[{"skill_id":"a"}]}]}]}')
    monkeypatch.setattr(planner, "get_settings", lambda: SimpleNamespace(ai_model_mode="OPENROUTER", openrouter_api_key="k"))
    skills = [{"skill_id": "a", "skill_name": "A", "skill_type": "tech", "importance": 4, "level": None}]
    planner.build_plan("Role", None, skills, {"stage": "fresh", "have": {"a": 0.67}})
    assert "Learner stage: fresh" in sent["m"][1]["content"] and '"have": 0.67' in sent["m"][1]["content"]
    assert "Personalise the plan" in sent["m"][0]["content"]
    planner.build_plan("Role", None, skills)
    assert "Personalise" not in sent["m"][0]["content"] and "have" not in sent["m"][1]["content"]
