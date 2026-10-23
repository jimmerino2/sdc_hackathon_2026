"""Run the skill-demand workflow end to end: ingest -> backtest -> select -> holdout -> forecast -> promote.

Usage (from src/backend):
    python -m forecasting.run              # fetch new Indeed vintages, then everything below
    python -m forecasting.run --no-pull    # use the local vintage clones
    python -m forecasting.run --skip-ingest  # use data/processed/forecasting/*_vintages.csv as they are

Outputs in src/backend/forecasting/output/ (nothing is overwritten except the two "current" pointers):
  runs/<run_id>/backtest.csv.gz   every scored prediction: origin, horizon, candidate, feature set, geo, outcome
  runs/<run_id>/evaluation.json   split, selection table, holdout scores, coverage, ablations, health, warnings
  runs/<run_id>/forecast.csv      this run's forecast per country and horizon, with its 10-90% range
  forecast_log.csv                every forecast row ever issued (append only)
  model_registry.json             per horizon: the promoted run and model, plus every attempt and its verdict
  latest_forecast.csv             the forecast of the promoted runs (what the API should serve)
A run that fails acceptance is kept in runs/ and the log, but does not replace the promoted model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import contracts, evaluation as E, features as F, registry, vintages as V
from .models import CANDIDATES

HERE = Path(__file__).parent
OUT = HERE / "output"
TARGET = "ai_mention_share"
CODE_FILES = ["features.py", "models.py", "evaluation.py", "run.py", "contracts.py"]


def model_version() -> str:
    h = hashlib.sha256()
    for f in CODE_FILES:
        h.update((HERE / f).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=HERE).stdout.strip()
    except FileNotFoundError:
        return ""


def feature_sets() -> dict[str, list[str]]:
    sets = {"all": F.ALL_FEATURES}
    for g, cols in F.FEATURE_GROUPS.items():
        sets[f"without_{g}"] = [c for c in F.ALL_FEATURES if c not in cols]
    return sets


def status_for(row: pd.Series) -> str:
    if row["candidate"] == "naive":
        return "baseline"
    if row["holdout_mase_vs_naive"] is not None and row["holdout_mase_vs_naive"] < 1:
        return "validated"
    return "not_demonstrably_better"


def acceptance(sel: pd.DataFrame, health: dict, h: int) -> list[str]:
    """Reasons this run may not be promoted for horizon h (empty = accepted)."""
    c = sel[(sel["h"] == h) & sel["chosen"]].iloc[0]
    fails = []
    if health["indeed_ai_tracker"]["status"] != "fresh":
        fails.append("target source is stale")
    if not c["holdout_n_origins"] or c["holdout_n_origins"] < E.MIN_HOLDOUT:
        fails.append(f"holdout has {c['holdout_n_origins']} origins (< {E.MIN_HOLDOUT})")
    if c["selection_mae_pp"] is None or not np.isfinite(c["selection_mae_pp"]):
        fails.append("selection score missing")
    if c["insufficient_history"]:
        fails.append("insufficient history for selection")
    return fails


def forecast(snap: F.Snapshot, sel: pd.DataFrame, qs: pd.DataFrame, run_id: str, made_at: str,
             health: dict) -> pd.DataFrame:
    rows_now = F.latest_rows(snap)
    out = []
    for h in E.HORIZONS:
        c = sel[(sel["h"] == h) & sel["chosen"]].iloc[0]
        m = CANDIDATES[c["candidate"]]().fit(F.labelled(snap, h), h, F.ALL_FEATURES)
        base = rows_now["lvl"].to_numpy() + m.predict(rows_now)
        lo, hi = qs.loc[(c["candidate"], h)] if (c["candidate"], h) in qs.index else (np.nan, np.nan)
        warnings = []
        if health["indeed_ai_tracker"]["status"] != "fresh":
            warnings.append("stale target data")
        if c["insufficient_history"]:
            warnings.append("insufficient history")
        out.append(pd.DataFrame({
            "run_id": run_id, "made_at": made_at, "target": TARGET, "geo": rows_now["geo"],
            "last_observed_month": str(snap.last_month), "last_observed_pct": 100 * F.expit(rows_now["lvl"]),
            "h": h, "target_month": str(snap.last_month + h), "model": c["candidate"],
            "forecast_pct": 100 * F.expit(base), "low_pct": 100 * F.expit(base + lo), "high_pct": 100 * F.expit(base + hi),
            "interval": "10-90% empirical (out-of-sample logit residuals)", "status": status_for(c),
            "holdout_mae_pp": c["holdout_mae_pp"], "naive_holdout_mae_pp":
                sel[(sel["h"] == h) & (sel["candidate"] == "naive")]["holdout_mae_pp"].iloc[0],
            "ai_vintage": snap.ai_vintage, "data_as_of": snap.origin.isoformat(),
            "warnings": "; ".join(warnings)}))
    return pd.concat(out, ignore_index=True)


def promote(run_id: str, made_at: str, sel: pd.DataFrame, health: dict, fc: pd.DataFrame, version: str) -> dict:
    path = OUT / "model_registry.json"
    reg = json.loads(path.read_text()) if path.exists() else {"target": TARGET, "promoted": {}, "attempts": []}
    for h in E.HORIZONS:
        c = sel[(sel["h"] == h) & sel["chosen"]].iloc[0]
        fails = acceptance(sel, health, h)
        entry = {"run_id": run_id, "made_at": made_at, "h": h, "model": c["candidate"], "model_version": version,
                 "status": status_for(c), "selection_mae_pp": c["selection_mae_pp"],
                 "holdout_mae_pp": c["holdout_mae_pp"], "holdout_mase_vs_naive": c["holdout_mase_vs_naive"],
                 "accepted": not fails, "rejected_because": fails}
        reg["attempts"].append(entry)
        if not fails:
            reg["promoted"][str(h)] = entry
    path.write_text(json.dumps(reg, indent=2, default=float))
    # latest_forecast.csv: per horizon, rows of the promoted run (looked up in the append-only log)
    log = pd.read_csv(OUT / "forecast_log.csv")
    keep = [log[(log["run_id"] == e["run_id"]) & (log["h"] == int(h))] for h, e in reg["promoted"].items()]
    if keep:
        pd.concat(keep).to_csv(OUT / "latest_forecast.csv", index=False)
    return reg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--skip-ingest", action="store_true")
    a = ap.parse_args()

    feats_by_source = {F.GROUP_SOURCE[g] for g in F.FEATURE_GROUPS}
    contracts.check_sources(TARGET, contracts.TARGETS[TARGET].label_source, feats_by_source)

    if not a.skip_ingest:
        if not a.no_pull:
            for r in V.REPOS:
                V.pull(r)
        ai = V.build_ai_share(V.RAW / "ait_full"); V.validate(ai, 0, 100); V.write(ai, "ai_share_vintages.csv")
        po = V.build_postings(V.RAW / "jpt_full"); V.validate(po, 0, 1000); V.write(po, "postings_vintages.csv")
    ai_v, po_v = V.load("ai_share_vintages.csv"), V.load("postings_vintages.csv")

    now = pd.Timestamp.now(tz="UTC")
    made_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    version = model_version()
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + version[:6]
    run_dir = OUT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    health = {"indeed_ai_tracker": registry.health("indeed_ai_tracker", ai_v, now),
              "indeed_postings": registry.health("indeed_postings", po_v, now)}

    snaps = E.origins(ai_v, po_v)
    y_true = E.truth(ai_v)
    split = E.make_split(snaps, y_true.index.get_level_values(0).max())
    print(f"{len(snaps)} origins ({sum(s.kind == 'real' for s in snaps)} real); holdout from "
          f"{split.holdout_start:%Y-%m-%d} (L={split.holdout_last_month}): {split.n_selection} selection, "
          f"{split.n_holdout} holdout origins")
    bt = E.tag_split(E.backtest(snaps, y_true, feature_sets=feature_sets()), snaps, split)
    bt.to_csv(run_dir / "backtest.csv.gz", index=False)

    sel = E.select(bt)
    qs_sel = E.interval_quantiles(bt, ("selection",))
    cov = E.coverage(bt, qs_sel)
    qs_all = E.interval_quantiles(bt, ("selection", "holdout"))
    abl = E.ablation_table(bt)
    by_kind = {f"{k}_{r}": E.metrics(bt[(bt["feature_set"] == "all") & (bt["vintage_kind"] == k) & (bt["role"] == r)
                                       & (bt["candidate"] == "naive")])
               for k in ("real", "reconstructed") for r in ("selection", "holdout")}

    fc = forecast(snaps[-1], sel, qs_all, run_id, made_at, health)
    fc.to_csv(run_dir / "forecast.csv", index=False)
    log = OUT / "forecast_log.csv"
    fc.to_csv(log, mode="a", header=not log.exists(), index=False)

    evaluation = {
        "run_id": run_id, "made_at": made_at, "target": TARGET, "target_definition": contracts.TARGETS[TARGET].definition,
        "model_version": version, "git_commit": git_commit(), "horizons_months": list(E.HORIZONS),
        "origins": {"total": len(snaps), "real": sum(s.kind == "real" for s in snaps),
                    "reconstructed": sum(s.kind == "reconstructed" for s in snaps),
                    "first": str(snaps[0].last_month), "last": str(snaps[-1].last_month)},
        "split": {"holdout_start": split.holdout_start.isoformat(), "holdout_first_last_month": str(split.holdout_last_month),
                  "selection_origins": split.n_selection, "holdout_origins": split.n_holdout,
                  "rule": f"last {E.HOLDOUT_SHARE:.0%} of origins scorable at h={max(E.HORIZONS)} (min {E.MIN_HOLDOUT}); "
                          "selection pairs purged when their outcome month is after the holdout's first observed month"},
        "selection_rule": f"lowest selection MAE (pp); simplest within {E.NEAR_BEST:.0%} of best",
        "selection": sel.replace({np.nan: None}).to_dict("records"),
        "holdout_interval_coverage_80": cov.to_dict("records"),
        "ablations": abl.replace({np.nan: None}).to_dict("records"),
        "naive_error_by_vintage_kind": by_kind,
        "source_contributions": {
            "label": {"indeed_ai_tracker": "target history (own level and trend)"},
            "features": {"indeed_postings": "postings-volume change (ablation: without_postings)",
                         "indeed_ai_tracker": "own trend and cross-country trend (ablations: without_own_trend, "
                                              "without_cross_country, without_level)"},
            "excluded_by_contract": {"census_btos": contracts.FORBIDDEN_FEATURE[("census_btos", "skill_demand")]},
            "not_yet_used": {"adzuna": "snapshots start 2026-10: no history to train or test on",
                             "gdelt_doc": "adapter not ported; to be tested as a feature through the same ablation"}},
        "source_health": health,
    }
    (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2, default=str))
    reg = promote(run_id, made_at, sel, health, fc, version)

    show = sel[["h", "candidate", "chosen", "selection_mae_pp", "holdout_mae_pp", "holdout_mase_vs_naive"]]
    print(show.round(4).to_string(index=False))
    print(cov.round(3).to_string(index=False))
    for h, e in reg["promoted"].items():
        print(f"h={h}: promoted {e['model']} ({e['status']}) from run {e['run_id']}")
    print(f"run written to {run_dir}")


if __name__ == "__main__":
    main()
