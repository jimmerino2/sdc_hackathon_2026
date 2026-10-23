"""Point-in-time store of the Indeed series, built from the git history of the two Hiring Lab repos.

Indeed revises its published history (e.g. AU, Jan 2019 AI share: 2.20% in the Apr 2024 file, 2.31% in the
Oct 2026 file), so a backtest that reads today's file would see revisions the forecaster could not have known.
Every commit that changed a data file is one published vintage; its commit time (UTC) is when it became
available. A forecast made at time T may only use the latest vintage with available_at <= T.

Raw layer   data/raw/vintages/ait_full, jpt_full   partial clones of the repos (blobs of the data files only);
                                                   each vintage is addressed by commit and blob SHA
Output      data/processed/forecasting/ai_share_vintages.csv   every AI-tracker vintage x geo x month
            data/processed/forecasting/postings_vintages.csv   one postings vintage per geo per calendar month
                                                                 (the month's last), x month

Usage:
    python -m forecasting.vintages            # git fetch both repos, rebuild both tables
    python -m forecasting.vintages --no-pull  # rebuild from the local clones only
A failed fetch keeps the local history; a failed build leaves the previous tables in place.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "vintages"
OUT = ROOT / "data" / "processed" / "forecasting"
REPOS = {"ait_full": "https://github.com/hiring-lab/ai-tracker.git",
         "jpt_full": "https://github.com/hiring-lab/job_postings_tracker.git"}
GEOS = ["AU", "CA", "DE", "FR", "GB", "IE", "IT", "NL", "US"]  # the AI tracker's countries
COLUMNS = ["source_id", "vintage_id", "blob_sha", "available_at", "source_file", "schema_version",
           "geo", "month", "value", "numerator", "denominator", "n_days", "is_partial"]

# AI-share file names over the repo's life, preferred first. GenAI_* files are a different measure.
AI_FILES = [re.compile(r"^AI_posting\.csv$"), re.compile(r"^ai-postings\.csv$"),
            re.compile(r"^AI_posting_\d{4}-\d{2}-\d{2}(_clean)?\.csv$")]
# Column names seen in the vintages -> our names. Anything else fails the build (schema change).
AI_COLUMNS = {"date": "date", "modified_date": "date", "jobcountry": "geo",
              "AI_share_postings": "value", "ai_share": "value", "ma_share_perc": "value",
              "% of job postings": "value",
              "AI_count": "numerator", "total": "denominator"}  # counts: only in mid-2024 vintages
# Postings value column per schema -> index (1 Feb 2020 = 100). Before mid-2021 Indeed published % change since
# 1 Feb 2020 (index = 100 + change); the oldest schema does not say whether it is seasonally adjusted, so its
# schema_version is kept and the features treat a schema change as a possible measurement break.
POSTINGS_VALUE = {"indeed_job_postings_index_SA": 0.0, "seasonally_adjusted_pct_chng_feb_1": 100.0,
                  "pct_chng_feb_1": 100.0}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def pull(repo_dir: str) -> None:
    """Fetch new commits (and their data blobs). On failure the existing local history is kept."""
    repo = RAW / repo_dir
    try:
        if not (repo / ".git").exists():
            RAW.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPOS[repo_dir], str(repo)],
                           check=True)
            if repo_dir == "jpt_full":
                git(repo, "sparse-checkout", "set", "--no-cone",
                    "/*/aggregate_job_postings_*.csv", "/aggregate_job_postings_*.csv")
        git(repo, "fetch", "--quiet", "origin")
        git(repo, "reset", "--soft", "origin/HEAD")  # move HEAD only; there is no working tree
        git(repo, "backfill", *(["--sparse"] if repo_dir == "jpt_full" else []))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: could not update {repo_dir} ({e}); building from the local history")


def commits(repo: Path, *paths: str) -> list[tuple[str, pd.Timestamp]]:
    """(sha, commit time UTC) of commits that touched `paths`, oldest first."""
    out = git(repo, "log", "--reverse", "--format=%H %cI", "--", *paths).split()
    return [(out[i], pd.Timestamp(out[i + 1]).tz_convert("UTC")) for i in range(0, len(out), 2)]


def read_blob(repo: Path, sha: str, path: str) -> tuple[str, pd.DataFrame]:
    blob = git(repo, "rev-parse", f"{sha}:{path}").strip()
    return blob, pd.read_csv(io.StringIO(git(repo, "show", f"{sha}:{path}")))


def parse_dates(s: pd.Series, geo: pd.Series | None = None) -> pd.Series:
    """One date format per file. Early files are day-first ("29/3/24"), so "1/2/19" is ambiguous: the
    format chosen is the one under which every value parses and each geo's dates run day by day."""
    for fmt in ("%Y-%m-%d", "%d/%m/%y", "%m/%d/%y"):
        d = pd.to_datetime(s, format=fmt, errors="coerce")
        if d.isna().any():
            continue
        steps = d.groupby(geo.to_numpy() if geo is not None else 0).diff().dropna()
        if steps.eq(pd.Timedelta(days=1)).all():
            return d
    return pd.Series(pd.NaT, index=s.index)


def monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily geo/date/value -> monthly mean, with day counts. A month short of days is flagged partial."""
    d = daily.dropna(subset=["date", "value"]).copy()
    d["month"] = d["date"].dt.to_period("M")
    agg = {"value": ("value", "mean"), "n_days": ("date", "nunique")}
    for c in ("numerator", "denominator"):  # published counts are summed; absent -> blank, never 0
        if c in d.columns:
            agg[c] = (c, "sum")
    g = d.groupby(["geo", "month"], as_index=False).agg(**agg)
    for c in ("numerator", "denominator"):
        g[c] = g[c] if c in g.columns else pd.NA
    g["is_partial"] = g["n_days"] < g["month"].dt.days_in_month
    g["month"] = g["month"].astype(str)
    return g


def ai_file(repo: Path, sha: str) -> str | None:
    names = git(repo, "ls-tree", "--name-only", sha).split("\n")
    for pat in AI_FILES:
        hits = sorted(n for n in names if pat.match(n))
        if hits:
            return hits[-1]  # dated files: the latest date
    return None


def build_ai_share(repo: Path) -> pd.DataFrame:
    parts, seen = [], set()
    paths = ["AI_posting.csv", "ai-postings.csv", "AI_posting_*.csv"]
    for sha, when in commits(repo, *paths):
        path = ai_file(repo, sha)
        if path is None:
            continue
        blob, raw = read_blob(repo, sha, path)
        if blob in seen:  # same content republished: the first availability counts
            continue
        seen.add(blob)
        unknown = set(raw.columns) - set(AI_COLUMNS)
        if unknown:
            raise ValueError(f"ai-tracker {sha[:7]}:{path}: unexpected columns {sorted(unknown)}")
        d = raw.rename(columns=AI_COLUMNS)
        d["date"] = parse_dates(d["date"].astype(str), d["geo"])
        if d["date"].isna().any():
            raise ValueError(f"ai-tracker {sha[:7]}:{path}: unparseable dates")
        m = monthly(d)
        m["schema_version"] = "|".join(raw.columns)
        m["vintage_id"], m["blob_sha"], m["available_at"], m["source_file"] = sha[:12], blob[:12], when, path
        parts.append(m)
    out = pd.concat(parts, ignore_index=True)
    out["source_id"] = "indeed_ai_tracker"
    return out[COLUMNS]


def build_postings(repo: Path) -> pd.DataFrame:
    parts = []
    for geo in GEOS:
        paths = [f"{geo}/aggregate_job_postings_{geo}.csv", f"aggregate_job_postings_{geo}.csv"]
        cs = pd.DataFrame(commits(repo, *paths), columns=["sha", "when"])
        if cs.empty:
            continue
        cs = cs.groupby(cs["when"].dt.strftime("%Y-%m")).tail(1)  # the month's last vintage
        for sha, when in cs.itertuples(index=False):
            names = git(repo, "ls-tree", "-r", "--name-only", sha).split("\n")
            path = next((p for p in paths if p in names), None)
            if path is None:
                continue
            blob, raw = read_blob(repo, sha, path)
            col = next((c for c in POSTINGS_VALUE if c in raw.columns), None)
            if col is None:
                raise ValueError(f"postings {sha[:7]}:{path}: unknown schema {list(raw.columns)}")
            if "variable" in raw.columns:
                raw = raw[raw["variable"] == "total postings"]
            d = pd.DataFrame({"geo": geo, "date": parse_dates(raw["date"].astype(str), raw.get("jobcountry")), "value": raw[col] + POSTINGS_VALUE[col]})
            m = monthly(d)
            m["schema_version"] = "|".join(raw.columns)
            m["vintage_id"], m["blob_sha"], m["available_at"], m["source_file"] = sha[:12], blob[:12], when, path
            parts.append(m)
    out = pd.concat(parts, ignore_index=True)
    out["source_id"] = "indeed_postings"
    return out[COLUMNS]


def validate(df: pd.DataFrame, lo: float, hi: float) -> None:
    """Checks every vintage table must pass before it replaces the previous one."""
    key = ["vintage_id", "geo", "month"]
    if df.duplicated(key).any():
        raise ValueError("duplicate vintage x geo x month rows")
    if df["value"].isna().any() or not df["value"].between(lo, hi).all():
        raise ValueError(f"values missing or outside [{lo}, {hi}]")
    if (df["n_days"] <= 0).any():
        raise ValueError("months with no days")


def write(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f".{name}.tmp"
    df.assign(available_at=df["available_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
              value=df["value"].round(5)).to_csv(tmp, index=False)
    tmp.replace(OUT / name)  # only after the full table was written


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(OUT / name, dtype={"vintage_id": str, "blob_sha": str})
    df["available_at"] = pd.to_datetime(df["available_at"], utc=True)
    return df


def as_of(vintages: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    """Per geo, the rows of the latest vintage published at or before `when`. Empty if none was."""
    v = vintages[vintages["available_at"] <= when]
    if v.empty:
        return v
    latest = v.groupby("geo")["available_at"].transform("max")
    return v[v["available_at"] == latest]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    a = ap.parse_args()
    if not a.no_pull:
        for r in REPOS:
            pull(r)
    ai = build_ai_share(RAW / "ait_full")
    validate(ai, 0, 100)
    po = build_postings(RAW / "jpt_full")
    validate(po, 0, 1000)
    write(ai, "ai_share_vintages.csv")
    write(po, "postings_vintages.csv")
    for name, df in (("ai_share", ai), ("postings", po)):
        print(f"{name}: {df['vintage_id'].nunique()} vintages, {len(df):,} rows, "
              f"{df['available_at'].min():%Y-%m-%d} .. {df['available_at'].max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
