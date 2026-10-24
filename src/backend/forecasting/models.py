"""Candidate models for the h-period change of a target on its modelling scale. Ordered simplest first: selection
prefers the simpler model when two score within NEAR_BEST, so complexity has to earn its place.

  naive         no change (the last published value carries forward)
  drift         the unit's change over the last trend_steps periods continues, scaled to h periods
  damped_drift  drift with a damping factor fitted on the snapshot's own history
  pooled_mean   the average h-period change of all units over the last trend_steps anchor periods
  local_trend   local-linear-trend state-space model (Kalman filter, variances by maximum likelihood)
  ridge         ridge regression on the feature groups; alpha by time-ordered CV inside the snapshot
  lightgbm      small, heavily regularised trees; a challenger only

Every learned step (imputation, scaling, alpha, phi, variances, trees) is fitted on what the origin's snapshot
contains: the training rows, and for local_trend the snapshot's own series (`panel`, periods <= the origin's last).
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261024
ALPHAS = [0.1, 1.0, 10.0, 100.0, 1000.0]
PHIS = [0.5, 0.7, 0.8, 0.9, 0.95, 1.0]
LGB_PARAMS = dict(objective="l1", n_estimators=150, learning_rate=0.03, num_leaves=4, min_child_samples=30,
                  subsample=0.8, subsample_freq=1, reg_lambda=5.0, random_state=SEED, verbose=-1, n_jobs=1)


class Model:
    name = ""
    complexity = 0
    uses_features = False

    def fit(self, train: pd.DataFrame, h: int, features: list[str], trend_steps: int = 12,
            panel: pd.DataFrame | None = None) -> "Model":
        self.h, self.features, self.trend_steps, self.panel = h, features, trend_steps, panel
        return self

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


class Naive(Model):
    name, complexity = "naive", 0

    def predict(self, rows):
        return np.zeros(len(rows))


class Drift(Model):
    name, complexity = "drift", 1

    def predict(self, rows):
        return rows["trend"].fillna(0).to_numpy() * self.h / self.trend_steps  # missing trend -> no change


class DampedDrift(Model):
    name, complexity = "damped_drift", 2

    def _path(self, trend: np.ndarray, phi: float) -> np.ndarray:
        return trend / self.trend_steps * sum(phi ** k for k in range(1, self.h + 1))

    def fit(self, train, h, features, trend_steps=12, panel=None):
        super().fit(train, h, features, trend_steps, panel)
        t = train.dropna(subset=["trend"])
        if t.empty:  # no trend observed yet: nothing to damp
            self.phi = 1.0
            return self
        err = {phi: np.abs(self._path(t["trend"].to_numpy(), phi) - t["target"].to_numpy()).mean() for phi in PHIS}
        self.phi = min(err, key=err.get)
        return self

    def predict(self, rows):
        return self._path(rows["trend"].fillna(0).to_numpy(), self.phi)


class PooledMean(Model):
    name, complexity = "pooled_mean", 2

    def fit(self, train, h, features, trend_steps=12, panel=None):
        super().fit(train, h, features, trend_steps, panel)
        recent = train[train["period"] > train["period"].max() - trend_steps]
        self.mean = float(recent["target"].mean()) if len(recent) else 0.0
        return self

    def predict(self, rows):
        return np.full(len(rows), self.mean)


def kalman_llt(Y: np.ndarray, log_var: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Local linear trend, filtered over time and vectorised over units (columns of Y; NaN = not observed).

    y_t = mu_t + eps;  mu_t+1 = mu_t + beta_t + eta;  beta_t+1 = beta_t + zeta;  variances exp(log_var) =
    (eps, eta, zeta), shared by all units. Each unit starts diffuse at its first observation; its first two
    observations do not enter the likelihood. Returns (log-likelihood, filtered level, filtered slope) at the end."""
    h_eps, q_eta, q_zeta = np.exp(log_var)
    n = Y.shape[1]
    a = np.zeros((n, 2))
    P = np.tile(np.eye(2) * 1e6, (n, 1, 1))
    seen = np.zeros(n, dtype=int)
    ll = 0.0
    for t in range(Y.shape[0]):
        y = Y[t]
        obs = ~np.isnan(y)
        first = obs & (seen == 0)
        a[first, 0], a[first, 1] = y[first], 0.0  # diffuse start at the first observation
        v = np.where(obs, y - a[:, 0], 0.0)
        F = np.maximum(P[:, 0, 0] + h_eps, 1e-12)
        K = P[:, :, 0] / F[:, None]
        upd = obs & ~first
        ll += float(np.sum(np.where(upd & (seen >= 2), -0.5 * (np.log(2 * np.pi * F) + v ** 2 / F), 0.0)))
        a[upd] += K[upd] * v[upd, None]
        P[upd] -= K[upd][:, :, None] * P[upd][:, 0, :][:, None, :]
        P[first] = np.array([[h_eps, 0.0], [0.0, 1e2]])  # level known up to noise, slope still vague
        seen += obs
        if t < Y.shape[0] - 1:  # predict the next period
            a = np.stack([a[:, 0] + a[:, 1], a[:, 1]], axis=1)
            T = np.array([[1.0, 1.0], [0.0, 1.0]])
            P = T @ P @ T.T + np.diag([q_eta, q_zeta])
    return ll, a[:, 0], a[:, 1]


class LocalTrend(Model):
    """The spec's primary capability model, run as a candidate everywhere. A unit's forecast change is
    level_T + h * slope_T - y_T. Variances are fitted once per snapshot and cached on the panel."""
    name, complexity = "local_trend", 3

    def fit(self, train, h, features, trend_steps=12, panel=None):
        super().fit(train, h, features, trend_steps, panel)
        if panel is None:
            raise ValueError("local_trend needs the snapshot panel")
        if "llt" not in panel.attrs:
            Y = panel.pivot(index="period", columns="unit", values="lvl").sort_index()
            diffs = np.nanvar(np.diff(Y.to_numpy(), axis=0)) if len(Y) > 2 else 1.0
            x0 = np.log(np.maximum([diffs / 2, diffs / 2, diffs / 50], 1e-8))
            res = minimize(lambda lv: -kalman_llt(Y.to_numpy(), lv)[0], x0, method="Nelder-Mead",
                           options={"maxiter": 300, "xatol": 1e-3, "fatol": 1e-3})
            _, level, slope = kalman_llt(Y.to_numpy(), res.x)
            panel.attrs["llt"] = {"units": list(Y.columns), "level": level, "slope": slope, "log_var": res.x,
                                  "last": Y.ffill().iloc[-1].to_numpy()}
        return self

    def predict(self, rows):
        c = self.panel.attrs["llt"]
        idx = {u: i for i, u in enumerate(c["units"])}
        out = []
        for u, y in zip(rows["unit"], rows["lvl"]):
            i = idx.get(u)
            out.append(0.0 if i is None else c["level"][i] + self.h * c["slope"][i] - y)
        return np.array(out)


def _period_folds(periods: pd.Series, n: int = 4, h: int = 1):
    """Time-ordered inner folds over anchor periods, with an h-period gap so labels do not overlap the fold."""
    u = np.array(sorted(periods.unique()))
    cuts = np.linspace(len(u) * 0.5, len(u), n + 1).astype(int)[:-1]
    for c in cuts:
        if c - h <= 0 or c >= len(u):
            continue
        yield periods.isin(u[:c - h]).to_numpy(), periods.isin(u[c:c + 6]).to_numpy()


class RidgeModel(Model):
    name, complexity, uses_features = "ridge", 3, True

    @staticmethod
    def _pipe(alpha):
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                             StandardScaler(), Ridge(alpha=alpha))

    def fit(self, train, h, features, trend_steps=12, panel=None):
        super().fit(train, h, features, trend_steps, panel)
        X, y = train[features], train["target"].to_numpy()
        scores = {a: [] for a in ALPHAS}
        for tr, va in _period_folds(train["period"], h=h):
            if tr.sum() < 20 or va.sum() == 0:
                continue
            for a in ALPHAS:
                m = self._pipe(a).fit(X[tr], y[tr])
                scores[a].append(np.abs(m.predict(X[va]) - y[va]).mean())
        self.alpha = min(ALPHAS, key=lambda a: np.mean(scores[a]) if scores[a] else np.inf) if any(scores.values()) else 10.0
        self.pipe = self._pipe(self.alpha).fit(X, y)
        return self

    def predict(self, rows):
        return self.pipe.predict(rows[self.features])


class LightGBMModel(Model):
    name, complexity, uses_features = "lightgbm", 4, True

    def fit(self, train, h, features, trend_steps=12, panel=None):
        super().fit(train, h, features, trend_steps, panel)
        # Too few rows to split (a leaf needs min_child_samples): no trees, just the average change
        self.m = (lgb.LGBMRegressor(**LGB_PARAMS).fit(train[features], train["target"])
                  if len(train) >= 2 * LGB_PARAMS["min_child_samples"] else None)
        self.mean = float(train["target"].mean()) if len(train) else 0.0
        return self

    def predict(self, rows):
        return self.m.predict(rows[self.features]) if self.m is not None else np.full(len(rows), self.mean)


CANDIDATES: dict[str, type[Model]] = {c.name: c for c in
                                      [Naive, Drift, DampedDrift, PooledMean, LocalTrend, RidgeModel, LightGBMModel]}
BASELINES = ("naive", "drift", "damped_drift", "pooled_mean")
