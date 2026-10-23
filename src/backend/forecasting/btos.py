"""Census BTOS AI questions as point-in-time observations, for target btos_ai_use_rate (business adoption).

Two questions, kept as separate measures and never mixed:
  Q7   current_use    did the business use AI in the last two weeks
  Q24  expected_use   does it expect to use AI in the next six months
Two wordings, kept as separate series (a structural break, never joined):
  old  "AI in producing goods or services"        AI Core Questions.xlsx, fortnights 202319-202520
  new  "SI/AI in any of its business functions"   Sector.xlsx / National.xlsx, from 202524
  Fortnights 202521-202523 were not asked; Census marks them "." (status not_asked, not missing, not 0).

Point in time: each fortnight's estimate is available from its Census publication date (the "Collection and
Reference Dates" sheet). BTOS estimates are treated as unrevised once published; that is an assumption, checked
from now on by keeping every download (raw/btos/snapshots/<date>/, with its SHA-256) and comparing on each build.

Raw    data/raw/btos/*.xlsx, plus dated copies in data/raw/btos/snapshots/
Output data/processed/forecasting/btos_ai_observations.csv  (columns in data/documentation/STRUCTURE.md section 10)
       data/processed/forecasting/btos_calendar.csv          fortnight numbering and dates, incl. scheduled ones

Usage:
    python -m forecasting.btos            # download the current files (keeps a dated copy), rebuild
    python -m forecasting.btos --no-pull  # rebuild from data/raw/btos
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from .vintages import OUT, ROOT

RAW = ROOT / "data" / "raw" / "btos"
BASE = "https://www.census.gov/hfp/btos/downloads/"
FILES = {"new_sector": "Sector.xlsx", "new_national": "National.xlsx", "old": "AI Core Questions.xlsx"}
QUESTIONS = {7: "current_use", 24: "expected_use"}
SECTORS = ["11", "21", "22", "23", "31", "42", "44", "48", "51", "52", "53", "54", "55", "56", "61", "62", "71",
           "72", "81"]  # NAICS sectors; "XX" (multi-sector companies) is left out
COLUMNS = ["measure", "question_id", "wording", "question", "unit", "smpdt", "period", "ref_start", "ref_end",
           "published_at", "estimate_pct", "se_pct", "status", "source_file", "file_sha256"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pull() -> None:
    """Download the three files. A dated copy is kept; a failed download keeps the previous files."""
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    snap = RAW / "snapshots" / stamp
    snap.mkdir(parents=True, exist_ok=True)
    for name in FILES.values():
        url = BASE + urllib.parse.quote(name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sdc-hackathon-2026 pipeline)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            (snap / name).write_bytes(body)
            tmp = RAW / f".{name}.tmp"
            tmp.write_bytes(body)
            tmp.replace(RAW / name)
        except OSError as e:
            print(f"warning: could not download {name} ({e}); keeping the previous file")


def snapshot_existing() -> None:
    """Keep a dated copy of files downloaded before snapshots existed (dated by their modification time)."""
    for name in FILES.values():
        f = RAW / name
        if not f.exists():
            continue
        stamp = pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC").strftime("%Y-%m-%d")
        dst = RAW / "snapshots" / stamp / name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)


def parse_pct(v) -> tuple[float | None, str]:
    """Census cell -> (percent, status). "S" suppressed, "." not asked, blank missing; never 0 for any of them."""
    if pd.isna(v):
        return None, "missing"
    s = str(v).strip()
    if s == "S":
        return None, "suppressed"
    if s == ".":
        return None, "not_asked"
    try:
        return float(s.rstrip("%")), "ok"
    except ValueError:
        return None, "unparseable"


def calendar() -> pd.DataFrame:
    """Census's fortnight calendar (past and scheduled): smpdt -> period number, reference dates, publication date.

    Periods are numbered in calendar order over the whole schedule, so a forecast's target fortnight has a number
    and dates even before it is published."""
    d = pd.read_excel(RAW / FILES["new_national"], sheet_name="Collection and Reference Dates")
    d = d[pd.to_numeric(d["Smpdt"], errors="coerce").notna()]  # fortnights not published (202521-23) stay in
    d = d.assign(smpdt=d["Smpdt"].astype(int).astype(str)).sort_values("smpdt").reset_index(drop=True)
    d["period"] = d.index
    return d.rename(columns={"Reference Period Start": "ref_start", "Ref End": "ref_end",
                             "Publication Date": "published_at"})[["smpdt", "period", "ref_start", "ref_end",
                                                                   "published_at"]]


def _long(est: pd.DataFrame, se: pd.DataFrame, unit_col: str | None, wording: str, source: str, digest: str):
    rows = []
    periods = [c for c in est.columns if str(c).isdigit()]
    est = est[est["Question ID"].isin(QUESTIONS) & (est["Answer"] == "Yes")]
    se = se[se["Question ID"].isin(QUESTIONS) & (se["Answer"] == "Yes")]
    key = ["Question ID"] + ([unit_col] if unit_col else [])
    se = se.set_index(key)
    for _, r in est.iterrows():
        unit = "US" if unit_col is None else str(r[unit_col]).split(".")[0]
        if unit_col and unit not in SECTORS:
            continue
        srow = se.loc[tuple(r[k] for k in key)] if len(key) > 1 else se.loc[r["Question ID"]]
        for p in periods:
            v, status = parse_pct(r[p])
            s_v, _ = parse_pct(srow[p])
            rows.append({"measure": QUESTIONS[int(r["Question ID"])], "question_id": int(r["Question ID"]),
                         "wording": wording, "question": r["Question"], "unit": unit, "smpdt": str(p),
                         "estimate_pct": v, "se_pct": s_v, "status": status, "source_file": source,
                         "file_sha256": digest})
    return rows


def build() -> pd.DataFrame:
    rows = []
    for key, sheet_est, sheet_se, unit_col, wording in [
        ("old", "National Estimates", "National SE", None, "old"),
        ("old", "Sector Estimates", "Sector SE", "Sector", "old"),
        ("new_national", "Response Estimates", "Response Standard Errors", None, "new"),
        ("new_sector", "Response Estimates", "Response Standard Errors", "Sector", "new"),
    ]:
        f = RAW / FILES[key]
        est, se = pd.read_excel(f, sheet_name=sheet_est), pd.read_excel(f, sheet_name=sheet_se)
        rows += _long(est, se, unit_col, wording, FILES[key], sha256(f))
    d = pd.DataFrame(rows)
    # The current files also list the old-wording fortnights, all ".": those rows say nothing, drop them.
    d = d[~((d["wording"] == "new") & (d["smpdt"] <= "202520") & (d["status"] == "not_asked"))]
    cal = calendar()
    d = d.merge(cal, on="smpdt", how="left")
    return d[COLUMNS].sort_values(["measure", "wording", "unit", "smpdt"]).reset_index(drop=True)


def validate(d: pd.DataFrame) -> None:
    if d.duplicated(["measure", "wording", "unit", "smpdt"]).any():
        raise ValueError("duplicate BTOS observations")
    ok = d[d["status"] == "ok"]
    if not ok["estimate_pct"].between(0, 100).all():
        raise ValueError("BTOS estimate outside 0-100")
    if ok["published_at"].isna().any():
        raise ValueError("BTOS estimates without a publication date")
    both = d[d["status"] == "ok"].groupby(["measure", "unit", "smpdt"])["wording"].nunique()
    if (both > 1).any():
        raise ValueError("a fortnight has estimates under both wordings: the break is not where expected")


def load_calendar() -> pd.DataFrame:
    return pd.read_csv(OUT / "btos_calendar.csv", dtype={"smpdt": str}, parse_dates=["ref_start", "ref_end", "published_at"])


def load() -> pd.DataFrame:
    d = pd.read_csv(OUT / "btos_ai_observations.csv", dtype={"unit": str, "smpdt": str})
    for c in ("ref_start", "ref_end", "published_at"):
        d[c] = pd.to_datetime(d[c])
    # A release is counted as available at the end of its publication day, US Eastern (UTC-4/5): +1 day in UTC.
    d["available_at"] = (d["published_at"] + pd.Timedelta(days=1)).dt.tz_localize("UTC")
    return d


def ingest(pull_first: bool) -> None:
    snapshot_existing()
    if pull_first:
        pull()
    d = build()
    validate(d)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in (("btos_ai_observations.csv", d), ("btos_calendar.csv", calendar())):
        tmp = OUT / f".{name}.tmp"
        df.to_csv(tmp, index=False)
        tmp.replace(OUT / name)
    ok = d[d["status"] == "ok"]
    print(f"btos: {len(d):,} rows, {len(ok):,} estimates; status counts {d['status'].value_counts().to_dict()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ingest(not ap.parse_args().no_pull)


if __name__ == "__main__":
    main()
