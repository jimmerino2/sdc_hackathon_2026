"""Build data/processed/btos_ai.csv from the Census Business Trends and Outlook Survey (BTOS).

Usage:
    python pipeline/build_btos_ai.py --raw data/raw/btos --processed data/processed

Inputs (downloaded into --raw if missing; delete the folder to fetch the latest fortnight):
  Sector.xlsx, National.xlsx   current files; question 7 asks whether the business used AI "in any of its
                               business functions" (the wording since Nov 2025; Census now writes "Super
                               Intelligence or SI (formerly referred to as Artificial Intelligence or AI)").
  AI Core Questions.xlsx       the earlier series (Sep 2023 - Oct 2025), when the question asked about AI
                               "in producing goods or services". The level jumps at the change, so the two
                               wordings are kept apart in the `wording` column and must not be joined.

Output, one row per sector x fortnight x wording:
  ai_use_rate     share of businesses that used AI in the last two weeks (question 7, answer Yes), 0-1
  ai_use_se       its standard error
  ai_expect_rate  share expecting to use AI in the next six months (question 24, answer Yes)
Cells Census suppresses ("S") are left blank. sector "US" = all businesses.
"""
from __future__ import annotations

import argparse
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

BASE = "https://www.census.gov/hfp/btos/downloads/"
FILES = {"sector": "Sector.xlsx", "national": "National.xlsx", "old": "AI Core Questions.xlsx"}
USE_Q, EXPECT_Q = "7", "24"
SECTORS = {
    "11": "Agriculture, Forestry, Fishing and Hunting", "21": "Mining, Quarrying, and Oil and Gas Extraction",
    "22": "Utilities", "23": "Construction", "31": "Manufacturing", "42": "Wholesale Trade", "44": "Retail Trade",
    "48": "Transportation and Warehousing", "51": "Information", "52": "Finance and Insurance",
    "53": "Real Estate and Rental and Leasing", "54": "Professional, Scientific, and Technical Services",
    "55": "Management of Companies and Enterprises",
    "56": "Administrative and Support and Waste Management and Remediation Services",
    "61": "Educational Services", "62": "Health Care and Social Assistance",
    "71": "Arts, Entertainment, and Recreation", "72": "Accommodation and Food Services",
    "81": "Other Services (except Public Administration)", "XX": "Multi-unit companies (several sectors)",
    "US": "All businesses",
}
WORDING = {"current": "AI in any business function (since Nov 2025)",
           "old": "AI in producing goods or services (Sep 2023 - Oct 2025)"}
SOURCE = "U.S. Census Bureau, Business Trends and Outlook Survey (BTOS)"
USER_AGENT = "Mozilla/5.0 (sdc-hackathon-2026 data pipeline)"
COLS = ["sector", "sector_name", "period", "ref_start", "ref_end", "wording", "ai_use_rate", "ai_use_se",
        "ai_expect_rate", "source", "as_of_date"]


def fetch(name: str, raw: Path) -> Path:
    path = raw / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = BASE + urllib.parse.quote(name)
        print(f"download {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # census.gov 403s Python's default
        with urllib.request.urlopen(req, timeout=120) as res:
            path.write_bytes(res.read())
    return path


def pct(v) -> float | None:
    """'41.0%' -> 0.41; 'S' (suppressed), '.' (not asked) or blank -> None."""
    s = str(v).strip()
    return float(s.rstrip("%")) / 100 if s.endswith("%") else None


def long_answers(df: pd.DataFrame, key: str, q: str) -> pd.DataFrame:
    """Rows for question q, answer Yes, melted to one row per key x period."""
    yes = df[(df["Question ID"].astype(str) == q) & (df["Answer"].astype(str).str.strip() == "Yes")]
    periods = [c for c in df.columns if str(c).isdigit()]
    out = yes.melt(id_vars=[key], value_vars=periods, var_name="period", value_name="v")
    out["v"] = out["v"].map(pct)
    return out.rename(columns={key: "sector"})


def read_wording(est: pd.DataFrame, se: pd.DataFrame, key: str, wording: str) -> pd.DataFrame:
    use = long_answers(est, key, USE_Q).rename(columns={"v": "ai_use_rate"})
    use_se = long_answers(se, key, USE_Q).rename(columns={"v": "ai_use_se"})
    expect = long_answers(est, key, EXPECT_Q).rename(columns={"v": "ai_expect_rate"})
    out = use.merge(use_se, on=["sector", "period"]).merge(expect, on=["sector", "period"], how="left")
    out["wording"] = wording
    return out


def dates(path: Path, sheet: str) -> pd.DataFrame:
    d = pd.read_excel(path, sheet_name=sheet, dtype=str)
    smp = next(c for c in d.columns if c.lower() == "smpdt")
    start = next(c for c in d.columns if c.lower().startswith("ref") and "start" in c.lower())
    end = next(c for c in d.columns if c.lower().startswith("ref") and "end" in c.lower())
    d = d[[smp, start, end]].dropna().rename(columns={smp: "period", start: "ref_start", end: "ref_end"})
    for c in ("ref_start", "ref_end"):
        d[c] = pd.to_datetime(d[c]).dt.strftime("%Y-%m-%d")
    return d


def build(raw: Path) -> pd.DataFrame:
    p = {k: fetch(v, raw) for k, v in FILES.items()}
    sector = pd.ExcelFile(p["sector"])
    national = pd.ExcelFile(p["national"])
    old = pd.ExcelFile(p["old"])
    nat_cur = pd.read_excel(national, "Response Estimates", dtype=str).assign(sector="US")
    nat_cur_se = pd.read_excel(national, "Response Standard Errors", dtype=str).assign(sector="US")
    frames = [
        read_wording(pd.read_excel(sector, "Response Estimates", dtype=str),
                     pd.read_excel(sector, "Response Standard Errors", dtype=str), "Sector", "current"),
        read_wording(nat_cur, nat_cur_se, "sector", "current"),
        read_wording(pd.read_excel(old, "Sector Estimates", dtype=str),
                     pd.read_excel(old, "Sector SE", dtype=str), "Sector", "old"),
        read_wording(pd.read_excel(old, "National Estimates", dtype=str).assign(sector="US"),
                     pd.read_excel(old, "National SE", dtype=str).assign(sector="US"), "sector", "old"),
    ]
    out = pd.concat(frames, ignore_index=True)
    out = out[out["sector"].isin(SECTORS)]
    # the current files repeat the old periods as "."; keep only periods where the question was asked
    out = out[out[["ai_use_rate", "ai_expect_rate"]].notna().any(axis=1) | (out["wording"] == "old")]
    out = out[~((out["wording"] == "old") & out["ai_use_rate"].isna() & out["ai_expect_rate"].isna())]
    d = pd.concat([dates(p["sector"], "Collection and Reference Dates"),
                   dates(p["old"], "Collection and Reference Dates")]).drop_duplicates("period")
    out = out.merge(d, on="period", how="left")
    assert out["ref_end"].notna().all(), "period without reference dates"
    assert not out.duplicated(["sector", "period", "wording"]).any(), "duplicate rows"
    assert out["ai_use_rate"].dropna().between(0, 1).all()
    for c in ("ai_use_rate", "ai_use_se", "ai_expect_rate"):
        out[c] = out[c].round(4)
    out["sector_name"] = out["sector"].map(SECTORS)
    out["wording"] = out["wording"].map(WORDING)
    out["source"] = SOURCE
    out["as_of_date"] = out["ref_end"].max()
    return out.sort_values(["wording", "sector", "period"])[COLS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/btos")
    ap.add_argument("--processed", default="data/processed")
    a = ap.parse_args()
    out = build(Path(a.raw))
    out.to_csv(Path(a.processed) / "btos_ai.csv", index=False)
    for w, g in out.groupby("wording"):
        print(f"btos_ai [{w}]: {g.sector.nunique()} sectors, {g.period.nunique()} fortnights "
              f"({g.ref_end.min()} to {g.ref_end.max()}), {g.ai_use_rate.isna().sum()} suppressed cells")


if __name__ == "__main__":
    main()
