"""Forecasting safeguards: no look-ahead, chronological split, baselines, intervals, and the evidence ranking."""
import numpy as np
import pandas as pd

from occupational import backtest as B, emerging, models as M


def _panel(T=80, seed=1):
    """SYNTHETIC panel: 2 cells x 3 skills with known shares."""
    rng = np.random.default_rng(seed)
    months = [str(m) for m in pd.period_range("2018-01", periods=T, freq="M")]
    tot, cnt = [], []
    for c in ("US", "GB"):
        for i, m in enumerate(months):
            n = 60 if c == "US" else 25
            tot.append({"month": m, "country": c, "occupation": "software_engineer", "n_ads": n, "is_partial": False})
            for s, p in (("python", 0.4), ("rust", 0.02 + 0.003 * i), ("django", 0.3)):
                cnt.append({"month": m, "country": c, "occupation": "software_engineer", "skill_id": s,
                            "n_ads_skill": int(rng.binomial(n, min(p, 0.95)))})
    reg = {"skills": [{"skill_id": s, "origin": "curated"} for s in ("python", "rust", "django")]}
    return B.Panel(pd.DataFrame(tot), pd.DataFrame(cnt), reg)


def test_features_do_not_look_ahead():
    p = _panel()
    t = 40
    before = {k: v[:, t].copy() for k, v in p.f.items() if isinstance(v, np.ndarray) and v.ndim == 2}
    K2 = p.K.copy()
    K2[:, t + 1:] = 999  # change the future only
    f2 = M.features(K2, p.N, np.array([0, 1, 2] * 2), np.zeros(6, int), 1)
    for k, v in before.items():
        np.testing.assert_allclose(f2[k][:, t], v, err_msg=k)


def test_persistence_is_last_three_months_share():
    p = _panel()
    rows, cols = np.array([0]), np.array([30])
    exp = p.K[0, 28:31].sum() / p.N[0, 28:31].sum()
    assert np.isclose(M.predict("persistence", p.f, rows, cols, 3)[0], exp)


def test_backtest_split_and_ridge_training_are_chronological():
    p = _panel()
    b = B.run_backtest(p)
    assert set(b["role"]) == {"train", "validation", "test"}
    tt = b["origin_idx"] + b["h"]
    assert tt[b["role"] == "test"].min() > tt[b["role"] == "validation"].max() > tt[b["role"] == "train"].max()
    assert (b["origin_idx"] + b["h"] < p.T).all()
    # every method present is scored on the same rows
    assert b.groupby(["series", "origin_idx", "h"])["method"].nunique().eq(b["method"].nunique()).all()


def test_ridge_ignores_data_after_its_refit_origin(monkeypatch):
    monkeypatch.setattr(B, "MIN_RIDGE_ROWS", 50)
    p, r, h = _panel(), 50, 6
    a = B._ridges(p, h, [r])[r]
    q = _panel()
    q.K[:, r + 1:] = q.N[:, r + 1:]  # every later ad names every skill
    q.f = M.features(q.K, q.N, np.array([0, 1, 2] * 2), np.zeros(6, int), 1)
    q.k24 = M.wsum(q.K, 24)
    b = B._ridges(q, h, [r])[r]
    assert a is not None and b is not None
    np.testing.assert_allclose(a.model.coef_, b.model.coef_)


def test_evaluation_gate_and_intervals():
    p = _panel()
    b = B.run_backtest(p)
    ev = B.evaluate(b)
    for h in map(str, B.HORIZONS):
        v = ev["horizons"][h]
        assert v["served"] in M.METHODS
        if v["status"] == "baseline_retained":
            assert v["served"] == "persistence"
        cov = v["interval_test"][v["served"]]["coverage_80"]
        assert 0.4 <= cov <= 1.0
    fc, _ = B.forecast(p, b, ev)
    assert (fc["low"] <= fc["forecast"] + 1e-9).all() and (fc["forecast"] <= fc["high"] + 1e-9).all()
    assert fc["forecast"].between(0, 1).all()


def test_low_volume_cannot_top_the_growth_ranking():
    # skill a: 1 -> 3 ads (x3, tiny); skill b: 60 -> 120 ads (x2, solid). b must rank higher.
    months = [str(m) for m in pd.period_range("2025-01", "2026-06", freq="M")]
    totals = pd.DataFrame([{"month": m, "country": "US", "occupation": "o", "n_ads": 100} for m in months])
    counts = []
    for i, m in enumerate(months):
        recent = i >= len(months) - 6
        counts.append({"month": m, "country": "US", "occupation": "o", "skill_id": "a", "n_ads_skill": (1 if recent else 0) if i % 2 else 0})
        counts.append({"month": m, "country": "US", "occupation": "o", "skill_id": "b", "n_ads_skill": 20 if recent else 5})
    s = emerging.window_stats(pd.DataFrame(counts), totals, pd.Period("2026-06", "M")).set_index("skill_id")
    assert s.loc["a", "growth_ratio"] > 1
    assert s.loc["b", "growth_lb_pp"] > s.loc["a", "growth_lb_pp"]


def test_candidate_terms_need_a_stack_context(data_dir):
    t = emerging.terms("We use Python, Zorblang and Postgres for everything.\nFounded by ex-Google folks in Gotham.",
                       employer="Acme", known_keys=emerging.known_key_set())
    assert "zorblang" in t
    assert "gotham" not in t and "google" not in t  # prose, not a stack list
