"""AI capability: frontier construction, METR version separation, measurement lag, local trend and regimes."""
import numpy as np
import pandas as pd
import pytest

from forecasting import evaluation as E, features as F
from forecasting.models import LocalTrend, kalman_llt
from forecasting.targets import capability_metr as CM


def _obs():
    """Synthetic capability vintages (not real data). v1.0 vintages in 2025, v1.1 from 2026-03; the v1.1 suite
    re-measures an old model lower, and a model released 2025-12 is only measured in the 2026-04 vintage."""
    rows = []
    def add(vid, when, version, model, rel, value):
        rows.append({"vintage_id": vid, "available_at": pd.Timestamp(when, tz="UTC"), "measure": CM.MEASURE,
                     "metr_version": version, "model": model, "release_date": pd.Timestamp(rel), "value": value})
    v10, v11 = "METR-Horizon-v1.0", "METR-Horizon-v1.1"
    for vid, when in (("a", "2025-06-10"), ("b", "2025-11-20")):
        add(vid, when, v10, "m1", "2024-03-01", 10.0)
        add(vid, when, v10, "m2", "2025-01-15", 40.0)
    add("b", "2025-11-20", v10, "m3", "2025-07-01", 80.0)
    for vid, when in (("c", "2026-03-20"), ("d", "2026-04-25")):
        add(vid, when, v11, "m1", "2024-03-01", 6.0)  # re-measured lower under v1.1
        add(vid, when, v11, "m3", "2025-07-01", 90.0)
        add(vid, when, v10, "m1", "2024-03-01", 10.0)  # legacy row still listed
    add("d", "2026-04-25", v11, "m4", "2025-12-01", 300.0)  # measured late
    d = pd.DataFrame(rows)
    return {"obs": d, "active": CM.active_vintages(d)}


def test_frontier_holds_between_releases_and_never_falls():
    rows = pd.DataFrame({"release_date": pd.to_datetime(["2024-01-10", "2024-04-02", "2024-05-01"]),
                         "value": [10.0, 30.0, 20.0]})
    f = CM.frontier(rows, pd.Period("2024-06", freq="M")).set_index("period")["value"]
    assert list(f) == [10, 10, 10, 30, 30, 30]  # held through Feb-Mar and Jun; the weaker May model changes nothing


def test_versions_are_separate_and_active_only_while_current():
    data = _obs()
    assert {u: [v for _, v in vs] for u, vs in data["active"].items()} == {"v1.0": ["a", "b"], "v1.1": ["c", "d"]}
    s = CM.snapshot(data["obs"], data["active"], pd.Timestamp("2026-05-01", tz="UTC"))
    assert set(s.values["unit"]) == {"v1.1"}  # v1.0 is retired once v1.1 is current
    v11 = s.values.set_index("period")["value"]
    assert v11.loc[pd.Period("2024-06", freq="M")] == 6.0  # the v1.0 measurement (10) never leaks in


def test_measurement_lag_keeps_unmeasured_months_out():
    data = _obs()
    s = CM.snapshot(data["obs"], data["active"], pd.Timestamp("2026-03-25", tz="UTC"))  # vintage c only
    assert s.last == pd.Period("2025-12", freq="M")  # complete through March - 3 months
    assert s.values["value"].max() == 90.0  # m4 (released 2025-12) is not measured in vintage c
    t = CM.truth(data)
    assert t[(pd.Period("2026-01", freq="M"), "v1.1")] == 300.0  # the later vintage does include it


def test_snapshot_never_reads_a_later_vintage():
    data = _obs()
    s = CM.snapshot(data["obs"], data["active"], pd.Timestamp("2025-07-01", tz="UTC"))
    assert "v1.0:a" in s.vintage and "v1.0:b" not in s.vintage
    assert s.kind == "mixed"  # v1.0 real; v1.1 had no vintage yet, so it is reconstructed (flagged)


def test_kalman_recovers_a_known_slope():
    t = np.arange(40, dtype=float)
    Y = np.column_stack([1.0 + 0.25 * t, 3.0 - 0.1 * t])
    ll, level, slope = kalman_llt(Y, np.log([1e-4, 1e-6, 1e-8]))
    assert np.isfinite(ll) and np.allclose(slope, [0.25, -0.1], atol=0.01) and np.allclose(level, Y[-1], atol=0.05)


def test_local_trend_extrapolates_the_slope():
    t = np.arange(30)
    panel = pd.DataFrame({"period": np.tile(t, 2), "unit": np.repeat(["a", "b"], 30),
                          "lvl": np.concatenate([0.5 * t, 2 + 0.0 * t])})
    rows = panel[panel["period"] == 29]
    d = LocalTrend().fit(panel.assign(target=0.0), 4, [], 12, panel).predict(rows)
    assert np.allclose(d, [2.0, 0.0], atol=0.1)


def test_regime_probabilities_sum_to_one_and_follow_the_bounds():
    lo, hi = E.regime_bounds(np.array([12.0, 0.0]), 6, 12)  # trailing rate 1 per period, and flat
    assert np.allclose(lo, [4.5, -0.12]) and np.allclose(hi, [7.5, 0.12])
    p = E.regime_probs(np.array([6.0, 1.0]), np.array([-0.5, 0.0, 0.5]), lo, hi)
    assert np.allclose(p.sum(axis=1), 1) and np.allclose(p[0], [0, 1, 0]) and np.allclose(p[1], [1, 0, 0])
    assert list(E.regime_of(np.array([8.0, 5.0, 1.0]), lo[[0, 0, 0]], hi[[0, 0, 0]])) == \
        ["acceleration", "stable", "slowdown"]


def test_capability_errors_are_in_doublings():
    spec = CM.SPEC
    assert spec.errors_on_model_scale and spec.error_unit == "doublings (log2)"
    assert np.isclose(F.LOG2.to_model(np.array([8.0]))[0], 3.0)
