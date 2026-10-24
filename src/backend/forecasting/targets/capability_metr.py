"""AI capability: frontier METR 50% task-completion time horizon (target frontier_time_horizon).

Value at month m: the longest 50% time horizon (minutes) among models released by the end of m, as measured by
METR and published in Epoch AI's data (forecasting/capability.py). Modelled as log2(minutes), so a constant
doubling time is a straight line, and the local-linear-trend model's slope is "doublings per month".

Measurement versions are separate units, never mixed: METR's v1.1 suite (from Mar 2026) re-measured older models
and moved them a lot (e.g. Claude 3.5 Sonnet 18.7 -> 11.4 min). A version is *active* in the vintages where it is
the current suite (v1.0: no v1.1 rows yet; v1.1: from its first appearance). Each unit reads only its active
vintages, and its truth is its last active vintage, so a frozen legacy series is never scored as if it had
stopped improving. Rows METR later deleted therefore do not rewrite v1.0's history either.

Measurement lag: METR measures a model weeks to months after release, so the latest months of any vintage would
look flat and be revised up later. A vintage counts as complete only up to MEASUREMENT_LAG_MONTHS before it was
published, for snapshots and truth alike.

Point in time: a vintage is available from Epoch's Last-Modified time (or the capture time). Before a unit's first
active vintage, origins use that vintage cut at the origin's month: *reconstructed* (measurements made later, on
models released by then). Snapshot kind: real, reconstructed, or mixed (some units each way).

Features (groups are what the ablations drop): level (lvl), own_trend (d1 d3 d6 d12 months).
Regime probabilities (acceleration / stable / slowdown) are produced for every forecast (evaluation.regime_*).
Only ECI from Epoch is not modelled: it is refitted jointly and has 3 vintages (from Sep 2026), so it cannot be
backtested without retrospective normalisation.
"""
from __future__ import annotations

import pandas as pd

from .. import capability, registry, success_curves
from ..features import LOG2, Snapshot, lag_features, stack, wide_logit
from . import TargetSpec

MEASURE = "metr_h50_minutes"
FEATURE_GROUPS = {"level": ["lvl"], "own_trend": ["d1", "d3", "d6", "d12"]}
GROUP_SOURCE = {g: "epoch_metr" for g in FEATURE_GROUPS}
FIRST_RECONSTRUCTED = pd.Period("2023-01", freq="M")  # from GPT-4-era models; was 2024-01 in the first run,
                                                     # moved after it left too few selection origins (documented)
MAX_STALE_MONTHS = 12  # a month has a measured frontier only if a measured model was released in the past 12
MEASUREMENT_LAG_MONTHS = 3  # METR measures a model 38-139 days after release (median 64; upper end inflated by
                            # gaps between archive captures): a vintage counts as complete only up to 3 months back
UNITS = {"METR-Horizon-v1.0": "v1.0", "METR-Horizon-v1.1": "v1.1"}
HISTORY_WARNING = ("few real vintages (METR in Epoch data since 2025-06; v1.1 since 2026-03); most backtest origins "
                   "are reconstructed")


def _month_of(t: pd.Timestamp) -> pd.Period:
    return pd.Period(t.tz_convert("UTC").tz_localize(None), freq="M")


def active_vintages(d: pd.DataFrame) -> dict[str, list[tuple[pd.Timestamp, str]]]:
    """unit -> [(available_at, vintage_id)] of the vintages where that METR version is the current suite."""
    m = d[d["measure"] == MEASURE]
    has_v11 = set(m.loc[m["metr_version"] == "METR-Horizon-v1.1", "vintage_id"])
    out = {"v1.0": [], "v1.1": []}
    for (vid, when), g in m.groupby(["vintage_id", "available_at"]):
        out["v1.1" if vid in has_v11 else "v1.0"].append((when, vid))
    return {u: sorted(v) for u, v in out.items()}


def frontier(rows: pd.DataFrame, last: pd.Period) -> pd.DataFrame:
    """Monthly frontier (max value among models released by month end), first release month .. last."""
    if rows.empty:
        return pd.DataFrame(columns=["period", "value"])
    rel = rows.assign(period=rows["release_date"].dt.to_period("M"))
    months = pd.period_range(rel["period"].min(), last, freq="M")
    by_month = rel.groupby("period")["value"].max().reindex(months)
    best = by_month.ffill().cummax()  # no release: frontier holds
    # ... but only while a measured model is recent. METR measured almost nothing from 2019-2022, so before GPT-4
    # the "frontier" would be GPT-2 (2019); a later jump from it says nothing about the pace of progress.
    last_release = pd.Series(months, index=months).where(by_month.notna()).ffill()
    stale = [(m - r).n > MAX_STALE_MONTHS if pd.notna(r) else True for m, r in zip(months, last_release)]
    best[stale] = float("nan")
    return pd.DataFrame({"period": months, "value": best.to_numpy()})


def _unit_rows(d: pd.DataFrame, vid: str, unit: str) -> pd.DataFrame:
    version = next(k for k, v in UNITS.items() if v == unit)
    return d[(d["vintage_id"] == vid) & (d["measure"] == MEASURE) & (d["metr_version"] == version)]


def snapshot(d: pd.DataFrame, act: dict, origin: pd.Timestamp, last: pd.Period | None = None) -> Snapshot:
    """Per unit: its latest active vintage published by `origin` (real), or its first active vintage cut at the
    origin's month (reconstructed) if none was published yet and the unit is not retired by then."""
    parts, kinds, vids = [], set(), []
    for unit, vs in act.items():
        if not vs:
            continue
        pub = [(w, v) for w, v in vs if w <= origin]
        later_suite = any(w <= origin for u2, vs2 in act.items() if u2 > unit for w, _ in vs2)
        if later_suite:
            continue  # retired: a newer METR suite is current at this origin
        if pub:
            when, vid = pub[-1]
            kinds.add("real")
        else:
            when, vid = vs[0]
            kinds.add("reconstructed")
        unit_last = _month_of(when) - MEASUREMENT_LAG_MONTHS  # complete through
        if last is not None:
            unit_last = min(unit_last, last)
        rows = _unit_rows(d, vid, unit)
        rows = rows[rows["release_date"].dt.to_period("M") <= unit_last]
        f = frontier(rows, unit_last).assign(unit=unit)
        parts.append(f)
        vids.append(f"{unit}:{vid}")
    vals = pd.concat(parts, ignore_index=True).dropna(subset=["value"])
    kind = kinds.pop() if len(kinds) == 1 else "mixed"
    return Snapshot(origin, vals["period"].max(), kind, vals[["unit", "period", "value"]], ",".join(vids))


def load() -> dict:
    d = capability.load()
    return {"obs": d, "active": active_vintages(d)}


def origins(data: dict) -> list[Snapshot]:
    d, act = data["obs"], data["active"]
    real_times = sorted({w for vs in act.values() for w, _ in vs})
    by_last = {}
    for when in real_times:
        s = snapshot(d, act, when)
        by_last[s.last] = s  # the last vintage published for each month
    first_real = min(by_last)
    recon = []
    for m in pd.period_range(FIRST_RECONSTRUCTED, first_real - 1, freq="M"):
        origin = ((m + 1).to_timestamp() + pd.Timedelta(days=14)).tz_localize("UTC")
        s = snapshot(d, act, origin, last=m)
        if s.last == m:  # skip months with no measured frontier (nothing recent to forecast from)
            recon.append(s)
    return recon + [by_last[m] for m in sorted(by_last)]


def truth(data: dict) -> pd.Series:
    """Per unit, the frontier in its last active vintage."""
    d, act = data["obs"], data["active"]
    parts = []
    for unit, vs in act.items():
        if vs:
            when, vid = vs[-1]
            parts.append(frontier(_unit_rows(d, vid, unit), _month_of(when) - MEASUREMENT_LAG_MONTHS).assign(unit=unit))
    t = pd.concat(parts, ignore_index=True).dropna(subset=["value"])
    return t.set_index(["period", "unit"])["value"]


def panel(s: Snapshot) -> pd.DataFrame:
    periods = pd.period_range(s.values["period"].min(), s.last, freq="M")
    y = wide_logit(s.values, periods, scale=LOG2)
    return stack(lag_features(y, lags=(1, 3, 6), trend_steps=12, cross=()))


def health(data: dict, now: pd.Timestamp) -> dict:
    d = data["obs"]
    m = d[d["measure"] == MEASURE]
    last = m["available_at"].max()
    return {"epoch_metr": registry.health("epoch_metr", last, str(_month_of(last) - MEASUREMENT_LAG_MONTHS), now)}


def _ingest(pull: bool) -> None:
    capability.ingest(pull)
    success_curves.ingest(pull)  # display only: curves at other success rates


SPEC = TargetSpec(
    id="frontier_time_horizon", horizons=(3, 6, 12), period_unit="month", unit_kind="METR suite version",
    trend_steps=12, feature_groups=FEATURE_GROUPS, group_source=GROUP_SOURCE, load=load, origins=origins,
    truth=truth, panel=panel, health=health, ingest=lambda pull: _ingest(pull), segment=lambda u: u,
    min_selection_origins=12, min_holdout=4, history_warning=HISTORY_WARNING, scale=LOG2,
    value_unit="minutes (50% task time horizon)", regimes=True, errors_on_model_scale=True)
