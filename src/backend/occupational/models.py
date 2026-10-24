"""Skill-share forecasting methods. Target: the share of an occupation's eligible ads in a country that name a skill,
pooled over the 3 months ending h months after the origin (pooling 3 months cuts sampling noise; one month of a
small occupation can hold a handful of ads).

Every method sees only months <= origin. Arrays are [series, month]; a series is country x occupation x skill.
  persistence   the last 3 months' share (the "no change" baseline)
  mean12        the last 12 months' share
  shrink        last 3 months shrunk toward the last 12 by evidence: w = n3 / (n3 + KAPPA)
  trend         12-month share moved along the damped slope of logit share over the last 8 quarters (weighted)
  ridge         one pooled ridge regression per horizon over all series: predicts the change in logit share from
                the 12-month level, using recent deviation, yearly change, 2-year change, level, volume,
                volume growth, the skill's change across all cells, and the occupation. Refit as origins advance,
                on rows whose target was already observed at that origin.
  blend         the average of shrink and ridge. Added after the first run's validation AND test scores had been
                seen, so its test score is not untouched (evaluation.json lists it under post_hoc_methods).
Hyperparameters (KAPPA, DAMP, RIDGE_ALPHA) are fixed in advance, not tuned on the test period.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

WINDOW = 3
KAPPA = 30.0
DAMP = 0.6
RIDGE_ALPHA = 10.0
METHODS = ("persistence", "mean12", "shrink", "trend", "ridge", "blend")
POST_HOC = ("blend",)
EPS = 1e-4


def wsum(x: np.ndarray, w: int) -> np.ndarray:
    """Sum over the w months ending at each month (NaN where fewer than w months exist)."""
    c = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, axis=1)], axis=1)
    out = np.full(x.shape, np.nan)
    out[:, w - 1:] = c[:, w:] - c[:, :-w]
    return out


def shift(x: np.ndarray, k: int) -> np.ndarray:
    out = np.full(x.shape, np.nan)
    if k < x.shape[1]:
        out[:, k:] = x[:, :x.shape[1] - k]
    return out


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def expit(z):
    return 1 / (1 + np.exp(-z))


def features(K: np.ndarray, N: np.ndarray, skill_idx: np.ndarray, occ_idx: np.ndarray, n_occ: int) -> dict:
    """All features at every month (as an origin). K, N: [series, month] counts and denominators."""
    k3, n3 = wsum(K, 3), wsum(N, 3)
    k12, n12 = wsum(K, 12), wsum(N, 12)
    k24, n24 = wsum(K, 24), wsum(N, 24)
    k12l, n12l = shift(k12, 12), shift(n12, 12)
    sm = lambda k, n: (k + 0.5) / (n + 1)
    p3, p12, p24, p12l = sm(k3, n3), sm(k12, n12), sm(k24, n24), sm(k12l, n12l)
    f = {"k3": k3, "n3": n3, "k12": k12, "n12": n12, "p3s": p3, "p12s": p12,
         "p3": np.where(n3 > 0, k3 / np.maximum(n3, 1), np.nan),
         "p12": np.where(n12 > 0, k12 / np.maximum(n12, 1), np.nan),
         "x_dev": logit(p3) - logit(p12), "x_yoy": logit(p12) - logit(p12l), "x_2y": logit(p12) - logit(p24),
         "x_lvl": logit(p12), "x_vol": np.log1p(n12), "x_volg": np.log1p(n12) - np.log1p(n12l)}
    # the skill's yearly change across every cell (weighted by volume): a shared signal, still only past data
    w = np.nan_to_num(n12)
    yoy = np.nan_to_num(f["x_yoy"])
    num, den = np.zeros((skill_idx.max() + 1, K.shape[1])), np.zeros((skill_idx.max() + 1, K.shape[1]))
    np.add.at(num, skill_idx, yoy * w)
    np.add.at(den, skill_idx, w)
    f["x_skill_yoy"] = (num / np.maximum(den, 1))[skill_idx]
    # trend: weighted slope of logit share over the last 8 quarterly windows
    q = [(shift(k3, 3 * j), shift(n3, 3 * j)) for j in range(8)]
    xs = np.arange(0, -8, -1, dtype=float)  # quarters back
    ys = np.stack([logit(sm(kq, nq)) for kq, nq in q])
    ws = np.stack([np.nan_to_num(nq) for _, nq in q])
    sw = ws.sum(0)
    xm = (ws * xs[:, None, None]).sum(0) / np.maximum(sw, 1e-9)
    ym = (ws * np.nan_to_num(ys)).sum(0) / np.maximum(sw, 1e-9)
    sxy = (ws * (xs[:, None, None] - xm) * (np.nan_to_num(ys) - ym)).sum(0)
    sxx = (ws * (xs[:, None, None] - xm) ** 2).sum(0)
    f["slope_q"] = np.where(sxx > 0, sxy / np.maximum(sxx, 1e-9), 0.0)
    f["occ"] = occ_idx
    f["n_occ"] = n_occ
    return f


RIDGE_X = ("x_dev", "x_yoy", "x_2y", "x_lvl", "x_vol", "x_volg", "x_skill_yoy")


def design(f: dict, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    X = np.column_stack([np.nan_to_num(f[c][rows, cols]) for c in RIDGE_X])
    occ = np.zeros((len(rows), f["n_occ"]))
    occ[np.arange(len(rows)), f["occ"][rows]] = 1
    return np.hstack([X, occ])


class RidgeModel:
    def __init__(self):
        self.scaler, self.model, self.n_train = None, None, 0

    def fit(self, X: np.ndarray, y: np.ndarray, w: np.ndarray) -> "RidgeModel":
        self.scaler = StandardScaler().fit(X)
        self.model = Ridge(alpha=RIDGE_ALPHA).fit(self.scaler.transform(X), y, sample_weight=w)
        self.n_train = len(y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(self.scaler.transform(X))

    def card(self) -> dict:
        names = list(RIDGE_X) + [f"occ_{i}" for i in range(len(self.model.coef_) - len(RIDGE_X))]
        return {"alpha": RIDGE_ALPHA, "n_train": self.n_train, "intercept": float(self.model.intercept_),
                "coef_standardized": dict(zip(names, map(float, self.model.coef_)))}


def predict(method: str, f: dict, rows: np.ndarray, cols: np.ndarray, h: int, ridge: RidgeModel | None = None) -> np.ndarray:
    """Point forecasts (shares) for series `rows` at origins `cols`."""
    p3, p12 = f["p3"][rows, cols], f["p12"][rows, cols]
    p12s = f["p12s"][rows, cols]
    if method == "persistence":
        return np.where(np.isnan(p3), p12, p3)
    if method == "mean12":
        return p12
    if method == "shrink":
        n3 = np.nan_to_num(f["n3"][rows, cols])
        w = n3 / (n3 + KAPPA)
        return w * np.nan_to_num(p3) + (1 - w) * p12
    if method == "trend":
        dist = (h + 4.5) / 3  # quarters from the 12-month window's centre to the target window's centre
        return expit(logit(p12s) + DAMP * f["slope_q"][rows, cols] * dist)
    if method == "ridge":
        if ridge is None:
            return np.full(len(rows), np.nan)
        return expit(logit(p12s) + ridge.predict(design(f, rows, cols)))
    if method == "blend":
        return 0.5 * predict("shrink", f, rows, cols, h) + 0.5 * predict("ridge", f, rows, cols, h, ridge)
    raise ValueError(method)


def ridge_target(f: dict, K: np.ndarray, N: np.ndarray, rows: np.ndarray, cols: np.ndarray, h: int) -> np.ndarray:
    k, n = wsum(K, WINDOW)[rows, cols + h], wsum(N, WINDOW)[rows, cols + h]
    return logit((k + 0.5) / (n + 1)) - logit(f["p12s"][rows, cols])
