"""The match formula, its breakdown and the What-If simulator: one calculation, reconciled, and nothing saved."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.deps import get_supabase_admin
from app.jobs import scoring, service, simulator
from app.jobs.schemas import RecommendRequest, RecommendResponse, SimulatedSkill
from app.main import create_app
from app.profile import service as profiles
from app.resume.schemas import SkillScore

SKILLS = [SkillScore(name="Python", score=0.67), SkillScore(name="Structured query language SQL", score=1.0)]


@pytest.fixture(autouse=True)
def no_supabase(monkeypatch):
    monkeypatch.setattr(service, "_role_icons", lambda: {})
    monkeypatch.setattr(service, "_role_sdgs", lambda: {})


def run(tried=(), stage="fresh", focus=None):
    return simulator.simulate("p", SKILLS, stage, [], [SimulatedSkill(**t) for t in tried], 12, focus)


def test_shares_add_up_to_one_and_keep_the_relative_weights():
    s = scoring.shares()
    assert sum(s.values()) == pytest.approx(1)
    assert s["skills"] == pytest.approx(0.35 / 1.05) and s["education"] == pytest.approx(0.10 / 1.05)
    assert s["interests"] / s["education"] == pytest.approx(2.5)
    without = scoring.shares(False)
    assert "interests" not in without and sum(without.values()) == pytest.approx(1)
    assert without["skills"] == pytest.approx(0.4375)


@pytest.mark.parametrize("parts", [(0.6, 0.5, 0.7, 0.4), (1, 1, 1, 1), (0, 0, 0, 0), (0.4, 0.33, 0.5, None)])
def test_breakdown_reconciles_with_combine(parts):
    b = scoring.breakdown(*parts)
    assert sum(c["points"] for c in b["components"]) == pytest.approx(b["raw_score"], abs=2e-4)
    assert sum(c["share"] for c in b["components"]) == pytest.approx(1, abs=2e-4)
    assert b["match_percent"] == round(100 * scoring.combine(*parts))


def test_score_stays_in_range_at_the_extremes():
    assert scoring.combine(1, 1, 1, 1) == pytest.approx(1)
    assert scoring.combine(0, 0, 0, 0) == 0


def test_recommend_breakdown_matches_every_scenario_and_ranks_follow_the_score():
    res = service.recommend(RecommendRequest(top_skills=SKILLS, skills=SKILLS), "p", "fresh")
    assert len(res.jobs) == 8 and res.stage == "fresh"
    for j in res.jobs:
        assert len(j.skill_fit) == j.skills_total
        for o in j.outlook:
            assert o.breakdown.match_percent == o.match_percent
            assert next(c for c in o.breakdown.components if c.key == "skills").score == j.match_parts.skills
    for s, _ in service.SCENARIOS:
        order = sorted((o.rank, o.match_percent) for j in res.jobs for o in j.outlook if o.scenario == s)
        assert [r for r, _ in order] == list(range(1, 9))
        assert [m for _, m in order] == sorted((m for _, m in order), reverse=True)


def test_education_is_shared_by_every_role():
    res = service.recommend(RecommendRequest(top_skills=SKILLS, skills=SKILLS), "p", "working")
    assert {j.match_parts.education for j in res.jobs} == {1.0}


def test_simulating_nothing_changes_nothing():
    res = run()
    assert len(res.roles) == 8
    for r in res.roles:
        assert not r.skills_gained and not r.skills_replaced
        for s in r.scenarios:
            assert s.change == 0 and s.current_rank == s.simulated_rank and s.current == s.simulated


def test_simulated_scores_are_the_matching_engines_own():
    tried = [{"name": "JavaScript", "score": 0.67}]
    res = run(tried)
    real = service.recommend(RecommendRequest(top_skills=SKILLS, skills=[*SKILLS, SkillScore(**tried[0])]), "p", "fresh")
    jobs = {j.onet_code: j for j in real.jobs}
    for r in res.roles:
        for s in r.scenarios:
            o = next(o for o in jobs[r.onet_code].outlook if o.scenario == s.scenario)
            assert s.simulated_percent == o.match_percent and s.simulated_rank == o.rank and s.simulated == o.breakdown


def test_a_skill_the_learner_has_is_not_duplicated_or_lowered():
    assert run([{"name": "Structured query language SQL", "score": 0.33}]).model_dump()["roles"] == run().model_dump()["roles"]
    higher = run([{"name": "Python", "score": 1.0}])
    assert any(g.name == "Python" and g.before == 0.67 and g.after == 1.0 for r in higher.roles for g in r.skills_gained)


def test_proficiency_level_changes_the_result():
    gain = lambda res: sum(s.change for r in res.roles for s in r.scenarios)  # noqa: E731
    assert gain(run([{"name": "JavaScript", "score": 1.0}])) > gain(run([{"name": "JavaScript", "score": 0.33}])) >= 0


def test_explanations_name_what_really_changed():
    res = run([{"name": "JavaScript", "score": 1.0}])
    up = [r for r in res.roles if r.skills_gained and r.scenarios[0].change > 0]
    assert up
    for r in up:
        assert r.skills_gained[0].name in r.scenarios[0].explanation and str(r.scenarios[0].change) in r.scenarios[0].explanation
        assert r.title in r.scenarios[0].explanation
    for r in res.roles:
        if not r.skills_gained:
            assert "None of the skills you added" in r.scenarios[0].explanation


def test_scenarios_all_come_back_and_can_differ():
    res = run([{"name": "JavaScript", "score": 1.0}])
    assert [s.scenario for s in res.summary] == ["Rapid AI", "Baseline", "Slow"]
    assert all({s.scenario for s in r.scenarios} == {"Rapid AI", "Baseline", "Slow"} for r in res.roles)
    assert any(len({s.current_percent for s in r.scenarios}) > 1 for r in res.roles)


def test_options_never_offer_a_skill_at_the_learner_level_and_are_real_gains():
    res = run()
    assert res.options
    assert all(o.trial > o.current for o in res.options)
    for o in res.options[:5]:
        assert max(g.best_change for g in o.gains) > 0
        one = run([{"name": o.name, "score": o.trial}], focus=res.focus_role)
        best = next(g for g in o.gains if g.scenario == "Rapid AI")
        focus_role = next(r for r in one.roles if r.onet_code == res.focus_role)
        assert next(s for s in focus_role.scenarios if s.scenario == "Rapid AI").change == best.best_change


def test_options_are_only_the_skills_onet_links_to_the_focus_role():
    top = run()
    codes = [r.onet_code for r in top.roles]
    assert top.focus_role in codes  # the default is one of the matched roles
    for code in codes[:3]:
        res = run(focus=code)
        assert res.focus_role == code and res.options
        assert {o.name for o in res.options} <= simulator._linked(code) <= set(simulator._catalogue().values())
        assert {g.best_role for o in res.options for g in o.gains} == {next(r.title for r in res.roles if r.onet_code == code)}


def test_a_zero_gain_is_a_real_zero_for_the_focus_role():
    res = run()
    still = next(o for o in reversed(res.options) if max(g.best_change for g in o.gains) == 0)
    one = run([{"name": still.name, "score": still.trial}], focus=res.focus_role)
    focus_role = next(r for r in one.roles if r.onet_code == res.focus_role)
    assert all(s.change == 0 for s in focus_role.scenarios)
    assert one.options == []


def test_an_unmatched_focus_role_is_refused():
    with pytest.raises(simulator.UnknownRole):
        run(focus="99-9999.99")


def test_unknown_skill_is_refused():
    with pytest.raises(simulator.UnknownSkill):
        run([{"name": "Underwater basket weaving", "score": 1.0}])


class Profile:
    skills, stage, interests = SKILLS, "fresh", []


def test_simulate_endpoint_writes_nothing(monkeypatch):
    db = MagicMock()
    app = create_app()
    app.dependency_overrides[get_supabase_admin] = lambda: db
    monkeypatch.setattr(profiles, "get_profile", lambda *_: Profile)
    saved = MagicMock()
    monkeypatch.setattr(profiles, "save_suggestions", saved)
    r = TestClient(app).post("/jobs/simulate", json={"profile_id": str(uuid4()), "skills": [{"name": "JavaScript", "score": 0.67}]})
    assert r.status_code == 200 and len(r.json()["roles"]) == 8
    saved.assert_not_called()
    table = db.table.return_value
    assert not table.update.called and not table.insert.called and not table.upsert.called


def test_saved_set_keeps_its_scores_and_gains_a_reconciled_breakdown():
    fresh = service.recommend(RecommendRequest(top_skills=SKILLS, skills=SKILLS), "p", "fresh").model_dump()
    for j in fresh["jobs"]:
        j.pop("skill_fit")
        for o in j["outlook"]:
            o.pop("breakdown"), o.pop("rank")
    fresh["jobs"][0]["outlook"][0]["match_percent"] += 7  # as if made by an older formula
    fresh["note"] = "old"
    out = service.with_breakdowns(RecommendResponse(**fresh))
    assert out.jobs[0].outlook[0].breakdown is None
    assert out.jobs[0].outlook[0].match_percent == fresh["jobs"][0]["outlook"][0]["match_percent"]
    assert all(o.breakdown.match_percent == o.match_percent for j in out.jobs[1:] for o in j.outlook)
    assert "35%" not in out.note


def test_a_skill_with_rising_demand_counts_double_in_the_skills_part():
    role = next(r for r in service._roles() if r["onet_code"] == "15-1252.00")
    key = service._with_key_skills(role, set())
    assert key["trending"] and key["trending"] <= set(key["key_skills"])
    plain = dict(role_weights := {n: w for n, w in role["tools"] + role["abilities"]})
    for name in key["key_skills"]:
        factor = service.TREND_WEIGHT if name in key["trending"] else 1.0
        assert key["weights"][name] == pytest.approx(plain[name] * factor)


def test_a_role_without_trend_data_is_scored_exactly_as_before():
    role = next(r for r in service._roles() if r["onet_code"] == "15-2051.00")
    key = service._with_key_skills(role, set())
    assert not key["trending"] and all(key["weights"][n] == dict(role["tools"] + role["abilities"])[n] for n in key["key_skills"])


def test_rising_skills_are_listed_first_and_flagged():
    res = run(focus="15-1252.00")
    flags = [o.rising for o in res.options]
    assert any(flags) and flags == sorted(flags, reverse=True)  # every rising skill comes before every other
    assert not any(o.rising for o in run(focus="15-2051.00").options)  # no trend data for that role's skills
