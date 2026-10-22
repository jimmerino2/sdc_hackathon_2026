"""Build data/processed/ai_adoption.csv and ai_adoption_jobs.csv from the Real-Time Population Survey.

Usage:
    python pipeline/build_ai_adoption.py --raw data/raw/rps --processed data/processed

Inputs (downloaded into --raw if missing; delete the folder to fetch a new quarter):
  fred/RPSGENAIUSAGESHARE*.csv  FRED quarterly series: % of employed US adults (18-64) who answer yes to
                                "Do you use Generative AI for your job?", one series per SOC major group
                                (OCC1..OCC22) plus all workers (WORK).
  occupation_index.xlsx         the authors' occupation adoption index: the same question, pooled over the
                                survey waves (Aug 2025 - May 2026), by SOC major / minor / broad occupation,
                                with the number of respondents behind each rate.

Method:
  ai_adoption.csv       the FRED series as they are, rate converted from percent to 0-1. soc_major "00" =
                        all workers. respondents_per_quarter is an estimate (pooled respondents / waves),
                        used by ml/ai_adoption_mc.py to tell sampling noise from real change.
  ai_adoption_jobs.csv  each of our jobs gets the pooled rate of the most detailed SOC level with a
                        published value (broad occupation, else minor group, else major group; the authors
                        blank cells with fewer than 20 respondents). soc_major links the job to its series;
                        group_pooled_rate is that group's rate over the same waves, so ml/ai_adoption_mc.py
                        can move a job with its group's simulated paths on a like-for-like basis.

It measures self-reported use by workers, not exposure or job loss.
"""
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
INDEX_URL = "https://docs.google.com/spreadsheets/d/1_JfNtZVoBi5W_jHEJ1UOs2rhHYRtLXGM/export?format=xlsx"
# FRED series number -> 2018 SOC major group (order of the FRED release; checked against the series titles)
MAJORS = ["11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31",
          "33", "35", "37", "39", "41", "43", "45", "47", "49", "51", "53"]
SERIES = {f"RPSGENAIUSAGESHAREOCC{i}": m for i, m in enumerate(MAJORS, start=1)} | {"RPSGENAIUSAGESHAREWORK": "00"}
WAVES = 4  # survey waves pooled in the occupation index (Aug 2025, Nov 2025, Feb 2026, May 2026)
SOURCE = ("Real-Time Population Survey (Bick, Blandin & Deming), Generative AI Adoption Tracker, "
          "via FRED and the authors' occupation adoption index")
SERIES_COLS = ["soc_major", "soc_major_name", "quarter", "adoption_rate", "respondents_per_quarter",
               "fred_series", "source", "as_of_date"]
JOB_COLS = ["onet_code", "title", "soc_major", "soc_major_name", "adoption_rate", "adoption_level",
            "number_observations", "group_pooled_rate", "source", "as_of_date"]


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"download {url}")
        urllib.request.urlretrieve(url, path)
    return path


def load_series(raw: Path, major: pd.DataFrame) -> pd.DataFrame:
    names = dict(zip(major.soc_code.str[:2], major.soc_name))
    n = dict(zip(major.soc_code.str[:2], major.number_observations / WAVES))
    n["00"] = sum(n.values())
    frames = []
    for sid, code in SERIES.items():
        d = pd.read_csv(fetch(FRED_URL.format(sid), raw / "fred" / f"{sid}.csv"))
        assert list(d.columns) == ["observation_date", sid], f"{sid}: unexpected columns {list(d.columns)}"
        d = d.dropna()
        frames.append(pd.DataFrame({
            "soc_major": code,
            "soc_major_name": names.get(code, "All workers"),
            "quarter": pd.to_datetime(d["observation_date"]).dt.strftime("%Y-%m"),
            "adoption_rate": (d[sid].astype(float) / 100).round(4),
            "respondents_per_quarter": round(n[code]),
            "fred_series": sid,
        }))
    out = pd.concat(frames, ignore_index=True)
    assert out["adoption_rate"].between(0, 1).all()
    assert not out.duplicated(["soc_major", "quarter"]).any(), "duplicate rows"
    assert out.groupby("soc_major")["quarter"].count().nunique() == 1, "series have different lengths"
    return out


def job_rates(index_xlsx: Path, roles_csv: Path, names: dict[str, str]) -> pd.DataFrame:
    sheets = {lvl: pd.read_excel(index_xlsx, sheet_name=s, dtype={"soc_code": str}).set_index("soc_code")
              for lvl, s in (("broad", "SOC Broad Occupation"), ("minor", "SOC Minor Group"), ("major", "SOC Major Group"))}
    roles = pd.read_csv(roles_csv, dtype=str)[["onet_code", "title"]].drop_duplicates("onet_code")
    codes = {"broad": roles.onet_code.str[:6] + "0",  # 15-1252.00 -> 15-1250
             "minor": roles.onet_code.str[:5] + "00",  # -> 15-1200
             "major": roles.onet_code.str[:2] + "-0000"}  # -> 15-0000
    out = roles.copy()
    out["soc_major"] = roles.onet_code.str[:2]
    out["soc_major_name"] = out["soc_major"].map(names)
    out["adoption_rate"], out["adoption_level"], out["number_observations"] = pd.NA, pd.NA, pd.NA
    for lvl in ("major", "minor", "broad"):  # most detailed level with a published rate wins
        rate = codes[lvl].map(sheets[lvl]["adoption_rate"])
        n = codes[lvl].map(sheets[lvl]["number_observations"])
        hit = rate.notna()
        out.loc[hit, "adoption_rate"] = rate[hit].round(4)
        out.loc[hit, "adoption_level"] = lvl
        out.loc[hit, "number_observations"] = n[hit]
    out["number_observations"] = pd.to_numeric(out["number_observations"]).astype("Int64")
    out["group_pooled_rate"] = codes["major"].map(sheets["major"]["adoption_rate"]).round(4)
    missing = out[out.adoption_rate.isna()].onet_code.tolist()
    if missing:
        print(f"WARNING: no adoption rate at any SOC level for {missing}")
    print("ai_adoption_jobs:", out.adoption_level.value_counts(dropna=False).to_dict())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/rps")
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--roles", default="data/processed/onet_roles.csv")
    a = ap.parse_args()
    raw, processed = Path(a.raw), Path(a.processed)

    index_xlsx = fetch(INDEX_URL, raw / "occupation_index.xlsx")
    major = pd.read_excel(index_xlsx, sheet_name="SOC Major Group", dtype={"soc_code": str})
    series = load_series(raw, major)
    as_of = series["quarter"].max()
    series["source"], series["as_of_date"] = SOURCE, as_of
    jobs = job_rates(index_xlsx, Path(a.roles), dict(zip(major.soc_code.str[:2], major.soc_name)))
    jobs["source"], jobs["as_of_date"] = SOURCE, as_of

    series[SERIES_COLS].to_csv(processed / "ai_adoption.csv", index=False)
    jobs[JOB_COLS].to_csv(processed / "ai_adoption_jobs.csv", index=False)
    print(f"ai_adoption: {series.soc_major.nunique()} series x {series.quarter.nunique()} quarters "
          f"({series.quarter.min()} to {as_of}); ai_adoption_jobs: {len(jobs)} jobs")


if __name__ == "__main__":
    main()
