"""Retraining the forecast on the data up to a quarter. Reads signals.csv (Supabase is switched off), so no network."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.forecast import retrain, service, signals
from app.main import app

client = TestClient(app)
SOFTWARE = "15-1252.00"


@pytest.fixture(scope="module", autouse=True)
def csv_only():
    settings = get_settings()
    old = settings.supabase_url
    settings.supabase_url = ""
    retrain.clear()
    yield
    settings.supabase_url = old
    retrain.clear()


LATE = ["2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]  # everything after 2025-Q1


def test_year_quarter_and_its_months():
    assert signals.year_quarter("2026-09") == "2026-Q3"
    assert signals.year_quarter("2026-01") == "2026-Q1"
    assert retrain.quarter_months("2026-Q2") == ["2026-04", "2026-05", "2026-06"]
    for bad in ("2026-Q5", "2026Q2", "", "2026-06"):
        with pytest.raises(retrain.RetrainError):
            retrain.quarter_months(bad)


def test_quarters_say_which_have_an_outcome():
    df, source = signals.load_signals()
    assert source == "csv"
    qs = {q["quarter"]: q for q in retrain.quarters(df)}
    assert list(qs)[0] == "2020-Q1"
    assert qs[list(qs)[-1]]["has_outcome"] is False  # its 3-month outcome isn't known yet
    assert qs[list(qs)[-2]]["has_outcome"] is True


def test_all_the_data_matches_the_stored_forecast():
    result, cached = retrain.retrain([])
    assert cached is False
    stored = pd.read_csv(service.OUTPUT_DIR / "forecast_output.csv")
    # the stored file is what ml/train_lgbm.py wrote from the same rows, so the retrain must agree with it
    mine = result.jobs[(result.jobs["onet_code"] == SOFTWARE) & (result.jobs["scenario"] == "Baseline")].sort_values("horizon_m")
    theirs = service._jobs()
    theirs = theirs[(theirs["onet_code"] == SOFTWARE) & (theirs["scenario"] == "Baseline")].sort_values("horizon_m")
    assert list(mine["change_pct"]) == list(theirs["change_pct"])
    assert list(mine["model_change_pct"]) == list(theirs["model_change_pct"])
    assert result.forecast_from == stored["origin_month"].iloc[0]


def test_leaving_out_the_newest_quarter_only_moves_the_start():
    full, _ = retrain.retrain([])
    result, _ = retrain.retrain(["2026-Q3"])
    assert result.forecast_from == "2026-06" and result.excluded == ["2026-Q3"]
    assert result.sector_index.index.max() == "2026-06"
    assert result.trained_rows <= full.trained_rows


def test_a_range_ending_in_the_past_trains_on_less():
    full, _ = retrain.retrain([])
    result, _ = retrain.retrain(LATE)  # 2019-Q1 to 2025-Q1
    assert result.forecast_from == "2025-03"
    assert result.trained_rows < full.trained_rows


def test_early_quarters_and_gaps_can_be_left_out_too():
    full, _ = retrain.retrain([])
    pandemic, _ = retrain.retrain([f"{y}-Q{n}" for y in (2020, 2021) for n in (1, 2, 3, 4)])
    assert pandemic.forecast_from == full.forecast_from  # the latest month is still used
    assert pandemic.trained_rows < full.trained_rows
    gap, _ = retrain.retrain(["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"])
    assert gap.trained_rows < full.trained_rows
    assert "2023-06" not in gap.sector_index.index  # the months left out aren't in the history either


def test_the_same_quarters_in_any_order_are_trained_once():
    first, _ = retrain.retrain(["2026-Q3", "2026-Q2"])
    again, cached = retrain.retrain(["2026-Q2", "2026-Q3"])
    assert cached is True and again is first


def test_too_little_data_or_a_bad_quarter_is_refused():
    everything = [q["quarter"] for q in retrain.quarters(signals.load_signals()[0])]
    with pytest.raises(retrain.RetrainError, match="Too little data"):
        retrain.retrain(everything[:-1])
    with pytest.raises(retrain.RetrainError, match="No data for 1999-Q1"):
        retrain.retrain(["1999-Q1"])
    with pytest.raises(retrain.RetrainError):
        retrain.retrain(["nonsense"])


def test_quarters_endpoint():
    res = client.get("/forecast/quarters")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "csv" and body["latest_quarter"] == body["quarters"][-1]["quarter"]
    assert body["default_trained_rows"] > 0


def test_retrain_endpoint_returns_the_jobs_forecast_without_those_quarters():
    res = client.post("/forecast/retrain", json={"onet_code": SOFTWARE, "excluded_quarters": ["2026-Q3"]})
    assert res.status_code == 200
    body = res.json()
    assert body["forecast_from"] == "2026-06" and body["excluded_quarters"] == ["2026-Q3"]
    assert {f["scenario"] for f in body["forecasts"]} == {"Slow", "Baseline", "Rapid AI"}
    first = body["forecasts"][0]
    assert first["forecast_from"] == "2026-06" and first["history"][-1]["month"] == "2026-06"
    assert [o["horizon_months"] for o in first["outlook"]] == [3, 6, 9, 12]


def test_retrain_endpoint_without_excluded_quarters_uses_all_the_data():
    body = client.post("/forecast/retrain", json={"onet_code": SOFTWARE}).json()
    assert body["excluded_quarters"] == [] and body["forecast_from"] == "2026-09"


def test_retrain_endpoint_rejects_bad_input():
    assert client.post("/forecast/retrain", json={"onet_code": SOFTWARE, "excluded_quarters": ["nonsense"]}).status_code == 422
    assert client.post("/forecast/retrain", json={"onet_code": SOFTWARE, "excluded_quarters": ["1999-Q1"]}).status_code == 422
    assert client.post("/forecast/retrain", json={"onet_code": "00-0000.00"}).status_code == 404


def test_refresh_is_off_unless_enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", False)  # whatever .env says
    assert client.post("/forecast/refresh").status_code == 403
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", True)
    assert client.post("/forecast/refresh").status_code == 204
    _, cached = retrain.retrain(["2026-Q3"])
    assert cached is False  # the refresh forgot it
