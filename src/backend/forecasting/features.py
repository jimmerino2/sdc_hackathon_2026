"""Shared feature machinery: snapshots, value scales, lag features, labels. Target-specific code is in targets/.

An origin is a moment T. Its snapshot holds, per source, only what was published by T (each target module says
how it knows that: git vintages, publication dates, or fetch times). Every feature and every training label at that
origin comes from the snapshot; the realised outcome used to score it comes from the latest data
(evaluation.truth). So nothing published after T reaches a model at T.

Modelling scale: each target sets one (TargetSpec.scale). Shares use y = logit(share), so forecasts stay inside
0-100% and a 0.5 pp move at 2% counts more than at 20%; METR time horizons use y = log2(minutes).
Label at anchor period p, horizon h: y(p + h) - y(p). `period` is a pandas Period (months, quarters) or an int
(BTOS fortnights, numbered in calendar order); either supports p + h.

Columns every target panel provides: period, unit, lvl, trend (y(p) - y(p - trend_steps)), plus its features.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Snapshot:
    origin: pd.Timestamp  # when the forecast is made (UTC)
    last: object  # last complete period of the target series in the snapshot
    kind: str  # how point-in-time it is: real | reconstructed | publication_dated | current_only
    values: pd.DataFrame  # unit, period, value (percent), periods <= last
    vintage: str  # identifier(s) of the data the snapshot was cut from
    extras: dict = field(default_factory=dict)  # other sources, already cut at the origin


def logit(p: np.ndarray | pd.Series) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def expit(x: np.ndarray | pd.Series) -> np.ndarray:
    return 1 / (1 + np.exp(-np.asarray(x, dtype=float)))


@dataclass(frozen=True)
class Scale:
    """Value <-> modelling scale. Errors are always reported back on the value scale, in `unit`."""
    name: str
    unit: str
    to_model: object  # array of values -> array on the modelling scale
    from_model: object


PERCENT = Scale("logit of percent", "pp", lambda v: logit(np.asarray(v, dtype=float) / 100),
                lambda y: 100 * expit(y))
LOG2 = Scale("log2", "doublings (log2)", lambda v: np.log2(np.asarray(v, dtype=float)), lambda y: np.exp2(np.asarray(y, dtype=float)))


def wide_logit(values: pd.DataFrame, periods, scale: Scale = PERCENT) -> pd.DataFrame:
    """period x unit values on the modelling scale, on the full period index: gaps stay NaN, never 0."""
    w = values.pivot(index="period", columns="unit", values="value").reindex(list(periods))
    return pd.DataFrame(scale.to_model(w.to_numpy()), index=w.index, columns=w.columns)


def lag_features(y: pd.DataFrame, lags: tuple[int, ...], trend_steps: int, cross: tuple[int, ...]) -> dict:
    """lvl, d<k> = y - y.shift(k), trend, and xc_d<k> = mean of d<k> over all units at that period."""
    f = {"lvl": y}
    for k in sorted(set(lags) | {trend_steps} | set(cross)):
        f[f"d{k}"] = y - y.shift(k)
    f["trend"] = f[f"d{trend_steps}"]
    for k in cross:
        f[f"xc_d{k}"] = pd.DataFrame({u: f[f"d{k}"].mean(axis=1) for u in y.columns})
    return f


def stack(feats: dict) -> pd.DataFrame:
    out = pd.concat({k: v.stack(future_stack=True) for k, v in feats.items()}, axis=1)
    out.index.names = ["period", "unit"]
    return out.reset_index()


def labelled(spec, s: Snapshot, h: int) -> pd.DataFrame:
    """Training rows: anchors whose h-step-ahead value is inside the snapshot (known at the origin)."""
    p = spec.panel(s)
    y = p.set_index(["period", "unit"])["lvl"]
    future = y.copy()
    future.index = pd.MultiIndex.from_arrays([future.index.get_level_values(0) - h, future.index.get_level_values(1)])
    p["target"] = future.reindex(pd.MultiIndex.from_frame(p[["period", "unit"]])).to_numpy() - p["lvl"].to_numpy()
    p = p[p["period"] + h <= s.last].dropna(subset=["lvl", "target"])
    assert (p["period"] + h <= s.last).all()
    return p


def latest_rows(spec, s: Snapshot) -> pd.DataFrame:
    """Prediction rows: each unit observed at the snapshot's last period."""
    p = spec.panel(s)
    return p[(p["period"] == s.last) & p["lvl"].notna()].reset_index(drop=True)
