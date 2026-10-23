"""Occupation adoption: % of employed US adults using generative AI for their job, per SOC major group
(target worker_genai_use_rate). Worker-level evidence only: no BTOS, no task exposure (contracts enforce it).

The series has 9 quarters (2024-Q3 on), so only a handful of origins can be scored: every forecast carries a
short-history warning, selection needs only 3 origins and the holdout only 2, and results are indicative.
A survey reading per group is also noisy (small samples), so naive and smoothing baselines matter more here.

Point in time: see forecasting/rps.py. Without ALFRED vintages the snapshot kind is "current_only": values are
today's, cut at the origin's quarter, available from an assumed date.

Features at quarter q (groups are what the ablations drop):
  level        lvl
  own_trend    d1 d2 d4
  all_workers  xc_d1 xc_d2   mean change over all groups at q
"""
from __future__ import annotations

import pandas as pd

from .. import registry, rps
from ..features import Snapshot, lag_features, stack, wide_logit
from . import TargetSpec

FEATURE_GROUPS = {"level": ["lvl"], "own_trend": ["d1", "d2", "d4"], "all_workers": ["xc_d1", "xc_d2"]}
GROUP_SOURCE = {g: "rps_genai" for g in FEATURE_GROUPS}
FIRST_LAST = pd.Period("2025Q1", freq="Q")  # first origin: three quarters observed
HISTORY_WARNING = "short history: 9 quarterly readings per group; backtest covers few origins (indicative only)"


def load() -> dict:
    return {"obs": rps.load()}


def _as_of(obs: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    """Per group and quarter, the latest value available at `when`."""
    o = obs[obs["available_at"] <= when].sort_values("available_at")
    return o.groupby(["unit", "quarter"], as_index=False).last()


def origins(d: dict) -> list[Snapshot]:
    obs, out = d["obs"], []
    basis = "real" if (obs["availability_basis"] == "alfred").all() else "current_only"
    for q in sorted(obs["quarter"].unique()):
        if q < FIRST_LAST:
            continue
        when = obs.loc[obs["quarter"] == q, "available_at"].max()
        cut = _as_of(obs, when)
        cut = cut[cut["quarter"] <= q]
        assert (cut["available_at"] <= when).all()
        vals = pd.DataFrame({"unit": cut["unit"], "period": cut["quarter"], "value": cut["value_pct"]})
        out.append(Snapshot(when, q, basis, vals, f"rps as of {when:%Y-%m-%d} ({basis})"))
    return out


def truth(d: dict) -> pd.Series:
    t = _as_of(d["obs"], d["obs"]["available_at"].max())
    return t.set_index(["quarter", "unit"])["value_pct"].rename_axis(["period", "unit"])


def panel(s: Snapshot) -> pd.DataFrame:
    periods = pd.period_range(s.values["period"].min(), s.last, freq="Q")
    y = wide_logit(s.values, periods)
    return stack(lag_features(y, lags=(1, 2), trend_steps=4, cross=(1, 2)))


def health(d: dict, now: pd.Timestamp) -> dict:
    o = d["obs"]
    return {"rps_genai": registry.health("rps_genai", o["available_at"].max(), str(o["quarter"].max()), now)}


SPEC = TargetSpec(
    id="worker_genai_use_rate", horizons=(1, 2), period_unit="quarter", unit_kind="SOC major group (00 = all)",
    trend_steps=4, feature_groups=FEATURE_GROUPS, group_source=GROUP_SOURCE, load=load, origins=origins,
    truth=truth, panel=panel, health=health, ingest=rps.ingest, label=lambda q: str(q),
    min_selection_origins=3, min_holdout=2, history_warning=HISTORY_WARNING)
