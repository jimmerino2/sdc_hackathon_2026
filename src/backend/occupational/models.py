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
  ewma          recent level: exponentially weighted pooled share (counts weighted by half-life `hl` months),
                partially pooled across countries by `kappa` (ew_level)
  dtrend        damped trend: the weighted least-squares line of monthly logit share over the last `W` months,
                its slope shrunk toward zero by its uncertainty (shrunk_slope), projected from the line's end with
                damping `phi`
  adaptive      recent level plus adjusted trend, in logit share: the ewma level (with ewma's tuned hl and
                kappa) + beta * x, where
                x = shrunk slope (times its agreement with the last two quarter-on-quarter changes, if `consistency`)
                    * months from the level's centre to the target window's centre
                the slope is the cell's own (`source` = cell) or the skill's, pooled over every IT cell (pooled),
                and beta, the trend's measured persistence, is the weighted least-squares coefficient of the realised
                change from the level on x (clipped to [0, BETA_MAX]), fitted separately per evidence band (ads in
                the last 3 months) and refit like ridge on rows whose target was already observed at the refit
                origin. beta = 0 (the level alone) in a band until it has MIN_BETA_ROWS such rows.
Parameters of ewma / dtrend / adaptive (hl, kappa, W, phi, source, consistency) are chosen per horizon on training targets
(backtest.tune). KAPPA, DAMP, RIDGE_ALPHA and PRIOR_ADS are fixed in advance, not tuned on the test period.

Months with no ads in a cell are missing, not zero: they carry no weight in any share, level or slope. A month
with ads but no mention of the skill is an observed zero. Monthly shares are smoothed toward the series' own
trailing 24-month share (PRIOR_ADS pseudo-ads) before taking logits, so a zero or a 1-of-2 month stays finite and
counts for little.
Direction (shared by the backtest and the published forecast): forecast minus the baseline, the last 3 months'
pooled share at the origin, in share points; rising / falling beyond LABEL_PP, otherwise "flat" (about stable).
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

WINDOW = 3
KAPPA = 30.0
DAMP = 0.6
RIDGE_ALPHA = 10.0
PRIOR_ADS = 2.0
MIN_SLOPE_MONTHS = 4
LABEL_PP = 1.0
BETA_MAX = 2.0
MIN_BETA_ROWS = 1000
METHODS = ("persistence", "mean12", "shrink", "trend", "ridge", "blend", "ewma", "dtrend", "adaptive")
POST_HOC = ("blend",)
TUNED = ("ewma", "dtrend", "adaptive")
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
    f["K"], f["N"], f["skill"] = K, N, skill_idx
    f["cache"] = {}
    return f


def trailing_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Sum over up to w months ending at each month (fewer at the start, never NaN)."""
    c = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, axis=1)], axis=1)
    lo = np.maximum(np.arange(x.shape[1]) + 1 - w, 0)
    return c[:, 1:] - c[:, lo]


def prior_share(f: dict) -> np.ndarray:
    """The series' trailing 24-month share at each month (smoothed), the anchor for smoothing monthly shares."""
    if "p0" not in f["cache"]:
        f["cache"]["p0"] = (trailing_sum(f["K"], 24) + 0.5) / (trailing_sum(f["N"], 24) + 1)
    return f["cache"]["p0"]


def ew_level(f: dict, hl: float, kappa: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Exponentially weighted pooled share (weights 0.5 ** (lag / hl) on counts) and its count-weighted mean lag
    in months, at every month. kappa = 0: smoothed toward the series' own prior share by PRIOR_ADS pseudo-ads.
    kappa > 0: partially pooled with the same skill in the same occupation in every country (its weighted share
    over the same months), worth kappa ads, so a small cell borrows strength and a large one keeps its own level."""
    key = ("ew", hl, kappa)
    if key not in f["cache"]:
        sk, sn, sl = ew_sums(f, hl)
        if kappa > 0:
            grp = f["skill"] * (f["occ"].max() + 1) + f["occ"]
            gk, gn = np.zeros((grp.max() + 1, sk.shape[1])), np.zeros((grp.max() + 1, sk.shape[1]))
            np.add.at(gk, grp, sk)
            np.add.at(gn, grp, sn)
            g = ((gk + 0.5) / (gn + 1))[grp]
            lvl = (sk + kappa * g) / (sn + kappa)
        else:
            lvl = (sk + PRIOR_ADS * prior_share(f)) / (sn + PRIOR_ADS)
        f["cache"][key] = (lvl, sl / np.maximum(sn, 1e-9))
    return f["cache"][key]


def ew_sums(f: dict, hl: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exponentially weighted skill ads, ads and lag-weighted ads at every month."""
    key = ("ews", hl)
    if key not in f["cache"]:
        K, N = f["K"], f["N"]
        lam = 0.5 ** (1 / hl)
        sk, sn, sl = np.zeros(K.shape), np.zeros(K.shape), np.zeros(K.shape)
        for t in range(K.shape[1]):
            if t:
                sl[:, t] = lam * (sl[:, t - 1] + sn[:, t - 1])
                sk[:, t], sn[:, t] = lam * sk[:, t - 1], lam * sn[:, t - 1]
            sk[:, t] += K[:, t]
            sn[:, t] += N[:, t]
        f["cache"][key] = (sk, sn, sl)
    return f["cache"][key]


def slope(f: dict, W: int) -> dict:
    """Weighted least-squares slope of smoothed monthly logit share over the last W months (logit units per month),
    weights = ads that month. Its variance is binomial, inflated by the residual overdispersion when months scatter
    more than sampling explains. b = 0 and var = inf where fewer than MIN_SLOPE_MONTHS months have ads."""
    key = ("slope", W)
    if key not in f["cache"]:
        K, N = f["K"], f["N"]
        p0 = prior_share(f)
        # p0 one month back, so the month's own count does not set its own anchor
        p0 = np.concatenate([p0[:, :1], p0[:, :-1]], axis=1)
        y = logit((K + PRIOR_ADS * p0) / (N + PRIOR_ADS))
        x = np.broadcast_to(np.arange(K.shape[1], dtype=float), K.shape)
        S = {k: trailing_sum(v, W) for k, v in
             {"n": N, "nx": N * x, "ny": N * y, "nxx": N * x * x, "nxy": N * x * y, "nyy": N * y * y,
              "m": (N > 0).astype(float), "k": K}.items()}
        n = np.maximum(S["n"], 1e-9)
        xm, ym = S["nx"] / n, S["ny"] / n
        sxx = S["nxx"] - n * xm * xm
        sxy = S["nxy"] - n * xm * ym
        syy = S["nyy"] - n * ym * ym
        ok = (S["m"] >= MIN_SLOPE_MONTHS) & (sxx > 1e-6)
        b = np.where(ok, sxy / np.where(ok, sxx, 1), 0.0)
        pbar = (S["k"] + 0.5) / (S["n"] + 1)
        v = pbar * (1 - pbar)
        rss = np.maximum(syy - b * sxy, 0)
        od = np.maximum(1.0, v * rss / np.maximum(S["m"] - 2, 1))
        var = np.where(ok, od / (v * np.where(ok, sxx, 1)), np.inf)
        t = np.arange(K.shape[1], dtype=float)
        f["cache"][key] = {"b": b, "var": var, "end": np.where(ok, ym + b * (t - xm), logit(pbar)), "ok": ok}
    return f["cache"][key]


def shrunk_slope(f: dict, W: int) -> np.ndarray:
    """Slope times z^2 / (z^2 + 1), z = slope / its standard error: a slope within its noise (few ads, scattered
    months) shrinks toward zero, a clear one keeps most of its size. It must also hold without the latest month. (A pooled empirical-Bayes prior was tried
    first: across these series the spread of true slopes estimates at ~0, which flattens every slope.)"""
    key = ("bs", W)
    if key not in f["cache"]:
        s = slope(f, W)
        b = s["b"] * s["b"] ** 2 / (s["b"] ** 2 + s["var"])
        # the same slope one month earlier must agree in sign; the smaller of the two is kept, so a slope made by
        # the latest month alone (a one-month spike) does not count as a trend
        prev = np.concatenate([np.zeros((b.shape[0], 1)), b[:, :-1]], axis=1)
        f["cache"][key] = np.where(np.sign(b) == np.sign(prev), np.sign(b) * np.minimum(np.abs(b), np.abs(prev)), 0.0)
    return f["cache"][key]


def agreement(f: dict, b: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """Share of the last two quarter-on-quarter changes in logit share (pooled 3-month windows) with the slope's
    sign: 1, 0.5 or 0. A slope that recent quarters contradict, or one driven by a single month, counts less."""
    key = "quarters"
    if key not in f["cache"]:
        p0 = prior_share(f)
        k3, n3 = trailing_sum(f["K"], 3), trailing_sum(f["N"], 3)
        q = [logit((shift(k3, 3 * j) + PRIOR_ADS * p0) / (shift(n3, 3 * j) + PRIOR_ADS)) for j in range(3)]
        f["cache"][key] = (np.sign(q[0] - q[1]), np.sign(q[1] - q[2]))
    d1, d2 = (d[rows, cols] for d in f["cache"][key])
    s = np.sign(b)
    return ((d1 == s).astype(float) + (d2 == s).astype(float)) / 2


def damped(d: np.ndarray, phi: float) -> np.ndarray:
    """Sum of phi ** i for i = 1..d (d months, may be fractional): how far a damped slope carries."""
    d = np.maximum(d, 0)
    return d if phi >= 1 else phi * (1 - phi ** d) / (1 - phi)


def baseline(f: dict, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """The share a forecast's direction is measured from: the last 3 months' pooled share (12 months if none)."""
    p3, p12 = f["p3"][rows, cols], f["p12"][rows, cols]
    return np.where(np.isnan(p3), p12, p3)


def direction(change_pp: np.ndarray, thr: float = LABEL_PP) -> np.ndarray:
    """rising / falling / flat (about stable) from forecast minus baseline, in share points."""
    c = np.asarray(change_pp, float)
    return np.select([c >= thr, c <= -thr], ["rising", "falling"], "flat")


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


def predict(method: str, f: dict, rows: np.ndarray, cols: np.ndarray, h: int, ridge: RidgeModel | None = None,
            params: dict | None = None) -> np.ndarray:
    """Point forecasts (shares) for series `rows` at origins `cols`. `params` holds the tuned settings of ewma,
    dtrend and adaptive. The target window's centre is h - 1 months after the origin."""
    if method in TUNED:
        q = params or {}
        if method == "ewma":
            return ew_level(f, q["hl"], q.get("kappa", 0.0))[0][rows, cols]
        if method == "adaptive":
            lvl, x = adaptive_parts(f, rows, cols, h, q)
            return expit(lvl + q.get("beta", 0.0) * x)
        b = shrunk_slope(f, q["W"])[rows, cols]
        if q.get("consistency"):
            b = b * agreement(f, b, rows, cols)
        return expit(slope(f, q["W"])["end"][rows, cols] + b * damped(np.full(len(rows), h - 1.0), q["phi"]))
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


def pooled(f: dict) -> dict:
    """Counts per skill summed over every cell (country x occupation) in the panel, as a features-like dict."""
    if "pooled" not in f["cache"]:
        K, N = np.zeros((f["skill"].max() + 1, f["K"].shape[1])), np.zeros((f["skill"].max() + 1, f["K"].shape[1]))
        np.add.at(K, f["skill"], f["K"])
        np.add.at(N, f["skill"], f["N"])
        f["cache"]["pooled"] = {"K": K, "N": N, "cache": {}}
    return f["cache"]["pooled"]


def adaptive_parts(f: dict, rows: np.ndarray, cols: np.ndarray, h: int, q: dict) -> tuple[np.ndarray, np.ndarray]:
    """(logit of the ewma level, trend term x) of the adaptive method; the forecast is expit(level + beta * x)."""
    src, idx = (pooled(f), f["skill"][rows]) if q.get("source") == "pooled" else (f, rows)
    b = shrunk_slope(src, q["W"])[idx, cols]
    if q.get("consistency"):
        b = b * agreement(src, b, idx, cols)
    lvl, lag = ew_level(f, q["hl"], q.get("kappa", 0.0))
    return logit(lvl[rows, cols]), b * (h - 1 + lag[rows, cols])


def fit_beta(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """Trend persistence: weighted least squares of y on x through the origin, clipped to [0, BETA_MAX]."""
    sxx = float(np.sum(w * x * x))
    if len(x) < MIN_BETA_ROWS or sxx <= 0:
        return 0.0
    return float(np.clip(np.sum(w * x * y) / sxx, 0.0, BETA_MAX))


def adaptive_target(f: dict, k: np.ndarray, n: np.ndarray, rows: np.ndarray, cols: np.ndarray, lvl: np.ndarray) -> np.ndarray:
    """Realised change in smoothed logit share from the level (the y that beta is fitted on)."""
    p0 = prior_share(f)[rows, cols]
    return logit((k + PRIOR_ADS * p0) / (n + PRIOR_ADS)) - lvl


def ridge_target(f: dict, K: np.ndarray, N: np.ndarray, rows: np.ndarray, cols: np.ndarray, h: int) -> np.ndarray:
    k, n = wsum(K, WINDOW)[rows, cols + h], wsum(N, WINDOW)[rows, cols + h]
    return logit((k + 0.5) / (n + 1)) - logit(f["p12s"][rows, cols])
