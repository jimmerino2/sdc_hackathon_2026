"""Validate the hand-built crosswalk and write data/processed/crosswalk.csv.

Checks:
  - every sector exists in signals.csv for the chosen geo (Indeed sector names differ by country)
  - weights sum to 1 per role
  - if O*NET Occupation Data is available, every onet_code exists in O*NET
    (titles are replaced with the official O*NET title)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from onet_utils import read_onet_table

OUT_COLS = ["onet_code", "title", "indeed_sector", "weight", "rationale"]


def build(source: Path, signals: Path, geo: str, onet_dir: Path | None) -> pd.DataFrame:
    cw = pd.read_csv(source, dtype={"onet_code": str})
    sig = pd.read_csv(signals, dtype={"sector": str}, keep_default_na=False)
    sectors = set(sig[(sig.series == "job_postings_index") & (sig.geo == geo) & (sig.sector != "")].sector)

    unknown = sorted(set(cw.indeed_sector) - sectors)
    assert not unknown, f"sectors not in Indeed {geo} data: {unknown}"

    sums = cw.groupby("onet_code").weight.sum().round(6)
    bad = sums[sums != 1.0]
    assert bad.empty, f"weights do not sum to 1: {bad.to_dict()}"
    assert not cw.duplicated(["onet_code", "indeed_sector"]).any(), "duplicate role-sector rows"

    if onet_dir is not None:
        occ = read_onet_table(onet_dir, "Occupation Data")
        official = dict(zip(occ["O*NET-SOC Code"], occ["Title"]))
        missing = sorted(set(cw.onet_code) - set(official))
        assert not missing, f"codes not found in O*NET: {missing}"
        cw["title"] = cw["onet_code"].map(official)
        print("O*NET codes verified; titles set to official O*NET titles")
    else:
        print("WARNING: O*NET not available, onet_code values NOT verified")

    print(f"crosswalk: {cw.onet_code.nunique()} roles, {len(cw)} rows, "
          f"{cw.indeed_sector.nunique()} of {len(sectors)} {geo} sectors used")
    return cw[OUT_COLS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="pipeline/crosswalk_source.csv")
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--geo", default="US")
    ap.add_argument("--onet", default="data/raw/onet", help="folder with the unzipped O*NET text database")
    a = ap.parse_args()
    onet = Path(a.onet) if Path(a.onet).exists() else None
    out = build(Path(a.source), Path(a.processed) / "signals.csv", a.geo, onet)
    out.to_csv(Path(a.processed) / "crosswalk.csv", index=False)


if __name__ == "__main__":
    main()
