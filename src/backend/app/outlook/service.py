"""Read the rebuilt forecasting pipeline's outputs (src/backend/forecasting/output/<target>/) for the API.

Only promoted forecasts are served (latest_forecast.csv). Files are re-read when they change, so a new run shows up
without restarting the server. Nothing here computes a forecast.
"""
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from forecasting import contracts
from forecasting.run import WARNING_SEP
from forecasting.targets import all_specs

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "forecasting" / "output"


def targets() -> list[str]:
    return [t for t in all_specs() if (OUTPUT_DIR / t / "latest_forecast.csv").exists()]


@lru_cache(maxsize=32)
def _read_csv(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"unit": str})


@lru_cache(maxsize=64)
def _read_json(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text())


def _csv(p: Path) -> pd.DataFrame:
    return _read_csv(str(p), p.stat().st_mtime)


def _json(p: Path) -> dict:
    return _read_json(str(p), p.stat().st_mtime)


def evaluation(target: str) -> dict:
    """evaluation.json of the newest run (whether or not it was promoted)."""
    runs = sorted((OUTPUT_DIR / target / "runs").glob("*/evaluation.json"))
    return _json(runs[-1]) if runs else {}


def summary(target: str) -> dict:
    spec, t = all_specs()[target], contracts.TARGETS[target]
    reg = _json(OUTPUT_DIR / target / "model_registry.json")
    ev = evaluation(target)
    return {"target": target, "domain": t.domain, "definition": t.definition, "label_source": t.label_source,
            "unit_kind": spec.unit_kind, "value_unit": spec.value_unit, "period_unit": spec.period_unit,
            "error_unit": spec.error_unit, "horizons": list(spec.horizons),
            "promoted": [{k: e.get(k) for k in ("h", "model", "chosen_model", "status", "holdout_mase_vs_naive",
                                                 "run_id", "made_at")} for e in reg["promoted"].values()],
            "history_warning": spec.history_warning, "source_health": ev.get("source_health", {}),
            "has_regimes": spec.regimes}


def rows(target: str, unit: str | None = None, h: int | None = None) -> list[dict]:
    f = _csv(OUTPUT_DIR / target / "latest_forecast.csv")
    if unit is not None:
        f = f[f["unit"].str.lower() == unit.lower()]
    if h is not None:
        f = f[f["h"] == h]
    f = f.astype(object).where(f.notna(), None)
    out = []
    for r in f.to_dict("records"):
        r["warnings"] = [w.strip() for w in (r.get("warnings") or "").split(WARNING_SEP) if w.strip()]
        out.append(r)
    return out


def _backtest(target: str, run_id: str) -> pd.DataFrame:
    """Held-back (holdout) predictions of one run, with an outcome: the test the published forecast passed or failed."""
    b = _csv(OUTPUT_DIR / target / "runs" / run_id / "backtest.csv.gz")
    return b[(b["feature_set"] == "all") & (b["role"] == "holdout") & b["actual"].notna()]


def accuracy(target: str, unit: str) -> list[dict]:
    """Per promoted horizon: every method's average error on the held-back test data for this one unit, next to the
    same methods pooled over all units. Errors are absolute, in the target's error unit (pp, or doublings)."""
    spec = all_specs()[target]
    reg = _json(OUTPUT_DIR / target / "model_registry.json")
    out = []
    for h, e in sorted(reg["promoted"].items(), key=lambda kv: int(kv[0])):
        b = _backtest(target, e["run_id"])
        b = b[b["h"] == int(h)]
        mine = b[b["unit"].str.lower() == unit.lower()]

        def score(d: pd.DataFrame) -> list[dict]:
            # Accuracy per forecast = smaller / larger of forecast and actual (30 vs 40 -> 75%, either way round).
            # Bounded 0-100 and symmetric, so it also works for time horizons, where a forecast can be several times
            # off. % off = |forecast - actual| / actual.
            lo, hi = d[["pred", "actual"]].min(axis=1), d[["pred", "actual"]].max(axis=1)
            d = d.assign(acc=lo / hi * 100, pct_off=(d["pred"] - d["actual"]).abs() / d["actual"] * 100,
                         miss=(d["pred"] - d["actual"]).abs())  # in the value's own unit (pp, or minutes)
            g = d.groupby("candidate")
            t = pd.DataFrame({"mae": g["error"].apply(lambda x: x.abs().mean()), "bias": g["error"].mean(),
                              "pct_off": g["pct_off"].mean(), "acc": g["acc"].mean(), "miss": g["miss"].mean(),
                              "n": g.size()})
            return [{"method": m, "mae": float(r.mae), "bias": float(r.bias), "pct_off": float(r.pct_off),
                     "accuracy_pct": float(r.acc), "avg_miss": float(r.miss), "n": int(r.n)}
                    for m, r in t.sort_values("mae").iterrows()]

        rows = score(mine)
        by = {r["method"]: r for r in rows}
        served, naive = by.get(e["model"]), by.get("naive")
        out.append({"h": int(h), "unit": unit, "served_model": e["model"], "chosen_model": e.get("chosen_model"),
                    "error_unit": spec.error_unit, "n_test_points": served["n"] if served else 0,
                    "served_mae": served["mae"] if served else None, "naive_mae": naive["mae"] if naive else None,
                    "beats_naive": (served["mae"] < naive["mae"]) if served and naive and e["model"] != "naive" else None,
                    "methods": rows, "all_units": score(b), "run_id": e["run_id"]})
    return out


def _engine_file(target: str) -> Path | None:
    """engine.json of the run behind the served forecast (capability only)."""
    f = _csv(OUTPUT_DIR / target / "latest_forecast.csv")
    runs = sorted(set(f["run_id"]))
    p = OUTPUT_DIR / target / "runs" / runs[-1] / "engine.json" if runs else None
    return p if p is not None and p.exists() else None


def engine(target: str) -> dict:
    """The capability engine's chart series (observed, bridged, frontier, forecast fan), per-horizon pace detail,
    backtest scores and diagnostics, for the run that is served. Empty for targets without an engine."""
    p = _engine_file(target)
    return _json(p) if p else {}


def regime_explained(target: str, unit: str) -> list[dict]:
    """Every ingredient of the P(faster / same pace / slower) bars, per published horizon, in plain units.

    Paces are in doublings per year. The chances are the shares of simulated trajectories whose pace over the
    horizon is above, within or below the band around the past 12 months' pace (capability_engine)."""
    spec = all_specs()[target]
    eng = engine(target)
    u = eng.get("units", {}).get(unit) or next((v for k, v in eng.get("units", {}).items() if k.lower() == unit.lower()), None)
    if not spec.regimes or not u:
        return []
    f = _csv(OUTPUT_DIR / target / "latest_forecast.csv")
    f = f[f["unit"].str.lower() == unit.lower()]
    ev = _json(OUTPUT_DIR / target / "runs" / f["run_id"].iloc[0] / "evaluation.json") if len(f) else {}
    bt = eng["backtest"]
    out = []
    for x in u["horizons"]:
        h = x["h"]
        r = f[f["h"] == h].to_dict("records")
        if not r:
            continue
        r = r[0]
        pace = lambda role, c="ensemble": next((p for p in bt["pace"] if p["h"] == h and p["role"] == role  # noqa: E731
                                                and p["candidate"] == c), None)
        point = lambda role, c: next((p for p in bt["point"] if p["h"] == h and p["role"] == role  # noqa: E731
                                      and p["candidate"] == c), {})
        methods = [{"method": c, "served": c == r["model"], "weight": x["weights"].get(c),
                    "selection_typical_miss": point("selection", c).get("typical_factor"),
                    "holdout_typical_miss": point("holdout", c).get("typical_factor"),
                    "holdout_coverage_80": point("holdout", c).get("coverage_80"),
                    "n_holdout": point("holdout", c).get("n")}
                   for c in ("ensemble", "damped_trend", "robust_local_trend", "jump_process", "drift", "naive")]
        out.append({
            "h": h, "unit": r["unit"], "period_unit": r["period_unit"], "model": r["model"], "status": r["status"],
            "last_observed": r["last_observed"], "last_observed_period": r["last_observed_period"],
            "current_model": u["current_model"], "current_saturated": u["current_saturated"],
            "forecast": r["forecast"], "low": r["low"], "high": r["high"], "target_period": r["target_period"],
            "pace_basis": u["pace_basis"], "hist_pace": x["hist_pace"], "hist_pace_range": x["hist_pace_q10_q90"],
            "tolerance": x["tolerance"], "same_band": x["same_band"],
            "future_pace_median": x["future_pace_median"], "future_pace_range": x["future_pace_q10_q90"],
            "pace_histogram": x["pace_histogram"], "n_sims": eng["config"]["n_sims"],
            "p_faster": r["p_acceleration"], "p_same": r["p_stable"], "p_slower": r["p_slowdown"],
            "p_simulated": x["p_simulated"], "base_rate": x["base_rate"], "prior_assisted": x["prior_assisted"],
            "shrink": x["shrink"], "p_no_new_record": x.get("p_no_new_record"),
            "components": {c: {**v, "weight": x["weights"].get(c)} for c, v in x["components"].items()},
            "methods": methods,
            "reliability": next(({k: s.get(k) for k in ("n", "brier_model", "brier_climatology", "brier_uniform")}
                                 for s in (ev.get("regime_scores") or []) if s["h"] == h), None),
            "pace_scores": {"selection": pace("selection"), "holdout": pace("holdout")},
            "pace_rule": bt["shrink"].get(str(h)),
        })
    return out



def success_curves() -> dict:
    """Task lengths each model completes at several success rates (METR's curve, read beyond 50%). Display only."""
    data = OUTPUT_DIR.parents[3] / "data" / "processed" / "forecasting"
    t = _csv(data / "metr_success_curves.csv")
    bins = _csv(data / "metr_success_bins.csv")
    levels = [95, 90, 80, 75, 50, 25, 10]
    longest = float(t["longest_task_minutes"].max())
    models = []
    for r in t.to_dict("records"):
        hz = {str(p): (None if pd.isna(r.get(f"h{p}")) else float(r[f"h{p}"])) for p in levels}
        models.append({"model": r["model"], "epoch_model": None if pd.isna(r.get("epoch_model")) else r["epoch_model"],
                       "release_date": None if pd.isna(r.get("release_date")) else str(r["release_date"])[:10],
                       "source": r["source"], "fitted": str(r["source"]).startswith("fitted"),
                       "intercept": None if pd.isna(r.get("intercept")) else float(r["intercept"]),
                       "slope": None if pd.isna(r.get("slope")) else float(r["slope"]),
                       "horizons": hz,
                       "observed": [{k: (v if not isinstance(v, float) or not pd.isna(v) else None) for k, v in b.items()
                                     if k != "model"} for b in bins[bins["model"] == r["model"]].to_dict("records")]})
    return {"levels": levels, "longest_task_minutes": longest, "models": models,
            "note": "Fitted from METR's raw runs with METR's own method; reproduces the official 50% and 80% horizons. "
                    "Values beyond the longest task METR tested are extrapolations."}
