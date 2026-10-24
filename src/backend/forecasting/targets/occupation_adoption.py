"""Occupation adoption: % of employed US adults using generative AI for their job, per SOC major group
(target worker_genai_use_rate). Worker-level evidence only: no BTOS, no task exposure (contracts enforce it).

The series has 9 quarters (2024-Q3 on), so only a handful of origins can be scored: every forecast carries a
short-history warning, selection needs only 3 origins and the holdout only 2, and results are indicative.
A survey reading per group is also noisy (small samples), so naive and smoothing baselines matter more here.

Point in time: see forecasting/rps.py. With ALFRED vintages (FRED_API_KEY): FRED first published the whole series
on 2026-06-18 and revised it on 2026-10-16, so there are two real origins; earlier quarters are reconstructed from
the first FRED release (flagged). FRED's date is an upper bound: the authors published earlier on their own site.
Without a key the snapshot kind is "current_only": today's values, cut at each quarter, dated by an assumed lag.

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


def _snapshot(cut: pd.DataFrame, when: pd.Timestamp, last: pd.Period, kind: str, label: str) -> Snapshot:
    cut = cut[cut["quarter"] <= last]
    vals = pd.DataFrame({"unit": cut["unit"], "period": cut["quarter"], "value": cut["value_pct"]})
    return Snapshot(when, last, kind, vals, label)


def origins(d: dict) -> list[Snapshot]:
    """With ALFRED vintages: one real origin per FRED release, and before the first release, reconstructed origins
    (the first release cut at each quarter, dated quarter end + rps.ASSUMED_LAG). Without: current values cut at
    each quarter, dated by the assumed lag (kind current_only)."""
    obs = d["obs"]
    if not (obs["availability_basis"] == "alfred").all():
        out = []
        for q in sorted(obs["quarter"].unique()):
            if q >= FIRST_LAST:
                when = obs.loc[obs["quarter"] == q, "available_at"].max()
                cut = _as_of(obs, when)
                assert (cut["available_at"] <= when).all()
                out.append(_snapshot(cut, when, q, "current_only", f"rps as of {when:%Y-%m-%d} (current_only)"))
        return out
    real = {}
    for when in sorted(obs["available_at"].unique()):
        when = pd.Timestamp(when)
        cut = _as_of(obs, when)
        assert (cut["available_at"] <= when).all()
        last = cut["quarter"].max()
        real[last] = _snapshot(cut, when, last, "real", f"rps FRED vintage {when:%Y-%m-%d}")
    first_when = min(s.origin for s in real.values())
    first = _as_of(obs, first_when)
    recon = []
    for q in pd.period_range(FIRST_LAST, min(real) - 1, freq="Q"):
        when = (q.end_time.normalize() + rps.ASSUMED_LAG).tz_localize("UTC")
        recon.append(_snapshot(first, when, q, "reconstructed", f"rps FRED vintage {first_when:%Y-%m-%d} cut at {q}"))
    return recon + [real[q] for q in sorted(real)]


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
