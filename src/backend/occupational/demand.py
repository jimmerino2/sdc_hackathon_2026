"""Skill-demand measurements.

HN panel (the modelled series), one row per month x country x occupation [x skill]:
  n_ads        eligible ads with that country and occupation (the denominator; normalize.py defines eligible)
  n_ads_skill  of those, ads naming the skill (each ad counts once per skill)
  share        n_ads_skill / n_ads
Only complete months are modelled; the current month is kept with is_partial = True for display.
Adzuna snapshots: the same counts per retrieval date x country x occupation (a different population with
~500-character snippets, so shares are lower; shown next to the HN series, never pooled with it).
"""
from __future__ import annotations

import pandas as pd


def _explode(ads: pd.DataFrame) -> pd.DataFrame:
    e = ads[ads["eligible"] & ads["occupations"].ne("") & ads["countries"].ne("")]
    e = e.assign(country=e["countries"].str.split("|"), occupation=e["occupations"].str.split("|"))
    return e.explode("country").explode("occupation")


def hn_panel(ads: pd.DataFrame, ad_skills: pd.DataFrame, current: pd.Period) -> tuple[pd.DataFrame, pd.DataFrame]:
    e = _explode(ads[ads["source"] == "hn_whoishiring"])
    totals = e.groupby(["month", "country", "occupation"])["ad_id"].nunique().rename("n_ads").reset_index()
    totals["is_partial"] = pd.PeriodIndex(totals["month"], freq="M") >= current
    j = e[["ad_id", "month", "country", "occupation"]].merge(ad_skills, on="ad_id")
    counts = j.groupby(["month", "country", "occupation", "skill_id"])["ad_id"].nunique().rename("n_ads_skill").reset_index()
    return totals, counts


def adzuna_snapshots(ads: pd.DataFrame, ad_skills: pd.DataFrame) -> pd.DataFrame:
    e = _explode(ads[ads["source"] == "adzuna"])
    if e.empty:
        return pd.DataFrame(columns=["retrieved_at", "country", "occupation", "skill_id", "n_ads", "n_ads_skill", "share"])
    tot = e.groupby(["retrieved_at", "country", "occupation"])["ad_id"].nunique().rename("n_ads").reset_index()
    j = e[["ad_id", "retrieved_at", "country", "occupation"]].merge(ad_skills, on="ad_id")
    cnt = j.groupby(["retrieved_at", "country", "occupation", "skill_id"])["ad_id"].nunique().rename("n_ads_skill").reset_index()
    out = cnt.merge(tot, on=["retrieved_at", "country", "occupation"])
    out["share"] = out["n_ads_skill"] / out["n_ads"]
    return out


def coverage(ads: pd.DataFrame) -> pd.DataFrame:
    """Per source x month: ads seen, eligible, classified into a tracked occupation, with a country, multi-occupation."""
    g = ads.assign(classified=ads["occupations"].ne(""), located=ads["countries"].ne(""),
                   multi=ads["occupations"].str.contains(r"\|"))
    return g.groupby(["source", "month"]).agg(
        ads=("ad_id", "size"), duplicates=("is_duplicate", "sum"), eligible=("eligible", "sum"),
        classified=("classified", lambda s: int((s & g.loc[s.index, "eligible"]).sum())),
        classified_with_country=("located", lambda s: int((s & g.loc[s.index, "eligible"] & g.loc[s.index, "classified"]).sum())),
        multi_occupation=("multi", lambda s: int((s & g.loc[s.index, "eligible"]).sum()))).reset_index()
