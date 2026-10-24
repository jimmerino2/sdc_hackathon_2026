"""Skill-demand forecasting candidates, direction labels and selection on SYNTHETIC series with known behaviour."""
import numpy as np
import pandas as pd
import pytest

from occupational import backtest as B, models as M

from .test_models import _panel

T = 60
H = 6


def _f(K, N, skill=None, occ=None):
    K, N = np.atleast_2d(np.asarray(K, float)), np.atleast_2d(np.asarray(N, float))
    skill = np.arange(len(K)) if skill is None else np.asarray(skill)
    occ = np.zeros(len(K), int) if occ is None else np.asarray(occ)
    return M.features(K, N, skill, occ, int(occ.max()) + 1)


def _series(share, n=400, seed=0):
    """Binomial counts for a share path (one value per month)."""
    rng = np.random.default_rng(seed)
    share = np.clip(np.asarray(share, float), 0, 1)
    N = np.full(len(share), float(n))
    return rng.binomial(N.astype(int), share).astype(float), N


def _fc(f, method, q, row=0, t=T - 1, h=H):
    return float(M.predict(method, f, np.array([row]), np.array([t]), h, params=q)[0])


def _label(f, fc, row=0, t=T - 1):
    return str(M.direction(np.array([(fc - M.baseline(f, np.array([row]), np.array([t]))[0]) * 100]))[0])


Q = {"hl": 3.0, "kappa": 0.0, "W": 12, "source": "cell", "consistency": False, "beta": 1.0}


def test_sustained_increase_is_forecast_to_rise():
    K, N = _series(M.expit(np.linspace(-2.5, -0.5, T)))
    f = _f(K, N)
    assert M.shrunk_slope(f, 12)[0, -1] > 0.8 * M.slope(f, 12)["b"][0, -1] > 0
    fc = _fc(f, "adaptive", Q)
    assert fc > M.baseline(f, np.array([0]), np.array([T - 1]))[0]
    assert _label(f, fc) == "rising"
    # the trend carries the forecast past the level, but beta = 0 leaves the level alone
    assert fc > _fc(f, "adaptive", {**Q, "beta": 0.0}) == pytest.approx(_fc(f, "ewma", Q))


def test_sustained_decline_is_forecast_to_fall():
    K, N = _series(M.expit(np.linspace(0.4, -1.4, T)))  # 60% -> 20%
    f = _f(K, N)
    fc = _fc(f, "adaptive", Q)
    assert _label(f, fc) == "falling"
    assert fc < float(f["p12"][0, -1])  # not anchored to the trailing year


def test_one_month_spike_is_not_extrapolated():
    share = np.full(T, 0.20)
    share[-1] = 0.45  # a single noisy month at the origin
    K, N = _series(share, seed=3)
    f = _f(K, N)
    assert M.shrunk_slope(f, 12)[0, -1] == 0  # the slope needs the spike month, so it is not a trend
    fc = _fc(f, "adaptive", Q)
    assert fc == pytest.approx(_fc(f, "ewma", Q))
    assert abs(fc - 0.20) < 0.25 * 0.25  # the level moves less than a quarter of the spike
    # a spike earlier on, then reversion: no trend, about stable
    share = np.full(T, 0.20)
    share[-8] = 0.45
    K, N = _series(share, seed=4)
    f = _f(K, N)
    assert _label(f, _fc(f, "adaptive", {**Q, "consistency": True})) == "flat"


def test_stable_share_is_flat():
    K, N = _series(np.full(T, 0.30), seed=5)
    f = _f(K, N)
    fc = _fc(f, "adaptive", Q)
    assert abs(fc - 0.30) < 0.02
    assert _label(f, fc) == "flat"


def test_low_frequency_skill_slope_is_shrunk():
    share = np.linspace(0.01, 0.06, T)
    K, N = _series(share, n=6, seed=6)  # a handful of ads a month
    f = _f(K, N)
    s = M.slope(f, 12)
    assert abs(M.shrunk_slope(f, 12)[0, -1]) <= 0.5 * abs(s["b"][0, -1]) + 1e-12
    for m in ("ewma", "dtrend", "adaptive"):
        v = _fc(f, m, {**Q, "phi": 0.9, "beta": M.BETA_MAX})
        assert 0 < v < 1


def test_missing_months_are_not_zero_demand():
    share = 0.30
    K, N = _series(np.full(T, share), seed=7)
    Km, Nm = K.copy(), N.copy()
    Km[-8:-2], Nm[-8:-2] = 0, 0  # no ads at all for six months: missing
    Kz = K.copy()
    Kz[-8:-2] = 0  # ads, none naming the skill: observed zeros
    f = _f(np.vstack([K, Km, Kz]), np.vstack([N, Nm, N]), skill=[0, 1, 2])
    lvl = M.ew_level(f, 3.0)[0][:, -1]
    assert abs(lvl[1] - lvl[0]) < 0.03
    assert lvl[2] < lvl[0] - 0.05
    assert M.slope(f, 12)["ok"][1, -1]  # still enough months with ads for a slope
    assert abs(M.slope(f, 12)["b"][1, -1]) < abs(M.slope(f, 12)["b"][2, -1])


def test_rapid_change_in_ad_volume_keeps_the_share():
    N = np.where(np.arange(T) < T - 6, 40.0, 600.0)  # volume jumps 15x; the share stays exactly 25%
    f = _f(0.25 * N, N)
    assert abs(M.slope(f, 12)["b"][0, -1]) < 1e-4  # only the 2-pseudo-ad smoothing differs by volume
    fc = _fc(f, "adaptive", Q)
    assert fc == pytest.approx(0.25, abs=1e-3)
    assert _label(f, fc) == "flat"


@pytest.mark.parametrize("share", [0.0, 1.0])
def test_shares_at_the_bounds_stay_valid(share):
    K, N = _series(np.full(T, share), n=50)
    f = _f(K, N)
    for m in M.TUNED:
        v = _fc(f, m, {**Q, "phi": 1.0, "beta": M.BETA_MAX})
        assert np.isfinite(v) and 0 <= v <= 1
        assert abs(v - share) < 0.05


def test_insufficient_history_falls_back_to_the_level():
    K, N = np.zeros(T), np.zeros(T)
    K[-3:], N[-3:] = [3, 4, 5], [20, 20, 20]  # three months of ads only
    f = _f(K, N)
    s = M.slope(f, 12)
    assert not s["ok"][0, -1] and s["b"][0, -1] == 0 and np.isinf(s["var"][0, -1])
    assert _fc(f, "adaptive", Q) == pytest.approx(_fc(f, "ewma", Q))


def test_direction_is_relative_to_the_recent_baseline():
    assert list(M.direction(np.array([1.0, 0.99, -1.0, -0.5, 3.0]))) == ["rising", "flat", "falling", "flat", "rising"]
    # 12-month share 30%, last 3 months 20%: a forecast of 25% is a rise from the recent baseline
    K = np.r_[np.full(T - 3, 30.0), np.full(3, 20.0)]
    f = _f(K, np.full(T, 100.0))
    assert f["p12"][0, -1] > 0.25 > M.baseline(f, np.array([0]), np.array([T - 1]))[0]
    assert _label(f, 0.25) == "rising"


def test_backtest_and_serving_share_the_model_and_the_direction():
    p = _panel()
    tuned = B.tune(p)
    b = B.run_backtest(p, tuned)
    assert set(M.TUNED) <= set(b["method"])
    ev = B.evaluate(b, tuned)
    for h in map(str, B.HORIZONS):
        ev["horizons"][h]["served"] = "adaptive"  # force the path that has a refit part
    fc, cards = B.forecast(p, b, ev, tuned)
    t0 = p.T - 1
    for h in B.HORIZONS:
        g = fc[fc["h"] == h]
        rows = np.array([p.series.index[(p.series["country"] == c) & (p.series["skill_id"] == s)][0]
                         for c, s in zip(g["country"], g["skill_id"])])
        cols = np.full(len(rows), t0)
        q = B.params_for(tuned, h, "adaptive")
        same = B._refit_predict(p, "adaptive", rows, cols, h, q)  # what the backtest would forecast at t0
        np.testing.assert_allclose(g["forecast"].to_numpy(), same)
        assert "beta_by_ads_3m" in cards[str(h)]
    lab = M.direction(((fc["forecast"] - fc["baseline_share"]) * 100).to_numpy())
    assert (fc["direction"].to_numpy() == lab).all()
    assert np.allclose(fc["baseline_share"], fc["last_share_3m"].fillna(fc["share_12m"]))
    # the backtest scores direction from the same baseline
    assert np.allclose(b["p3_origin"], M.baseline(p.f, b["series"].to_numpy(), b["origin_idx"].to_numpy()))


def test_new_features_do_not_look_ahead():
    p = _panel()
    t = 40
    q = {"hl": 3.0, "kappa": 30.0, "W": 12, "source": "pooled", "consistency": True, "beta": 0.5}
    rows = np.arange(len(p.series))
    cols = np.full(len(rows), t)
    before = {m: M.predict(m, p.f, rows, cols, H, params={**q, "phi": 0.9}) for m in M.TUNED}
    K2 = p.K.copy()
    K2[:, t + 1:] = p.N[:, t + 1:]  # every later ad names every skill
    f2 = M.features(K2, p.N, p.f["skill"], p.f["occ"], p.f["n_occ"])
    for m in M.TUNED:
        np.testing.assert_allclose(M.predict(m, f2, rows, cols, H, params={**q, "phi": 0.9}), before[m], err_msg=m)


def test_beta_ignores_targets_after_its_refit_origin(monkeypatch):
    monkeypatch.setattr(M, "MIN_BETA_ROWS", 10)
    p, r = _panel(), 50
    q = {"hl": 3.0, "kappa": 0.0, "W": 12, "source": "cell", "consistency": False}
    a = B._betas(p, H, q, [r])[r]
    p.K[:, r + 1:] = p.N[:, r + 1:]
    p.f = M.features(p.K, p.N, p.f["skill"], p.f["occ"], p.f["n_occ"])
    np.testing.assert_allclose(B._betas(p, H, q, [r])[r], a)


def test_tuning_never_sees_validation_or_test_targets():
    p = _panel()
    a = B.tune(p)
    q = _panel()
    q.K[:, q.T - 24:] = q.N[:, q.T - 24:]  # change every validation and test month
    q.f = M.features(q.K, q.N, q.f["skill"], q.f["occ"], q.f["n_occ"])
    q.k24 = M.wsum(q.K, 24)
    assert B.tune(q) == a


def test_evaluation_and_selection_are_reproducible():
    p = _panel()
    tuned = B.tune(p)
    e1 = B.evaluate(B.run_backtest(p, tuned), tuned)
    e2 = B.evaluate(B.run_backtest(_panel(), B.tune(_panel())), tuned)
    for h in map(str, B.HORIZONS):
        for k in ("served", "chosen_on_validation", "status", "bootstrap_best_beats", "selection_sensitivity"):
            assert e1["horizons"][h][k] == e2["horizons"][h][k]
        assert e1["horizons"][h]["scores"]["test"] == e2["horizons"][h]["scores"]["test"]


def test_selection_prefers_the_simpler_method_unless_clearly_better():
    rng = np.random.default_rng(0)
    n = 400
    actual = rng.uniform(0.1, 0.5, n)
    base = pd.DataFrame({"series": np.arange(n), "origin_idx": 30 + np.arange(n) % 12, "actual": actual,
                         "actual_n": 200.0, "n3_origin": 200.0, "p3_origin": actual + rng.normal(0, 0.05, n)})
    noise = rng.normal(0, 0.03, n)
    g = pd.concat([base.assign(method="persistence", forecast=base["p3_origin"]),
                   base.assign(method="mean12", forecast=actual + noise),
                   base.assign(method="adaptive", forecast=actual + rng.normal(0, 0.0299, n))])  # as good, by chance
    val = {m: B.metrics(x, g[g["method"] == "persistence"]) for m, x in g.groupby("method")}
    chosen, checks = B.select(val, g=g)
    assert chosen == "mean12"
    assert not checks or checks["mean12"] < B.CONFIDENCE
    g2 = pd.concat([g[g["method"] != "adaptive"], base.assign(method="adaptive", forecast=actual + noise * 0.5)])
    val2 = {m: B.metrics(x, g2[g2["method"] == "persistence"]) for m, x in g2.groupby("method")}
    assert B.select(val2, g=g2)[0] == "adaptive"
    # a method worse than persistence overall is never served, whatever its direction score
    g3 = pd.concat([g[g["method"] != "adaptive"], base.assign(method="adaptive", forecast=base["p3_origin"] + 0.2 * np.sign(actual - base["p3_origin"]) + rng.normal(0, 0.2, n))])
    val3 = {m: B.metrics(x, g3[g3["method"] == "persistence"]) for m, x in g3.groupby("method")}
    assert B.select(val3, g=g3)[0] != "adaptive"
