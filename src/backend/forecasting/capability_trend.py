"""Secondary output: the model-estimated underlying growth trend of the METR frontier, and whether it is speeding up.

The observed frontier is a staircase. Underneath it this module estimates a latent level L_t and growth rate b_t
(doublings per month) with a local-linear-trend state-space model:
    y_t = L_t + e_t,   L_(t+1) = L_t + b_t + eta_t,   b_(t+1) = b_t + zeta_t
Huber-robust updates (an innovation beyond `c` standard errors counts as `c`), variances by MAP (robust likelihood
plus log-normal priors), and a Rauch-Tung-Striebel smoother for the history. For this output the level has no shocks
of its own (Harvey's "smooth trend" model, `smooth_trend=True`): it moves only through the slowly drifting growth
rate, so the staircase's jumps count as deviations around the trend instead of being followed step by step. (With
level shocks, the first version reproduced the staircase; changed after seeing that, disclosed in FORECAST_REBUILD.) Parameters are fitted on the origin's
own snapshot; nothing is a hand-chosen rolling window.

Estimand (doublings / year):
  past trend pace    12 * mean(b) over the 12 months before the origin, smoothed on the snapshot
  future trend pace  12 * mean(b) over the next h months; forecast from the filtered b_T and its drift
  accelerating / stable / decelerating: future vs past, same tolerance rule as the frontier pace chances
Evaluation target ("what the trend turned out to be"): the same smoother fitted on the latest data, read at the
origin's months. That reference uses later data by design; it is the definition of the estimand, not a forecast.
This is a model-estimated quantity: it is never shown or scored as an observation of the frontier.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

TMAT = np.array([[1.0, 1.0], [0.0, 1.0]])


def llt_filter(y: np.ndarray, log_var: np.ndarray, c: float = 2.0) -> dict:
    """Robust Kalman filter. Returns the robust log-likelihood, predicted / filtered means and covariances per
    month (NaN before the first observation) and the variances."""
    h_eps, q_eta, q_zeta = np.exp(log_var)
    n = len(y)
    a_p, P_p = np.full((n, 2), np.nan), np.full((n, 2, 2), np.nan)
    a_f, P_f = np.full((n, 2), np.nan), np.full((n, 2, 2), np.nan)
    a, P, seen, ll = np.zeros(2), np.eye(2) * 1e6, 0, 0.0
    Q = np.diag([q_eta, q_zeta])
    for t, v_obs in enumerate(y):
        if seen:
            a_p[t], P_p[t] = a, P
        if not np.isnan(v_obs):
            if seen == 0:
                a, P = np.array([v_obs, 0.0]), np.array([[h_eps, 0.0], [0.0, 1.0]])
            else:
                v = v_obs - a[0]
                Fv = max(P[0, 0] + h_eps, 1e-12)
                u = v / np.sqrt(Fv)
                rho = u * u if abs(u) <= c else 2 * c * abs(u) - c * c
                if seen >= 2:
                    ll += -0.5 * (np.log(2 * np.pi * Fv) + rho)
                K = P[:, 0] / Fv
                a = a + K * np.sqrt(Fv) * np.clip(u, -c, c)
                P = P - np.outer(K, P[0, :])
            seen += 1
        if seen:
            a_f[t], P_f[t] = a, P
            a, P = TMAT @ a, TMAT @ P @ TMAT.T + Q
    return {"ll": ll, "a_p": a_p, "P_p": P_p, "a_f": a_f, "P_f": P_f, "var": (h_eps, q_eta, q_zeta)}


NO_LEVEL_SHOCK = np.log(1e-10)


def fit(y: np.ndarray, prior_sd=(0.3, 0.15, 0.01), prior_log_sd: float = 1.5, c: float = 2.0,
        smooth_trend: bool = False) -> dict:
    """MAP variances, then the filter at those variances. smooth_trend: the level variance is fixed at ~0 and only
    the observation and slope variances are fitted."""
    centre = 2 * np.log(np.array(prior_sd))
    if smooth_trend:
        full = lambda lv2: np.array([lv2[0], NO_LEVEL_SHOCK, lv2[1]])  # noqa: E731
        obj = lambda lv2: (-llt_filter(y, full(lv2), c)["ll"]  # noqa: E731
                           + 0.5 * np.sum(((lv2 - centre[[0, 2]]) / prior_log_sd) ** 2))
        res = minimize(obj, centre[[0, 2]], method="Nelder-Mead", options={"maxiter": 300, "xatol": 1e-3, "fatol": 1e-3})
        return llt_filter(y, full(res.x), c)
    obj = lambda lv: -llt_filter(y, lv, c)["ll"] + 0.5 * np.sum(((lv - centre) / prior_log_sd) ** 2)  # noqa: E731
    res = minimize(obj, centre, method="Nelder-Mead", options={"maxiter": 300, "xatol": 1e-3, "fatol": 1e-3})
    return llt_filter(y, res.x, c)


def smooth(f: dict) -> tuple[np.ndarray, np.ndarray]:
    """Rauch-Tung-Striebel smoother: smoothed means (n x 2) and covariances (n x 2 x 2), NaN before the first obs."""
    a_f, P_f, a_p, P_p = f["a_f"], f["P_f"], f["a_p"], f["P_p"]
    n = len(a_f)
    a_s, P_s = a_f.copy(), P_f.copy()
    for t in range(n - 2, -1, -1):
        if np.isnan(a_f[t, 0]) or np.isnan(a_p[t + 1, 0]):
            continue
        J = P_f[t] @ TMAT.T @ np.linalg.inv(P_p[t + 1])
        a_s[t] = a_f[t] + J @ (a_s[t + 1] - a_p[t + 1])
        P_s[t] = P_f[t] + J @ (P_s[t + 1] - P_p[t + 1]) @ J.T
    return a_s, P_s


def tolerance(past: np.ndarray | float, abs_tol: float, rel_tol: float):
    return np.maximum(abs_tol, rel_tol * np.abs(past))


def classify(future: float, past: float, abs_tol: float, rel_tol: float) -> str:
    tol = tolerance(past, abs_tol, rel_tol)
    return "accelerating" if future > past + tol else "decelerating" if future < past - tol else "stable"


CLASSES = ("accelerating", "stable", "decelerating")


def forecast(y: np.ndarray, horizons, n: int, rng: np.random.Generator, abs_tol: float, rel_tol: float,
             max_h: int = 12, **fit_kw) -> dict:
    """Trend forecast at the end of series y (log2 hours). Raises ValueError when there is too little history."""
    if np.isfinite(y).sum() < 13:
        raise ValueError("fewer than 13 months of frontier: no 12-month trend history")
    f = fit(y, **fit_kw)
    a_s, P_s = smooth(f)
    h_eps, q_eta, q_zeta = f["var"]
    aT, PT = f["a_f"][-1], f["P_f"][-1]
    sl = a_s[-13:-1, 1]  # slopes driving months T-11..T
    past = 12 * float(np.mean(sl))
    past_sd = 12 * float(np.sqrt(np.mean(P_s[-13:-1, 1, 1])))  # ignores covariance between months: an approximation
    past_draw = rng.normal(past, past_sd, n)
    out = {"past_pace": past, "past_pace_sd": past_sd, "slope_now": 12 * float(aT[1]),
           "slope_now_sd": 12 * float(np.sqrt(PT[1, 1])), "horizons": {}}
    # Past and current growth rates come from the same smoother, so most of their uncertainty is shared. What decides
    # the class is their difference: under a random-walk slope, b_T minus the past 12 months' mean slope is a sum of
    # slope shocks (variance q_zeta * mean(j) over j = 1..12), plus the future drift.
    shift_var = q_zeta * np.mean(np.arange(1, 13))
    for h in horizons:
        drift = q_zeta * sum(((h - j) / h) ** 2 for j in range(1, h))
        fut = 12 * rng.normal(aT[1], np.sqrt(PT[1, 1] + drift), n)  # the future pace itself (for its range)
        diff = 12 * (aT[1] - float(np.mean(sl))) + 12 * rng.normal(0, np.sqrt(shift_var + drift), n)
        tol = tolerance(past_draw, abs_tol, rel_tol)
        acc, dec = float((diff > tol).mean()), float((diff < -tol).mean())
        out["horizons"][h] = {"future_pace_q": np.quantile(fut, [0.1, 0.5, 0.9]).tolist(),
                              "p": [acc, 1 - acc - dec, dec]}
    k = np.arange(1, max_h + 1)
    lvl_var = PT[0, 0] + 2 * k * PT[0, 1] + k ** 2 * PT[1, 1] + k * q_eta + q_zeta * k * (k + 1) * (2 * k + 1) / 6
    out["level_forecast"] = {"mean": (aT[0] + k * aT[1]).tolist(), "sd": np.sqrt(lvl_var).tolist()}
    out["history"] = {"level": a_s[:, 0].tolist(), "level_sd": np.sqrt(P_s[:, 0, 0]).tolist(),
                      "slope_per_year": (12 * a_s[:, 1]).tolist()}
    out["var"] = {"observation": float(np.sqrt(h_eps)), "level": float(np.sqrt(q_eta)), "slope": float(np.sqrt(q_zeta))}
    return out


def reference(y_full: np.ndarray, **fit_kw) -> np.ndarray:
    """Smoothed slopes (doublings / month) of the whole latest series: what the trend 'turned out to be'."""
    return smooth(fit(y_full, **fit_kw))[0][:, 1]


def realised(slopes: np.ndarray, t: int, h: int) -> tuple[float, float] | None:
    """(past, future) trend pace around month index t from reference slopes, or None if out of range."""
    if t - 12 < 0 or t + h > len(slopes):
        return None
    past, fut = slopes[t - 12:t], slopes[t:t + h]
    if not (np.isfinite(past).all() and np.isfinite(fut).all()):
        return None
    return 12 * float(past.mean()), 12 * float(fut.mean())
