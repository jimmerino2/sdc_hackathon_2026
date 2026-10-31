from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.roadmap import planner, service
from app.roadmap.planner import PlanNode, PlanSection

SKILLS = [
    {"skill_id": "a", "skill_name": "A", "skill_type": "tech", "importance": 4.0, "level": None, "forecast_demand": 0.2},
    {"skill_id": "b", "skill_name": "B", "skill_type": "skill", "importance": 3.5, "level": 4, "forecast_demand": None},
    {"skill_id": "c", "skill_name": "C", "skill_type": "knowledge", "importance": 3.0, "level": 3, "forecast_demand": None},
    {"skill_id": "d", "skill_name": "D", "skill_type": "tech", "importance": 2.5, "level": None, "forecast_demand": None},
]


def _model(monkeypatch, reply):
    sent = []
    monkeypatch.setattr(planner, "_complete", lambda messages: sent.append(messages) or reply)
    monkeypatch.setattr(planner, "get_settings", lambda: SimpleNamespace(ai_model_mode="OPENROUTER", openrouter_api_key="k"))
    return sent


def test_selection_keeps_known_ids_once_in_the_models_order(monkeypatch):
    _model(monkeypatch, '{"skills": ["c", "zzz", "a", "c", 7]}')
    assert planner.select_skills("Role", None, SKILLS, {"stage": "fresh", "have": {"b": 1.0}}) == ["c", "a"]


def test_selection_asks_only_for_a_list_and_tells_the_model_the_learner(monkeypatch):
    sent = _model(monkeypatch, '{"skills": ["a"]}')
    planner.select_skills("Role", None, SKILLS, {"stage": "fresh", "have": {"b": 0.67}})
    system, user = sent[0][0]["content"], sent[0][1]["content"]
    assert "Do not group, order or label" in system and "Leave out skills with `have` of 0.67" in system
    assert "Learner stage: fresh" in user and '"have": 0.67' in user


def test_an_unusable_selection_is_a_502_after_one_retry(monkeypatch):
    sent = _model(monkeypatch, '{"skills": []}')
    with pytest.raises(HTTPException) as e:
        planner.select_skills("Role", None, SKILLS)
    assert e.value.status_code == 502 and len(sent) == 2


def test_fallback_selection_skips_what_the_learner_knows_and_prefers_demand():
    ids = planner.fallback_selection(SKILLS, {"b": 0.67})
    assert "b" not in ids and ids[0] == "a" and set(ids) == {"a", "c", "d"}


def test_organising_uses_every_chosen_skill_even_if_the_model_drops_one(monkeypatch):
    sent = _model(monkeypatch, '{"sections":[{"title":"T","units":[{"nodes":[{"skill_id":"a"},{"skill_id":"b","previous_nodes":["a"]}]}]}]}')
    plan = planner.organize_plan("Role", None, SKILLS[:3])
    assert {n.skill_id for sec in plan for u in sec.units for n in u} == {"a", "b", "c"}
    assert "use every one of them exactly once" in sent[0][0]["content"]


def test_the_fallback_plan_holds_every_skill_grouped_by_type():
    plan = planner.fallback_plan(SKILLS)
    assert [s.title for s in plan] == ["Core skills", "Tools and technology", "Subject knowledge"]
    assert {n.skill_id for sec in plan for u in sec.units for n in u} == {"a", "b", "c", "d"}


def test_complete_plan_adds_missing_skills_to_the_last_section():
    plan = [PlanSection("One", [[PlanNode("a")]]), PlanSection("Two", [[PlanNode("b")]])]
    done = planner.complete_plan(plan, SKILLS)
    assert [n.skill_id for u in done[-1].units for n in u][:1] == ["b"] and {n.skill_id for u in done[-1].units for n in u} == {"b", "c", "d"}
    assert [n.skill_id for u in done[0].units for n in u] == ["a"]


def test_a_chosen_list_always_ends_up_whole_on_the_roadmap(monkeypatch):
    chosen = SKILLS[:3]
    partial = '{"sections":[{"title":"T","units":[{"nodes":[{"skill_id":"b"}]}]}]}'  # the model keeps only one of three
    _model(monkeypatch, partial)
    ids = lambda plan: {n.skill_id for sec in plan for u in sec.units for n in u}
    assert ids(planner.organize_plan("Role", None, chosen)) == {"a", "b", "c"}
    assert ids(planner.complete_plan(planner.fallback_plan(chosen), chosen)) == {"a", "b", "c"}
