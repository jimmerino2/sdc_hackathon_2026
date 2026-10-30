"""The transparency layer reports the pipelines' own outputs and never dresses up a baseline."""
import json

import pytest
from fastapi.testclient import TestClient

from app.forecast import service as role_forecast
from app.main import create_app
from app.methodology import service
from app.outlook import service as outlook
from app.roadmap.planner import PlanNode, PlanSection
from app.roadmap.service import prioritised

client = TestClient(create_app())
INFO = client.get("/methodology").json()


def test_endpoint_describes_every_series():
    assert {"btos_ai_use_rate", "worker_genai_use_rate", "frontier_time_horizon", "ai_mention_share", "role_postings"} <= set(INFO["forecasts"])
    assert "United States" in INFO["forecasts"]["btos_ai_use_rate"]["provenance"]["geography"]
    assert "US historical data" in INFO["geography"]["note"]


@pytest.mark.parametrize("target", list(service.OUTLOOK_TEXT))
def test_served_models_match_the_registry(target):
    reg = json.loads((outlook.OUTPUT_DIR / target / "model_registry.json").read_text())
    rows = {r["h"]: r for r in INFO["forecasts"][target]["configuration"]["horizons"]}
    assert set(rows) == {int(h) for h in reg["promoted"]}
    for h, e in reg["promoted"].items():
        assert rows[int(h)]["is_baseline"] == (e["model"] == "naive") and rows[int(h)]["status"] == e["status"]


def test_baseline_is_never_said_to_outperform_itself():
    for f in INFO["forecasts"].values():
        by_h = {r["h"]: r for r in f["configuration"]["horizons"]}
        for t in f["reliability"]["horizons"]:
            if by_h[t["h"]]["is_baseline"] and f["id"] != "role_postings":
                assert t["outperformed"] is None


def test_role_forecast_is_reported_as_a_baseline_with_its_true_comparison():
    f = INFO["forecasts"]["role_postings"]
    assert all(r["is_baseline"] and "LightGBM" in r["status_text"] for r in f["configuration"]["horizons"])
    scores = role_forecast._meta()["by_horizon"]["12"]["holdout"]["scores"]
    t = next(r for r in f["reliability"]["horizons"] if r["h"] == 12)
    assert t["model_error"] == scores["yoy (last year's pace repeats)"]["MAE"] and t["baseline_error"] == scores["flat (index unchanged)"]["MAE"]
    assert t["outperformed"] is (t["model_error"] < t["baseline_error"])


def test_bands_are_labelled_by_how_they_were_made():
    assert INFO["forecasts"]["btos_ai_use_rate"]["uncertainty"]["label"] == "Historical error band"
    assert INFO["forecasts"]["frontier_time_horizon"]["uncertainty"]["label"] == "80% predictive interval"


def test_scenarios_are_assumptions_and_carry_their_real_effect():
    s = INFO["scenarios"]
    assert "not learned from data" in s["summary"]
    assert {f["scenario"]: f["effect_12m"] for f in s["futures"]} == role_forecast._meta()["scenario_effect_assumption_12m"]


def test_skill_demand_defines_its_denominator_when_built():
    f = INFO["forecasts"].get("skill_demand")
    if f is None:
        pytest.skip("occupational pipeline not built")
    assert "Hacker News" in f["measure"]["metric"] and "Malaysian" in f["measure"]["value_type"]
    assert INFO["emerging"]["kind"].startswith("An observed rise")


def _node(i):
    return PlanNode(i, [], True)


def test_priority_moves_whole_units_and_sections_and_loses_nothing():
    plan = [PlanSection("A", [[_node("a1")], [_node("a2")]]), PlanSection("B", [[_node("b1")], [_node("b2"), _node("b3")]])]
    out = prioritised(plan, {"b3"})
    assert [s.title for s in out] == ["B", "A"]
    assert [n.skill_id for n in out[0].units[0]] == ["b2", "b3"]
    assert sorted(n.skill_id for s in out for u in s.units for n in u) == ["a1", "a2", "b1", "b2", "b3"]
    assert prioritised(plan, set()) == plan


def test_the_role_panel_credits_every_source_it_uses():
    prov = INFO["forecasts"]["role_postings"]["provenance"]
    assert prov["license"] == "CC-BY-4.0"
    assert [a["source"] for a in prov["also_uses"]] == ["Indeed AI Tracker"]
