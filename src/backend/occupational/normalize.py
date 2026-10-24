"""Raw ads -> one normalised row per ad: occupation(s), country(ies), duplicate flag, eligibility, and the known skills
it names.

Definitions (applied the same way everywhere):
  duplicate   HN: a second post by the same author in the same thread, or the same opening text (first 300
              letters/digits) in the same month. Adzuna: the same ad id in several snapshots (first sighting kept),
              or the same title + employer + location in one snapshot. A repost in a later month is a new ad.
  eligible    not a duplicate, and has a description (HN >= 150 characters; Adzuna snippet >= 60).
  occupation  title patterns in occupations.json (multi-label: one HN post can hire for several occupations).
  country     HN: location patterns in geo.json on the post's first line (multi-label; none = unspecified).
              Adzuna: the country site searched.
The skill-demand denominator for (month, country, occupation) is the number of eligible ads with that country and
occupation; demand.py uses exactly this.
"""
from __future__ import annotations

import re

import pandas as pd

from . import store, taxonomy as T

MIN_TEXT = {"hn_whoishiring": 150, "adzuna": 60}


def _fingerprint(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())[:300]


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw
    d = raw.copy()
    d["ad_id"] = d["source"] + ":" + d["source_id"].astype(str)
    d["text"] = d["text"].fillna("")
    d["text_len"] = d["text"].str.len()
    hn = d["source"] == "hn_whoishiring"
    body = d["text"].where(hn, "").str.split("\n", n=1).str[1].fillna("")
    d["occupations"] = [
        "|".join(T.occupations_in(h, b)) for h, b in zip(d["title_raw"].fillna(""), body)]
    hint = d["country_hint"] if "country_hint" in d else pd.Series("", index=d.index)
    d["countries"] = [
        (c if c in T.countries() else "") if not is_hn else "|".join(T.countries_in(loc))
        for c, loc, is_hn in zip(hint.fillna(""), d["location_raw"].fillna(""), hn)]

    d = d.sort_values(["source", "posted_at", "source_id"]).reset_index(drop=True)
    dup = pd.Series(False, index=d.index)
    h = d[hn]
    dup[h.index] = h.duplicated(["thread_id", "author"]) & (h["author"] != "")
    fp = d["text"].map(_fingerprint)
    dup |= hn & fp.ne("") & pd.concat([d["month"], fp], axis=1).duplicated()
    az = d["source"] == "adzuna"
    a = d[az]
    dup[a.index] |= a.duplicated(["retrieved_at", "title_raw", "employer", "location_raw"])
    d["is_duplicate"] = dup
    min_len = d["source"].map(MIN_TEXT).fillna(100)
    d["eligible"] = ~dup & (d["text_len"] >= min_len)
    d["ineligible_reason"] = ""
    d.loc[d["text_len"] < min_len, "ineligible_reason"] = "missing or short description"
    d.loc[dup, "ineligible_reason"] = "duplicate"
    d["available_at"] = d.apply(_available_at, axis=1)
    # distinct-employer counts: the company name, or the HN poster when the post names none
    d["employer_key"] = d["employer"].fillna("").str.lower().str.strip()
    d.loc[d["employer_key"] == "", "employer_key"] = "author:" + d["author"].fillna("").astype(str)
    return d


def _available_at(r) -> str:
    """When an observation could first be used. HN: the month is complete from the 1st of the next month.
    Adzuna: the snapshot's retrieval date."""
    if r["source"] == "hn_whoishiring":
        return str((pd.Period(r["month"], freq="M") + 1).to_timestamp().date())
    return str(r["retrieved_at"])[:10]


def extract_known(ads: pd.DataFrame) -> pd.DataFrame:
    """(ad_id, skill_id) for every curated skill named in an eligible, classified ad.
    Matches are cached per ad (keyed by text length) and reused while curated_skills.csv is unchanged, so a weekly
    run only reads new or edited ads."""
    rel = ads[ads["eligible"] & ads["occupations"].ne("")]
    sig = rel["ad_id"] + "#" + rel["text_len"].astype(str)
    vocab = store.file_hash("taxonomy/curated_skills.csv")
    cache = pd.DataFrame(columns=["sig", "skill_id"])
    if store.exists(CACHE) and store.read_json(CACHE_META, default={"vocab": None}).get("vocab") == vocab:
        cache = store.read_table(CACHE, dtype=str, keep_default_na=False)
    done = set(cache["sig"])
    todo = rel[~sig.isin(done)]
    skills = T.curated()
    new = [(f"{aid}#{n}", sid) for aid, n, text in zip(todo["ad_id"], todo["text_len"], todo["text"])
           for sid in (T.match_skills(text, skills) or [""])]
    cache = pd.concat([cache[cache["sig"].isin(set(sig))], pd.DataFrame(new, columns=["sig", "skill_id"])])
    store.write_table(CACHE, cache)
    store.write_json(CACHE_META, {"vocab": vocab})
    hit = cache[cache["skill_id"] != ""]
    return pd.DataFrame({"ad_id": hit["sig"].str.rsplit("#", n=1).str[0], "skill_id": hit["skill_id"]}).reset_index(drop=True)


CACHE, CACHE_META = "normalized/known_skill_cache.csv.gz", "normalized/known_skill_cache.json"


META_COLS = ["ad_id", "source", "source_id", "thread_id", "month", "posted_at", "retrieved_at", "available_at",
             "employer", "employer_key", "title_raw", "countries", "occupations", "text_len", "is_duplicate", "eligible",
             "ineligible_reason", "url"]
