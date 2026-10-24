"""External candidate predictors for the capability engine. Each is tested before use (capability_engine) and
enters the forecast only if it improves the selection-period backtest; none is assumed to help.

Tested (monthly; the value for month m uses only models released in or before m):
  lab_releases_3m     language models from frontier labs released in the previous 3 months (Epoch AI models data)
  compute_growth_12m  change in log10 of the largest training compute among models released so far, over 12 months

Point in time: release dates are public at release, but Epoch's models file exists only as today's copy, and
compute figures are estimated after release. Both features are therefore *approximately* point-in-time (flagged).

Inventoried, not testable here (`benchmark_coverage`): SWE-bench Verified, LiveBench, Terminal-Bench and Aider
Polyglot from Epoch's benchmark archive copies. They start between Feb 2024 and Jun 2025 and appear in Epoch's
files only from 2025-2026, so they barely overlap the selection period; validating them would need the holdout,
which never chooses anything.

Raw  data/raw/epoch_models/<UTC timestamp>_all_ai_models.csv  (a dated copy per change; a hand-placed
     all_ai_models.csv is also read). No file -> no features, and the engine runs without them.
"""
from __future__ import annotations

import hashlib
import io
import zipfile

import numpy as np
import pandas as pd

from . import capability
from .vintages import ROOT

RAW = ROOT / "data" / "raw" / "epoch_models"
URL = "https://epoch.ai/data/all_ai_models.csv"
LABS = ("OpenAI", "Anthropic", "Google", "DeepMind", "xAI", "Meta", "DeepSeek", "Alibaba", "Moonshot", "Mistral")
FEATURES = ("lab_releases_3m", "compute_growth_12m")
BENCHMARKS = {"swe_bench_verified.csv": "SWE-bench Verified", "live_bench_external.csv": "LiveBench",
              "terminalbench_external.csv": "Terminal-Bench", "aider_polyglot_external.csv": "Aider Polyglot"}


def pull() -> None:
    """Store today's Epoch models file if it changed. A failure keeps the stored copies."""
    try:
        body = capability._get(URL, timeout=120)
        pd.read_csv(io.BytesIO(body), nrows=5, usecols=["Model", "Publication date"])  # must be the models table
    except Exception as e:  # noqa: BLE001 (network or format: keep what is stored)
        print(f"warning: Epoch models file not downloaded ({e})")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    old = sorted(RAW.glob("*_all_ai_models.csv"))
    if old and hashlib.sha256(old[-1].read_bytes()).digest() == hashlib.sha256(body).digest():
        return
    (RAW / f"{pd.Timestamp.now(tz='UTC'):%Y%m%dT%H%M%SZ}_all_ai_models.csv").write_bytes(body)


def load_models() -> tuple[pd.DataFrame, str] | None:
    """Newest stored models file -> (language models with release date and compute, file name), or None."""
    files = sorted(RAW.glob("*_all_ai_models.csv")) + sorted(RAW.glob("all_ai_models.csv"))
    if not files:
        return None
    try:
        m = pd.read_csv(files[-1], low_memory=False,
                        usecols=["Model", "Domain", "Organization", "Publication date", "Training compute (FLOP)"])
    except (ValueError, OSError) as e:
        print(f"warning: {files[-1].name} unreadable ({e}); external features off")
        return None
    m = m.assign(released=pd.to_datetime(m["Publication date"], errors="coerce"),
                 compute=pd.to_numeric(m["Training compute (FLOP)"], errors="coerce"))
    m = m[m["Domain"].astype(str).str.contains("Language") & m["released"].notna()]
    return m, files[-1].name


def monthly_features(models: pd.DataFrame, first: pd.Period, last: pd.Period) -> pd.DataFrame:
    """period -> lab_releases_3m, compute_growth_12m (NaN where undefined)."""
    months = pd.period_range(first, last, freq="M")
    rel = models["released"].dt.to_period("M")
    lab = models["Organization"].astype(str).str.contains("|".join(LABS))
    per_month = rel[lab].value_counts().reindex(months, fill_value=0).sort_index()
    releases_3m = per_month.rolling(3, min_periods=3).sum()
    c = models.dropna(subset=["compute"])
    best = (pd.Series(np.log10(c["compute"].to_numpy()), index=c["released"].dt.to_period("M"))
            .groupby(level=0).max().reindex(pd.period_range(min(first, c["released"].dt.to_period("M").min()), last,
                                                             freq="M")).cummax().ffill())
    growth = (best - best.shift(12)).reindex(months)
    return pd.DataFrame({"lab_releases_3m": releases_3m.to_numpy(), "compute_growth_12m": growth.to_numpy()},
                        index=months)


def benchmark_coverage() -> list[dict]:
    """For each candidate benchmark: when it first appears in Epoch's archive copies, and the release dates it covers."""
    out = []
    snaps = sorted(capability.RAW.glob("*/benchmark_data.zip"))
    for f, name in BENCHMARKS.items():
        first_seen, rows = None, None
        for zp in snaps:
            try:
                z = zipfile.ZipFile(zp)
            except zipfile.BadZipFile:
                continue
            n = [x for x in z.namelist() if x.endswith(f)]
            if n:
                first_seen = first_seen or zp.parent.name[:8]
                rows = pd.read_csv(z.open(n[0]))
        if rows is None:
            out.append({"benchmark": name, "available": False})
            continue
        rd = pd.to_datetime(rows.get("Release date"), errors="coerce")
        out.append({"benchmark": name, "available": True, "first_in_epoch_archive": first_seen, "rows": int(len(rows)),
                    "release_from": str(rd.min())[:10], "release_to": str(rd.max())[:10]})
    return out
