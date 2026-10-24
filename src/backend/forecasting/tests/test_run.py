"""Forecast output and promotion: timestamps, versions, valid ranges, and no overwrite by a rejected model."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forecasting import run
from forecasting.targets import all_specs, skill_demand

SPEC = skill_demand.SPEC
OUTPUT = Path(run.__file__).parent / "output"


def _sel(holdout_n=10, insufficient=False):
    rows = []
    for h in SPEC.horizons:
        for c in ("naive", "ridge"):
            rows.append({"h": h, "candidate": c, "chosen": c == "ridge", "selection_mae": 0.5,
                         "holdout_mae": 0.4, "holdout_mase_vs_naive": 0.8 if c == "ridge" else 1.0,
                         "holdout_n_origins": holdout_n, "insufficient_history": insufficient})
    return pd.DataFrame(rows)


FRESH = {"indeed_ai_tracker": {"status": "fresh"}}
STALE = {"indeed_ai_tracker": {"status": "stale"}}


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "OUT", tmp_path)
    return tmp_path


def _issue(out, run_id, model):
    rows = pd.DataFrame([{"run_id": run_id, "h": h, "model": model} for h in SPEC.horizons])
    rows.to_csv(out / "forecast_log.csv", mode="a", header=not (out / "forecast_log.csv").exists(), index=False)
    return rows


def test_rejected_run_keeps_the_last_accepted_model(out):
    _issue(out, "good", "ridge")
    run.promote(SPEC, out, "good", "t1", _sel(), FRESH, "v1")
    _issue(out, "bad", "ridge")
    reg = run.promote(SPEC, out, "bad", "t2", _sel(holdout_n=2), STALE, "v2")
    assert all(e["run_id"] == "good" for e in reg["promoted"].values())
    assert [a["accepted"] for a in reg["attempts"]] == [True] * 3 + [False] * 3
    assert "target source is stale" in reg["attempts"][-1]["rejected_because"]
    assert set(pd.read_csv(out / "latest_forecast.csv")["run_id"]) == {"good"}


def test_insufficient_history_blocks_promotion():
    assert "insufficient history for selection" in run.acceptance(SPEC, _sel(insufficient=True), FRESH, 1)


def test_status_labels_follow_the_holdout_comparison():
    assert run.status_for(pd.Series({"candidate": "naive", "holdout_mase_vs_naive": 1.0})) == "baseline"
    assert run.status_for(pd.Series({"candidate": "ridge", "holdout_mase_vs_naive": 0.9})) == "validated"
    assert run.status_for(pd.Series({"candidate": "ridge", "holdout_mase_vs_naive": 1.1})) == "not_demonstrably_better"
    # a near-tie is not evidence: "validated" needs a margin over naive
    assert run.status_for(pd.Series({"candidate": "ridge", "holdout_mase_vs_naive": 0.9997})) == "not_demonstrably_better"


@pytest.mark.parametrize("tid", list(all_specs()))
def test_published_forecast_is_timestamped_versioned_and_bounded(tid):
    latest = OUTPUT / tid / "latest_forecast.csv"
    if not latest.exists():
        pytest.skip("no forecast run yet")
    f = pd.read_csv(latest, dtype={"unit": str})
    log = pd.read_csv(OUTPUT / tid / "forecast_log.csv", dtype={"unit": str})
    assert set(f["unit"]) <= set(log["unit"])  # codes survive the round trip (e.g. SOC "00")
    assert f["run_id"].notna().all() and f["made_at"].notna().all() and f["data_as_of"].notna().all()
    lo, fc, hi = ("low", "forecast", "high") if "forecast" in f else ("low_pct", "forecast_pct", "high_pct")
    assert ((f[lo] <= f[fc]) & (f[fc] <= f[hi])).all()
    if all_specs()[tid].value_unit == "percent":
        assert f[[lo, hi]].stack().between(0, 100).all()
    assert (f["target"] == tid).all()
    reg = json.loads((OUTPUT / tid / "model_registry.json").read_text())
    assert all(e["model_version"] for e in reg["promoted"].values())
    assert {int(h) for h in reg["promoted"]} == set(f["h"])  # only promoted horizons are served
    spec = all_specs()[tid]
    if spec.history_warning:
        assert f["warnings"].str.contains(spec.history_warning, regex=False).all()
    if spec.regimes:
        p = f[["p_acceleration", "p_stable", "p_slowdown"]]
        assert np.allclose(p.sum(axis=1), 1) and p.stack().between(0, 1).all()
