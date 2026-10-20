"""Build data/processed/ai_exposure.csv from the Anthropic Economic Index (task 1.3).

Usage:
    python pipeline/build_ai_exposure.py --src data/raw/economic_index --processed data/processed

Input: the release files aei_claude_ai_<release>.csv and aei_1p_api_<release>.csv (long format:
date_start, date_end, geo_id, geo_level, category_name, hierarchy_level, metric_id, value,
node_name, node_external_id). We use rows with geo_id == GLOBAL and
category_name == soc_occupation, hierarchy_level == 0, where node_external_id is an O*NET-SOC code.

Method (v1, occupation-level):
  usage_share         WORK usage share: metric `pct` (share of conversations mapped to the occupation)
                      x `use_case_work_pct` / 100, so personal and coursework use is excluded;
                      averaged over all months in the release, then over both sources (Claude.ai
                      consumer, 1P API) with equal weight. Missing = 0 (no observed usage).
  exposure (0-1)      percentile rank of usage_share among ALL occupations in the index
                      (not just our roles), so it is comparable across releases.
                      Meaning: "how much of observed Claude usage touches this occupation's tasks",
                      relative to other occupations. It is observed usage, not a forecast of job loss.
  automation_share    collaboration_bucket_automation_pct / 100, averaged over sources weighted by work usage
  augmentation_share  1 - automation_share
  low_sample          usage_share below the 25th percentile of occupations with data: shares are noisy

Outputs:
  ai_exposure.csv         contract columns, our roles only
  ai_exposure_detail.csv  all occupations, all inputs + per-source values + low_sample flag
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

METRICS = ["pct", "collaboration_bucket_automation_pct", "collaboration_bucket_augmentation_pct",
           "use_case_work_pct", "ai_autonomy_mean"]
SOURCES = {"claude_ai": "aei_claude_ai_", "api": "aei_1p_api_"}
CONTRACT = ["onet_code", "title", "exposure", "automation_share", "augmentation_share", "source", "as_of_date"]


def find_release(src: Path) -> tuple[str, dict[str, Path]]:
    files = {}
    for key, prefix in SOURCES.items():
        hits = sorted(src.glob(f"{prefix}*.csv"))
        assert hits, f"no {prefix}*.csv in {src}"
        files[key] = hits[-1]  # latest release by name
    releases = {re.search(r"(\d{4}-\d{2}-\d{2})", p.name).group(1) for p in files.values()}
    assert len(releases) == 1, f"files come from different releases: {releases}"
    return releases.pop(), files


def load_occupations(path: Path) -> pd.DataFrame:
    keep = []
    for ch in pd.read_csv(path, chunksize=1_000_000, dtype=str):
        m = ((ch.geo_id == "GLOBAL") & (ch.category_name == "soc_occupation")
             & (ch.hierarchy_level == "0") & ch.metric_id.isin(METRICS))
        keep.append(ch[m])
    d = pd.concat(keep, ignore_index=True)
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    assert not d.duplicated(["date_start", "node_external_id", "metric_id"]).any(), "duplicate rows"
    # average over months in the release
    w = d.pivot_table(index=["node_external_id", "node_name"], columns="metric_id", values="value", aggfunc="mean")
    months = sorted(d.date_start.unique())
    return w.reset_index().rename(columns={"node_external_id": "onet_code", "node_name": "title"}), months


def build(src: Path, roles_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    release, files = find_release(src)
    per, months = {}, set()
    for key, p in files.items():
        w, m = load_occupations(p)
        months |= set(m)
        per[key] = w.set_index("onet_code")
        print(f"{key}: {len(w)} occupations, months {m}")

    codes = sorted(set().union(*[set(w.index) for w in per.values()]))
    det = pd.DataFrame(index=pd.Index(codes, name="onet_code"))
    det["title"] = pd.concat([w["title"] for w in per.values()]).groupby(level=0).first()
    for key, w in per.items():
        for m in METRICS:
            if m in w:
                det[f"{m}_{key}"] = w[m]
    # WORK usage share: pct x share of those conversations that are work use (drops personal/coursework
    # use, e.g. shopping questions mapped to Retail Salespersons). Equal weight per source, missing = 0.
    for k in per:
        det[f"work_pct_{k}"] = det[f"pct_{k}"].fillna(0) * det[f"use_case_work_pct_{k}"].fillna(0) / 100
    det["usage_share"] = det[[f"work_pct_{k}" for k in per]].mean(axis=1)
    det["exposure"] = det["usage_share"].rank(pct=True, method="average")

    # automation share, weighted by each source's usage share
    num = sum(det[f"work_pct_{k}"] * det[f"collaboration_bucket_automation_pct_{k}"].fillna(0) / 100 for k in per)
    den = sum(det[f"work_pct_{k}"] * det[f"collaboration_bucket_automation_pct_{k}"].notna() for k in per)
    det["automation_share"] = (num / den).where(den > 0)
    det["augmentation_share"] = 1 - det["automation_share"]
    q25 = det.loc[det.usage_share > 0, "usage_share"].quantile(0.25)
    det["low_sample"] = det["usage_share"] < q25
    det = det.reset_index()

    as_of = max(months)  # start of latest month covered
    source = (f"Anthropic Economic Index release {release} (Claude.ai + 1P API, months starting {', '.join(sorted(months))}); "
              "exposure = percentile rank of observed work-usage share among all occupations")

    roles = pd.read_csv(roles_csv, dtype=str)[["onet_code", "title"]].drop_duplicates("onet_code")
    out = roles.merge(det.drop(columns="title"), on="onet_code", how="left")
    no_data = out[out.usage_share.isna()].onet_code.tolist()
    if no_data:
        print(f"WARNING: no usage observed for {no_data}; exposure set to 0")
    out["exposure"] = out["exposure"].fillna(0.0)
    out["source"], out["as_of_date"] = source, release
    for c in ("exposure", "automation_share", "augmentation_share"):
        out[c] = out[c].round(3)
    assert out.exposure.between(0, 1).all()
    low = out[out.low_sample.fillna(True)].onet_code.tolist()
    print(f"ai_exposure: {len(out)} roles; low-sample (shares noisy): {len(low)}")
    det["release"] = release
    return out[CONTRACT], det


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/economic_index")
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--roles", default="data/processed/onet_roles.csv")
    a = ap.parse_args()
    out, det = build(Path(a.src), Path(a.roles))
    out.to_csv(Path(a.processed) / "ai_exposure.csv", index=False)
    det.round(4).to_csv(Path(a.processed) / "ai_exposure_detail.csv", index=False)


if __name__ == "__main__":
    main()
