"""Forecast output and promotion: timestamps, versions, valid ranges, and no overwrite by a rejected model."""
import json
from pathlib import Path

import pandas as pd
import pytest

from forecasting import evaluation as E, run

LATEST = Path(run.__file__).parent / "output" / "latest_forecast.csv"


def _sel(holdout_n=10, insufficient=False):
    rows = []
    for h in E.HORIZONS:
        for c in ("naive", "ridge"):
            rows.append({"h": h, "candidate": c, "chosen": c == "ridge", "selection_mae_pp": 0.5,
                         "holdout_mae_pp": 0.4, "holdout_mase_vs_naive": 0.8 if c == "ridge" else 1.0,
                         "holdout_n_origins": holdout_n, "insufficient_history": insufficient})
    return pd.DataFrame(rows)


FRESH = {"indeed_ai_tracker": {"status": "fresh"}}
STALE = {"indeed_ai_tracker": {"status": "stale"}}


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "OUT", tmp_path)
    return tmp_path


def _issue(out, run_id, model):
    rows = pd.DataFrame([{"run_id": run_id, "h": h, "model": model} for h in E.HORIZONS])
    rows.to_csv(out / "forecast_log.csv", mode="a", header=not (out / "forecast_log.csv").exists(), index=False)
    return rows


def test_rejected_run_keeps_the_last_accepted_model(out):
    _issue(out, "good", "ridge")
    run.promote("good", "t1", _sel(), FRESH, None, "v1")
    _issue(out, "bad", "ridge")
    reg = run.promote("bad", "t2", _sel(holdout_n=2), STALE, None, "v2")
    assert all(e["run_id"] == "good" for e in reg["promoted"].values())
    assert [a["accepted"] for a in reg["attempts"]] == [True] * 3 + [False] * 3
    assert "target source is stale" in reg["attempts"][-1]["rejected_because"]
    assert set(pd.read_csv(out / "latest_forecast.csv")["run_id"]) == {"good"}


def test_insufficient_history_blocks_promotion():
    assert "insufficient history for selection" in run.acceptance(_sel(insufficient=True), FRESH, 1)


def test_status_labels_follow_the_holdout_comparison():
    assert run.status_for(pd.Series({"candidate": "naive", "holdout_mase_vs_naive": 1.0})) == "baseline"
    assert run.status_for(pd.Series({"candidate": "ridge", "holdout_mase_vs_naive": 0.9})) == "validated"
    assert run.status_for(pd.Series({"candidate": "ridge", "holdout_mase_vs_naive": 1.1})) == "not_demonstrably_better"


@pytest.mark.skipif(not LATEST.exists(), reason="no forecast run yet")
def test_published_forecast_is_timestamped_versioned_and_bounded():
    f = pd.read_csv(LATEST)
    assert f["run_id"].notna().all() and f["made_at"].notna().all() and f["data_as_of"].notna().all()
    assert ((f["low_pct"] <= f["forecast_pct"]) & (f["forecast_pct"] <= f["high_pct"])).all()
    assert f[["low_pct", "high_pct"]].stack().between(0, 100).all()
    assert set(f["h"]) == set(E.HORIZONS)
    reg = json.loads((LATEST.parent / "model_registry.json").read_text())
    assert all(e["model_version"] for e in reg["promoted"].values())
