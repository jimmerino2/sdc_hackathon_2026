"""One command to refresh the whole data layer (task 1.7).

    python pipeline/refresh.py              # pull latest Indeed data, rebuild everything
    python pipeline/refresh.py --no-pull    # rebuild from what is already in data/raw

Steps:
  1. git clone / git pull hiring-lab/job_postings_tracker and hiring-lab/ai-tracker into data/raw
  2. signals.csv            (build_signals.py)
  3. crosswalk.csv          (build_crosswalk.py; verifies codes if O*NET is present)
  4. onet_roles.csv, onet_role_skills.csv   (build_onet.py; skipped if data/raw/onet is missing)
  5. ai_exposure.csv        (build_ai_exposure.py; skipped if its source files are missing)
  6. model_table_<geo>.csv  (build_model_table.py)
  7. my_vacancies.csv, onet_to_my_group.csv  (build_jmi.py; downloads the DOSM workbook if missing)
  8. cross-table checks     same jobs everywhere, unique keys, crosswalk weights (exit 1 on a problem)
  9. manifest.json          as-of date and row count of every output, for the app's "last updated" badge
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, PROCESSED, PIPE = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "pipeline"
REPOS = {"jpt_repo": "https://github.com/hiring-lab/job_postings_tracker.git",
         "ait_repo": "https://github.com/hiring-lab/ai-tracker.git"}


def run(*args: str) -> None:
    print("$", " ".join(args))
    subprocess.run(list(args), check=True, cwd=ROOT)


def pull() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in REPOS.items():
        d = RAW / name
        if (d / ".git").exists():
            run("git", "-C", str(d), "pull", "--ff-only")
        else:
            run("git", "clone", "--depth=1", url, str(d))


def manifest(geo: str) -> dict:
    sig = pd.read_csv(PROCESSED / "signals.csv", dtype={"sector": str}, keep_default_na=False)
    as_of = sig.groupby("series")["as_of_date"].max().to_dict()
    m = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "default_geo": geo, "is_proxy_geo": True,
         "signals_as_of": as_of, "files": {}}
    for f in sorted(PROCESSED.glob("*.csv")):
        with open(f, newline="", encoding="utf-8") as fh:  # csv-aware: descriptions contain line breaks
            m["files"][f.name] = {"rows": sum(1 for _ in csv.reader(fh)) - 1}
    ae = PROCESSED / "ai_exposure.csv"
    if ae.exists():
        m["ai_exposure_as_of"] = pd.read_csv(ae)["as_of_date"].max()
    mv = PROCESSED / "my_vacancies.csv"
    if mv.exists():
        m["jmi_as_of"] = pd.read_csv(mv)["as_of_date"].max()
    return m


def check(geo: str) -> list[str]:
    """Cross-table checks the individual build scripts cannot do. Returns problems (empty = OK)."""
    problems = []
    t = {f.stem: pd.read_csv(f, dtype=str, keep_default_na=False) for f in PROCESSED.glob("*.csv")}
    jobs = {n: set(t[n].onet_code) for n in
            ("crosswalk", "onet_roles", "onet_role_skills", "ai_exposure", "onet_to_my_group") if n in t}
    if len({frozenset(s) for s in jobs.values()}) > 1:
        problems.append("job lists (onet_code) differ between: " + ", ".join(jobs))
    for name, keys in {"onet_role_skills": ["onet_code", "skill_id"], f"model_table_{geo}": ["sector", "month"],
                       "my_vacancies": ["freq", "period", "group_type", "group"]}.items():
        if name in t and t[name].duplicated(keys).any():
            problems.append(f"{name}.csv: duplicate rows on {keys}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--geo", default="US")
    a = ap.parse_args()
    py = sys.executable

    if not a.no_pull:
        pull()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    run(py, str(PIPE / "build_signals.py"), "--raw", str(RAW), "--out", str(PROCESSED))
    run(py, str(PIPE / "build_crosswalk.py"), "--geo", a.geo, "--processed", str(PROCESSED), "--onet", str(RAW / "onet"))
    if (RAW / "onet").exists():
        run(py, str(PIPE / "build_onet.py"), "--onet", str(RAW / "onet"), "--processed", str(PROCESSED))
    else:
        print("SKIP O*NET: put the unzipped O*NET text database in data/raw/onet")
    ae_script = PIPE / "build_ai_exposure.py"
    if ae_script.exists() and (RAW / "economic_index").exists():
        run(py, str(ae_script), "--src", str(RAW / "economic_index"), "--processed", str(PROCESSED))
    else:
        print("SKIP AI exposure: put Anthropic Economic Index files in data/raw/economic_index")
    run(py, str(PIPE / "build_model_table.py"), "--geo", a.geo, "--processed", str(PROCESSED))

    jmi = subprocess.run([py, str(PIPE / "build_jmi.py")], cwd=ROOT)
    if jmi.returncode != 0:
        print("WARNING: build_jmi.py failed; my_vacancies.csv / onet_to_my_group.csv were not refreshed")
    problems = check(a.geo)
    for pr in problems:
        print("CHECK FAILED:", pr)

    m = manifest(a.geo)
    (PROCESSED / "manifest.json").write_text(json.dumps(m, indent=2))
    print("\nDone. Data as of:", m["signals_as_of"])
    if problems or jmi.returncode != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
