"""Candidate models for the h-period change in logit share. Ordered simplest first: selection prefers the
simpler model when two score within NEAR_BEST, so complexity has to earn its place.

  naive         no change (the last published value carries forward)
  drift         the unit's change over the last trend_steps periods continues, scaled to h periods
  damped_drift  drift with a damping factor fitted on the snapshot's own history
  pooled_mean   the average h-period change of all units over the last trend_steps anchor periods
  ridge         ridge regression on the feature groups; alpha by time-ordered CV inside the snapshot
  lightgbm      small, heavily regularised trees; a challenger only

Every learned step (imputation, scaling, alpha, phi, trees) is fitted on the training rows passed in, which are
themselves only what the origin's snapshot contains.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
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

    def fit(self, train: pd.DataFrame, h: int, features: list[str], trend_steps: int = 12) -> "Model":
        self.h, self.features, self.trend_steps = h, features, trend_steps
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

    def fit(self, train, h, features, trend_steps=12):
        super().fit(train, h, features, trend_steps)
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

    def fit(self, train, h, features, trend_steps=12):
        super().fit(train, h, features, trend_steps)
        recent = train[train["period"] > train["period"].max() - trend_steps]
        self.mean = float(recent["target"].mean()) if len(recent) else 0.0
        return self

    def predict(self, rows):
        return np.full(len(rows), self.mean)


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

    def fit(self, train, h, features, trend_steps=12):
        super().fit(train, h, features, trend_steps)
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

    def fit(self, train, h, features, trend_steps=12):
        super().fit(train, h, features, trend_steps)
        self.m = lgb.LGBMRegressor(**LGB_PARAMS).fit(train[features], train["target"])
        return self

    def predict(self, rows):
        return self.m.predict(rows[self.features])


CANDIDATES: dict[str, type[Model]] = {c.name: c for c in
                                      [Naive, Drift, DampedDrift, PooledMean, RidgeModel, LightGBMModel]}
BASELINES = ("naive", "drift", "damped_drift", "pooled_mean")
