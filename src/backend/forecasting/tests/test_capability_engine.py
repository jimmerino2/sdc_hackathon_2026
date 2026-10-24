"""Capability engine: data layers and bridge, leakage, simulation, intervals, pace chances, missing data, weights."""
import numpy as np
import pandas as pd
import pytest

from forecasting import capability_engine as CE
from forecasting.features import Snapshot
from forecasting.targets import capability_metr as CM

from test_capability import _obs  # rootdir-relative: tests is not a package

RNG = lambda s=0: np.random.default_rng(s)  # noqa: E731


def _rows(models, version="METR-Horizon-v1.1"):
    """(name, release date, minutes) -> rows as the snapshot carries them (synthetic, not real data)."""
    return pd.DataFrame([{"model": m, "release_date": pd.Timestamp(d), "value": v, "ci_low": v / 2, "ci_high": v * 2,
                          "metr_version": version} for m, d, v in models])


def _growing(n_months=36, doubling=6.0, start="2023-01-15", per_month=1, noise=0.0, seed=0):
    """Synthetic models released monthly on an exact exponential trend (minutes double every `doubling` months)."""
    r = np.random.default_rng(seed)
    t0 = pd.Timestamp(start)
    return [(f"m{i}_{k}", t0 + pd.DateOffset(months=i), 4.0 * 2 ** (i / doubling + noise * r.standard_normal()))
            for i in range(n_months) for k in range(per_month)]


def _snap(rows: pd.DataFrame, last: str, unit="v1.1", legacy=None) -> Snapshot:
    last = pd.Period(last, freq="M")
    rows = rows[rows["release_date"].dt.to_period("M") <= last]
    f = CM.frontier(rows, last).assign(unit=unit).dropna(subset=["value"])
    return Snapshot(pd.Timestamp(last.to_timestamp(how="end"), tz="UTC"), last, "real", f[["unit", "period", "value"]],
                    unit, extras={"models": {unit: rows}, "legacy": {unit: legacy} if legacy is not None else {}})


# ------------------------------------------------------------------------------------------------ data versions

def test_bridge_matches_run_settings_and_recovers_a_known_mapping():
    old = CE.layer_a(_rows([(f"x{i}-2025_16K", "2025-01-01", 2.0 ** i) for i in range(2, 10)], "METR-Horizon-v1.0"))
    new = CE.layer_a(_rows([(f"x{i}-2025_unknown", "2025-01-01", 2.0 ** (1.2 * i - 1)) for i in range(2, 10)]))
    br = CE.bridge(new, old, RNG())
    assert br["applied"] and br["credible"] and br["n_pairs"] == 8
    assert abs(br["slope"] - 1.2) < 1e-6  # exact line, Theil-Sen recovers it


def test_bridged_rows_are_only_unmatched_older_models_and_carry_more_uncertainty():
    old = CE.layer_a(_rows([("a_16K", "2024-01-01", 10.0), ("b", "2024-06-01", 20.0), ("c", "2024-09-01", 40.0),
                            ("only-old", "2024-10-01", 30.0)], "METR-Horizon-v1.0"))
    new = CE.layer_a(_rows([("a_unknown", "2024-01-01", 9.0), ("b", "2024-06-01", 22.0), ("c", "2024-09-01", 41.0)]))
    br = CE.bridge(new, old, RNG())
    assert not br["credible"]  # 3 pairs: weak prior, slope 1
    assert br["slope"] == 1.0
    b = CE.layer_b(new, old, br)
    assert list(b["model"]) == ["only-old"] and (b["layer"] == "bridged").all()
    assert b["s_lo"].iloc[0] > old.loc[old["model"] == "only-old", "s_lo"].iloc[0]


def test_bridge_is_skipped_without_overlap():
    new = CE.layer_a(_rows([("a", "2024-01-01", 9.0)]))
    assert CE.bridge(new, new.iloc[:0], RNG())["applied"] is False


def test_measurements_above_the_suite_ceiling_are_flagged_and_left_out_of_the_trend():
    a = CE.layer_a(_rows([("big", "2026-01-01", 17 * 60.0), ("small", "2026-01-01", 60.0)]))
    assert list(a["saturated"]) == [True, False]
    rows = pd.concat([_rows(_growing(30)), _rows([("outlier", "2025-06-10", 60 * 1000.0)])], ignore_index=True)
    ctx = CE.context(_snap(rows, "2025-06"), "v1.1", RNG(), 500)
    p = CE.jump_params(ctx["models"], ctx["T_end"], RNG())
    assert p["n_fit"] == p["n_relevant"] - 1  # the saturated outlier is not fitted


# ----------------------------------------------------------------------------------------------------- leakage

def test_snapshot_models_are_the_vintage_published_by_the_origin_cut_at_its_month():
    data = _obs()
    s = CM.snapshot(data["obs"], data["active"], pd.Timestamp("2026-03-25", tz="UTC"))  # vintage c only
    m = s.extras["models"]["v1.1"]
    assert set(m["model"]) == {"m1", "m3"}  # m4 is only in the later vintage d
    assert (m["release_date"].dt.to_period("M") <= s.last).all()
    assert set(s.extras["legacy"]["v1.1"]["model"]) == {"m1"}  # older-suite rows from the same vintage only


def test_a_unit_complete_only_to_an_earlier_month_is_not_held_flat():
    data = _obs()
    s = CM.snapshot(data["obs"], data["active"], pd.Timestamp("2025-07-01", tz="UTC"))  # v1.0 real, v1.1 reconstructed
    lasts = s.values.groupby("unit")["period"].max()
    for unit in s.extras["models"]:
        ctx = CE.context(s, unit, RNG(), 100)
        assert (ctx is None) == (lasts[unit] != s.last)


def test_ensemble_weights_use_only_cases_resolved_before_the_origin():
    errs = pd.DataFrame([{"origin": i, "unit": "u", "h": 3, "candidate": c, "abs_err": e}
                         for i in range(8) for c, e in (("damped_trend", 1.0), ("robust_local_trend", 0.5),
                                                        ("jump_process", 0.25))])
    three = ("damped_trend", "robust_local_trend", "jump_process")
    eq = CE.ensemble_weights(errs.iloc[:9], 3, three)  # 3 cases < min_weight_cases
    assert all(abs(v - 1 / 3) < 1e-12 for v in eq.values())
    w = CE.ensemble_weights(errs, 3, three)
    assert abs(sum(w.values()) - 1) < 1e-12 and w["jump_process"] > w["robust_local_trend"] > w["damped_trend"]
    assert min(w.values()) >= CE.CFG.ensemble_shrink / 3  # shrinkage keeps every component in


# --------------------------------------------------------------------------------- forecasts and their ranges

def test_simulation_is_reproducible_monotone_and_never_below_the_current_frontier():
    s = _snap(_rows(_growing(36, noise=0.3)), "2025-12")
    out = []
    for _ in range(2):
        ctx = CE.context(s, "v1.1", RNG(7), 1000)
        paths, notes = CE.simulate(ctx, 1000, RNG(7))
        out.append(paths)
    assert set(out[0]) == set(CE.COMPONENTS)
    for c, p in out[0].items():
        assert p.shape == (1000, CE.CFG.max_h)
        assert np.array_equal(p, out[1][c])
        assert (np.diff(p, axis=1) >= -1e-12).all() and (p >= ctx["y0"][:, None] - 1e-12).all()


def test_forecast_follows_a_clean_exponential_trend():
    s = _snap(_rows(_growing(36, doubling=6.0)), "2025-12")  # 2 doublings a year, no noise
    ctx = CE.context(s, "v1.1", RNG(), 2000)
    paths, _ = CE.simulate(ctx, 2000, RNG())
    ens, _ = CE.mixture(paths, {c: 1 / 3 for c in paths}, 2000)
    q = np.quantile(ens[:, 11], [0.1, 0.5, 0.9])
    change = q[1] - ctx["y_now"]
    assert 1.4 < change < 2.6  # about 2 doublings in 12 months
    assert q[0] < q[1] < q[2]
    assert abs(ctx["hist_point"] - 2.0) < 1e-9 and ctx["pace_basis"] == "observed_12m"


def test_80_percent_range_covers_about_80_percent_on_data_from_the_model_itself():
    """Pace sims checked against their own generating process: share of fresh draws inside the 10-90% range."""
    rng = RNG(3)
    paths = rng.normal(0, 1, (4000, 12)).cumsum(axis=1)
    q10, q90 = np.quantile(paths[:, 5], [0.1, 0.9])
    fresh = rng.normal(0, 1, (4000, 12)).cumsum(axis=1)[:, 5]
    assert abs(((fresh >= q10) & (fresh <= q90)).mean() - 0.8) < 0.03
    sc = CE.point_scores(pd.DataFrame({"origin": 0, "q10": q10, "q50": 0.0, "q90": q90, "y_actual": fresh}))
    assert abs(sc["coverage_80"] - 0.8) < 0.03 and sc["interval_score_80"] > sc["width_80"]


# --------------------------------------------------------------------------------------------- pace chances

def test_pace_chances_come_from_the_trajectories_and_sum_to_one():
    y0 = np.zeros(6)
    hist = np.full(6, 2.0)  # 2 doublings a year; tolerance = max(0.25, 0.4) = 0.4
    fut12 = np.array([3.0, 2.5, 2.2, 1.9, 1.5, 0.5])  # paces at h=12 equal the 12-month change
    paths = np.repeat(fut12[:, None], 12, axis=1)
    p = CE.pace_probs(paths, y0, hist, 12)
    assert np.allclose(p, [2 / 6, 2 / 6, 2 / 6]) and np.isclose(p.sum(), 1)
    p3 = CE.pace_probs(paths, y0, hist, 3)  # same change in 3 months = 4x the yearly pace
    assert np.isclose(p3[0], 5 / 6) and np.isclose(p3.sum(), 1)
    assert CE.pace_class(2.3, 2.0) == "same" and CE.pace_class(2.5, 2.0) == "faster" and CE.pace_class(0.1, 0.0) == "same"


def test_base_rate_and_scores_against_a_one_in_three_guess():
    assert np.allclose(CE.base_rate([]), 1 / 3)
    assert np.allclose(CE.base_rate(["faster", "faster"]), [3 / 5, 1 / 5, 1 / 5])
    d = pd.DataFrame({"origin": range(4), "realised_class": ["faster"] * 4, "p_faster": 0.9, "p_same": 0.05,
                      "p_slower": 0.05, "clim_faster": 1 / 3, "clim_same": 1 / 3, "clim_slower": 1 / 3,
                      "pc_faster": 0.9, "pc_same": 0.05, "pc_slower": 0.05})  # calibrated = raw here
    s = CE.pace_scores(d, shrink=0.5)
    assert s["brier_model"] < s["brier_served"] < s["brier_uniform"]
    assert np.isclose(s["brier_uniform"], 2 / 3) and s["log_loss_model"] < s["log_loss_uniform"]


# ------------------------------------------------------------------------------------------------ missing data

def test_too_few_models_leaves_the_jump_model_out_but_still_forecasts():
    s = _snap(_rows([("a", "2025-01-10", 10.0), ("b", "2025-04-10", 20.0), ("c", "2025-09-10", 30.0)]), "2025-12")
    ctx = CE.context(s, "v1.1", RNG(), 500)
    paths, notes = CE.simulate(ctx, 500, RNG())
    assert "jump_process" not in paths and "unavailable" in notes["jump_process"]
    assert "damped_trend" in paths
    ens, share = CE.mixture(paths, CE.ensemble_weights(pd.DataFrame(), 3, paths), 500)
    assert ens.shape == (500, 12) and set(share) == set(paths)


def test_short_history_has_no_observed_pace_and_says_so():
    s = _snap(_rows(_growing(8)), "2023-08")  # 8 months: no 12-month history, no bridge
    ctx = CE.context(s, "v1.1", RNG(), 200)
    assert ctx["pace_basis"] in ("trend_prior", "none") and len(ctx["hist"]) == 200


def test_unit_without_models_or_frontier_is_skipped():
    empty = _rows([]).reindex(columns=["model", "release_date", "value", "ci_low", "ci_high"])
    s = Snapshot(pd.Timestamp("2025-01-01", tz="UTC"), pd.Period("2024-12", freq="M"), "real",
                 pd.DataFrame({"unit": ["v1.1"], "period": [pd.Period("2024-12", freq="M")], "value": [1.0]}), "",
                 extras={"models": {"v1.1": empty}})
    assert CE.context(s, "v1.1", RNG(), 10) is None


def test_missing_ci_gets_the_default_spread():
    lo, hi = CE.sigmas([10.0, 10.0], [None, 5.0], [None, np.nan])
    assert lo[0] == hi[0] == CE.CFG.default_sigma and np.isclose(lo[1], 1 / 1.96) and hi[1] == CE.CFG.default_sigma
