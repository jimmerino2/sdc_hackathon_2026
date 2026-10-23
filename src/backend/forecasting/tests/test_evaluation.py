"""Model selection, baselines, metrics and holdout discipline."""
import numpy as np
import pandas as pd

from forecasting import evaluation as E
from forecasting.models import BASELINES, CANDIDATES


def _bt(scores: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Fake backtest: per candidate a constant absolute error in selection and in holdout (one horizon)."""
    rows = []
    for c, (sel_err, hold_err) in scores.items():
        for role, err in (("selection", sel_err), ("holdout", hold_err)):
            for o in range(4):
                rows.append({"origin": f"{role}{o}", "h": 1, "candidate": c, "feature_set": "all", "role": role,
                             "actual": 1.0, "error": err, "geo": "AA", "logit_resid": err})
    return pd.DataFrame(rows)


ALL = {c: (1.0, 1.0) for c in CANDIDATES}


def test_selection_ignores_the_holdout():
    bt = _bt(ALL | {"ridge": (0.5, 5.0), "lightgbm": (0.9, 0.01)})
    t = E.select(bt)
    assert t.loc[t["chosen"], "candidate"].item() == "ridge"  # best in selection, despite its holdout


def test_simpler_model_wins_a_near_tie():
    bt = _bt(ALL | {"ridge": (0.50, 1.0), "drift": (0.505, 1.0)})
    t = E.select(bt)
    assert t.loc[t["chosen"], "candidate"].item() == "drift"


def test_every_candidate_is_compared_with_naive():
    t = E.select(_bt(ALL | {"ridge": (0.5, 0.5)}))
    assert set(BASELINES) <= set(t["candidate"]) and "naive" in BASELINES
    r = t[t["candidate"] == "ridge"].iloc[0]
    assert np.isclose(r["selection_mase_vs_naive"], 0.5) and np.isclose(r["holdout_mase_vs_naive"], 0.5)


def test_unavailable_evaluation_is_not_zero_error():
    m = E.metrics(pd.DataFrame({"origin": [1], "actual": [np.nan], "error": [np.nan]}))
    assert m["mae_pp"] is None and m["n"] == 0


def test_coverage_uses_selection_residuals_only():
    bt = _bt(ALL)
    bt.loc[bt["role"] == "holdout", "logit_resid"] = 100.0  # far outside any selection residual
    cov = E.coverage(bt, E.interval_quantiles(bt, ("selection",)))
    assert (cov["holdout_coverage_80"] == 0).all()
