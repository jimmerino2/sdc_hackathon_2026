"""Evaluation helpers for the capability engine: probability scores, temperature calibration, non-overlapping test
cases and a block bootstrap for score differences.

Brier score (used everywhere in the capability engine and on the page): for K outcome classes,
    BS = sum_k (p_k - o_k)^2   (o_k = 1 for the class that happened), averaged over cases.
0 is perfect and 2 the worst; a uniform 1/3 guess over three classes scores 2/3 whatever happens. For a yes/no
event (no new record) the same formula with K = 2 is used, so a 50/50 guess scores 0.5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-3


def brier(p: np.ndarray, onehot: np.ndarray) -> float:
    return float(np.mean(np.sum((p - onehot) ** 2, axis=1)))


def log_loss(p: np.ndarray, onehot: np.ndarray) -> float:
    return float(np.mean(-np.log(np.clip(np.sum(p * onehot, axis=1), EPS, 1))))


def binary(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    return np.column_stack([p, 1 - p])


def apply_temperature(p: np.ndarray, T: float) -> np.ndarray:
    """p^(1/T), renormalised. T > 1 softens towards 1/K, T < 1 sharpens; zero probabilities are floored at EPS."""
    q = np.clip(p, EPS, 1) ** (1 / T)
    return q / q.sum(axis=1, keepdims=True)


TEMPS = np.exp(np.linspace(-1.5, 1.5, 61))


def fit_temperature(p: np.ndarray, onehot: np.ndarray, prior_sd: float = 0.5) -> float:
    """MAP temperature on earlier forecasts only: log loss plus a Normal(0, prior_sd) prior on log T, so a few
    cases cannot push the probabilities to extremes."""
    if len(p) == 0:
        return 1.0
    obj = [len(p) * log_loss(apply_temperature(p, t), onehot) + 0.5 * (np.log(t) / prior_sd) ** 2 for t in TEMPS]
    return float(TEMPS[int(np.argmin(obj))])


def non_overlapping(d: pd.DataFrame, h: int) -> pd.DataFrame:
    """Per unit, keep origins whose observed month is at least h months after the previously kept one (earliest
    first), so no two kept forecasts share an outcome month."""
    keep = []
    for _, g in d.sort_values("last_period").groupby("unit"):
        last = None
        for i, p in zip(g.index, g["last_period"]):
            m = pd.Period(p, freq="M")
            if last is None or (m - last).n >= h:
                keep.append(i)
                last = m
    return d.loc[keep]


def block_bootstrap(diff: pd.Series, block: int, n_boot: int = 2000, seed: int = 0) -> dict:
    """Moving-block bootstrap of the mean of `diff` (ordered in time): its 80% and 95% intervals and the share of
    resamples below 0. Blocks of `block` consecutive cases keep neighbouring (overlapping) forecasts together."""
    x = diff.dropna().to_numpy(float)
    n = len(x)
    if n < 4:
        return {"n": n, "mean": float(x.mean()) if n else None}
    b = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    starts = np.arange(n - b + 1)
    k = int(np.ceil(n / b))
    means = np.array([np.concatenate([x[s:s + b] for s in rng.choice(starts, k)])[:n].mean() for _ in range(n_boot)])
    return {"n": n, "block": b, "mean": float(x.mean()), "ci80": np.quantile(means, [0.1, 0.9]).tolist(),
            "ci95": np.quantile(means, [0.025, 0.975]).tolist(), "share_below_0": float((means < 0).mean())}
