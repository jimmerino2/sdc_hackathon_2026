"""Time horizons at other success rates (not just 50%), from METR's raw results.

METR's headline number is the task length (in a skilled person's working time) a model completes 50% of the time.
It comes from a curve: for each model, the chance of success falls as tasks get longer. METR fits
    P(success) = logistic(a + b * log2(human minutes))
to every attempt, weighting each task by 1/sqrt(attempts on it). Fitting the same curve here reproduces the
official 50% and 80% horizons exactly (checked: Claude Opus 4.6 718.8 / 69.9 min, GPT-5.2 352.2 / 66.0), so the
curve can be read at any other success rate.

Source: METR/eval-analysis-public, reports/time-horizon-1-1/data/raw/runs.jsonl (current suite, v1.1), cloned
into data/raw/vintages/metr_full (blobs of the data files only). Models METR has not released raw runs for get
only the official 50% / 80% numbers from Epoch's file.

Output data/processed/forecasting/metr_success_curves.csv  one row per model (columns in STRUCTURE.md section 13)
       data/processed/forecasting/metr_success_bins.csv    observed success rate per model and task-length bin

Usage:
    python -m forecasting.success_curves            # git fetch METR's repo, rebuild
    python -m forecasting.success_curves --no-pull
Display only: these are the current curves, not a forecast, and are not used by any model.
"""
from __future__ import annotations

import argparse
import io
import subprocess

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from . import capability
from .vintages import OUT, RAW, git

REPO = RAW / "metr_full"
URL = "https://github.com/METR/eval-analysis-public.git"
RUNS = "reports/time-horizon-1-1/data/raw/runs.jsonl"
LEVELS = (0.95, 0.9, 0.8, 0.75, 0.5, 0.25, 0.1)
BINS = [0, 1, 4, 15, 60, 240, 960, 1e9]  # human minutes
BIN_LABELS = ["<1 min", "1-4 min", "4-15 min", "15-60 min", "1-4 h", "4-16 h", "16 h+"]


def pull() -> None:
    try:
        if not (REPO / ".git").exists():
            subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", URL, str(REPO)], check=True)
        git(REPO, "fetch", "--quiet", "origin")
        git(REPO, "reset", "--soft", "origin/HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: could not update METR's repo ({e}); using the local copy")


def runs() -> tuple[pd.DataFrame, str]:
    sha = git(REPO, "rev-parse", "HEAD").strip()
    d = pd.read_json(io.StringIO(git(REPO, "show", f"HEAD:{RUNS}")), lines=True)
    return d[d["alias"] != "human"], sha[:12]


def fit(g: pd.DataFrame) -> tuple[float, float]:
    """(a, b) of P(success) = logistic(a + b * log2(human minutes)), METR's task weighting, no regularisation."""
    X = np.log2(g["human_minutes"].to_numpy())[:, None]
    m = LogisticRegression(C=1e6, max_iter=1000).fit(X, g["score_binarized"].to_numpy(),
                                                     sample_weight=g["invsqrt_task_weight"].to_numpy())
    return float(m.intercept_[0]), float(m.coef_[0][0])


def horizon(a: float, b: float, p: float) -> float:
    """Task length (human minutes) completed with probability p."""
    return float(2 ** ((np.log(p / (1 - p)) - a) / b))


def official() -> pd.DataFrame:
    """Latest Epoch vintage: official v1.1 50% and 80% horizons with release dates."""
    d = capability.load()
    d = d[(d["measure"] == "metr_h50_minutes") & (d["metr_version"] == "METR-Horizon-v1.1")]
    d = d[d["vintage_id"] == d["vintage_id"].max()]
    import zipfile
    zp = sorted(capability.RAW.glob("*/benchmark_data.zip"))[-1]
    z = zipfile.ZipFile(zp)
    e = pd.read_csv(z.open([n for n in z.namelist() if "metr" in n.lower() and n.endswith(".csv")][0]))
    e = e[e["METR version"] == "METR-Horizon-v1.1"][["Model version", "Time horizon", "Time Horizon (80%)"]]
    e.columns = ["model", "official_h50", "official_h80"]
    return d[["model", "release_date"]].merge(e, on="model", how="right")


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    d, sha = runs()
    longest = float(d["human_minutes"].max())
    off = official()
    rows, bins = [], []
    for alias, g in d.groupby("alias"):
        a, b = fit(g)
        r = {"model": alias, "source": "fitted from METR raw runs", "n_runs": len(g), "intercept": a, "slope": b,
             "longest_task_minutes": longest, "metr_commit": sha}
        r.update({f"h{int(p * 100)}": horizon(a, b, p) for p in LEVELS})
        # Match to Epoch's name by the official 50% horizon (the fit reproduces it; names differ between files)
        near = off.iloc[(off["official_h50"] - r["h50"]).abs().argsort()[:1]]
        if len(near) and abs(near["official_h50"].iloc[0] / r["h50"] - 1) < 0.005:
            r.update({"epoch_model": near["model"].iloc[0], "release_date": near["release_date"].iloc[0],
                      "official_h50": near["official_h50"].iloc[0], "official_h80": near["official_h80"].iloc[0]})
        rows.append(r)
        g = g.assign(bin=pd.cut(g["human_minutes"], BINS, labels=BIN_LABELS))
        for lab, x in g.groupby("bin", observed=True):
            bins.append({"model": alias, "bin": lab, "median_human_minutes": float(x["human_minutes"].median()),
                         "attempts": len(x), "success_rate": float(np.average(x["score_binarized"],
                                                                              weights=x["invsqrt_task_weight"]))})
    t = pd.DataFrame(rows)
    matched = set(t.get("epoch_model", pd.Series(dtype=str)).dropna())
    extra = off[~off["model"].isin(matched)].assign(source="official 50% / 80% only (no public raw runs)")
    extra = extra.rename(columns={"model": "epoch_model"}).assign(model=lambda x: x["epoch_model"],
                                                                h50=lambda x: x["official_h50"],
                                                                h80=lambda x: x["official_h80"])
    t = pd.concat([t, extra], ignore_index=True).sort_values("h50", ascending=False).reset_index(drop=True)
    return t, pd.DataFrame(bins)


def validate(t: pd.DataFrame) -> None:
    f = t[t["source"].str.startswith("fitted") & t["official_h50"].notna()]
    worst = float(((f["h50"] / f["official_h50"]) - 1).abs().max()) if len(f) else 0.0
    if worst > 0.01:
        raise ValueError(f"fitted 50% horizons differ from METR's official ones by up to {worst:.1%}")
    if not (t.dropna(subset=["h80"])["h80"] <= t.dropna(subset=["h80"])["h50"]).all():
        raise ValueError("an 80% horizon is longer than the 50% one")


def ingest(pull_first: bool) -> None:
    if pull_first:
        pull()
    t, bins = build()
    validate(t)
    for name, df in (("metr_success_curves.csv", t), ("metr_success_bins.csv", bins)):
        tmp = OUT / f".{name}.tmp"
        df.to_csv(tmp, index=False)
        tmp.replace(OUT / name)
    print(f"success curves: {t['source'].str.startswith('fitted').sum()} fitted models, "
          f"{(~t['source'].str.startswith('fitted')).sum()} official-only")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ingest(not ap.parse_args().no_pull)


if __name__ == "__main__":
    main()
