"""The /outlook API serves only promoted forecasts, with their status and warnings, and leaves /forecast alone."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.outlook import service
from forecasting import run
from forecasting.targets import all_specs

client = TestClient(create_app())


def test_warning_texts_never_contain_the_separator():
    for spec in all_specs().values():
        assert run.WARNING_SEP not in spec.history_warning


@pytest.mark.skipif(not service.targets(), reason="no forecast run yet")
def test_outlook_lists_targets_with_status_and_health():
    r = client.get("/outlook")
    assert r.status_code == 200
    for t in r.json():
        assert t["domain"] in ("skill_demand", "business_adoption", "occupation_adoption", "ai_capability")
        assert t["source_health"] and set(p["h"] for p in t["promoted"]) <= set(t["horizons"])


@pytest.mark.skipif(not service.targets(), reason="no forecast run yet")
def test_outlook_rows_are_the_promoted_forecast():
    for t in service.targets():
        rows = client.get(f"/outlook/{t}").json()
        promoted = {p["h"] for p in service.summary(t)["promoted"]}
        assert rows and {r["h"] for r in rows} == promoted
        assert all(isinstance(r["warnings"], list) and r["status"] for r in rows)
        spec = all_specs()[t]
        if spec.history_warning:
            assert all(spec.history_warning in r["warnings"] for r in rows)


def test_unknown_target_is_404_and_old_forecast_api_still_answers():
    assert client.get("/outlook/no_such_target").status_code == 404
    assert client.get("/forecast/sectors").status_code == 200


@pytest.mark.skipif(not service.targets(), reason="no forecast run yet")
def test_accuracy_is_per_unit_and_includes_no_change():
    for t in service.targets():
        unit = client.get(f"/outlook/{t}").json()[0]["unit"]
        acc = client.get(f"/outlook/{t}/accuracy", params={"unit": unit}).json()
        assert {a["h"] for a in acc} == {p["h"] for p in service.summary(t)["promoted"]}
        for a in acc:
            methods = {m["method"]: m for m in a["methods"]}
            assert "naive" in methods and a["served_model"] in methods
            assert a["naive_mae"] == methods["naive"]["mae"] and a["n_test_points"] > 0
            assert [m["mae"] for m in a["methods"]] == sorted(m["mae"] for m in a["methods"])
            if a["served_model"] == "naive":
                assert a["beats_naive"] is None
            else:
                assert a["beats_naive"] == (a["served_mae"] < a["naive_mae"])


@pytest.mark.skipif("frontier_time_horizon" not in service.targets(), reason="no capability run yet")
def test_regime_explanation_reproduces_the_published_chances():
    for r in client.get("/outlook/frontier_time_horizon/regime", params={"unit": "v1.1"}).json():
        g = [o["growth"] for o in r["possible_outcomes"]]
        assert len(g) == r["n"] > 0
        faster = sum(x > r["band_high_growth"] for x in g) / len(g)
        slower = sum(x < r["band_low_growth"] for x in g) / len(g)
        assert abs(faster - r["p_faster"]) < 1e-9 and abs(slower - r["p_slower"]) < 1e-9  # counts = published %
        assert r["band_low_growth"] < r["same_pace_growth"] < r["band_high_growth"]
        assert sum(m["served"] for m in r["methods"]) == 1
