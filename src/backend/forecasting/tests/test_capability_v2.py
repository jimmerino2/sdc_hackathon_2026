"""Capability engine, second round: two-stage record model, smoothed trend, calibration, dependence-aware checks,
component inclusion, external-signal retention, the bridge's point-in-time rule, and a small synthetic backtest."""
import numpy as np
import pandas as pd

from forecasting import capability_engine as CE, capability_eval as V, capability_record as RC
from forecasting import capability_trend as TR
from forecasting.features import Snapshot
from forecasting.targets import capability_metr as CM

from test_capability_engine import _growing, _rows, _snap  # rootdir-relative: tests is not a package

RNG = lambda s=0: np.random.default_rng(s)  # noqa: E731


# ------------------------------------------------------------------------------------------ two-stage record model

def test_records_ignore_months_before_a_measurement_gap():
    y = np.array([1.0, 1.0, 1.0, np.nan, np.nan, 3.0, 3.0, 3.5, 3.5, 4.0])
    rec, jumps = RC.records(y)
    assert np.isnan(rec[:5]).all()  # the flat stretch before the gap is "no measurement", not "no record"
    assert list(rec[5:]) == [0, 1, 0, 1] and np.allclose(jumps, [0.5, 0.5])


def test_constant_hazard_never_makes_a_record_due():
    early = np.array([1.0] * 6 + [0.0] * 18)
    late = np.array([0.0] * 18 + [1.0] * 6)  # same records, now after a long quiet stretch
    assert RC.hazard_beta(early) == RC.hazard_beta(late)


def test_jump_sizes_are_shrunk_towards_the_prior_when_few():
    one = RC.jump_posterior(np.array([4.0]))
    many = RC.jump_posterior(np.full(40, 4.0))
    assert RC.RCFG.jump_mu0 < one["mu"] < many["mu"] < np.log(4.0) + 1e-9


def test_record_simulation_has_no_record_small_and_large_jumps():
    y0 = np.zeros(20000)
    paths, hit = RC.simulate(y0, np.full(20000, 0.2), RC.jump_posterior(np.array([0.3, 0.5, 1.0, 0.4])), 12, RNG())
    assert ((~hit[:, :3].any(axis=1)).mean() - 0.8 ** 3) ** 2 < 1e-4  # P(no record in 3 months) = (1 - p)^3
    jumps = np.diff(np.column_stack([y0, paths]), axis=1)[hit]
    assert (np.diff(paths, axis=1) >= 0).all() and jumps.min() < 0.2 and jumps.max() > 2.0
    assert np.isclose(RC.p_record_within(0.2, 3), 1 - 0.8 ** 3)


def test_logistic_hazard_finds_a_real_signal_and_month_events_are_labelled():
    r = RNG(1)
    z = r.normal(size=400)
    rec = (r.random(400) < 1 / (1 + np.exp(-(-0.5 + 1.5 * z)))).astype(float)
    fit = RC.hazard_logit(rec, z)
    assert fit["beta"][1] > 0.5 and RC.logit_p(fit, 2.0) > RC.logit_p(fit, -2.0)
    ev = RC.month_events(np.array([np.nan, 1.0, 1.0, 2.0]), np.array([0, 1, 1, 0]))
    assert ev == ["no recent measurement", "measured release, no record", "measured release, no record", "new record"]


# ------------------------------------------------------------------------------------------------ smoothed trend

def test_smooth_trend_recovers_the_slope_under_a_staircase_and_does_not_follow_the_steps():
    t = np.arange(48)
    stairs = np.floor(t / 4) * 4 * 0.2  # a jump every 4 months, 2.4 doublings a year on average
    f = TR.fit(stairs, smooth_trend=True)
    level, _ = TR.smooth(f)
    assert abs(12 * f["a_f"][-1][1] - 2.4) < 0.6
    assert np.abs(np.diff(level[10:40, 0])).max() < 0.5  # no 0.8-doubling step in the smoothed level


def test_trend_forecast_chances_sum_to_one_and_realised_windows_line_up():
    y = np.arange(30) * 0.2
    out = TR.forecast(y, (3, 12), 4000, RNG(), 0.25, 0.2, smooth_trend=True)
    for v in out["horizons"].values():
        assert np.isclose(sum(v["p"]), 1) and v["p"][1] > 0.5  # a straight line: most likely steady
    slopes = np.r_[np.full(12, 0.1), np.full(6, 0.3)]
    assert TR.realised(slopes, 12, 3) == (12 * 0.1, 12 * 0.3)
    assert TR.realised(slopes, 12, 12) is None and TR.classify(3.6, 1.2, 0.25, 0.2) == "accelerating"


# ---------------------------------------------------------------------------------------- calibration and checks

def test_temperature_softens_overconfident_chances_and_keeps_them_summing_to_one():
    r = RNG(2)
    truth = r.integers(0, 3, 300)
    onehot = np.eye(3)[truth]
    guess = np.eye(3)[r.integers(0, 3, 300)] * 0.9 + 0.1 / 3  # confident and mostly wrong
    T = V.fit_temperature(guess, onehot)
    assert T > 1.5
    p = V.apply_temperature(guess, T)
    assert np.allclose(p.sum(axis=1), 1) and V.log_loss(p, onehot) < V.log_loss(guess, onehot)
    assert V.fit_temperature(guess[:0], onehot[:0]) == 1.0


def test_non_overlapping_cases_share_no_outcome_month():
    d = pd.DataFrame({"unit": "u", "last_period": [str(pd.Period("2024-01", "M") + i) for i in range(12)]})
    keep = V.non_overlapping(d, 6)
    assert list(keep["last_period"]) == ["2024-01", "2024-07"]


def test_block_bootstrap_interval_contains_the_mean_and_flags_a_clear_difference():
    x = pd.Series(np.r_[np.full(30, -1.0), np.full(10, 0.2)])
    b = V.block_bootstrap(x, 3)
    assert b["ci80"][0] <= b["mean"] <= b["ci80"][1] and b["share_below_0"] > 0.99
    assert V.block_bootstrap(pd.Series([1.0, 2.0]), 3) == {"n": 2, "mean": 1.5}


# ------------------------------------------------------------------------------------------ decisions and leakage

def _comp(ratio_jump: float, n: int = 12) -> pd.DataFrame:
    rows = []
    for i in range(n):
        for c, w in (("damped_trend", 1.0), ("jump_process", ratio_jump), ("record_jump", 5.0)):
            rows.append({"origin": i, "unit": "u", "h": 3, "role": "selection", "candidate": c,
                         "q10": -w / 2, "q90": w / 2, "y_actual": 0.0})
    return pd.DataFrame(rows)


def test_inclusion_keeps_the_baseline_and_only_components_close_to_it():
    inc = CE.inclusion(_comp(1.05))
    assert inc["damped_trend"]["included"] and inc["jump_process"]["included"]
    assert not inc["record_jump"]["included"]  # 5x the baseline's interval score
    assert not inc["robust_local_trend"]["included"]  # never available
    assert not CE.inclusion(_comp(1.05, n=5))["jump_process"]["included"]  # too few shared cases


def test_signal_is_kept_only_when_it_beats_both_references():
    rows = []
    for i in range(60):
        rec = float(i % 3 != 0)
        for v, p in (("constant", 0.5), ("logit_no_signal", 0.5), ("logit_good", 0.9 if rec else 0.1),
                     ("logit_noise", 0.5 + (0.3 if i % 2 else -0.3))):
            rows.append({"origin": i, "unit": "u", "h": 3, "role": "selection", "variant": v, "p_record": p, "record": rec})
    d = CE.signal_decision(pd.DataFrame(rows))
    assert d["logit_good"]["kept"] and not d["logit_noise"]["kept"]


def test_no_bridge_before_the_current_suite_was_published():
    rows = _rows(_growing(30)).assign(snapshot_kind="reconstructed")
    old = _rows([(m, d, v * 1.3) for m, d, v in _growing(30)], "METR-Horizon-v1.0")
    s = _snap(rows, "2025-06", legacy=old)
    s.extras["models"]["v1.1"] = s.extras["models"]["v1.1"].assign(snapshot_kind="reconstructed")
    ctx = CE.context(s, "v1.1", RNG(), 100)
    assert not ctx["bridge"]["applied"] and ctx["bridged"].empty
    s.extras["models"]["v1.1"] = s.extras["models"]["v1.1"].assign(snapshot_kind="real")
    assert CE.context(s, "v1.1", RNG(), 100)["bridge"]["applied"]


def test_small_backtest_weights_and_temperature_only_use_outcomes_known_at_each_origin():
    rows = _rows(_growing(40, doubling=5.0, noise=0.4, seed=3))
    months = [pd.Period("2024-06", "M") + i for i in range(0, 12, 2)]
    snaps = []
    for m in months:
        s = _snap(rows, str(m))
        snaps.append(Snapshot(s.origin, s.last, "real", s.values, s.vintage, s.extras))
    full = _snap(rows, "2026-04").values
    y_true = full.set_index(["period", "unit"])["value"]

    class Split:
        holdout_start = snaps[-2].origin
        holdout_last = snaps[-2].last
    comp, store, rec, trend = CE.pass_one(None, snaps, y_true, Split, CE.CFG)
    assert set(comp["role"]) <= {"selection", "holdout", "purged"} and len(rec) and len(trend)
    ens = CE.pass_two(comp, store, snaps, ["damped_trend", "jump_process", "record_jump"], CE.CFG)
    first = ens[ens["last_ord"] == ens["last_ord"].min()]
    assert np.allclose(first[["w_damped_trend", "w_jump_process", "w_record_jump"]], 1 / 3)  # nothing resolved yet
    assert (ens["temperature"] == 1.0).all()  # fewer than min_calib_cases resolved cases anywhere
    for _, r in ens.iterrows():  # every case a weight could have used was resolved by that origin
        used = comp[(comp["target_ord"] <= r["last_ord"]) & comp["y_actual"].notna()]
        assert (used["target_ord"] <= r["last_ord"]).all()
    assert np.allclose(ens[["p_faster", "p_same", "p_slower"]].sum(axis=1), 1)
