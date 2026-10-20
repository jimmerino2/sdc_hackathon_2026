"""Build onet_roles.csv and onet_role_skills.csv from the O*NET 31.0 text database.

Usage:
    python pipeline/build_onet.py --onet data/raw/onet
(--onet is the folder where db_31_0_text.zip was unzipped)

Only roles in pipeline/crosswalk_source.csv are kept.

onet_role_skills.csv rows come from three O*NET files:
  Skills.txt, Knowledge.txt  -> skill_id = O*NET Element ID (e.g. 2.A.1.a)
                                importance = IM scale (1-5), level = LV scale (0-7)
  Software Skills (31.0; "Technology Skills" before)
                             -> skill_id = "tech:<slug>" (e.g. tech:python), skill_type = tech
                                O*NET gives no importance/level for these, so:
                                importance = 4.0 In Demand, 3.5 Hot Technology only, 2.5 neither
                                level = blank
                                Only Hot / In Demand items are kept; a role with none keeps up to 10 others.
  O*NET 31.0 splits Skills into Essential Skills (2.A.*) and Transferable Skills (2.B.*);
  both are written with skill_type = skill.
  NOTE: the "tech:" prefix is an addition to the team ID rule (Element IDs / custom:<slug>),
  because technology skills (Python, Excel...) are in O*NET but have no Element ID.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from onet_utils import read_onet_table

SKILL_COLS = ["onet_code", "skill_id", "skill_name", "skill_type", "importance", "level"]
MAX_UNFLAGGED = 10


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def scaled(onet_dir: Path, name: str, skill_type: str, codes: set[str]) -> pd.DataFrame:
    d = read_onet_table(onet_dir, name)
    d = d[d["O*NET-SOC Code"].isin(codes)].copy()
    # O*NET flags some estimates "Recommend Suppress" (low precision). We keep them anyway:
    # dropping the LV row would leave core skills (e.g. Programming for Software Developers)
    # without a level, so their skills gap could not be computed. Documented in docs/data_sources.md.
    d["Data Value"] = pd.to_numeric(d["Data Value"], errors="coerce")
    keys = ["O*NET-SOC Code", "Element ID", "Element Name"]
    im = d[d["Scale ID"] == "IM"][keys + ["Data Value"]].rename(columns={"Data Value": "importance"})
    lv = d[d["Scale ID"] == "LV"][keys + ["Data Value"]].rename(columns={"Data Value": "level"})
    if "Not Relevant" in d.columns:  # O*NET marks level as not relevant for some rows
        nr = d[(d["Scale ID"] == "LV") & (d["Not Relevant"] == "Y")][keys]
        lv = lv.merge(nr.assign(_nr=True), on=keys, how="left")
        lv.loc[lv["_nr"].eq(True), "level"] = 0.0
        lv = lv.drop(columns="_nr")
    out = im.merge(lv, on=keys, how="left", validate="one_to_one")
    out = out.rename(columns={"O*NET-SOC Code": "onet_code", "Element ID": "skill_id", "Element Name": "skill_name"})
    out["skill_type"] = skill_type
    return out[SKILL_COLS]


def tech(onet_dir: Path, codes: set[str]) -> pd.DataFrame:
    try:  # O*NET 31.0 renamed Technology Skills -> Software Skills, Example -> Workplace Example
        d = read_onet_table(onet_dir, "Software Skills")
    except FileNotFoundError:
        d = read_onet_table(onet_dir, "Technology Skills")
    d = d.rename(columns={"Workplace Example": "Example"})
    d = d[d["O*NET-SOC Code"].isin(codes)].copy()
    hot = d.get("Hot Technology", pd.Series("N", index=d.index)).fillna("N").eq("Y")
    demand = d.get("In Demand", pd.Series("N", index=d.index)).fillna("N").eq("Y")
    d["importance"] = 2.5
    d.loc[hot, "importance"] = 3.5
    d.loc[demand, "importance"] = 4.0
    d["skill_id"] = "tech:" + d["Example"].map(slug)
    out = d.rename(columns={"O*NET-SOC Code": "onet_code", "Example": "skill_name"})
    out["skill_type"], out["level"] = "tech", pd.NA
    # stable, tie-broken sort so reruns are identical (slug() maps C, C# and C++ to the same tech:c id,
    # so which one survives drop_duplicates must not depend on sort order)
    out = out.sort_values(["importance", "skill_name"], ascending=[False, True], kind="stable").drop_duplicates(["onet_code", "skill_id"])
    # Keep only Hot / In Demand software; roles with none flagged keep up to MAX_UNFLAGGED items,
    # so long software lists don't swamp the importance-weighted match score.
    flagged = out[out.importance > 2.5]
    fallback = out[~out.onet_code.isin(flagged.onet_code)].groupby("onet_code").head(MAX_UNFLAGGED)
    return pd.concat([flagged, fallback])[SKILL_COLS]


def build(onet_dir: Path, crosswalk_source: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    codes = set(pd.read_csv(crosswalk_source, dtype=str).onet_code)

    occ = read_onet_table(onet_dir, "Occupation Data")
    occ = occ[occ["O*NET-SOC Code"].isin(codes)]
    missing = sorted(codes - set(occ["O*NET-SOC Code"]))
    assert not missing, f"role codes not in O*NET: {missing}"
    jz = read_onet_table(onet_dir, "Job Zones")[["O*NET-SOC Code", "Job Zone"]]
    roles = occ.merge(jz, on="O*NET-SOC Code", how="left", validate="one_to_one")
    roles = roles.rename(columns={"O*NET-SOC Code": "onet_code", "Title": "title",
                                  "Job Zone": "job_zone", "Description": "description"})
    roles = roles[["onet_code", "title", "job_zone", "description"]].sort_values("onet_code")
    no_jz = roles[roles.job_zone.isna()].onet_code.tolist()
    if no_jz:
        print(f"WARNING: no job zone for {no_jz}")

    try:  # O*NET 31.0 split Skills into Essential (2.A.*) and Transferable (2.B.*)
        skill_parts = [scaled(onet_dir, "Essential Skills", "skill", codes),
                       scaled(onet_dir, "Transferable Skills", "skill", codes)]
    except FileNotFoundError:
        skill_parts = [scaled(onet_dir, "Skills", "skill", codes)]
    skills = pd.concat(skill_parts + [scaled(onet_dir, "Knowledge", "knowledge", codes),
                        tech(onet_dir, codes)], ignore_index=True)
    skills["importance"] = skills["importance"].round(2)
    skills["level"] = pd.to_numeric(skills["level"], errors="coerce").round(2)
    assert not skills.duplicated(["onet_code", "skill_id"]).any(), "duplicate role-skill rows"
    no_skills = sorted(codes - set(skills.onet_code))
    if no_skills:
        print(f"WARNING: no skill rows for {no_skills}")
    print(f"onet_roles: {len(roles)} roles; onet_role_skills: {len(skills):,} rows "
          f"({skills.groupby('skill_type').size().to_dict()})")
    return roles, skills.sort_values(["onet_code", "skill_type", "importance"], ascending=[True, True, False])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onet", default="data/raw/onet")
    ap.add_argument("--crosswalk", default="pipeline/crosswalk_source.csv")
    ap.add_argument("--processed", default="data/processed")
    a = ap.parse_args()
    roles, skills = build(Path(a.onet), Path(a.crosswalk))
    roles.to_csv(Path(a.processed) / "onet_roles.csv", index=False)
    skills.to_csv(Path(a.processed) / "onet_role_skills.csv", index=False)


if __name__ == "__main__":
    main()
