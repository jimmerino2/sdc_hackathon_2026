"""Skill demand: monthly % of new Indeed job ads mentioning AI terms, per country (target ai_mention_share).

Point-in-time: Indeed's git history (forecasting/vintages.py). A snapshot at T reads the latest AI-tracker vintage
published by T, and each country's latest postings vintage. Before the first AI-tracker vintage (2024-04-29)
nothing was published to read, so earlier origins use a *reconstructed* snapshot: the first vintage cut at the
origin's month, dated RECONSTRUCTED_LAG_MONTHS later. Those values carry revisions made up to 2024-04, so they are
flagged and kept out of the holdout by the split (the holdout is the latest origins, all real).

Features at month m (groups are what the ablations drop):
  level          lvl
  own_trend      d1 d3 d6 d12
  cross_country  xc_d3 xc_d12        mean of d3 / d12 over the countries in the snapshot
  postings       post_d3 post_d12    log change of the country's postings index (source indeed_postings)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import registry, vintages as V
from ..features import Snapshot, lag_features, stack, wide_logit
from . import TargetSpec

RECONSTRUCTED_LAG_MONTHS = 2  # largest publication lag seen in the real vintages
FIRST_RECONSTRUCTED = pd.Period("2021-01", freq="M")
FEATURE_GROUPS = {"level": ["lvl"], "own_trend": ["d1", "d3", "d6", "d12"],
                  "cross_country": ["xc_d3", "xc_d12"], "postings": ["post_d3", "post_d12"]}
GROUP_SOURCE = {"level": "indeed_ai_tracker", "own_trend": "indeed_ai_tracker",
                "cross_country": "indeed_ai_tracker", "postings": "indeed_postings"}


def _complete(df: pd.DataFrame) -> pd.DataFrame:
    d = df[~df["is_partial"].astype(bool)].rename(columns={"geo": "unit"})
    return d.assign(period=pd.PeriodIndex(d["month"], freq="M"))[["unit", "period", "value"]]


def snapshot_real(ai_v: pd.DataFrame, po_v: pd.DataFrame, origin: pd.Timestamp) -> Snapshot:
    ai = V.as_of(ai_v, origin)
    if ai.empty:
        raise ValueError(f"no AI-tracker vintage published by {origin}")
    po = V.as_of(po_v, origin, per_geo=True)
    assert (ai["available_at"] <= origin).all() and (po["available_at"] <= origin).all()
    a = _complete(ai)
    last = a.groupby("unit")["period"].max().mode().max()  # most countries' last month
    return Snapshot(origin, last, "real", a[a["period"] <= last], ",".join(sorted(ai["vintage_id"].unique())),
                    {"postings": _complete(po)})


def snapshot_reconstructed(ai_v: pd.DataFrame, po_v: pd.DataFrame, last: pd.Period) -> Snapshot:
    first = ai_v[ai_v["available_at"] == ai_v["available_at"].min()]
    origin = ((last + RECONSTRUCTED_LAG_MONTHS).to_timestamp() + pd.Timedelta(days=14)).tz_localize("UTC")
    a = _complete(first)
    po = V.as_of(po_v, origin, per_geo=True)  # postings have real vintages from 2021-02
    return Snapshot(origin, last, "reconstructed", a[a["period"] <= last], first["vintage_id"].iloc[0] + "(cut)",
                    {"postings": _complete(po) if not po.empty else pd.DataFrame(columns=["unit", "period", "value"])})


def load() -> dict:
    return {"ai": V.load("ai_share_vintages.csv"), "postings": V.load("postings_vintages.csv")}


def origins(d: dict) -> list[Snapshot]:
    by_month = {}
    for when in sorted(d["ai"]["available_at"].unique()):
        s = snapshot_real(d["ai"], d["postings"], pd.Timestamp(when))
        by_month[s.last] = s  # the last vintage published for each month (later commits correct earlier ones)
    recon = [snapshot_reconstructed(d["ai"], d["postings"], m)
             for m in pd.period_range(FIRST_RECONSTRUCTED, min(by_month) - 1, freq="M")]
    return recon + [by_month[m] for m in sorted(by_month)]


def truth(d: dict) -> pd.Series:
    ai = d["ai"]
    t = _complete(ai[ai["available_at"] == ai["available_at"].max()])
    return t.set_index(["period", "unit"])["value"]


def panel(s: Snapshot) -> pd.DataFrame:
    periods = pd.period_range(s.values["period"].min(), s.last, freq="M")
    y = wide_logit(s.values, periods)
    f = lag_features(y, lags=(1, 3, 6), trend_steps=12, cross=(3, 12))
    po = s.extras.get("postings")
    if po is not None and not po.empty:
        pw = np.log(po.pivot(index="period", columns="unit", values="value")).reindex(index=y.index, columns=y.columns)
        f["post_d3"], f["post_d12"] = pw - pw.shift(3), pw - pw.shift(12)
    else:
        f["post_d3"] = f["post_d12"] = pd.DataFrame(np.nan, index=y.index, columns=y.columns)
    return stack(f)


def health(d: dict, now: pd.Timestamp) -> dict:
    return {"indeed_ai_tracker": registry.vintage_health("indeed_ai_tracker", d["ai"], now),
            "indeed_postings": registry.vintage_health("indeed_postings", d["postings"], now)}


def ingest(pull: bool) -> None:
    if pull:
        for r in V.REPOS:
            V.pull(r)
    ai = V.build_ai_share(V.RAW / "ait_full"); V.validate(ai, 0, 100); V.write(ai, "ai_share_vintages.csv")
    po = V.build_postings(V.RAW / "jpt_full"); V.validate(po, 0, 1000); V.write(po, "postings_vintages.csv")


SPEC = TargetSpec(
    id="ai_mention_share", horizons=(1, 3, 6), period_unit="month", unit_kind="country", trend_steps=12,
    feature_groups=FEATURE_GROUPS, group_source=GROUP_SOURCE, load=load, origins=origins, truth=truth,
    panel=panel, health=health, ingest=ingest, regimes=True)
