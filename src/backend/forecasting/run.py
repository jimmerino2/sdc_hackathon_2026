"""Run a forecast target end to end: ingest -> backtest -> select -> holdout -> forecast -> promote.

Usage (from src/backend):
    python -m forecasting.run                          # every target, fetching new data first
    python -m forecasting.run --target btos_ai_use_rate --no-pull
    python -m forecasting.run --skip-ingest            # use the point-in-time tables as they are
Targets: ai_mention_share (skill demand), btos_ai_use_rate (business adoption), worker_genai_use_rate
(occupation adoption). They are separate models with separate sources; none feeds another.

Outputs in src/backend/forecasting/output/<target>/ (nothing is overwritten except the two "current" pointers):
  runs/<run_id>/backtest.csv.gz   every scored prediction: origin, horizon, candidate, feature set, unit, outcome
  runs/<run_id>/evaluation.json   split, selection table, holdout scores, coverage, ablations, health, warnings
  runs/<run_id>/forecast.csv      this run's forecast per unit and horizon, with its 10-90% range
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
from pathlib import Path

import numpy as np
import pandas as pd

from . import contracts, evaluation as E, features as F
from .models import CANDIDATES
from .targets import TargetSpec, all_specs

HERE = Path(__file__).parent
OUT = HERE / "output"


def model_version() -> str:
    """Hash of the code that defines the models, features and evaluation (all targets)."""
    h = hashlib.sha256()
    for f in sorted([*HERE.glob("*.py"), *(HERE / "targets").glob("*.py")]):
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=HERE).stdout.strip()
    except FileNotFoundError:
        return ""


def feature_sets(spec: TargetSpec) -> dict[str, list[str]]:
    sets = {"all": spec.features}
    for g, cols in spec.feature_groups.items():
        sets[f"without_{g}"] = [c for c in spec.features if c not in cols]
    return sets


WARNING_SEP = " | "  # warning texts may contain ";"
VALIDATED_MASE = 0.95  # "validated" needs >= 5% lower holdout error than naive; a tie on a few noisy origins is not
                      # evidence. Added after an RPS run labelled a 0.03% gain "validated"; it changes labels, not choices.


def decision(sel: pd.DataFrame, h: int) -> tuple[pd.Series, pd.Series, str]:
    """(chosen row, served row, status) for horizon h. The chosen model is served unless its one holdout score is
    worse than naive's: then the baseline is retained (spec 16.1). This is a pass/fail gate on the predeclared
    choice, not a re-selection on the holdout. Added after BTOS h=13 chose local_trend, which then lost to naive
    by 70% on the new-wording holdout."""
    rows = sel[sel["h"] == h]
    c = rows[rows["chosen"]].iloc[0]
    m = c["holdout_mase_vs_naive"]
    if c["candidate"] != "naive" and m is not None and not pd.isna(m) and m > 1:
        return c, rows[rows["candidate"] == "naive"].iloc[0], "baseline_retained"
    return c, c, status_for(c)


def status_for(row: pd.Series) -> str:
    if row["candidate"] == "naive":
        return "baseline"
    m = row["holdout_mase_vs_naive"]
    if m is not None and not pd.isna(m) and m <= VALIDATED_MASE:
        return "validated"
    return "not_demonstrably_better"


def acceptance(spec: TargetSpec, sel: pd.DataFrame, health: dict, h: int) -> list[str]:
    """Reasons this run may not be promoted for horizon h (empty = accepted)."""
    c = sel[(sel["h"] == h) & sel["chosen"]].iloc[0]
    label = contracts.TARGETS[spec.id].label_source
    fails = []
    if health[label]["status"] != "fresh":
        fails.append("target source is stale")
    if not c["holdout_n_origins"] or c["holdout_n_origins"] < spec.min_holdout:
        fails.append(f"holdout has {c['holdout_n_origins']} origins (< {spec.min_holdout})")
    if c["selection_mae"] is None or pd.isna(c["selection_mae"]):
        fails.append("selection score missing")
    if c["insufficient_history"]:
        fails.append("insufficient history for selection")
    return fails


def range_bias(lo: float, hi: float) -> str:
    """'under' / 'over' when the residual range (actual - forecast) excludes 0, else ''."""
    if not np.isfinite([lo, hi]).all():
        return ""
    return "under" if lo > 0 else "over" if hi < 0 else ""


def forecast(spec: TargetSpec, snap: F.Snapshot, sel: pd.DataFrame, bt: pd.DataFrame, run_id: str, made_at: str,
             health: dict) -> pd.DataFrame:
    """Forecast from the latest snapshot. Ranges (and regime probabilities) use every out-of-sample residual of
    the chosen model, selection and holdout: the model is already fixed, so the holdout no longer chooses anything."""
    qs = E.interval_quantiles(bt, ("selection", "holdout"))
    scored = bt[(bt["feature_set"] == "all") & bt["role"].isin(["selection", "holdout"])].dropna(subset=["resid"])
    rows_now = F.latest_rows(spec, snap)
    label = contracts.TARGETS[spec.id].label_source
    out = []
    for h in spec.horizons:
        chosen, c, status = decision(sel, h)
        m = CANDIDATES[c["candidate"]]().fit(F.labelled(spec, snap, h), h, spec.features, spec.trend_steps,
                                             spec.panel(snap))
        base = rows_now["lvl"].to_numpy() + m.predict(rows_now)
        inv = spec.scale.from_model
        lo, hi = qs.loc[(c["candidate"], h)] if (c["candidate"], h) in qs.index else (np.nan, np.nan)
        warnings = [w for w in (spec.history_warning,) if w]
        if health[label]["status"] != "fresh":
            warnings.append("stale target data")
        if c["insufficient_history"]:
            warnings.append("insufficient history")
        if snap.kind != "real":
            warnings.append(f"point-in-time basis: {snap.kind}")
        if status == "baseline_retained":
            warnings.append(f"chosen model {chosen['candidate']} lost to naive on the holdout; baseline served")
        bias = range_bias(lo, hi)
        if bias:  # every past residual on one side: the model has been systematically biased
            warnings.append(f"point forecast outside its own 10-90% range: this model has consistently "
                            f"{bias}-forecast; read the range, not the point")
        out.append(pd.DataFrame({
            "run_id": run_id, "made_at": made_at, "target": spec.id, "unit_kind": spec.unit_kind,
            "unit": rows_now["unit"], "segment": [spec.segment(u) for u in rows_now["unit"]],
            "last_observed_period": spec.label(snap.last), "last_observed": inv(rows_now["lvl"].to_numpy()),
            "h": h, "period_unit": spec.period_unit, "target_period": spec.label(snap.last + h),
            "value_unit": spec.value_unit, "model": c["candidate"], "chosen_model": chosen["candidate"],
            "forecast": inv(base),
            "low": inv(base + lo), "high": inv(base + hi),
            "interval": f"10-90% empirical (out-of-sample residuals, {spec.scale.name} scale)", "status": status,
            "holdout_mae": chosen["holdout_mae"], "naive_holdout_mae":
                sel[(sel["h"] == h) & (sel["candidate"] == "naive")]["holdout_mae"].iloc[0],
            "vintage": snap.vintage, "data_as_of": snap.origin.isoformat(), "warnings": WARNING_SEP.join(warnings)}))
        if spec.regimes:
            resid = scored[(scored["candidate"] == c["candidate"]) & (scored["h"] == h)]["resid"].to_numpy()
            lo_b, hi_b = E.regime_bounds(rows_now["trend"].to_numpy(), h, spec.trend_steps)
            p = (E.regime_probs(base - rows_now["lvl"].to_numpy(), resid, lo_b, hi_b) if len(resid)
                 else np.full((len(rows_now), 3), np.nan))
            for i, r in enumerate(E.REGIMES):
                out[-1][f"p_{r}"] = p[:, i]
            out[-1]["regime_rule"] = (f"rate over next {h} vs trailing rate over {spec.trend_steps} periods; "
                                      f"tolerance +-{E.REGIME_TOL:.0%} (min {E.REGIME_TOL_FLOOR} per period); "
                                      f"from {len(resid)} out-of-sample residuals (few: tails are coarse)")
    return pd.concat(out, ignore_index=True)


def append_log(path: Path, rows: pd.DataFrame) -> None:
    """Append-only in content: earlier rows are kept as they are; a new column is added for all rows (blank for
    older ones). Written to a temporary file first, so a failure cannot truncate the log."""
    old = pd.read_csv(path, dtype={"unit": str}) if path.exists() else pd.DataFrame()
    new = pd.concat([old, rows], ignore_index=True)
    tmp = path.with_suffix(".tmp")
    new.to_csv(tmp, index=False)
    tmp.replace(path)


def promote(spec: TargetSpec, out: Path, run_id: str, made_at: str, sel: pd.DataFrame, health: dict,
            version: str) -> dict:
    path = out / "model_registry.json"
    reg = json.loads(path.read_text()) if path.exists() else {"target": spec.id, "promoted": {}, "attempts": []}
    for h in spec.horizons:
        c, served, status = decision(sel, h)
        fails = acceptance(spec, sel, health, h)
        entry = {"run_id": run_id, "made_at": made_at, "h": int(h), "model": served["candidate"],
                 "chosen_model": c["candidate"], "model_version": version,
                 "status": status, "selection_mae": c["selection_mae"],
                 "holdout_mae": c["holdout_mae"], "holdout_mase_vs_naive": c["holdout_mase_vs_naive"],
                 "accepted": not fails, "rejected_because": fails}
        reg["attempts"].append(entry)
        if not fails:
            reg["promoted"][str(h)] = entry
    path.write_text(json.dumps(reg, indent=2, default=lambda v: None if pd.isna(v) else float(v)))
    # latest_forecast.csv: per horizon, rows of the promoted run (looked up in the append-only log)
    log = pd.read_csv(out / "forecast_log.csv", dtype={"unit": str})  # SOC "00" must stay "00"
    keep = [log[(log["run_id"] == e["run_id"]) & (log["h"] == int(h))] for h, e in reg["promoted"].items()]
    if keep:
        pd.concat(keep).to_csv(out / "latest_forecast.csv", index=False)
    return reg


def run_target(spec: TargetSpec, now: pd.Timestamp | None = None) -> dict:
    sources = {spec.group_source[g] for g in spec.feature_groups}
    contracts.check_sources(spec.id, contracts.TARGETS[spec.id].label_source, sources)

    data = spec.load()
    now = now or pd.Timestamp.now(tz="UTC")
    made_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    version = model_version()
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + version[:6]
    out = OUT / spec.id
    run_dir = out / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    health = spec.health(data, now)

    snaps = [s for s in spec.origins(data) if s.origin <= now]
    E.check_chronological(snaps)
    y_true = spec.truth(data)
    split = E.make_split(spec, snaps, y_true.index.get_level_values(0).max())
    print(f"[{spec.id}] {len(snaps)} origins; holdout from {split.holdout_start:%Y-%m-%d} "
          f"(last observed {spec.label(split.holdout_last)}): {split.n_selection} selection, "
          f"{split.n_holdout} holdout origins")
    bt = E.backtest(spec, snaps, y_true, split, feature_sets=feature_sets(spec))
    bt.to_csv(run_dir / "backtest.csv.gz", index=False)

    sel = E.select(bt, spec.min_selection_origins)
    cov = E.coverage(bt, E.interval_quantiles(bt, ("selection",)))
    abl = E.ablation_table(bt)

    fc = forecast(spec, snaps[-1], sel, bt, run_id, made_at, health)
    fc.to_csv(run_dir / "forecast.csv", index=False)
    append_log(out / "forecast_log.csv", fc)

    target = contracts.TARGETS[spec.id]
    evaluation = {
        "run_id": run_id, "made_at": made_at, "target": spec.id, "domain": target.domain,
        "target_definition": target.definition, "label_source": target.label_source,
        "feature_sources": sorted(sources), "model_version": version, "git_commit": git_commit(),
        "horizons": list(spec.horizons), "period_unit": spec.period_unit,
        "origins": {"total": len(snaps), "by_kind": pd.Series([s.kind for s in snaps]).value_counts().to_dict(),
                    "first": spec.label(snaps[0].last), "last": spec.label(snaps[-1].last)},
        "split": {"holdout_start": split.holdout_start.isoformat(), "holdout_first_last_period": spec.label(split.holdout_last),
                  "selection_origins": split.n_selection, "holdout_origins": split.n_holdout,
                  "rule": f"last {spec.holdout_share:.0%} of origins scorable at h={max(spec.horizons)} "
                          f"(min {spec.min_holdout}); selection pairs purged when their outcome period is after the "
                          "holdout's first observed period"},
        "selection_rule": f"lowest selection MAE (pp); simplest within {E.NEAR_BEST:.0%} of best",
        "selection": sel.replace({np.nan: None}).to_dict("records"),
        "holdout_interval_coverage_80": cov.to_dict("records"),
        "ablations": abl.replace({np.nan: None}).to_dict("records"),
        "breakdown": E.breakdown(bt, sel),
        "history_warning": spec.history_warning,
        "value_unit": spec.value_unit, "error_unit": spec.error_unit, "modelling_scale": spec.scale.name,
        "regime_scores": E.regime_scores(spec, bt, sel) if spec.regimes else None,
        "source_health": health,
    }
    (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2, default=str))
    reg = promote(spec, out, run_id, made_at, sel, health, version)

    show = sel[["h", "candidate", "chosen", "selection_mae", "holdout_mae", "holdout_mase_vs_naive"]]
    print(show.round(4).to_string(index=False))
    for h, e in reg["promoted"].items():
        print(f"[{spec.id}] h={h}: promoted {e['model']} ({e['status']}) from run {e['run_id']}")
    rejected = [a for a in reg["attempts"] if a["run_id"] == run_id and not a["accepted"]]
    for a in rejected:
        print(f"[{spec.id}] h={a['h']}: not promoted: {'; '.join(a['rejected_because'])}")
    print(f"[{spec.id}] run written to {run_dir}")
    return evaluation


def main() -> None:
    specs = all_specs()
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=[*specs, "all"], default="all")
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--skip-ingest", action="store_true")
    a = ap.parse_args()
    for tid, spec in specs.items():
        if a.target in ("all", tid):
            if not a.skip_ingest:
                spec.ingest(not a.no_pull)
            run_target(spec)


if __name__ == "__main__":
    main()
