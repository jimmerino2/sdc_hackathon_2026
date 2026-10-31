"""Pull the newest trend data, rebuild its tables and retrain the role forecasts. POST /forecast/sync runs this.

    python pipeline/sync_trends.py                         # pull, rebuild, retrain (about 10 seconds)
    python pipeline/sync_trends.py --no-pull               # rebuild from what is already in data/raw
    python pipeline/sync_trends.py --no-pull --until 2026-06   # rewind: keep the data up to that month only

Covers the Indeed postings and AI tracker data, which drive the role forecasts and the outlook part of match scores.
Then worker adoption and business adoption are forecast again, side by side, if their tables in
data/processed/forecasting changed since the last run (about 2.5 minutes; nothing is fetched for them). AI capability
and skill trends (occupational.run) stay offline jobs.

Everything is built in a temporary folder and copied in only when every step worked, so a failed run leaves the current
data as it was. If the pull fails, the last copy in data/raw is used and the result says so.

To change a figure by hand, edit its value in data/processed/signals.csv and run this. A change since the last sync is
kept: nothing is pulled and the forecasts are retrained on the edited file. The next run pulls again, which puts the
source's value back. The copy to compare with is data/raw/signals_last_sync.csv, so run this once before editing.

The last line printed is a JSON summary.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import refresh

ROOT, RAW, PROCESSED, PIPE = refresh.ROOT, refresh.RAW, refresh.PROCESSED, refresh.PIPE
ML = ROOT / "src" / "backend" / "ml"
OUTPUT = ML / "output"
SNAPSHOT = RAW / "signals_last_sync.csv"  # signals.csv as the last run left it, to spot a hand edit
KEYS = ["series", "geo", "sector", "month"]
PULL_TIMEOUT = 45  # seconds per repo; a stalled network must not hold the button for long
SERIES = "job_postings_index"
GEO = "US"
BACKEND = ROOT / "src" / "backend"
AI_TABLES = PROCESSED / "forecasting"
AI_STATE = RAW / "ai_tables_last_sync.json"  # a hash of each target's tables at its last forecast, to spot a change
AI_TIMEOUT = 300  # seconds per target
AI_TARGETS = {  # forecasting.run target -> (name on the page, the tables it reads)
    "worker_genai_use_rate": ("Worker adoption", ["rps_observations.csv"]),
    "btos_ai_use_rate": ("Business adoption", ["btos_ai_observations.csv"]),
}


def pulled() -> str | None:
    """Pull both repos. Returns what went wrong, or None. Only a missing data/raw is fatal: the last copy still builds."""
    try:
        refresh.pull(timeout=PULL_TIMEOUT)
        return None
    except (subprocess.SubprocessError, OSError) as e:
        if all((RAW / name / ".git").exists() for name in refresh.REPOS):
            return f"{type(e).__name__}: using the last copy in data/raw"
        raise


def read_signals(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"sector": str}, keep_default_na=False)


def hand_edits(current: pd.DataFrame) -> int:
    """How many records of signals.csv differ from the last run's. Stops on a repeated record: there must be one per month."""
    twice = current[current.duplicated(KEYS)]
    if len(twice):
        r = twice.iloc[0]
        sys.exit(f"signals.csv: {r['sector'] or r['series']} {r['month']} ({r['geo']}) is there twice. Change the value in the existing row instead of adding one.")
    if not SNAPSHOT.exists():
        return 0
    both = current[[*KEYS, "value"]].merge(read_signals(SNAPSHOT)[[*KEYS, "value"]], on=KEYS, how="outer", suffixes=("", "_last"))
    now, last = (pd.to_numeric(both[c], errors="coerce").fillna(-1e18).round(6) for c in ("value", "value_last"))
    return int((now != last).sum())


def rewind(signals: pd.DataFrame, until: str) -> pd.DataFrame:
    """The table as if nothing after this month had been published yet."""
    year, month = map(int, until.split("-"))
    last_day = f"{until}-{calendar.monthrange(year, month)[1]:02d}"
    kept = signals[signals["month"] <= until].copy()
    kept["as_of_date"] = kept["as_of_date"].where(kept["as_of_date"] <= last_day, last_day)
    return kept


def state(signals: Path, jobs: Path) -> dict:
    """The dates a person can see change."""
    as_of = pd.read_csv(signals, usecols=["series", "as_of_date"]).groupby("series")["as_of_date"].max()
    return {"as_of": as_of.get(SERIES), "forecast_from": str(pd.read_csv(jobs, usecols=["forecast_from"])["forecast_from"].iloc[0])}


def write_manifest(work: Path, signals: pd.DataFrame) -> None:
    """Update the manifest in the work folder: training reads its dates, and the app shows them."""
    path = work / "manifest.json"
    m = json.loads(path.read_text()) if path.exists() else {}
    m["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    m["signals_as_of"] = signals.groupby("series")["as_of_date"].max().to_dict()
    m.setdefault("files", {})["signals.csv"] = {"rows": len(signals)}
    path.write_text(json.dumps(m, indent=2))


def build(work: Path, until: str | None, keep_signals: bool) -> None:
    """Rebuild and retrain inside the work folder. keep_signals uses signals.csv as it is instead of rebuilding it."""
    py = sys.executable
    shutil.copytree(PROCESSED, work, ignore=shutil.ignore_patterns("forecasting"), dirs_exist_ok=True)
    if not keep_signals:
        refresh.run(py, str(PIPE / "build_signals.py"), "--raw", str(RAW), "--out", str(work))
    signals = read_signals(work / "signals.csv")
    if until:
        signals = rewind(signals, until)
    signals.to_csv(work / "signals.csv", index=False)
    write_manifest(work, signals)
    refresh.run(py, str(PIPE / "build_model_table.py"), "--geo", GEO, "--processed", str(work))
    refresh.run(py, str(ML / "train_lgbm.py"), "--data", str(work / f"model_table_{GEO}.csv"), "--out-dir", str(work / "output"))


def install(work: Path) -> None:
    """Copy the finished files into place. Reached only when every step worked."""
    for name in ("signals.csv", f"model_table_{GEO}.csv", "manifest.json"):
        shutil.copy2(work / name, PROCESSED / name)
    for f in (work / "output").iterdir():
        shutil.copy2(f, OUTPUT / f.name)
    RAW.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / "signals.csv", SNAPSHOT)


def fingerprint(target: str) -> str:
    h = hashlib.sha256()
    for name in AI_TARGETS[target][1]:
        h.update((AI_TABLES / name).read_bytes())
    return h.hexdigest()


def read_ai_state() -> dict:
    return json.loads(AI_STATE.read_text()) if AI_STATE.exists() else {}


def reforecast(target: str) -> dict:
    """Run one AI target on its tables as they are. A failure or a stale source leaves its current forecast being served."""
    done = {"target": target, "name": AI_TARGETS[target][0]}
    try:
        p = subprocess.run([sys.executable, "-m", "forecasting.run", "--target", target, "--skip-ingest"], cwd=BACKEND,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=AI_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {**done, "status": "failed"}
    if p.returncode != 0:
        print(p.stderr[-2000:], file=sys.stderr)
        return {**done, "status": "failed"}
    return {**done, "status": "stale" if "target source is stale" in p.stdout else "updated"}


def reforecast_changed() -> list[dict]:
    """Forecast every AI target whose tables changed, side by side: each writes only to its own folder."""
    seen = read_ai_state()
    changed = [t for t in AI_TARGETS if seen.get(t) != fingerprint(t)]
    if not changed:
        return []
    marks = {t: fingerprint(t) for t in changed}  # before the run: a later edit must still count as a change
    with ThreadPoolExecutor(max_workers=len(changed)) as pool:
        results = list(pool.map(reforecast, changed))
    seen.update({r["target"]: marks[r["target"]] for r in results if r["status"] == "updated"})
    RAW.mkdir(parents=True, exist_ok=True)
    AI_STATE.write_text(json.dumps(seen, indent=2))
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true", help="build from what is already in data/raw")
    ap.add_argument("--until", help="keep the data up to this month only, like 2026-06")
    a = ap.parse_args()

    before = state(PROCESSED / "signals.csv", OUTPUT / "job_forecast.csv")
    edits = hand_edits(read_signals(PROCESSED / "signals.csv"))
    pull = not a.no_pull and not edits
    problem = pulled() if pull else None
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "processed"
        build(work, a.until, keep_signals=bool(edits))
        install(work)
    ai = [] if a.until else reforecast_changed()  # a rewind is about the job postings data only
    after = state(PROCESSED / "signals.csv", OUTPUT / "job_forecast.csv")
    print(json.dumps({"pulled": pull and problem is None, "pull_problem": problem, "manual_edits": edits, "before": before, "after": after, "ai": ai}))


if __name__ == "__main__":
    main()
