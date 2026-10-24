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
