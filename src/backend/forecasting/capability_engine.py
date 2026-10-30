"""AI capability engine: a jump-aware, probabilistic forecast of the METR 50% time-horizon frontier.

The frontier (the best 50% time horizon among models measured by an origin) is a staircase: flat for months, then a
jump when a stronger model is measured. The generic engine (models.py) only sees that staircase month by month, and
its faster / same / slower chances were residual counts, not a forecast distribution. This module replaces both
for target `frontier_time_horizon` (wired in through TargetSpec.engine). Everything below runs at every backtest
origin on that origin's snapshot only (targets/capability_metr.snapshot), and once more on the latest snapshot.

Scale: y = log2(time horizon in hours); a one-unit change is one doubling. Outputs are converted back to minutes,
the unit the rest of the pipeline and the API use.

Data layers (never mixed up):
  A observed   METR measurements as published in the snapshot's vintage: value, 95% CI, release date, suite.
  B bridged    older-suite (v1.0) models with no current-suite (v1.1) measurement, mapped onto the current suite
               by a robust line through the models measured under both (Theil-Sen, bootstrapped). Bridged rows
               only inform the jump model's trend and release rate (at half weight, with the mapping's uncertainty);
               they are never part of the frontier, the target, or the historical pace unless no observed 12-month
               history exists (then the pace is labelled "bridged").
  C simulated  CFG.n_sims future monthly trajectories. Used for ranges and the pace chances only; never shown as
               data and never used as evidence of accuracy.

Components, each simulating whole 12-month trajectories (a frontier never falls, so every path is a running max):
  damped_trend        trailing 12-month slope of the frontier, damped by phi (fitted on the snapshot's own history),
                      plus random-walk noise sized from its own in-snapshot h-month errors. Conservative baseline.
  robust_local_trend  local-linear-trend state-space model (level, slope, their covariance, slowly drifting slope)
                      with Huber-robust updates, so one outsized jump does not dominate; parameters by maximum
                      (robust) likelihood. Simulated from the filtered state and its covariance.
  jump_process        model level: frontier-relevant models (within CFG.near_frontier doublings of the frontier when
                      released) arrive as a Poisson process whose rate has a Gamma posterior (prior: the unit's
                      long-run rate), and each scores trend + Student-t noise. The trend is a recency-weighted Huber
                      fit, bootstrapped over models and their measurement error, with its slope shrunk towards the
                      unit's long-run slope by precision. The frontier is the running max: a month with no new
                      record and an outsized jump are both possible outcomes.
  ensemble            a mixture: each trajectory comes from one component, in proportion to weights set at each
                      origin from the components' errors on earlier origins whose outcome was already known
                      (inverse squared MAE, CFG.ensemble_shrink of it moved to equal weights; equal weights until
                      CFG.min_weight_cases cases exist). The damped trend is always in it.

Pace (faster / same / slower), from the same trajectories:
  historical pace  = change of the measured frontier over the past 12 months, in doublings / year, with each end's
                     measurement uncertainty drawn per trajectory (two-piece normal from METR's 95% CI)
  future pace      = (12 / h) * (frontier at T+h - frontier at T), per trajectory
  same             |future - historical| <= max(CFG.pace_tol_abs, CFG.pace_tol_rel * |historical|)
  The chances are the shares of trajectories, so they sum to 1. If the ensemble's chances did not beat both a
  1/3 guess and the rolling base rate in the *selection* period (Brier), CFG.pace_shrink of them is moved to the
  base rate and the row is labelled prior-assisted. The holdout never changes anything; it is reported.

Measurement: points above CFG.saturation_hours are left out of trend fits (METR's own rule: the task suite thins
out there), and every measurement carries its own asymmetric CI, so a horizon near the suite's ceiling is wide.

Second round (brief AI_CAPABILITY_IMPROVEMENT_V2.MD):
  record_jump       two-stage component (capability_record): a constant monthly chance of a new record (stage A),
                    log-normal jump sizes with a conservative prior (stage B).
  Decided on selection-period cases only, then applied everywhere:
    - which components join the damped trend in the ensemble (`inclusion`: interval score within CFG.include_ratio);
    - whether an external signal (capability_signals) enters stage A (`signal_decision`: it must beat the same model
      without it in >= CFG.signal_keep_share of block-bootstrap resamples, and beat the constant hazard);
    - raw or temperature-calibrated pace chances (lower selection log loss; the temperature at each origin is fitted
      on forecasts resolved before it), then the shrink rule above;
    - the chance of no new record: stage A if it beat the rolling base rate, else that base rate.
  Secondary output (capability_trend): the smoothed underlying trend and P(accelerating / stable / decelerating),
  scored against the same smoother run on the latest data. Kept apart from the observed-frontier forecast.
  Dependence: non-overlapping test cases and a moving-block bootstrap (capability_eval) next to the full backtest.
  The bridge is not used at origins where the current suite was not yet published (its fit would use future data).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import capability, capability_eval as V, capability_record as RC, capability_signals as SG
from . import capability_trend as TR, evaluation as E, features as F
from .models import CANDIDATES as GENERIC, PHIS
from .targets import capability_metr as CM

LOG2_60 = float(np.log2(60))  # log2 minutes = log2 hours + this


@dataclass(frozen=True)
class Config:
    """Every setting is fixed before scoring and documented in FORECAST_REBUILD.md section 8c; none is tuned on
    backtest outcomes."""
    n_sims: int = 5000  # trajectories for the served forecast
    n_sims_backtest: int = 2000  # per origin and unit in the backtest
    seed: int = 20261024
    horizons: tuple = (3, 6, 12)
    max_h: int = 12
    pace_tol_abs: float = 0.25  # doublings / year: "about the same pace" is at least this wide ...
    pace_tol_rel: float = 0.20  # ... or 20% of the historical pace, whichever is larger
    ci_z: float = 1.96  # METR's CIs are 95% bootstrap intervals
    default_sigma: float = 0.5  # doublings, when a measurement has no CI
    saturation_hours: float = 16.0  # METR leaves points above 16 h out of its trend fits
    near_frontier: float = 1.0  # doublings below the frontier at release that still count as frontier-relevant
    trend_half_life: float = 18.0  # months: recency weight of the jump model's trend
    trend_since: str = "2023-01"  # long-run slope prior: frontier-relevant models released since then
    slope_prior_floor: float = 0.5 / 12  # doublings / month: the long-run slope is never treated as more certain
    n_boot: int = 300
    resid_df: float = 4.0  # Student-t tails for a new model's distance from the trend
    resid_floor: float = 0.25  # doublings: minimum spread of new models around the trend
    rate_window: int = 24  # months of release history behind the release rate
    rate_prior_months: float = 12.0  # Gamma prior on the release rate is worth this many months at the long-run rate
    bridged_weight: float = 0.5
    huber_c: float = 1.5
    llt_robust_c: float = 2.0
    # local trend prior, per month: observation 0.3 doublings (staircase steps), level 0.15, slope 0.01 (the
    # slope drifts ~0.4 doublings/year over a year); log-variance prior sd 1.5 (variances free within ~e^3 either way)
    llt_prior_sd: tuple = (0.3, 0.15, 0.01)
    llt_prior_log_sd: float = 1.5
    ensemble_shrink: float = 0.5
    min_weight_cases: int = 6
    pace_shrink: float = 0.25
    min_pace_cases: int = 10
    bridge_min_pairs: int = 6
    bridge_slope_range: tuple = (0.6, 1.6)  # bootstrap 80% CI of the slope must lie inside, else a weak prior
    # which components enter the ensemble (decided on selection-period cases only): a component's 80% interval
    # score, case by case, may be at most include_ratio x the damped trend's on >= min_include_pairs shared cases
    include_ratio: float = 1.10
    min_include_pairs: int = 10
    # probability calibration: temperature fitted on earlier resolved forecasts only, once >= this many exist
    min_calib_cases: int = 20
    calib_prior_sd: float = 0.5
    # an external signal is kept only if its selection-period log loss beats the same model without it in >= 90%
    # of block-bootstrap resamples
    signal_keep_share: float = 0.9
    # a generic candidate gets a predictive distribution (generic_paths) only from this many earlier errors
    min_generic_errors: int = 10


CFG = Config()
COMPONENTS = ("damped_trend", "robust_local_trend", "jump_process", "record_jump")
ENSEMBLE = "ensemble"
PACES = ("faster", "same", "slower")
REGIME_OF = {"faster": "acceleration", "same": "stable", "slower": "slowdown"}  # the pipeline's column names
QS = (0.1, 0.25, 0.5, 0.75, 0.9)


# ---------------------------------------------------------------------------------------------------- data layers

def month_index(d: pd.Series) -> np.ndarray:
    """Release date -> months since 1970-01 as a float (2026-07-16 -> ordinal of 2026-07 + 0.5)."""
    d = pd.to_datetime(d)
    return ((d.dt.year - 1970) * 12 + d.dt.month - 1 + (d.dt.day - 1) / d.dt.days_in_month).to_numpy(float)


def sigmas(value, lo, hi, cfg: Config = CFG) -> tuple[np.ndarray, np.ndarray]:
    """log2 standard errors below and above each estimate, from its 95% CI (default where missing)."""
    v = np.asarray(value, float)
    num = lambda c: (np.full(len(v), np.nan) if c is None  # noqa: E731 (no CI column at all)
                     else pd.to_numeric(pd.Series(list(c) if not np.isscalar(c) else [c] * len(v)), errors="coerce").to_numpy(float))
    lo, hi = num(lo), num(hi)
    with np.errstate(divide="ignore", invalid="ignore"):
        s_lo = (np.log2(v) - np.log2(lo)) / cfg.ci_z
        s_hi = (np.log2(hi) - np.log2(v)) / cfg.ci_z
    ok = lambda s: np.where(np.isfinite(s) & (s > 0), np.clip(s, 0.02, 3.0), cfg.default_sigma)  # noqa: E731
    return ok(s_lo), ok(s_hi)


def layer_a(rows: pd.DataFrame, cfg: Config = CFG) -> pd.DataFrame:
    """Observed measurements -> model, release_date, t, y (log2 hours), s_lo, s_hi, saturated, layer."""
    if rows.empty:
        return pd.DataFrame(columns=["model", "release_date", "t", "y", "s_lo", "s_hi", "saturated", "layer"])
    s_lo, s_hi = sigmas(rows["value"], rows.get("ci_low"), rows.get("ci_high"), cfg)
    y = np.log2(rows["value"].to_numpy(float)) - LOG2_60
    return pd.DataFrame({"model": rows["model"].to_numpy(), "release_date": rows["release_date"].to_numpy(),
                         "t": month_index(rows["release_date"]), "y": y, "s_lo": s_lo, "s_hi": s_hi,
                         "saturated": y > np.log2(cfg.saturation_hours), "layer": "observed"})


def base_name(models: pd.Series) -> pd.Series:
    """Epoch's model name without the run setting: 'o3-2025-04-16_medium' and 'o3-2025-04-16_unknown' match."""
    return models.astype(str).str.lower().str.split("_").str[0]


def _theil_sen(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    i, j = np.triu_indices(len(x), 1)
    dx = x[j] - x[i]
    keep = np.abs(dx) > 1e-9
    b = float(np.median((y[j] - y[i])[keep] / dx[keep])) if keep.any() else 1.0
    return float(np.median(y - b * x)), b


def bridge(new: pd.DataFrame, old: pd.DataFrame, rng: np.random.Generator, cfg: Config = CFG) -> dict:
    """Map the older suite onto the current one from the models measured under both (log2 hours):
    y_new = a + b * y_old. With too few pairs or an implausible slope, b = 1 and the spread is doubled (weak prior).
    `boot` holds bootstrap (a, b) pairs for propagating the mapping's own uncertainty."""
    if new.empty or old.empty:
        return {"applied": False, "n_pairs": 0, "reason": "no overlap"}
    j = new.assign(k=base_name(new["model"])).merge(old.assign(k=base_name(old["model"])), on="k",
                                                     suffixes=("_new", "_old"))
    j = j.drop_duplicates("k")
    if len(j) < 2:
        return {"applied": False, "n_pairs": int(len(j)), "reason": "fewer than 2 models measured on both suites"}
    x, y = j["y_old"].to_numpy(), j["y_new"].to_numpy()
    a, b = _theil_sen(x, y)
    boot = np.array([_theil_sen(x[k], y[k]) for k in (rng.integers(0, len(x), len(x)) for _ in range(cfg.n_boot))
                     if len(np.unique(x[k])) > 1])
    lo_b, hi_b = np.quantile(boot[:, 1], [0.1, 0.9])
    credible = len(j) >= cfg.bridge_min_pairs and cfg.bridge_slope_range[0] <= lo_b and hi_b <= cfg.bridge_slope_range[1]
    if not credible:
        a, b = float(np.median(y - x)), 1.0
        boot = np.column_stack([[np.median((y - x)[k]) for k in (rng.integers(0, len(x), len(x)) for _ in range(cfg.n_boot))],
                                np.ones(cfg.n_boot)])
    resid = y - (a + b * x)
    sd = max(1.4826 * float(np.median(np.abs(resid - np.median(resid)))), 0.1) * (1 if credible else 2)
    return {"applied": True, "credible": bool(credible), "n_pairs": int(len(j)), "intercept": a, "slope": b,
            "slope_ci80": [float(lo_b), float(hi_b)], "resid_sd": sd, "boot": boot,
            "pairs": [{"model": k, "old_minutes": float(2 ** (xo + LOG2_60)), "new_minutes": float(2 ** (yn + LOG2_60))}
                      for k, xo, yn in zip(j["k"], x, y)]}


def layer_b(new: pd.DataFrame, old: pd.DataFrame, br: dict) -> pd.DataFrame:
    """Older-suite models with no current-suite measurement, mapped through the bridge, uncertainty included."""
    if not br.get("applied") or old.empty:
        return new.iloc[:0]
    only = old[~base_name(old["model"]).isin(set(base_name(new["model"])))]
    if only.empty:
        return new.iloc[:0]
    a, b = br["intercept"], br["slope"]
    x = only["y"].to_numpy()
    param_sd = np.std(br["boot"][:, [0]] + br["boot"][:, [1]] * x[None, :], axis=0)
    extra = np.sqrt(br["resid_sd"] ** 2 + param_sd ** 2)
    return only.assign(y=a + b * x, s_lo=np.sqrt((b * only["s_lo"]) ** 2 + extra ** 2),
                       s_hi=np.sqrt((b * only["s_hi"]) ** 2 + extra ** 2), layer="bridged")


def frontier_models(obs: pd.DataFrame, first: pd.Period, last: pd.Period) -> pd.DataFrame:
    """Monthly measured frontier and the model holding it (same rules as capability_metr.frontier: a month's
    frontier needs a measured model released in the previous CM.MAX_STALE_MONTHS)."""
    months = pd.period_range(first, last, freq="M")
    out = []
    for m in months:
        end = m.ordinal + 1  # month index (months since 1970-01) of the month's end
        e = obs[obs["t"] < end]
        if e.empty or (m.ordinal - int(np.floor(e["t"].max()))) > CM.MAX_STALE_MONTHS:
            out.append((m, np.nan, None, np.nan, np.nan))
            continue
        r = e.loc[e["y"].idxmax()]
        out.append((m, r["y"], r["model"], r["s_lo"], r["s_hi"]))
    return pd.DataFrame(out, columns=["period", "y", "model", "s_lo", "s_hi"])


def two_piece(y, s_lo, s_hi, z):
    """A draw with median y: below it the lower SE applies, above it the upper (METR's CIs are asymmetric)."""
    return y + np.where(z < 0, z * s_lo, z * s_hi)


# ------------------------------------------------------------------------------------------------------ components

def huber_fit(t: np.ndarray, y: np.ndarray, w: np.ndarray, c: float = CFG.huber_c, iters: int = 30) -> tuple:
    """Weighted Huber regression y = a + b t by IRLS -> (a, b, robust residual scale)."""
    X = np.column_stack([np.ones_like(t), t])
    hw = np.ones_like(y)
    beta = np.zeros(2)
    s = 1.0
    for _ in range(iters):
        W = w * hw
        A = X.T @ (X * W[:, None])
        if np.linalg.cond(A) > 1e12:
            break
        beta = np.linalg.solve(A, X.T @ (W * y))
        r = y - X @ beta
        s = max(1.4826 * float(np.median(np.abs(r))), 1e-3)
        u = np.abs(r) / s
        hw = np.where(u <= c, 1.0, c / np.maximum(u, 1e-12))
    return float(beta[0]), float(beta[1]), s


def robust_llt(y: np.ndarray, log_var: np.ndarray, c: float = CFG.llt_robust_c):
    """Local linear trend on one series (NaN = unobserved), Huber-robust (capability_trend.llt_filter).
    Returns (robust log-likelihood, last filtered state [level, slope], its covariance, variances)."""
    f = TR.llt_filter(y, log_var, c)
    return f["ll"], f["a_f"][-1], f["P_f"][-1], f["var"]


def _cum_paths(y0: np.ndarray, change: np.ndarray) -> np.ndarray:
    """Absolute frontier paths from changes: never below the current frontier, never falling."""
    return np.maximum.accumulate(np.maximum(y0[:, None] + change, y0[:, None]), axis=1)


def _rays(mean: np.ndarray, sd: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """n trajectories mean_k + sd_k * z, one z per trajectory: each horizon gets the right spread, and a rising
    mean gives non-falling paths. (A running max over random-walk noise would push the median up.)"""
    return mean[None, :] + sd[None, :] * rng.standard_normal(n)[:, None]


def sim_damped(ctx: dict, n: int, rng: np.random.Generator, cfg: Config = CFG) -> tuple[np.ndarray, dict]:
    y = ctx["series"]  # monthly frontier (log2 hours), last value = T
    k = np.arange(1, cfg.max_h + 1)
    trend = lambda i: y[i] - y[i - 12] if i >= 12 and np.isfinite(y[i]) and np.isfinite(y[i - 12]) else np.nan  # noqa: E731
    T = len(y) - 1
    b0 = trend(T)
    if np.isnan(b0):  # no 12-month history: slope over what there is (>= 6 months), else flat
        ok = np.where(np.isfinite(y))[0]
        b0 = (y[T] - y[ok[0]]) / (T - ok[0]) * 12 if len(ok) and T - ok[0] >= 6 else 0.0
    path = lambda tr, phi, kk: tr / 12 * np.array([sum(phi ** j for j in range(1, x + 1)) for x in kk])  # noqa: E731
    anchors = [i for i in range(12, T) if np.isfinite(trend(i))]
    errs = {}
    for phi in PHIS:
        e = [y[i + h] - y[i] - path(trend(i), phi, [h])[0] for i in anchors for h in cfg.horizons
             if i + h <= T and np.isfinite(y[i + h])]
        if e:
            errs[phi] = np.mean(np.abs(e))
    phi = min(errs, key=errs.get) if errs else 0.9
    res = [(h, y[i + h] - y[i] - path(trend(i), phi, [h])[0]) for i in anchors for h in cfg.horizons
           if i + h <= T and np.isfinite(y[i + h])]
    var_per_month = (float(np.median([e * e / h for h, e in res])) / 0.455 if len(res) >= 5 else 0.25 ** 2)
    var_per_month = max(var_per_month, 0.05 ** 2)  # median of chi2(1) is 0.455: median-based variance
    mean = path(b0, phi, k)
    change = _rays(mean, np.sqrt(var_per_month * k), n, rng)
    return _cum_paths(ctx["y0"][:n], change), {"phi": phi, "slope_per_year": float(b0),
                                               "noise_sd_per_month": float(np.sqrt(var_per_month))}


def llt_fit(y: np.ndarray, cfg: Config = CFG):
    """Variances by maximum a posteriori: the robust likelihood plus a log-normal prior on each variance (centres
    cfg.llt_prior_sd, spread cfg.llt_prior_log_sd). Without it a staircase drives the slope variance to 0 or to
    values that let the slope wander by 20 doublings a year."""
    f = TR.fit(y, cfg.llt_prior_sd, cfg.llt_prior_log_sd, cfg.llt_robust_c)
    return f["ll"], f["a_f"][-1], f["P_f"][-1], f["var"]


def sim_local(ctx: dict, n: int, rng: np.random.Generator, cfg: Config = CFG) -> tuple[np.ndarray, dict]:
    y = ctx["series"]
    if np.isfinite(y).sum() < 8:
        raise ValueError("fewer than 8 months of frontier")
    _, a, P, (h_eps, q_eta, q_zeta) = llt_fit(y, cfg)
    k = np.arange(1, cfg.max_h + 1)
    mean = a[0] + k * a[1] - y[-1]
    # level at T+k = level + k slope + sum of k level shocks + sum_j (k-j+1) slope shocks; plus observation noise
    var = P[0, 0] + 2 * k * P[0, 1] + k ** 2 * P[1, 1] + k * q_eta + q_zeta * k * (k + 1) * (2 * k + 1) / 6 + h_eps
    return _cum_paths(ctx["y0"][:n], _rays(mean, np.sqrt(var), n, rng)), {
        "slope_per_year": float(a[1] * 12), "slope_sd_per_year": float(np.sqrt(P[1, 1]) * 12),
        "sd": {"observation": float(np.sqrt(h_eps)), "level": float(np.sqrt(q_eta)), "slope": float(np.sqrt(q_zeta))}}


def _relevant(m: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Models within cfg.near_frontier doublings of the best model released before them (first ones count)."""
    m = m.sort_values("t")
    best, keep = -np.inf, []
    for y in m["y"]:
        keep.append(y >= best - cfg.near_frontier)
        best = max(best, y)
    return m[np.array(keep, dtype=bool)]


def jump_params(models: pd.DataFrame, T_end: float, rng: np.random.Generator, cfg: Config = CFG) -> dict:
    """Bootstrap draws of the jump model's trend (level at T_end, slope / month, spread) and release-rate posterior."""
    rel = _relevant(models, cfg)
    fit = rel[~rel["saturated"]]
    if len(fit) < 4:
        raise ValueError("fewer than 4 frontier-relevant models")
    t = fit["t"].to_numpy() - T_end
    w_layer = np.where(fit["layer"] == "bridged", cfg.bridged_weight, 1.0)
    w_recent = 0.5 ** (-t / cfg.trend_half_life) * w_layer
    since = month_index(pd.Series([pd.Timestamp(cfg.trend_since)]))[0] - T_end
    long = t >= since
    sd = (fit["s_lo"].to_numpy() + fit["s_hi"].to_numpy()) / 2
    a_r, b_r, s_r = huber_fit(t, fit["y"].to_numpy(), w_recent)
    draws = []
    for _ in range(cfg.n_boot):
        k = rng.integers(0, len(fit), len(fit))
        if len(np.unique(t[k])) < 3:
            continue
        yk = fit["y"].to_numpy()[k] + rng.normal(0, sd[k])  # measurement error, refitted
        a, b, s = huber_fit(t[k], yk, w_recent[k])
        lk = k[long[k]]
        bp = huber_fit(t[lk], yk[long[k]], w_layer[lk])[1] if len(np.unique(t[lk])) >= 3 else b
        draws.append((a, b, s, bp))
    dr = np.array(draws)
    v_r, v_p = np.var(dr[:, 1]), max(np.var(dr[:, 3]), cfg.slope_prior_floor ** 2)
    lam = v_p / (v_r + v_p)  # weight on the recent slope; the rest goes to the long-run slope
    slope = lam * dr[:, 1] + (1 - lam) * dr[:, 3]
    level = dr[:, 0]  # the level at T_end is what the recent fit says; only the slope is shrunk
    spread = np.maximum(dr[:, 2], cfg.resid_floor)
    # release rate: frontier-relevant models (observed and bridged) per month, Gamma(shape, rate) posterior
    rt = rel["t"].to_numpy()
    recent = (rt > T_end - cfg.rate_window).sum()
    span = max(T_end - rt.min(), 12.0)
    long_rate = len(rt) / span
    shape, rate = cfg.rate_prior_months * long_rate + recent, cfg.rate_prior_months + cfg.rate_window
    return {"level": level, "slope": slope, "spread": spread, "rate_shape": shape, "rate_rate": rate,
            "n_relevant": int(len(rel)), "n_fit": int(len(fit)), "recent_weight": float(lam),
            "slope_recent": float(b_r), "slope_long": float(np.median(dr[:, 3])), "relevant": rel}


def sim_jump(ctx: dict, n: int, rng: np.random.Generator, cfg: Config = CFG) -> tuple[np.ndarray, dict]:
    p = ctx.get("jump") or jump_params(ctx["models"], ctx["T_end"], rng, cfg)
    ctx["jump"] = p
    i = rng.integers(0, len(p["slope"]), n)
    level, slope, spread = p["level"][i], p["slope"][i], p["spread"][i]
    lam = rng.gamma(p["rate_shape"], 1 / p["rate_rate"], n)
    counts = rng.poisson(lam[:, None], (n, cfg.max_h))
    kmax = max(int(counts.max()), 1)
    tscale = np.sqrt((cfg.resid_df - 2) / cfg.resid_df)  # unit-variance Student t
    eps = rng.standard_t(cfg.resid_df, (n, cfg.max_h, kmax)) * tscale * spread[:, None, None]
    when = np.arange(1, cfg.max_h + 1) - 0.5
    scores = level[:, None, None] + slope[:, None, None] * when[None, :, None] + eps
    scores = np.where(np.arange(kmax)[None, None, :] < counts[:, :, None], scores, -np.inf)
    best = scores.max(axis=2)
    paths = np.maximum.accumulate(np.maximum(best, ctx["y0"][:n, None]), axis=1)
    info = {"slope_per_year": float(np.median(slope) * 12), "slope_recent_per_year": p["slope_recent"] * 12,
            "slope_long_per_year": p["slope_long"] * 12, "recent_weight": p["recent_weight"],
            "doubling_time_months": float(1 / np.median(slope)) if np.median(slope) > 0 else None,
            "releases_per_month": float(p["rate_shape"] / p["rate_rate"]), "spread": float(np.median(spread)),
            "n_relevant": p["n_relevant"], "n_fit": p["n_fit"],
            "p_no_new_record": {str(h): float((paths[:, h - 1] <= ctx["y0"][:n] + 1e-12).mean()) for h in cfg.horizons}}
    return paths, info


def record_hazard(ctx: dict, n: int, rng: np.random.Generator, signal: str | None = None) -> tuple[np.ndarray, dict]:
    """Per-trajectory monthly record chance: constant (Beta posterior) or, for a kept external signal, logistic."""
    rec, _ = RC.records(ctx["series"])
    if signal is None:
        a, b = RC.hazard_beta(rec)
        return rng.beta(a, b, n), {"hazard": "constant", "p_month": a / (a + b)}
    z = ctx["signals"][signal]
    fit = RC.hazard_logit(rec, z[:-1])  # z at the start of each month = the signal one month earlier
    draws = rng.multivariate_normal(fit["beta"], fit["cov"], n)
    x = (z[-1] - fit["mu"]) / fit["sd"]
    p = 1 / (1 + np.exp(-(draws[:, 0] + draws[:, 1] * x)))
    return p, {"hazard": signal, "p_month": float(np.mean(p))}


def sim_record(ctx: dict, n: int, rng: np.random.Generator, cfg: Config = CFG) -> tuple[np.ndarray, dict]:
    """Two-stage record model (capability_record): stage A whether a record comes, stage B how big it is."""
    p, info = record_hazard(ctx, n, rng, ctx.get("hazard_signal"))
    _, jumps = RC.records(ctx["series"])
    post = RC.jump_posterior(jumps)
    paths, hit = RC.simulate(ctx["y0"][:n], p, post, cfg.max_h, rng)
    paths = np.maximum.accumulate(paths, axis=1)
    med_jump = float(np.exp(post["mu"]))
    info.update({"n_jumps": post["n_jumps"], "median_jump_doublings": med_jump,
                 "p_no_new_record": {str(h): float((~hit[:, :h].any(axis=1)).mean()) for h in cfg.horizons},
                 "implied_pace_per_year": float(12 * info["p_month"] * np.exp(post["mu"] + post["beta"] / (post["alpha"] - 1) / 2))})
    return paths, info


SIMULATORS = {"damped_trend": sim_damped, "robust_local_trend": sim_local, "jump_process": sim_jump,
              "record_jump": sim_record}


# ------------------------------------------------------------------------------------------- one origin, one unit

def context(s: F.Snapshot, unit: str, rng: np.random.Generator, n: int, cfg: Config = CFG,
            signals: pd.DataFrame | None = None) -> dict | None:
    """Everything the components need for one unit at one origin, from that origin's snapshot only.
    `signals`: external monthly features (capability_signals), cut here at the origin's month."""
    raw = s.extras.get("models", {}).get(unit)
    if raw is None or raw.empty:
        return None
    if s.values.loc[s.values["unit"] == unit, "period"].max() != s.last:
        return None  # this unit is complete only to an earlier month: later months are unmeasured, not flat
    obs = layer_a(raw, cfg)
    old = s.extras.get("legacy", {}).get(unit)
    if "snapshot_kind" in raw and (raw["snapshot_kind"] == "reconstructed").any():
        old = None  # this suite was not published yet: a bridge fitted on its later file would use future data
        br = {"applied": False, "n_pairs": 0, "reason": "current suite not yet published at this origin"}
    else:
        br = bridge(obs, layer_a(old, cfg), rng, cfg) if old is not None and not old.empty else {"applied": False, "n_pairs": 0}
    bri = layer_b(obs, layer_a(old, cfg), br) if br.get("applied") else obs.iloc[:0]
    first = pd.Period(pd.Timestamp(obs["release_date"].min()), freq="M")
    fr = frontier_models(obs, first, s.last)
    if fr.empty or np.isnan(fr["y"].iloc[-1]):
        return None
    y = fr["y"].to_numpy()
    # draws of the true value of every model that holds the frontier at T or T-12 (one draw per model)
    z = {}
    def draw(row):
        if row["model"] not in z:
            z[row["model"]] = rng.standard_normal(n)
        return two_piece(row["y"], row["s_lo"], row["s_hi"], z[row["model"]])
    now = fr.iloc[-1]
    y0 = draw(now)
    pace_basis, hist = "observed_12m", None
    if len(fr) > 12 and np.isfinite(fr["y"].iloc[-13]):
        then = fr.iloc[-13]
        hist = y0 - draw(then)
        hist_point = float(now["y"] - then["y"])
    elif len(bri):  # no observed 12-month history: the bridged layer, labelled as such
        both = pd.concat([obs, bri], ignore_index=True)
        frb = frontier_models(both, pd.Period(pd.Timestamp(both["release_date"].min()), freq="M"), s.last)
        if len(frb) > 12 and np.isfinite(frb["y"].iloc[-13]):
            then = frb.iloc[-13]
            hist = y0 - draw(then)
            hist_point = float(now["y"] - then["y"])
            pace_basis = "bridged_12m"
    T_end = float(s.last.ordinal + 1)
    months = pd.period_range(first, s.last, freq="M")
    sig = {}
    if signals is not None:
        cut = signals.reindex(months)
        sig = {c: cut[c].to_numpy(float) for c in cut.columns if np.isfinite(cut[c].iloc[-1])}
    ctx = {"unit": unit, "obs": obs, "bridged": bri, "bridge": br, "models": pd.concat([obs, bri], ignore_index=True),
           "frontier": fr, "series": y, "y0": y0, "y_now": float(now["y"]), "now_model": now["model"], "T_end": T_end,
           "last": s.last, "months": months, "signals": sig}
    if hist is None:  # neither: the jump model's own slope (a prior, labelled)
        try:
            p = jump_params(ctx["models"], T_end, rng, cfg)
            ctx["jump"] = p
            hist = rng.choice(p["slope"], n) * 12
            hist_point, pace_basis = float(np.median(p["slope"]) * 12), "trend_prior"
        except ValueError:
            hist, hist_point, pace_basis = np.zeros(n), 0.0, "none"
    ctx.update(hist=hist, hist_point=hist_point, pace_basis=pace_basis)
    return ctx


def simulate(ctx: dict, n: int, rng: np.random.Generator, cfg: Config = CFG) -> tuple[dict, dict]:
    """Every component's trajectories (n x max_h, log2 hours) and notes; a component that cannot run is left out."""
    paths, notes = {}, {}
    for c, f in SIMULATORS.items():
        try:
            paths[c], notes[c] = f(ctx, n, rng, cfg)
        except (ValueError, np.linalg.LinAlgError) as e:
            notes[c] = {"unavailable": str(e)}
    return paths, notes


def mixture(paths: dict, weights: dict, n: int) -> tuple[np.ndarray, dict]:
    """Ensemble trajectories: component c contributes round(weight * n) of its own (the first ones, all iid)."""
    avail = {c: w for c, w in weights.items() if c in paths and w > 0}
    tot = sum(avail.values())
    counts = {c: int(round(w / tot * n)) for c, w in avail.items()}
    last = list(counts)[-1]
    counts[last] += n - sum(counts.values())
    return np.concatenate([paths[c][:k] for c, k in counts.items() if k > 0]), {c: k / n for c, k in counts.items()}


def pace_probs(paths: np.ndarray, y0: np.ndarray, hist: np.ndarray, h: int, cfg: Config = CFG) -> np.ndarray:
    """Shares of trajectories growing faster / about as fast / slower than the historical pace (sum to 1)."""
    n = len(paths)
    fut = 12 / h * (paths[:, h - 1] - y0[:n])
    hp = hist[:n]
    tol = np.maximum(cfg.pace_tol_abs, cfg.pace_tol_rel * np.abs(hp))
    faster, slower = (fut > hp + tol).mean(), (fut < hp - tol).mean()
    return np.array([faster, 1 - faster - slower, slower])


def pace_class(future_pace: float, hist_point: float, cfg: Config = CFG) -> str:
    tol = max(cfg.pace_tol_abs, cfg.pace_tol_rel * abs(hist_point))
    return "faster" if future_pace > hist_point + tol else "slower" if future_pace < hist_point - tol else "same"


def summarise(paths: np.ndarray, ctx: dict, cfg: Config = CFG) -> dict:
    out = {}
    for h in cfg.horizons:
        q = np.quantile(paths[:, h - 1], QS)
        out[h] = {"q": q, "p": pace_probs(paths, ctx["y0"], ctx["hist"], h, cfg)}
    return out


# ------------------------------------------------------------------------------------------------------- backtest
#
# Pass 1 (per origin and unit, snapshot only): every component's trajectories, the record-chance variants (stage A,
# with and without each external signal) and the secondary trend forecast. Then three decisions, each made on
# selection-period cases only: which components enter the ensemble, whether an external signal is kept, and which
# probability version is served. Pass 2 builds the ensemble at every origin with weights and a temperature fitted
# on cases resolved before that origin.

def ensemble_weights(errs: pd.DataFrame, h: int, avail, cfg: Config = CFG, members=COMPONENTS) -> dict:
    """Weights from resolved earlier cases at horizon h: shrunk inverse squared MAE (equal until enough cases)."""
    avail = [c for c in members if c in avail]
    eq = {c: 1 / len(avail) for c in avail}
    if errs.empty:
        return eq
    e = errs[(errs["h"] == h) & errs["candidate"].isin(avail)]
    cases = e.groupby(["origin", "unit"])["candidate"].nunique()
    full = cases[cases == len(avail)].index
    e = e.set_index(["origin", "unit"]).loc[lambda d: d.index.isin(full)]
    if len(full) < cfg.min_weight_cases:
        return eq
    mae = e.groupby("candidate")["abs_err"].mean()
    inv = 1 / np.maximum(mae, 0.05) ** 2
    raw = inv / inv.sum()
    return {c: (1 - cfg.ensemble_shrink) * float(raw[c]) + cfg.ensemble_shrink * eq[c] for c in avail}


def base_rate(classes: list[str], labels=PACES) -> np.ndarray:
    """Laplace-smoothed frequencies of the classes among resolved cases (uniform with none)."""
    c = np.array([sum(x == p for x in classes) for p in labels], float)
    return (c + 1) / (c.sum() + len(labels))


def truth_series(y_true: pd.Series, unit: str) -> tuple[pd.PeriodIndex, np.ndarray]:
    """The latest data's monthly frontier of one unit, log2 hours, on a full month range (gaps NaN)."""
    t = y_true.xs(unit, level=1).sort_index()
    months = pd.period_range(t.index.min(), t.index.max(), freq="M")
    return months, np.log2(t.reindex(months).to_numpy(float)) - LOG2_60


def _rolling(df: pd.DataFrame, outcome: str, labels) -> np.ndarray:
    """Per row, the base rate of `outcome` among rows of the same h whose outcome month is <= this row's observed
    month (known by then). Rows must carry h, last_ord, target_ord."""
    out = np.empty((len(df), len(labels)))
    for i, (h, last) in enumerate(zip(df["h"], df["last_ord"])):
        done = df[(df["h"] == h) & (df["target_ord"] <= last)][outcome].dropna()
        out[i] = base_rate(done.tolist(), labels)
    return out


def pass_one(spec, snaps, y_true: pd.Series, split, cfg: Config = CFG, signals: pd.DataFrame | None = None):
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_sims_backtest
    refs = {}
    for unit in y_true.index.get_level_values(1).unique():
        months, y = truth_series(y_true, unit)
        try:
            refs[unit] = (months, TR.reference(y, prior_sd=cfg.llt_prior_sd, prior_log_sd=cfg.llt_prior_log_sd,
                                               c=cfg.llt_robust_c, smooth_trend=True), y)
        except (ValueError, np.linalg.LinAlgError):
            pass
    comp, rec_rows, trend_rows, store = [], [], [], {}
    for i, s in enumerate(snaps):
        for unit in sorted(s.extras.get("models", {})):
            ctx = context(s, unit, rng, n, cfg, signals)
            if ctx is None:
                continue
            paths, _ = simulate(ctx, n, rng, cfg)
            if not paths:
                continue
            store[(i, unit)] = {"paths": {c: p.astype(np.float32) for c, p in paths.items()}, "y0": ctx["y0"],
                                "hist": ctx["hist"], "y_now": ctx["y_now"], "hist_point": ctx["hist_point"],
                                "pace_basis": ctx["pace_basis"], "n_models": len(ctx["obs"]),
                                "n_bridged": len(ctx["bridged"])}
            common = {"origin": s.origin, "last_period": str(s.last), "last_ord": s.last.ordinal,
                      "vintage_kind": s.kind, "vintage": s.vintage, "unit": unit}
            rec, _ = RC.records(ctx["series"])
            hz = {}
            try:
                a, b = RC.hazard_beta(rec)
                hz["constant"] = lambda h, p=rng.beta(a, b, 2000): float(np.mean(RC.p_record_within(p, h)))  # noqa: E731
                f0 = RC.hazard_logit(rec, None)
                hz["logit_no_signal"] = lambda h, f0=f0: float(RC.p_record_within(RC.logit_p(f0, None), h))  # noqa: E731
                for name, z in ctx["signals"].items():
                    if np.isfinite(z[:-1][np.isfinite(rec)]).sum() >= RC.RCFG.min_months:
                        fz = RC.hazard_logit(rec, z[:-1])
                        hz[f"logit_{name}"] = lambda h, fz=fz, zn=z[-1]: float(RC.p_record_within(RC.logit_p(fz, zn), h))  # noqa: E731
            except ValueError:
                pass
            try:
                tr = TR.forecast(ctx["series"], cfg.horizons, n, rng, cfg.pace_tol_abs, cfg.pace_tol_rel, cfg.max_h,
                                 prior_sd=cfg.llt_prior_sd, prior_log_sd=cfg.llt_prior_log_sd, c=cfg.llt_robust_c, smooth_trend=True)
            except (ValueError, np.linalg.LinAlgError):
                tr = None
            for h in cfg.horizons:
                target = s.last + h
                actual = y_true.get((target, unit), np.nan)
                y_act = np.log2(actual) - LOG2_60 if np.isfinite(actual) else np.nan
                fut = 12 / h * (y_act - ctx["y_now"])
                cls = pace_class(fut, ctx["hist_point"], cfg) if np.isfinite(y_act) else None
                row = {**common, "h": h, "target_period": str(target), "target_ord": target.ordinal,
                       "role": E.role(s, h, split)}
                for c, p in paths.items():
                    q = np.quantile(p[:, h - 1], QS)
                    pr = pace_probs(p, ctx["y0"], ctx["hist"], h, cfg)
                    comp.append({**row, "candidate": c, "y_now": ctx["y_now"],
                                 **{f"q{int(x * 100)}": v for x, v in zip(QS, q)}, "y_actual": y_act,
                                 "p_faster": pr[0], "p_same": pr[1], "p_slower": pr[2], "hist_pace": ctx["hist_point"],
                                 "pace_basis": ctx["pace_basis"], "realised_pace": fut, "realised_class": cls,
                                 "n_models": len(ctx["obs"]), "n_bridged": len(ctx["bridged"])})
                now_t = y_true.get((s.last, unit), np.nan)
                happened = (float(actual > now_t * (1 + 1e-9)) if np.isfinite(actual) and np.isfinite(now_t) else np.nan)
                for v, f in hz.items():
                    rec_rows.append({**row, "variant": v, "p_record": f(h), "record": happened})
                if tr is not None:
                    ref = refs.get(unit)
                    real = None
                    if ref is not None and s.last in ref[0]:
                        real = TR.realised(ref[1], ref[0].get_loc(s.last), h)
                    x = tr["horizons"][h]
                    trend_rows.append({**row, "p_accelerating": x["p"][0], "p_stable": x["p"][1],
                                       "p_decelerating": x["p"][2], "future_q50": x["future_pace_q"][1],
                                       "future_q10": x["future_pace_q"][0], "future_q90": x["future_pace_q"][2],
                                       "past_pace": tr["past_pace"],
                                       "realised_past": real[0] if real else np.nan,
                                       "realised_future": real[1] if real else np.nan,
                                       "realised_class": TR.classify(real[1], real[0], cfg.pace_tol_abs, cfg.pace_tol_rel)
                                       if real else None})
    rec = pd.DataFrame(rec_rows)
    if len(rec):
        rec["base"] = np.nan
        for v, g in rec.groupby("variant"):
            rec.loc[g.index, "base"] = _rolling(g.assign(o=g["record"].map({1.0: "yes", 0.0: "no"})), "o",
                                                ("yes", "no"))[:, 0]
    trend = pd.DataFrame(trend_rows)
    if len(trend):
        b = _rolling(trend, "realised_class", TR.CLASSES)
        trend[["base_accelerating", "base_stable", "base_decelerating"]] = b
    comp = pd.DataFrame(comp)
    cases = comp.drop_duplicates(["origin", "unit", "h"]).reset_index(drop=True)  # outcomes are the same for every component
    cases[["clim_faster", "clim_same", "clim_slower"]] = _rolling(cases, "realised_class", PACES)
    comp = comp.merge(cases[["origin", "unit", "h", "clim_faster", "clim_same", "clim_slower"]], on=["origin", "unit", "h"])
    return comp, store, rec, trend


def interval_score(lo, hi, y, alpha=0.2):
    return (hi - lo) + 2 / alpha * np.maximum(lo - y, 0) + 2 / alpha * np.maximum(y - hi, 0)


def inclusion(comp: pd.DataFrame, cfg: Config = CFG) -> dict:
    """Which components enter the ensemble, from selection-period cases only. The damped trend (the simple
    baseline) is always in; another component must have an 80% interval score at most cfg.include_ratio times the
    damped trend's on the cases both forecast, with enough shared cases to judge."""
    d = comp[(comp["role"] == "selection")].dropna(subset=["y_actual"])
    d = d.assign(isc=interval_score(d["q10"], d["q90"], d["y_actual"]))
    w = d.pivot_table(index=["origin", "unit", "h"], columns="candidate", values="isc")
    out = {"damped_trend": {"included": True, "reason": "simple baseline, always included"}}
    for c in COMPONENTS[1:]:
        if c not in w or "damped_trend" not in w:
            out[c] = {"included": False, "reason": "never available in the selection period"}
            continue
        both = w[[c, "damped_trend"]].dropna()
        if len(both) < cfg.min_include_pairs:
            out[c] = {"included": False, "pairs": int(len(both)),
                      "reason": f"only {len(both)} shared selection cases (< {cfg.min_include_pairs}): not enough evidence"}
            continue
        ratio = float(both[c].mean() / both["damped_trend"].mean())
        ok = ratio <= cfg.include_ratio
        out[c] = {"included": bool(ok), "pairs": int(len(both)), "ratio": ratio,
                  "reason": f"interval score {ratio:.2f} x the damped trend's ({'<=' if ok else '>'} {cfg.include_ratio})"}
    return out


def signal_decision(rec: pd.DataFrame, cfg: Config = CFG) -> dict:
    """Keep an external signal only if, on selection cases, the logistic hazard with it beats the same model
    without it (log loss) in >= cfg.signal_keep_share of block-bootstrap resamples."""
    out = {}
    if rec.empty:
        return out
    sel = rec[(rec["role"] == "selection")].dropna(subset=["record"])
    base = sel[sel["variant"] == "logit_no_signal"].set_index(["origin", "unit", "h"])
    const = sel[sel["variant"] == "constant"].set_index(["origin", "unit", "h"])
    ll = lambda p, y: -np.log(np.clip(np.where(y == 1, p, 1 - p), V.EPS, 1))  # noqa: E731
    for v in sorted(set(sel["variant"]) - {"constant", "logit_no_signal"}):
        x = sel[sel["variant"] == v].set_index(["origin", "unit", "h"])
        j = x.join(base, rsuffix="_0", how="inner")
        if j.empty:
            out[v] = {"kept": False, "reason": "no shared selection cases"}
            continue
        diff = pd.Series(ll(j["p_record"], j["record"]) - ll(j["p_record_0"], j["record"]),
                         index=j.index).sort_index(level="origin")  # < 0: the signal helped on that case
        bs = V.block_bootstrap(diff.reset_index(drop=True), block=6, seed=cfg.seed)
        jc = x.join(const, rsuffix="_c", how="inner")
        vs_const = float((ll(jc["p_record"], jc["record"]) - ll(jc["p_record_c"], jc["record"])).mean()) if len(jc) else np.nan
        ablation = bool(bs.get("mean") is not None and bs["mean"] < 0 and bs.get("share_below_0", 0) >= cfg.signal_keep_share)
        kept = ablation and vs_const < 0
        out[v] = {"kept": kept, "n": int(len(j)), "log_loss_change": bs.get("mean"), "bootstrap": bs,
                  "log_loss_change_vs_constant": vs_const,
                  "reason": ("lower log loss than the same model without it in >= 90% of resamples, and than the "
                             "constant hazard" if kept else
                             "beat the same model without it, but not the constant hazard the forecast uses"
                             if ablation else "did not lower log loss consistently over the same model without it")}
    return out


def pass_two(comp: pd.DataFrame, store: dict, snaps, members: list[str], cfg: Config = CFG) -> pd.DataFrame:
    """The ensemble at every origin: weights and temperature from cases resolved before it."""
    resolved = comp.dropna(subset=["y_actual"]).assign(abs_err=lambda d: (d["q50"] - d["y_actual"]).abs())
    rows = []
    for (i, unit), st in sorted(store.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        last = snaps[i].last.ordinal
        done = resolved[resolved["target_ord"] <= last]
        paths = {c: st["paths"][c].astype(float) for c in members if c in st["paths"]}
        if not paths:
            continue
        mine = comp[(comp["origin"] == snaps[i].origin) & (comp["unit"] == unit)]
        for h in cfg.horizons:
            w = ensemble_weights(done, h, paths, cfg, members)
            ens, _ = mixture(paths, w, len(st["y0"]))
            q = np.quantile(ens[:, h - 1], QS)
            p = pace_probs(ens, st["y0"], st["hist"], h, cfg)
            prev = pd.DataFrame([r for r in rows if r["h"] == h and r["target_ord"] <= last and r["realised_class"]])
            if len(prev) >= cfg.min_calib_cases:
                oh = np.column_stack([prev["realised_class"] == c for c in PACES]).astype(float)
                T = V.fit_temperature(prev[["p_faster", "p_same", "p_slower"]].to_numpy(), oh, cfg.calib_prior_sd)
            else:
                T = 1.0
            pc = V.apply_temperature(p[None, :], T)[0] if T != 1.0 else p
            clim = base_rate(prev["realised_class"].tolist() if len(prev) else [])
            r = mine[mine["h"] == h].iloc[0]
            rows.append({k: r[k] for k in ("origin", "last_period", "last_ord", "vintage_kind", "vintage", "unit", "h",
                                           "target_period", "target_ord", "role", "y_actual", "realised_pace",
                                           "realised_class", "hist_pace", "pace_basis", "n_models", "n_bridged")}
                        | {"candidate": ENSEMBLE, "y_now": st["y_now"], **{f"q{int(x * 100)}": v for x, v in zip(QS, q)},
                           "p_faster": p[0], "p_same": p[1], "p_slower": p[2], "temperature": T,
                           "pc_faster": pc[0], "pc_same": pc[1], "pc_slower": pc[2],
                           "clim_faster": clim[0], "clim_same": clim[1], "clim_slower": clim[2],
                           "weight": 1.0, **{f"w_{c}": w.get(c, 0.0) for c in COMPONENTS}})
    return pd.DataFrame(rows)


def point_scores(d: pd.DataFrame) -> dict:
    d = d.dropna(subset=["y_actual"])
    if d.empty:
        return {"n": 0, "n_origins": 0}
    e = d["q50"] - d["y_actual"]
    inside = d["y_actual"].between(d["q10"], d["q90"])
    return {"n": int(len(d)), "n_origins": int(d["origin"].nunique()), "mae": float(e.abs().mean()),
            "median_ae": float(e.abs().median()), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
            "typical_factor": float(2 ** e.abs().mean()), "coverage_80": float(inside.mean()),
            "width_80": float((d["q90"] - d["q10"]).mean()),
            "interval_score_80": float(interval_score(d["q10"], d["q90"], d["y_actual"]).mean())}


def served_probs(d: pd.DataFrame, method: str, shrink: float) -> np.ndarray:
    p = d[["pc_faster", "pc_same", "pc_slower"] if method == "calibrated" else ["p_faster", "p_same", "p_slower"]].to_numpy()
    return (1 - shrink) * p + shrink * d[["clim_faster", "clim_same", "clim_slower"]].to_numpy()


def pace_scores(d: pd.DataFrame, method: str = "raw", shrink: float = 0.0) -> dict:
    d = d.dropna(subset=["realised_class"])
    if d.empty:
        return {"n": 0}
    onehot = np.column_stack([d["realised_class"] == p for p in PACES]).astype(float)
    p = d[["p_faster", "p_same", "p_slower"]].to_numpy()
    clim = d[["clim_faster", "clim_same", "clim_slower"]].to_numpy()
    uni = np.full_like(p, 1 / 3)
    out = {"n": int(len(d)), "n_origins": int(d["origin"].nunique()),
           "brier_model": V.brier(p, onehot), "brier_climatology": V.brier(clim, onehot),
           "brier_uniform": V.brier(uni, onehot), "log_loss_model": V.log_loss(p, onehot),
           "log_loss_climatology": V.log_loss(clim, onehot), "log_loss_uniform": V.log_loss(uni, onehot),
           "class_counts": {c: int((d["realised_class"] == c).sum()) for c in PACES},
           "mean_prob": {c: float(d[f"p_{c}"].mean()) for c in PACES}}
    if "pc_faster" in d:
        pc = d[["pc_faster", "pc_same", "pc_slower"]].to_numpy()
        sv = served_probs(d, method, shrink)
        out.update(brier_calibrated=V.brier(pc, onehot), log_loss_calibrated=V.log_loss(pc, onehot),
                   brier_served=V.brier(sv, onehot), log_loss_served=V.log_loss(sv, onehot))
    return out


def calibration(d: pd.DataFrame, cols=("p_faster", "p_same", "p_slower"), bins=(0, 0.2, 0.4, 0.6, 0.8, 1.0001)) -> list[dict]:
    """Per class and probability bin: mean forecast probability vs how often that class happened."""
    d = d.dropna(subset=["realised_class"])
    out = []
    for c, col in zip(PACES, cols):
        b = pd.cut(d[col], bins, right=False)
        for k, g in d.groupby(b, observed=True):
            out.append({"class": c, "bin": f"{k.left:.1f}-{min(k.right, 1):.1f}", "n": int(len(g)),
                        "mean_p": float(g[col].mean()), "observed": float((g["realised_class"] == c).mean())})
    return out


def _binary_scores(d: pd.DataFrame) -> dict:
    d = d.dropna(subset=["record"])
    if d.empty:
        return {"n": 0}
    oh = V.binary(d["record"].to_numpy())
    return {"n": int(len(d)), "rate": float(d["record"].mean()), "mean_p": float(d["p_record"].mean()),
            "brier_model": V.brier(V.binary(d["p_record"]), oh), "brier_base_rate": V.brier(V.binary(d["base"]), oh),
            "brier_half": V.brier(V.binary(np.full(len(d), 0.5)), oh),
            "log_loss_model": V.log_loss(V.binary(d["p_record"]), oh),
            "log_loss_base_rate": V.log_loss(V.binary(d["base"]), oh)}


def _trend_scores(d: pd.DataFrame) -> dict:
    d = d.dropna(subset=["realised_future"])
    if d.empty:
        return {"n": 0}
    oh = np.column_stack([d["realised_class"] == c for c in TR.CLASSES]).astype(float)
    p = d[["p_accelerating", "p_stable", "p_decelerating"]].to_numpy()
    b = d[["base_accelerating", "base_stable", "base_decelerating"]].to_numpy()
    return {"n": int(len(d)), "n_origins": int(d["origin"].nunique()),
            "mae_pace": float((d["future_q50"] - d["realised_future"]).abs().mean()),
            "mae_persistence": float((d["past_pace"] - d["realised_future"]).abs().mean()),
            "coverage_80": float(d["realised_future"].between(d["future_q10"], d["future_q90"]).mean()),
            "brier_model": V.brier(p, oh), "brier_base_rate": V.brier(b, oh), "brier_uniform": V.brier(np.full_like(p, 1 / 3), oh),
            "log_loss_model": V.log_loss(p, oh), "log_loss_uniform": V.log_loss(np.full_like(p, 1 / 3), oh),
            "class_counts": {c: int((d["realised_class"] == c).sum()) for c in TR.CLASSES}}


def scores(comp: pd.DataFrame, ens: pd.DataFrame, gen: pd.DataFrame, rec: pd.DataFrame, trend: pd.DataFrame,
           cfg: Config = CFG) -> dict:
    """Point, interval and probability scores per horizon and role, against naive and drift on the same cases and
    against a 1/3 guess and the rolling base rate; the served-probability choice (selection period only);
    non-overlapping cases; block-bootstrap intervals; record-chance and trend scores."""
    out = {"point": [], "pace": [], "calibration": {}, "shrink": {}, "non_overlapping": [], "bootstrap": [],
           "record": [], "trend": [], "record_choice": {}}
    base = gen[gen["feature_set"] == "all"][["origin", "unit", "h", "candidate", "pred", "actual"]]
    allc = pd.concat([comp, ens], ignore_index=True)

    def baseline_err(keys: pd.DataFrame, c: str, h: int) -> pd.DataFrame:
        b = base[(base["h"] == h) & (base["candidate"] == c)].merge(keys, on=["origin", "unit"]).dropna(subset=["actual"])
        return b.assign(err=np.log2(b["pred"]) - np.log2(b["actual"]))

    for h in cfg.horizons:
        e_h = ens[ens["h"] == h]
        for role in ("selection", "holdout"):
            g = allc[(allc["h"] == h) & (allc["role"] == role)]
            for c in [*COMPONENTS, ENSEMBLE]:
                out["point"].append({"h": h, "role": role, "candidate": c, **point_scores(g[g["candidate"] == c])})
            keys = g[g["candidate"] == ENSEMBLE].dropna(subset=["y_actual"])[["origin", "unit"]]
            for c in ("naive", "drift"):
                b = baseline_err(keys, c, h)
                out["point"].append({"h": h, "role": role, "candidate": c, "n": int(len(b)),
                                     "n_origins": int(b["origin"].nunique()),
                                     "mae": float(b["err"].abs().mean()) if len(b) else None,
                                     "median_ae": float(b["err"].abs().median()) if len(b) else None,
                                     "bias": float(b["err"].mean()) if len(b) else None,
                                     "typical_factor": float(2 ** b["err"].abs().mean()) if len(b) else None})
        # served probabilities: raw or temperature-calibrated, by selection log loss; then the skill check
        sel = pace_scores(e_h[e_h["role"] == "selection"])
        method = "calibrated" if sel.get("n", 0) and sel["log_loss_calibrated"] < sel["log_loss_model"] else "raw"
        sv = pace_scores(e_h[e_h["role"] == "selection"], method)
        skill = (sv.get("n", 0) >= cfg.min_pace_cases and sv["brier_served"] < sv["brier_uniform"]
                 and sv["brier_served"] < sv["brier_climatology"])
        shrink = 0.0 if skill else cfg.pace_shrink
        out["shrink"][h] = {"method": method, "selection_skill": bool(skill), "shrink": shrink,
                            "rule": "raw or temperature-calibrated chances, whichever had the lower selection log loss; "
                                    f"then shrunk {cfg.pace_shrink:.0%} to the base rate unless their selection Brier "
                                    f"beat both a 1/3 guess and the base rate on >= {cfg.min_pace_cases} cases"}
        for role in ("selection", "holdout"):
            for c in COMPONENTS:
                d = comp[(comp["h"] == h) & (comp["candidate"] == c) & (comp["role"] == role)]
                out["pace"].append({"h": h, "role": role, "candidate": c, **pace_scores(d)})
            out["pace"].append({"h": h, "role": role, "candidate": ENSEMBLE,
                                **pace_scores(e_h[e_h["role"] == role], method, shrink)})
        scored = e_h[e_h["role"].isin(["selection", "holdout"])].dropna(subset=["y_actual"])
        sp = served_probs(scored, method, shrink)
        out["calibration"][h] = calibration(scored.assign(s_f=sp[:, 0], s_s=sp[:, 1], s_l=sp[:, 2]), ("s_f", "s_s", "s_l"))

        # non-overlapping cases (no two share an outcome month), all scored roles
        no = V.non_overlapping(scored, h)
        nb = {c: baseline_err(no[["origin", "unit"]], c, h) for c in ("naive", "drift")}
        ps = pace_scores(no, method, shrink)
        out["non_overlapping"].append({"h": h, "n": int(len(no)), "n_holdout": int((no["role"] == "holdout").sum()),
                                       "mae_ensemble": float((no["q50"] - no["y_actual"]).abs().mean()) if len(no) else None,
                                       "mae_naive": float(nb["naive"]["err"].abs().mean()) if len(nb["naive"]) else None,
                                       "mae_drift": float(nb["drift"]["err"].abs().mean()) if len(nb["drift"]) else None,
                                       **{k: ps.get(k) for k in ("brier_served", "brier_uniform", "brier_climatology")}})

        # block bootstrap over all scored cases in time order (block = h months of origins)
        o = scored.sort_values("origin")
        ae = (o["q50"] - o["y_actual"]).abs().to_numpy()
        for c in ("naive", "drift"):
            b = baseline_err(o[["origin", "unit"]], c, h).set_index(["origin", "unit"])["err"].abs()
            diff = pd.Series(ae, index=pd.MultiIndex.from_frame(o[["origin", "unit"]])) - b
            out["bootstrap"].append({"h": h, "comparison": f"ensemble minus {c}, absolute error (doublings)",
                                     **V.block_bootstrap(diff.reset_index(drop=True), h, seed=cfg.seed)})
        oh = np.column_stack([o["realised_class"] == c for c in PACES]).astype(float)
        bs_model = np.sum((served_probs(o, method, shrink) - oh) ** 2, axis=1)
        for name, ref in (("1/3 guess", np.full((len(o), 3), 1 / 3)),
                          ("base rate", o[["clim_faster", "clim_same", "clim_slower"]].to_numpy())):
            out["bootstrap"].append({"h": h, "comparison": f"pace chances minus {name}, Brier",
                                     **V.block_bootstrap(pd.Series(bs_model - np.sum((ref - oh) ** 2, axis=1)), h,
                                                         seed=cfg.seed)})
        # chance of no new record: the stage-A model if it beat the base rate in the selection period, else the base rate
        hsel = _binary_scores(rec[(rec["h"] == h) & (rec["role"] == "selection") & (rec["variant"] == "constant")])             if len(rec) else {"n": 0}
        use_model = bool(hsel.get("n", 0) >= cfg.min_pace_cases and hsel["log_loss_model"] < hsel["log_loss_base_rate"])
        out["record_choice"][h] = {"method": "model" if use_model else "base_rate", "selection": hsel,
                                   "rule": "stage-A model if its selection log loss beat the rolling base rate on >= "
                                           f"{cfg.min_pace_cases} cases, else the base rate"}
        for role in ("selection", "holdout"):
            for v in sorted(set(rec["variant"])) if len(rec) else []:
                d = rec[(rec["h"] == h) & (rec["role"] == role) & (rec["variant"] == v)]
                out["record"].append({"h": h, "role": role, "variant": v, **_binary_scores(d)})
            if len(trend):
                out["trend"].append({"h": h, "role": role,
                                     **_trend_scores(trend[(trend["h"] == h) & (trend["role"] == role)])})
    return out


# ---------------------------------------------------------------------------- generic candidates, scored like the engine
#
# The generic models (models.py) forecast one number per horizon, so they were compared with the engine on the median
# only. Here each also gets a predictive distribution, built the way the adoption targets build their ranges: its
# forecast plus each of its own earlier out-of-sample errors at the same horizon (outcome known by the origin, every
# unit). Two spreads: "as_missed" adds the errors as they were (a one-sided past shifts the range), "size_only" adds
# each error both ways (centred on the forecast, as the damped trend's noise is). A frontier never falls, so a draw
# below the current frontier is set to it. The 80% range and the faster / same / slower chances then follow the
# engine's definitions, and every method is scored on the cases all of them forecast. Backtest only: nothing here
# changes the served forecast.
SPREADS = ("as_missed", "size_only")


def generic_paths(gen: pd.DataFrame, comp: pd.DataFrame, cfg: Config = CFG) -> pd.DataFrame:
    """Per generic candidate, spread and engine case: q10-q90 (q50 = the model's own forecast) and pace chances."""
    cols = ["origin", "unit", "h", "role", "last_ord", "target_ord", "y_now", "y_actual", "hist_pace",
            "realised_class", "clim_faster", "clim_same", "clim_slower"]
    cases = comp.drop_duplicates(["origin", "unit", "h"])[cols]
    g = gen[(gen["feature_set"] == "all") & gen["candidate"].isin(list(GENERIC))][["origin", "unit", "h", "candidate", "pred"]]
    g = g.dropna(subset=["pred"]).merge(cases, on=["origin", "unit", "h"])
    g = g.assign(y_pred=np.log2(g["pred"].astype(float)) - LOG2_60)
    g["err"] = g["y_actual"] - g["y_pred"]
    rows = []
    for (c, h), d in g.groupby(["candidate", "h"]):
        known = d.dropna(subset=["err"])
        for r in d.itertuples(index=False):
            e = known.loc[known["target_ord"] <= r.last_ord, "err"].to_numpy()
            if len(e) < cfg.min_generic_errors:
                continue
            tol = max(cfg.pace_tol_abs, cfg.pace_tol_rel * abs(r.hist_pace))
            for spread, es in zip(SPREADS, (e, np.concatenate([e, -e]))):
                y = np.maximum(r.y_pred + es, r.y_now)
                fut = 12 / h * (y - r.y_now)
                faster, slower = float((fut > r.hist_pace + tol).mean()), float((fut < r.hist_pace - tol).mean())
                rows.append({**{k: getattr(r, k) for k in cols}, "candidate": c, "spread": spread, "n_errors": len(e),
                             **{f"q{int(x * 100)}": v for x, v in zip(QS, np.quantile(y, QS))}, "q50": r.y_pred,
                             "p_faster": faster, "p_same": 1 - faster - slower, "p_slower": slower})
    return pd.DataFrame(rows)


def compare_scores(gp: pd.DataFrame, comp: pd.DataFrame, ens: pd.DataFrame, sc: dict, cfg: Config = CFG) -> dict:
    """Engine components, the ensemble and the generic candidates on the cases every one of them forecast: median
    miss, 80% range (coverage, interval score) and pace chances (Brier; the ensemble's as served)."""
    allm = pd.concat([comp, ens, gp], ignore_index=True).dropna(subset=["y_actual"])
    allm["spread"] = allm["spread"].fillna("simulated") if "spread" in allm else "simulated"
    rows = []
    for h in cfg.horizons:
        d = allm[allm["h"] == h]
        per_case = d.groupby(["origin", "unit"])["candidate"].nunique()
        shared = per_case[per_case == d["candidate"].nunique()].index
        d = d[pd.MultiIndex.from_frame(d[["origin", "unit"]]).isin(shared)]
        sh = sc["shrink"][h]
        for role in ("selection", "holdout"):
            for (c, spread), gc in d[d["role"] == role].groupby(["candidate", "spread"]):
                gc = gc.dropna(axis=1, how="all")
                pt = point_scores(gc)
                ps = pace_scores(gc, sh["method"], sh["shrink"]) if c == ENSEMBLE else pace_scores(gc)
                rows.append({"h": h, "role": role, "candidate": c, "spread": spread, "generic": c in GENERIC,
                             **{k: pt.get(k) for k in ("n", "n_origins", "mae", "typical_factor", "coverage_80",
                                                       "width_80", "interval_score_80")},
                             "brier": ps.get("brier_served" if c == ENSEMBLE else "brier_model"),
                             "log_loss": ps.get("log_loss_served" if c == ENSEMBLE else "log_loss_model"),
                             "brier_uniform": ps.get("brier_uniform"), "brier_climatology": ps.get("brier_climatology")})
    return {"rows": rows,
            "rule": "generic candidates: forecast plus each of the same model's earlier out-of-sample errors at that "
                    f"horizon (outcome known by the origin, at least {cfg.min_generic_errors}), as they were "
                    "(as_missed) or each both ways (size_only), floored at the current frontier; every method scored "
                    "on the cases all of them forecast; backtest only"}


# ------------------------------------------------------------------------------------------------ final forecast

def vintage_events(data: dict) -> list[dict]:
    """What each real vintage changed in its unit: new models, a new frontier, revised values, a suite switch."""
    d = data["obs"]
    d = d[d["measure"] == CM.MEASURE]
    out, prev = [], {}
    for unit, vs in data["active"].items():
        for when, vid in vs:
            rows = CM._unit_rows(d, vid, unit)
            cur = dict(zip(rows["model"], rows["value"]))
            p = prev.get(unit)
            ev = {"vintage": vid, "available_at": when.isoformat(), "unit": unit, "n_models": len(cur)}
            if p is None:
                ev["event"] = "suite first published" if unit != "v1.0" else "first vintage"
            else:
                new = sorted(set(cur) - set(p))
                rev = [m for m in set(cur) & set(p) if abs(np.log2(cur[m] / p[m])) > 0.01]
                ev.update(new_models=new, revised=sorted(rev), removed=sorted(set(p) - set(cur)),
                          new_frontier=bool(cur) and max(cur.values()) > max(p.values()) * 1.0001)
                ev["event"] = ("new frontier result" if ev["new_frontier"] else "new measurements, no new frontier"
                               if new else "values revised" if rev else "no new measurement")
            out.append(ev)
            prev[unit] = cur
    return out


def iid_checks(ctx: dict) -> dict:
    """Are monthly frontier increments independent, and are releases Poisson? Reported, not used to switch models."""
    y = ctx["series"][np.isfinite(ctx["series"])]
    d = np.diff(y)
    ac1 = float(np.corrcoef(d[:-1], d[1:])[0, 1]) if len(d) > 3 and d[:-1].std() > 0 and d[1:].std() > 0 else None
    rel = _relevant(ctx["models"], CFG)
    m = np.floor(rel["t"]).astype(int)
    counts = np.bincount(m - m.min()) if len(m) else np.array([])
    counts = counts[-36:]
    disp = float(counts.var() / counts.mean()) if len(counts) and counts.mean() > 0 else None
    # does a record become likelier the longer there has been none? record rate by months since the last record
    rec, _ = RC.records(ctx["series"])
    since, gap, by = 0, [], {}
    for r in rec:
        if np.isfinite(r):
            gap.append((min(since, 6), r))
            since = 0 if r else since + 1
    for g, r in gap:
        by.setdefault(g, []).append(r)
    return {"increment_lag1_autocorrelation": ac1, "months_with_new_record": int((d > 1e-9).sum()),
            "months": int(len(d)), "release_dispersion_index": disp,
            "record_rate_by_months_since_last": {f"{g}{'+' if g == 6 else ''}": {"n": len(v), "rate": float(np.mean(v))}
                                                 for g, v in sorted(by.items())},
            "note": "lag-1 autocorrelation near 0 and dispersion near 1 support independent increments and random "
                    "arrivals; a record rate that does not rise with months since the last record supports a "
                    "constant hazard (no 'jump is due')"}


def to_min(y):
    return np.exp2(np.asarray(y, float) + LOG2_60)


def final(s: F.Snapshot, comp: pd.DataFrame, ens_bt: pd.DataFrame, sc: dict, members: list[str], signal: str | None,
          cfg: Config = CFG, signals: pd.DataFrame | None = None, rec: pd.DataFrame | None = None) -> dict:
    """Forecast from the latest snapshot: per unit and horizon, the ensemble's median, 80% range and pace chances,
    the chance of no new record (stage A), and the secondary trend forecast."""
    rng = np.random.default_rng(cfg.seed + 1)
    resolved = comp.dropna(subset=["y_actual"]).assign(abs_err=lambda d: (d["q50"] - d["y_actual"]).abs())
    detail = {}
    for unit in sorted(s.extras.get("models", {})):
        ctx = context(s, unit, rng, cfg.n_sims, cfg, signals)
        if ctx is None:
            continue
        ctx["hazard_signal"] = signal.removeprefix("logit_") if signal else None
        paths, notes = simulate(ctx, cfg.n_sims, rng, cfg)
        mem = {c: paths[c] for c in members if c in paths}
        try:
            p_month, _ = record_hazard(ctx, 4000, rng, ctx["hazard_signal"])
        except (ValueError, KeyError):
            p_month = None
        try:
            trend = TR.forecast(ctx["series"], cfg.horizons, cfg.n_sims, rng, cfg.pace_tol_abs, cfg.pace_tol_rel,
                                cfg.max_h, prior_sd=cfg.llt_prior_sd, prior_log_sd=cfg.llt_prior_log_sd, c=cfg.llt_robust_c, smooth_trend=True)
        except (ValueError, np.linalg.LinAlgError) as e:
            trend = {"unavailable": str(e)}
        per_h, fan = {}, None
        for h in cfg.horizons:
            w = ensemble_weights(resolved, h, mem, cfg, members)
            ens, _ = mixture(mem, w, cfg.n_sims)
            if h == max(cfg.horizons):
                fan = ens
            q = np.quantile(ens[:, h - 1], QS)
            p_raw = pace_probs(ens, ctx["y0"], ctx["hist"], h, cfg)
            prev = ens_bt[(ens_bt["h"] == h)].dropna(subset=["realised_class"])
            clim = base_rate(prev["realised_class"].tolist())
            rule = sc["shrink"][h]
            T = 1.0
            if rule["method"] == "calibrated" and len(prev) >= cfg.min_calib_cases:
                oh = np.column_stack([prev["realised_class"] == c for c in PACES]).astype(float)
                T = V.fit_temperature(prev[["p_faster", "p_same", "p_slower"]].to_numpy(), oh, cfg.calib_prior_sd)
            p_cal = V.apply_temperature(p_raw[None, :], T)[0] if T != 1.0 else p_raw
            p = (1 - rule["shrink"]) * p_cal + rule["shrink"] * clim
            fut = 12 / h * (ens[:, h - 1] - ctx["y0"])
            p_none_model = float(np.mean((1 - p_month) ** h)) if p_month is not None else None
            done = rec[(rec["h"] == h) & (rec["variant"] == "constant")]["record"].dropna() if rec is not None and len(rec) else pd.Series(dtype=float)
            p_none_base = float((len(done) - done.sum() + 1) / (len(done) + 2))  # Laplace: share of windows without a record
            how = sc["record_choice"][h]["method"]
            per_h_none = {"p_no_record": p_none_model if how == "model" and p_none_model is not None else p_none_base,
                          "p_no_record_model": p_none_model, "p_no_record_base_rate": p_none_base,
                          "no_record_method": how, "no_record_n": int(len(done))}
            per_h[h] = {**per_h_none, "q": q, "p": p, "p_raw": p_raw, "p_calibrated": p_cal, "temperature": T, "clim": clim,
                        "shrink": rule["shrink"], "method": rule["method"], "weights": w, "fut_pace": fut,
                        "components": {c: {"q50": float(np.quantile(paths[c][:, h - 1], 0.5)),
                                           "q10": float(np.quantile(paths[c][:, h - 1], 0.1)),
                                           "q90": float(np.quantile(paths[c][:, h - 1], 0.9)),
                                           "in_ensemble": c in mem,
                                           "p": pace_probs(paths[c], ctx["y0"], ctx["hist"], h, cfg).tolist()}
                                       for c in paths}}
        detail[unit] = {"ctx": ctx, "paths": paths, "notes": notes, "per_h": per_h, "fan": fan, "trend": trend}
    return detail


def page_data(spec, s: F.Snapshot, data: dict, detail: dict, sc: dict, comp: pd.DataFrame, decisions: dict,
              cfg: Config = CFG) -> dict:
    """engine.json: chart series, per-horizon detail, the secondary trend, diagnostics. Read by the API."""
    off = capability.metr_official()
    units = {}
    for unit, d in detail.items():
        ctx = d["ctx"]
        obs, bri, fr = ctx["obs"], ctx["bridged"], ctx["frontier"]
        rel = set(_relevant(ctx["models"], cfg)["model"])
        pt = lambda r, layer: {"model": r["model"], "release_date": str(pd.Timestamp(r["release_date"]).date()),  # noqa: E731
                               "minutes": float(to_min(r["y"])), "low": float(to_min(r["y"] - cfg.ci_z * r["s_lo"])),
                               "high": float(to_min(r["y"] + cfg.ci_z * r["s_hi"])), "layer": layer,
                               "saturated": bool(r["saturated"]), "frontier_relevant": r["model"] in rel}
        fan = d["fan"]
        months = [s.last + k for k in range(1, cfg.max_h + 1)]
        hist = ctx["hist"]
        released = obs.assign(m=pd.to_datetime(obs["release_date"]).dt.to_period("M"))["m"].value_counts()
        events = RC.month_events(fr["y"].to_numpy(), fr["period"].map(released).fillna(0).to_numpy())
        horizons = []
        for h, x in d["per_h"].items():
            tol = max(cfg.pace_tol_abs, cfg.pace_tol_rel * abs(ctx["hist_point"]))
            edges = np.linspace(np.quantile(x["fut_pace"], 0.01), np.quantile(x["fut_pace"], 0.99), 41)
            cnt, _ = np.histogram(np.clip(x["fut_pace"], edges[0], edges[-1]), edges)
            horizons.append({
                "h": h, "target_period": str(s.last + h), "median_minutes": float(to_min(x["q"][2])),
                "q_minutes": {f"q{int(a * 100)}": float(to_min(v)) for a, v in zip(QS, x["q"])},
                "p": dict(zip(PACES, map(float, x["p"]))), "p_simulated": dict(zip(PACES, map(float, x["p_raw"]))),
                "p_calibrated": dict(zip(PACES, map(float, x["p_calibrated"]))), "temperature": x["temperature"],
                "probability_method": x["method"], "base_rate": dict(zip(PACES, map(float, x["clim"]))),
                "shrink": x["shrink"], "prior_assisted": x["shrink"] > 0, "weights": x["weights"],
                "hist_pace": ctx["hist_point"], "hist_pace_q10_q90": [float(np.quantile(hist, 0.1)), float(np.quantile(hist, 0.9))],
                "tolerance": tol, "same_band": [ctx["hist_point"] - tol, ctx["hist_point"] + tol],
                "future_pace_median": float(np.median(x["fut_pace"])),
                "future_pace_q10_q90": [float(np.quantile(x["fut_pace"], 0.1)), float(np.quantile(x["fut_pace"], 0.9))],
                "pace_histogram": {"edges": edges.tolist(), "counts": cnt.tolist()},
                "components": x["components"], "p_no_new_record": x["p_no_record"],
                "p_no_new_record_model": x["p_no_record_model"], "p_no_new_record_base_rate": x["p_no_record_base_rate"],
                "no_record_method": x["no_record_method"], "no_record_n": x["no_record_n"]})
        tr = d["trend"]
        trend = None
        if "unavailable" not in tr:
            lvl, sd = np.array(tr["history"]["level"]), np.array(tr["history"]["level_sd"])
            fm, fs = np.array(tr["level_forecast"]["mean"]), np.array(tr["level_forecast"]["sd"])
            z = 1.2816  # 80% normal interval
            trend = {
                "history": [{"period": str(p), "minutes": None if np.isnan(a) else float(to_min(a)),
                             "low": None if np.isnan(a) else float(to_min(a - z * b)),
                             "high": None if np.isnan(a) else float(to_min(a + z * b)),
                             "pace_per_year": None if np.isnan(g) else float(g)}
                            for p, a, b, g in zip(fr["period"], lvl, sd, tr["history"]["slope_per_year"])],
                "forecast": [{"period": str(m), "minutes": float(to_min(a)), "low": float(to_min(a - z * b)),
                              "high": float(to_min(a + z * b))} for m, a, b in zip(months, fm, fs)],
                "past_pace": tr["past_pace"], "past_pace_sd": tr["past_pace_sd"],
                "pace_now": tr["slope_now"], "pace_now_sd": tr["slope_now_sd"],
                "doubling_months": 12 / tr["slope_now"] if tr["slope_now"] > 0 else None,
                "horizons": [{"h": h, "p": dict(zip(TR.CLASSES, map(float, v["p"]))),
                              "future_pace_q10_q50_q90": v["future_pace_q"]} for h, v in tr["horizons"].items()],
                "variances": tr["var"]}
        br = ctx["bridge"]
        units[unit] = {
            "observed": [pt(r, "observed") for _, r in obs.iterrows()],
            "bridged": [pt(r, "bridged") for _, r in bri.iterrows()],
            "frontier": [{"period": str(r["period"]), "minutes": None if np.isnan(r["y"]) else float(to_min(r["y"])),
                          "model": r["model"], "event": ev} for (_, r), ev in zip(fr.iterrows(), events)],
            "fan": [{"period": str(m), **{f"q{int(a * 100)}": float(to_min(np.quantile(fan[:, k], a))) for a in QS}}
                    for k, m in enumerate(months)],
            "last_period": str(s.last), "current_minutes": float(to_min(ctx["y_now"])), "current_model": ctx["now_model"],
            "current_saturated": bool(ctx["y_now"] > np.log2(cfg.saturation_hours)),
            "pace_basis": ctx["pace_basis"], "horizons": horizons, "components": d["notes"], "trend": trend,
            "bridge": {k: v for k, v in br.items() if k != "boot"}, "iid_checks": iid_checks(ctx),
            "n_observed": len(obs), "n_bridged": len(bri)}
    clean = lambda rows: pd.DataFrame(rows).replace({np.nan: None}).to_dict("records")  # noqa: E731
    return {
        "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(cfg).items()},
        "units": units,
        "decisions": decisions,
        "backtest": {"point": clean(sc["point"]), "pace": clean(sc["pace"]), "calibration": sc["calibration"],
                     "shrink": sc["shrink"], "record_choice": sc["record_choice"],
                     "non_overlapping": clean(sc["non_overlapping"]),
                     "bootstrap": sc["bootstrap"], "record": clean(sc["record"]), "trend": clean(sc["trend"]),
                     "compare": {**sc["compare"], "rows": clean(sc["compare"]["rows"])} if "compare" in sc else None,
                     "n_origins": int(comp["origin"].nunique()),
                     "origins_by_kind": comp.drop_duplicates("origin")["vintage_kind"].value_counts().to_dict(),
                     "brier_definition": "sum over classes of (probability - outcome)^2, averaged: 0 perfect, 2 worst; "
                                         "a 1/3 guess scores 0.67 for three classes; 0.5 for a yes/no 50/50 guess",
                     "note": "Most origins are reconstructed (later measurements of models released by then), so "
                             "scores are approximate; real point-in-time origins exist only from Jun 2025. "
                             "Neighbouring forecasts overlap in time: see the non-overlapping and bootstrap results."},
        "data": {"source": "METR time horizons (Time Horizon 1.1 current; 1.0 legacy), as published in Epoch AI's "
                           "benchmark data (monthly Wayback captures = point-in-time vintages)",
                 "metr_official_file": off["file"] if off else None,
                 "metr_official_check": official_check(off, detail),
                 "metr_published_doubling_days": (off or {}).get("meta", {}).get("doubling_time_in_days"),
                 "vintage": s.vintage, "data_as_of": s.origin.isoformat(), "latest_complete_month": str(s.last),
                 "measurement_lag_months": CM.MEASUREMENT_LAG_MONTHS, "vintage_events": vintage_events(data)[-8:]},
        "limitations": [
            "Measures software-task completion under METR's benchmark conditions, not general intelligence or capability in every domain.",
            "Few real point-in-time vintages: most backtest origins are reconstructed, so scores are approximate.",
            "Neighbouring test forecasts overlap in time; the non-overlapping subset is small, so differences can be luck.",
            "Only evaluated models are seen: labs and models METR has not measured are missing (selection bias).",
            f"Horizons above {cfg.saturation_hours:g} hours are near the top of METR's task suite: their CIs are wide and they are left out of trend fits.",
            "The v1.0 to v1.1 bridge rests on a handful of models measured under both suites, and is not used before v1.1 was published.",
            "The underlying trend is model-estimated, not observed; it is scored against the same smoother run on later data.",
            "External signals (Epoch AI models data) exist only as today's file, so their tests are approximately point-in-time.",
        ],
    }


def official_check(off: dict | None, detail: dict) -> dict | None:
    """Do Epoch's v1.1 values match METR's own file? Max relative difference over models matched by value."""
    if not off or "v1.1" not in detail:
        return None
    ours = to_min(detail["v1.1"]["ctx"]["obs"]["y"].to_numpy())
    theirs = off["models"]["value"].to_numpy(float)
    rel = [float(np.min(np.abs(theirs / v - 1))) for v in ours]
    return {"models_compared": len(rel), "max_relative_difference": max(rel) if rel else None,
            "matched_within_1pct": int(sum(r < 0.01 for r in rel))}


# ----------------------------------------------------------------------------------------- pipeline integration

def load_signals() -> tuple[pd.DataFrame | None, dict]:
    """External monthly features and an inventory of what was looked at (absent file -> no features)."""
    got = SG.load_models()
    info = {"benchmarks": SG.benchmark_coverage(), "models_file": got[1] if got else None,
            "features": list(SG.FEATURES) if got else []}
    if not got:
        return None, info
    return SG.monthly_features(got[0], pd.Period("2019-01", freq="M"), pd.Period.now("M")), info


def run(spec, data: dict, snaps: list[F.Snapshot], y_true: pd.Series, split, gen_bt: pd.DataFrame,
        gen_sel: pd.DataFrame, health: dict, run_id: str, made_at: str, run_dir: Path, cfg: Config = CFG):
    """TargetSpec.engine for frontier_time_horizon -> (backtest rows to save, selection table, forecast rows,
    extra evaluation). The ensemble is the predeclared forecast; the generic candidates are kept for comparison."""
    signals, sig_info = load_signals()
    comp, store, rec, trend = pass_one(spec, snaps, y_true, split, cfg, signals)
    inc = inclusion(comp, cfg)
    members = [c for c in COMPONENTS if inc[c]["included"]]
    sig = signal_decision(rec, cfg)
    kept = [v for v, x in sig.items() if x["kept"]]
    signal = min(kept, key=lambda v: sig[v]["log_loss_change"]) if kept else None
    ens = pass_two(comp, store, snaps, members, cfg)
    del store
    sc = scores(comp, ens, gen_bt, rec, trend, cfg)
    sc["compare"] = compare_scores(generic_paths(gen_bt, comp, cfg), comp, ens, sc, cfg)
    decisions = {"components": inc, "members": members, "external_signals": sig, "hazard": signal or "constant",
                 "external_inventory": sig_info}
    detail = final(snaps[-1], comp, ens, sc, members, signal, cfg, signals, rec)
    page = page_data(spec, snaps[-1], data, detail, sc, comp, decisions, cfg)
    (run_dir / "engine.json").write_text(json.dumps(page, indent=1, default=_json_default))

    # backtest rows in the generic layout (log2 minutes; pred = median), so /accuracy lists them too
    bt = pd.concat([comp, ens], ignore_index=True)
    g = bt.assign(feature_set="all", segment=bt["unit"], lvl=bt["y_now"] + LOG2_60,
                  last_value=to_min(bt["y_now"]), pred=to_min(bt["q50"]), actual=to_min(bt["y_actual"]),
                  pred_change=bt["q50"] - bt["y_now"], trend=bt["hist_pace"], n_train=bt["n_models"],
                  error=bt["q50"] - bt["y_actual"], resid=bt["y_actual"] - bt["q50"])
    all_bt = pd.concat([gen_bt, g[[c for c in gen_bt.columns if c in g.columns]]], ignore_index=True)

    sel = _selection(gen_sel, sc, spec, cfg)
    rows = forecast_rows(spec, snaps[-1], detail, sel, sc, health, run_id, made_at, cfg)
    regime = [{"h": h, "candidate": ENSEMBLE, **next(p for p in sc["pace"] if p["h"] == h and p["role"] == "holdout"
                                                  and p["candidate"] == ENSEMBLE)} for h in cfg.horizons]
    for r in regime:  # the page's reliability line compares the probabilities actually served
        if r.get("n"):
            r["brier_model"] = r["brier_served"]
            r["holdout_regime_counts"] = {REGIME_OF[k]: v for k, v in r["class_counts"].items()}
    extra = {"regime_scores": regime, "engine": {"backtest": page["backtest"], "config": page["config"],
                                                 "decisions": decisions,
                                                 "data": {k: v for k, v in page["data"].items() if k != "vintage_events"}}}
    return all_bt, sel, rows, extra


def _selection(gen_sel: pd.DataFrame, sc: dict, spec, cfg: Config) -> pd.DataFrame:
    """The generic selection table (kept, none chosen) plus the engine's candidates; the ensemble is 'chosen' by
    design, not by contest. Same columns, so run.decision / acceptance / promote work unchanged."""
    pts = pd.DataFrame(sc["point"])
    out = gen_sel.assign(chosen=False)
    rows = []
    for h in cfg.horizons:
        for c in [*COMPONENTS, ENSEMBLE]:
            s = pts[(pts["h"] == h) & (pts["role"] == "selection") & (pts["candidate"] == c)].iloc[0]
            o = pts[(pts["h"] == h) & (pts["role"] == "holdout") & (pts["candidate"] == c)].iloc[0]
            rows.append({"h": h, "candidate": c, "is_baseline": c == "damped_trend", "chosen": c == ENSEMBLE,
                         "selection_mae": s.get("mae"), "selection_rmse": s.get("rmse"),
                         "selection_n_origins": s.get("n_origins"), "holdout_mae": o.get("mae"),
                         "holdout_rmse": o.get("rmse"), "holdout_bias": o.get("bias"),
                         "holdout_n_origins": o.get("n_origins"), "holdout_n": o.get("n"),
                         "insufficient_history": (s.get("n_origins") or 0) < spec.min_selection_origins})
    t = pd.concat([out, pd.DataFrame(rows)], ignore_index=True)
    # vs naive / drift on the ensemble's own cases (the generic ones cover slightly different unit sets)
    for h in cfg.horizons:
        for role, col in (("selection", "selection_mase_vs_naive"), ("holdout", "holdout_mase_vs_naive"),
                          ("holdout", "holdout_mase_vs_drift")):
            ref = "drift" if col.endswith("drift") else "naive"
            b = pts[(pts["h"] == h) & (pts["role"] == role) & (pts["candidate"] == ref)]["mae"]
            b = float(b.iloc[0]) if len(b) and b.iloc[0] else np.nan
            m = (t["h"] == h) & t["candidate"].isin([*COMPONENTS, ENSEMBLE])
            t.loc[m, col] = t.loc[m, f"{role}_mae"].astype(float) / b
    return t


def forecast_rows(spec, s: F.Snapshot, detail: dict, sel: pd.DataFrame, sc: dict, health: dict, run_id: str,
                  made_at: str, cfg: Config) -> pd.DataFrame:
    from . import contracts, run as R  # run imports the targets; imported here to avoid a cycle

    label = contracts.TARGETS[spec.id].label_source
    out = []
    for unit, d in detail.items():
        ctx = d["ctx"]
        for h, x in d["per_h"].items():
            chosen, served, status = R.decision(sel, h)
            warnings = [w for w in (spec.history_warning,) if w]
            if health[label]["status"] != "fresh":
                warnings.append("stale target data")
            if s.kind != "real":
                warnings.append(f"point-in-time basis: {s.kind}")
            if x["shrink"] > 0:
                warnings.append(f"pace chances prior-assisted: the simulated chances did not beat a 1/3 guess and the "
                                f"base rate in the selection period, so {x['shrink']:.0%} of them is the base rate")
            if ctx["pace_basis"] != "observed_12m":
                warnings.append(f"historical pace basis: {ctx['pace_basis']}")
            if ctx["y_now"] > np.log2(cfg.saturation_hours):
                warnings.append(f"current frontier is above {cfg.saturation_hours:g} h, near the top of the task suite: "
                                "its measurement is wide")
            q, p = x["q"], x["p"]
            if status == "baseline_retained":
                warnings.append("chosen model ensemble lost to naive on the holdout; baseline served")
                q, p = np.full(5, ctx["y_now"]), np.full(3, np.nan)
            tol = max(cfg.pace_tol_abs, cfg.pace_tol_rel * abs(ctx["hist_point"]))
            row = {"run_id": run_id, "made_at": made_at, "target": spec.id, "unit_kind": spec.unit_kind,
                   "unit": unit, "segment": unit, "last_observed_period": str(s.last),
                   "last_observed": float(to_min(ctx["y_now"])), "h": h, "period_unit": spec.period_unit,
                   "target_period": str(s.last + h), "value_unit": spec.value_unit, "model": served["candidate"],
                   "chosen_model": chosen["candidate"], "forecast": float(to_min(q[2])),
                   "low": float(to_min(q[0])), "high": float(to_min(q[4])),
                   "interval": f"80% predictive interval ({cfg.n_sims:,} simulated trajectories, mixture ensemble)",
                   "status": status, "holdout_mae": chosen["holdout_mae"],
                   "naive_holdout_mae": float(chosen["holdout_mae"] / chosen["holdout_mase_vs_naive"])
                   if chosen["holdout_mase_vs_naive"] else None,
                   "vintage": s.vintage, "data_as_of": s.origin.isoformat(), "warnings": R.WARNING_SEP.join(warnings),
                   "p_acceleration": p[0], "p_stable": p[1], "p_slowdown": p[2],
                   "regime_rule": (f"pace over next {h} months vs past 12 months (doublings/year); same = within "
                                   f"max({cfg.pace_tol_abs} /yr, {cfg.pace_tol_rel:.0%}); shares of {cfg.n_sims:,} "
                                   f"simulated trajectories ({x['method']})"),
                   "regime_past_change": ctx["hist_point"] * h / 12,
                   "regime_band_low": (ctx["hist_point"] - tol) * h / 12,
                   "regime_band_high": (ctx["hist_point"] + tol) * h / 12,
                   "regime_pred_change": float(q[2] - ctx["y_now"]), "regime_n_residuals": cfg.n_sims,
                   "pace_basis": ctx["pace_basis"], "pace_prior_assisted": x["shrink"] > 0,
                   "p_no_new_record": x["p_no_record"]}
            out.append(row)
    return pd.DataFrame(out)


def _json_default(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp, pd.Period)):
        return str(v)
    return str(v)
