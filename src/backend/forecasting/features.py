"""Skill-demand features for target `ai_mention_share`, built only from what was published at a forecast origin.

An origin is a moment T. Its snapshot is, per source, the latest vintage with available_at <= T, complete months
only. Every feature and every training label at that origin comes from the snapshot; the realised outcome used to
score it comes from the latest vintage (evaluation.py). So revisions published after T never reach a model at T.

Before the first AI-tracker vintage (2024-04-29) there is nothing published to read, so earlier origins use a
*reconstructed* snapshot: the first vintage cut at the origin's last month. Those values include revisions made
up to 2024-04 (look-ahead the forecaster did not have); such origins carry vintage_kind="reconstructed" and are
reported apart from "real" ones.

Modelling scale: y = logit(share), so forecasts stay in 0-100% and a 0.5 pp move at 2% counts more than at 20%.
Label at anchor month m, horizon h: y(m + h) - y(m). Features at m (groups are what the ablations drop):
  level          lvl            y(m)
  own_trend      d1 d3 d6 d12   y(m) - y(m - k)
  cross_country  xc_d3 xc_d12   mean of d3 / d12 over all countries in the snapshot at m
  postings       post_d3 post_d12  log change of the country's Indeed postings index (source indeed_postings)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import vintages as V

FEATURE_GROUPS = {
    "level": ["lvl"],
    "own_trend": ["d1", "d3", "d6", "d12"],
    "cross_country": ["xc_d3", "xc_d12"],
    "postings": ["post_d3", "post_d12"],
}
GROUP_SOURCE = {"level": "indeed_ai_tracker", "own_trend": "indeed_ai_tracker",
                "cross_country": "indeed_ai_tracker", "postings": "indeed_postings"}
ALL_FEATURES = [f for g in FEATURE_GROUPS.values() for f in g]
RECONSTRUCTED_LAG_MONTHS = 2  # largest publication lag seen in the real vintages: reconstructed origins wait this long


@dataclass
class Snapshot:
    origin: pd.Timestamp  # when the forecast is made (UTC)
    last_month: pd.Period  # last complete month of the target series in the snapshot
    kind: str  # real | reconstructed
    ai: pd.DataFrame  # geo x month value (percent), complete months <= last_month
    postings: pd.DataFrame  # geo x month value (index), complete months
    ai_vintage: str
    postings_vintages: str


def logit(p: np.ndarray | pd.Series) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def expit(x: np.ndarray | pd.Series) -> np.ndarray:
    return 1 / (1 + np.exp(-np.asarray(x, dtype=float)))


def _complete(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["is_partial"].astype(bool)][["geo", "month", "value"]]


def snapshot_real(ai_v: pd.DataFrame, po_v: pd.DataFrame, origin: pd.Timestamp) -> Snapshot:
    ai = V.as_of(ai_v, origin)
    if ai.empty:
        raise ValueError(f"no AI-tracker vintage published by {origin}")
    po = V.as_of(po_v, origin, per_geo=True)
    assert (ai["available_at"] <= origin).all() and (po["available_at"] <= origin).all()
    a = _complete(ai)
    last = pd.Period(a.groupby("geo")["month"].max().mode().max(), freq="M")  # most countries' last month
    a = a[a["month"] <= str(last)]
    return Snapshot(origin, last, "real", a, _complete(po), ",".join(sorted(ai["vintage_id"].unique())),
                    ",".join(sorted(po["vintage_id"].unique())))


def snapshot_reconstructed(ai_v: pd.DataFrame, po_v: pd.DataFrame, last: pd.Period) -> Snapshot:
    first = ai_v[ai_v["available_at"] == ai_v["available_at"].min()]
    origin = (last + RECONSTRUCTED_LAG_MONTHS).to_timestamp() + pd.Timedelta(days=14)
    origin = origin.tz_localize("UTC")
    a = _complete(first)
    a = a[a["month"] <= str(last)]
    po = V.as_of(po_v, origin, per_geo=True)  # postings have real vintages from 2021-02
    return Snapshot(origin, last, "reconstructed", a, _complete(po), first["vintage_id"].iloc[0] + "(cut)",
                    ",".join(sorted(po["vintage_id"].unique())) if not po.empty else "")


def panel(s: Snapshot) -> pd.DataFrame:
    """Features for every geo x anchor month in the snapshot (no labels)."""
    a = s.ai.copy()
    a["month"] = pd.PeriodIndex(a["month"], freq="M")
    w = a.pivot(index="month", columns="geo", values="value").sort_index()
    w = w.reindex(pd.period_range(w.index.min(), s.last_month, freq="M"))  # gaps stay NaN, never 0
    y = pd.DataFrame(logit(w / 100), index=w.index, columns=w.columns)
    feats = {"lvl": y}
    for k in (1, 3, 6, 12):
        feats[f"d{k}"] = y - y.shift(k)
    feats["xc_d3"] = pd.DataFrame({g: feats["d3"].mean(axis=1) for g in y.columns})
    feats["xc_d12"] = pd.DataFrame({g: feats["d12"].mean(axis=1) for g in y.columns})
    if not s.postings.empty:
        p = s.postings.copy()
        p["month"] = pd.PeriodIndex(p["month"], freq="M")
        pw = np.log(p.pivot(index="month", columns="geo", values="value")).reindex(index=y.index, columns=y.columns)
        feats["post_d3"], feats["post_d12"] = pw - pw.shift(3), pw - pw.shift(12)
    else:
        feats["post_d3"] = feats["post_d12"] = pd.DataFrame(np.nan, index=y.index, columns=y.columns)
    out = pd.concat({k: v.stack(future_stack=True) for k, v in feats.items()}, axis=1)
    out.index.names = ["month", "geo"]
    return out.reset_index()


def labelled(s: Snapshot, h: int) -> pd.DataFrame:
    """Training rows: anchors whose h-month-ahead value is inside the snapshot (known at the origin)."""
    p = panel(s)
    y = p.set_index(["month", "geo"])["lvl"]
    future = y.copy()
    future.index = pd.MultiIndex.from_arrays([future.index.get_level_values(0) - h, future.index.get_level_values(1)])
    p["target"] = (future.reindex(pd.MultiIndex.from_frame(p[["month", "geo"]])).to_numpy() - p["lvl"].to_numpy())
    p = p[p["month"] + h <= s.last_month].dropna(subset=["lvl", "target"])
    assert (p["month"] + h <= s.last_month).all()
    return p


def latest_rows(s: Snapshot) -> pd.DataFrame:
    """Prediction rows: each geo at the snapshot's last month."""
    p = panel(s)
    return p[(p["month"] == s.last_month) & p["lvl"].notna()].reset_index(drop=True)
