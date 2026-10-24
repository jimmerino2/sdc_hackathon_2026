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
            g = d.groupby("candidate")["error"]
            t = pd.DataFrame({"mae": g.apply(lambda x: x.abs().mean()), "bias": g.mean(), "n": g.size()})
            return [{"method": m, "mae": float(r.mae), "bias": float(r.bias), "n": int(r.n)}
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
