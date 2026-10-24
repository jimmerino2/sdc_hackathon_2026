"""Business adoption: % of US businesses that used AI in the last two weeks (target btos_ai_use_rate).

Units are sector x wording ("54|new", "US|old"): the Nov 2025 wording change is a structural break (10.0% -> 17.3%
nationally), so each wording is its own series and no feature or label crosses it. Old-wording origins choose the
model; the holdout falls mostly on the new wording, so it measures how the choice transfers across the break.

Point in time: a fortnight's estimate is available from the end of its Census publication day (forecasting/btos.py).
Estimates are treated as unrevised (snapshot kind "publication_dated").

This target is what BTOS measures, and it stays a *business* measure: no output here is labelled or used as worker
or occupation adoption (contracts.FORBIDDEN_LABEL).

Features at fortnight p (groups are what the ablations drop):
  level         lvl
  own_trend     d1 d3 d6 d13          logit change over 1, 3, 6, 13 fortnights (13 ~ six months)
  cross_sector  xc_d3 xc_d13          mean of d3 / d13 over all units at p
  expectation   exp_gap               logit(% expecting to use AI in 6 months) - logit(% using now), same unit
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .. import btos, registry
from ..features import Snapshot, lag_features, logit, stack, wide_logit
from . import TargetSpec

FEATURE_GROUPS = {"level": ["lvl"], "own_trend": ["d1", "d3", "d6", "d13"], "cross_sector": ["xc_d3", "xc_d13"],
                  "expectation": ["exp_gap"]}
GROUP_SOURCE = {g: "census_btos" for g in FEATURE_GROUPS}


def _series(obs: pd.DataFrame, measure: str) -> pd.DataFrame:
    o = obs[(obs["measure"] == measure) & (obs["status"] == "ok")]
    return pd.DataFrame({"unit": o["unit"] + "|" + o["wording"], "period": o["period"].astype(int),
                         "value": o["estimate_pct"], "se": o["se_pct"], "available_at": o["available_at"]})


def load() -> dict:
    obs = btos.load()
    return {"use": _series(obs, "current_use"), "expect": _series(obs, "expected_use"), "obs": obs}


def origins(d: dict) -> list[Snapshot]:
    out = []
    for when in sorted(d["use"]["available_at"].unique()):
        when = pd.Timestamp(when)
        use = d["use"][d["use"]["available_at"] <= when]
        exp = d["expect"][d["expect"]["available_at"] <= when]
        assert (use["available_at"] <= when).all()
        out.append(Snapshot(when, int(use["period"].max()), "publication_dated", use[["unit", "period", "value"]],
                            f"btos published by {when:%Y-%m-%d}", {"expect": exp[["unit", "period", "value"]]}))
    return out


def truth(d: dict) -> pd.Series:
    return d["use"].set_index(["period", "unit"])["value"]


def panel(s: Snapshot) -> pd.DataFrame:
    periods = range(int(s.values["period"].min()), int(s.last) + 1)
    y = wide_logit(s.values, periods)
    f = lag_features(y, lags=(1, 3, 6), trend_steps=13, cross=(3, 13))
    e = s.extras["expect"].pivot(index="period", columns="unit", values="value").reindex(index=y.index, columns=y.columns)
    f["exp_gap"] = pd.DataFrame(logit(e / 100), index=y.index, columns=y.columns) - y
    return stack(f)


def health(d: dict, now: pd.Timestamp) -> dict:
    u = d["use"]
    last = u["available_at"].max()
    return {"census_btos": registry.health("census_btos", last, label(int(u["period"].max())), now)}


@lru_cache(maxsize=1)
def _calendar() -> dict[int, str]:
    c = btos.load_calendar()
    return {int(p): f"{s} (ref {e:%Y-%m-%d})" for p, s, e in zip(c["period"], c["smpdt"], c["ref_end"])}


def label(period) -> str:
    return _calendar().get(int(period), f"fortnight {int(period)}")


def segment(unit: str) -> str:
    return unit.split("|")[1] + " wording"


def ingest(pull: bool) -> None:
    btos.ingest(pull)
    _calendar.cache_clear()


SPEC = TargetSpec(
    id="btos_ai_use_rate", horizons=(6, 13), period_unit="fortnight", unit_kind="NAICS sector (or US) x wording",
    trend_steps=13, feature_groups=FEATURE_GROUPS, group_source=GROUP_SOURCE, load=load, origins=origins,
    truth=truth, panel=panel, health=health, ingest=ingest, label=label, segment=segment)
