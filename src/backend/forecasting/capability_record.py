"""Two-stage model of the observed frontier: will a new record appear (stage A), and if so how big is it (stage B).

Works on one unit's monthly measured frontier y (log2 hours, NaN = no recent measured model), as seen at one origin.
A record month is one where the frontier rises. Nothing here lets the chance of a record grow with the time since the
last one: the default hazard is constant (the capability engine reports the evidence for that).

Stage A  P(record in a month) = p, constant. Beta posterior from the last `window` months, with a prior centred on
         the unit's whole-history rate and worth `prior_months` months. Variant for testing external signals:
         logistic hazard logit p_m = a + b * z_(m-1) (the signal known at the start of the month), MAP with Gaussian
         priors and a Laplace approximation; future months keep the last known signal.
Stage B  log(jump size in doublings) ~ Normal(mu, sigma^2), Normal-Inverse-Gamma posterior with a conservative
         prior (median jump 0.7 doublings, wide spread), so a few jumps cannot pin the tail down and very large
         jumps stay possible (log-normal tail).
Combined trajectories: per trajectory one (p, mu, sigma) draw; per month a Bernoulli record of a log-normal size.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit, logit


@dataclass(frozen=True)
class RecordConfig:
    window: int = 24  # months of record history behind the hazard
    prior_months: float = 12.0
    min_months: int = 6  # fewer usable months -> no record model at this origin
    jump_mu0: float = float(np.log(0.7))  # prior median jump: 0.7 doublings
    jump_kappa0: float = 2.0  # prior worth 2 jumps for the location ...
    jump_alpha0: float = 3.0  # ... and the spread (prior sd of log jump about 0.8)
    jump_sd0: float = 0.8
    logit_prior_sd_a: float = 1.5
    logit_prior_sd_b: float = 0.5  # on a standardised signal: a one-sd change moves the odds by at most ~e^1 a priori


RCFG = RecordConfig()


def records(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(record indicator per usable month, jump sizes). A usable month has a frontier this month and last month,
    within the latest unbroken stretch of measured frontier: before a gap, METR measured too few models to say
    whether a record could have happened (e.g. the year after GPT-2 is 'no measurement', not 'no record')."""
    fin = np.isfinite(y)
    start = 0
    for i in range(len(y) - 1, -1, -1):
        if not fin[i]:
            start = i + 1
            break
    y = np.where(np.arange(len(y)) >= start, y, np.nan)
    prev, cur = y[:-1], y[1:]
    ok = np.isfinite(prev) & np.isfinite(cur)
    up = np.where(ok, cur - prev, np.nan)
    rec = (up > 1e-9).astype(float)
    rec[~ok] = np.nan
    return rec, up[(up > 1e-9) & ok]


def month_events(y: np.ndarray, released_measured: np.ndarray) -> list[str]:
    """Per month: 'new record' | 'measured release, no record' | 'no measured release' | 'no recent measurement'.
    `released_measured`: count of measured models released in each month (same length as y)."""
    out = []
    for i in range(len(y)):
        if not np.isfinite(y[i]):
            out.append("no recent measurement")
        elif i > 0 and np.isfinite(y[i - 1]) and y[i] > y[i - 1] + 1e-9:
            out.append("new record")
        elif released_measured[i] > 0:
            out.append("measured release, no record")
        else:
            out.append("no measured release")
    return out


def hazard_beta(rec: np.ndarray, cfg: RecordConfig = RCFG) -> tuple[float, float]:
    """Beta(shape a, shape b) posterior of the monthly record chance."""
    r = rec[np.isfinite(rec)]
    if len(r) < cfg.min_months:
        raise ValueError(f"fewer than {cfg.min_months} months with a measured frontier")
    base = (r.sum() + 0.5) / (len(r) + 1)
    w = r[-cfg.window:]
    return cfg.prior_months * base + w.sum(), cfg.prior_months * (1 - base) + len(w) - w.sum()


def hazard_logit(rec: np.ndarray, z: np.ndarray | None, cfg: RecordConfig = RCFG) -> dict:
    """MAP logistic hazard on the usable months; z = signal at the start of each month (None = intercept only).
    Returns mean, covariance (Laplace) and the standardisation used, for drawing and for predicting."""
    ok = np.isfinite(rec) & (np.isfinite(z) if z is not None else True)
    r = rec[ok]
    if len(r) < cfg.min_months:
        raise ValueError(f"fewer than {cfg.min_months} months with a measured frontier and signal")
    if z is not None:
        mu, sd = float(np.mean(z[ok])), float(np.std(z[ok])) or 1.0
        X = np.column_stack([np.ones(len(r)), (z[ok] - mu) / sd])
    else:
        mu, sd = 0.0, 1.0
        X = np.ones((len(r), 1))
    m0 = np.zeros(X.shape[1])
    m0[0] = logit(np.clip((r.sum() + 0.5) / (len(r) + 1), 0.02, 0.98))
    prec0 = np.diag([1 / cfg.logit_prior_sd_a ** 2] + [1 / cfg.logit_prior_sd_b ** 2] * (X.shape[1] - 1))
    beta = m0.copy()
    for _ in range(50):  # Newton on the log posterior
        p = expit(X @ beta)
        g = X.T @ (r - p) - prec0 @ (beta - m0)
        H = X.T @ (X * (p * (1 - p))[:, None]) + prec0
        step = np.linalg.solve(H, g)
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    p = expit(X @ beta)
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + prec0)
    return {"beta": beta, "cov": cov, "mu": mu, "sd": sd}


def logit_p(fit: dict, z_now: float | None) -> float:
    x = np.array([1.0] + ([(z_now - fit["mu"]) / fit["sd"]] if len(fit["beta"]) > 1 else []))
    return float(expit(x @ fit["beta"]))


def p_record_within(p: np.ndarray | float, h: int) -> np.ndarray:
    return 1 - (1 - np.asarray(p, float)) ** h


def jump_posterior(jumps: np.ndarray, cfg: RecordConfig = RCFG) -> dict:
    """Normal-Inverse-Gamma posterior of log jump sizes (conjugate update of the conservative prior)."""
    x = np.log(jumps[jumps > 0])
    n = len(x)
    xbar = float(x.mean()) if n else cfg.jump_mu0
    ss = float(((x - xbar) ** 2).sum()) if n else 0.0
    kn = cfg.jump_kappa0 + n
    mun = (cfg.jump_kappa0 * cfg.jump_mu0 + n * xbar) / kn
    an = cfg.jump_alpha0 + n / 2
    b0 = cfg.jump_alpha0 * cfg.jump_sd0 ** 2
    bn = b0 + 0.5 * ss + cfg.jump_kappa0 * n * (xbar - cfg.jump_mu0) ** 2 / (2 * kn)
    return {"mu": mun, "kappa": kn, "alpha": an, "beta": bn, "n_jumps": n}


def draw_jump_params(post: dict, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    var = post["beta"] / rng.gamma(post["alpha"], 1.0, n)
    mu = rng.normal(post["mu"], np.sqrt(var / post["kappa"]))
    return mu, np.sqrt(var)


def simulate(y0: np.ndarray, p: np.ndarray, post: dict, max_h: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Trajectories (n x max_h, log2 hours) and record counts per month: a record each month with chance p (per
    trajectory), of log-normal size."""
    n = len(y0)
    mu, sd = draw_jump_params(post, n, rng)
    hit = rng.random((n, max_h)) < p[:, None]
    size = np.exp(mu[:, None] + sd[:, None] * rng.standard_normal((n, max_h)))
    return y0[:, None] + np.cumsum(np.where(hit, size, 0.0), axis=1), hit
