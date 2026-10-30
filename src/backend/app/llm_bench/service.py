"""The LLM forecast benchmark for the API: estimates, runs in a background thread, results.

Everything is computed by src/backend/llm_bench and stored under data/llm_bench/. One run at a time per backend
process; a run interrupted by a restart is resumed from where it stopped. A live run needs confirm=true, sent only
after the page has shown the estimate.
"""
from __future__ import annotations

import json
import math
import threading

from llm_bench import config, openrouter as OR, prompts as P, runner as R


class Busy(RuntimeError):
    pass


class Refused(RuntimeError):
    pass


_lock = threading.Lock()
_active: dict = {"run_id": None, "thread": None, "stop": None}


def _clean(v):
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def info() -> dict:
    s = config.settings()
    out = {"settings": {k: v for k, v in s.public().items() if k != "base_url"}, "key_configured": bool(config.api_key()),
           "modes": {"primary": list(P.PRIMARY), "exploratory": list(P.EXPLORATORY)}, "prompt_version": P.PROMPT_VERSION,
           "benchmarks": {
               "skills": {"label": "Skills demand", "horizons": [3, 6, 12], "default_horizons": [3],
                          "target": "share of an occupation's eligible HN ads in a country naming the skill, pooled over "
                                    "the 3 months ending at origin + h", "units": "pp of share",
                          "origins": "test period of the occupational backtest"},
               "capability": {"label": "AI acceleration", "horizons": [3, 6, 12], "default_horizons": [3, 6, 12],
                              "target": "frontier METR 50% time horizon (minutes) at last complete month + h",
                              "units": "doublings (log2 minutes)", "origins": "holdout of the served capability run"}},
           "running": active()}
    try:
        listing = OR.catalog(s.base_url, config.api_key(), s.price_margin)
        out["models"] = {mid: OR.model_info(listing, mid).public() for mid in dict.fromkeys([s.model, s.compare_model])}
        out["free_models"] = sorted(m["id"] for m in listing
                                    if OR.model_info(listing, m["id"]).free and "response_format" in (m.get("supported_parameters") or []))
    except Exception as e:  # the model list is public, but the network may be down
        out["models"], out["free_models"], out["models_error"] = {}, [], f"{type(e).__name__}: {e}"
    return _clean(out)


def active() -> dict | None:
    t = _active["thread"]
    return {"run_id": _active["run_id"]} if t is not None and t.is_alive() else None


def estimate(cfg: R.RunConfig) -> dict:
    return _clean(R.estimate(cfg))


def _launch(run_id: str) -> None:
    stop = threading.Event()

    def work():
        try:
            R.execute(run_id, stop=stop)
        except Exception:
            pass  # recorded in status.json by execute

    t = threading.Thread(target=work, name=f"llm-bench-{run_id}", daemon=True)
    _active.update(run_id=run_id, thread=t, stop=stop)
    t.start()


def start(cfg: R.RunConfig, confirm: bool) -> dict:
    with _lock:
        if active():
            raise Busy(f"run {_active['run_id']} is still running")
        if not cfg.dry_run:
            if not config.api_key():
                raise Refused("OPENROUTER_BENCH_API_KEY is not set in src/backend/.env; only a dry run is possible")
            if not confirm:
                raise Refused("a live run needs confirm=true after reviewing the estimate")
        run_id = R.create(cfg)
        _launch(run_id)
    return {"run_id": run_id}


def resume(run_id: str, confirm: bool) -> dict:
    with _lock:
        if active():
            raise Busy(f"run {_active['run_id']} is still running")
        cfg = R.load(run_id)["cfg"]
        if not cfg.dry_run and not confirm:
            raise Refused("resuming a live run needs confirm=true")
        _launch(run_id)
    return {"run_id": run_id}


def stop(run_id: str) -> dict:
    if _active["run_id"] == run_id and _active["stop"] is not None:
        _active["stop"].set()
        return {"stopping": True}
    return {"stopping": False}


def runs() -> list[dict]:
    return _clean(R.runs())


def detail(run_id: str) -> dict:
    r = R.load(run_id)
    rep_p = r["dir"] / "report.json"
    running = active() and _active["run_id"] == run_id
    rep = json.loads(rep_p.read_text(encoding="utf-8")) if rep_p.exists() and running else R.evaluate(run_id)
    c = r["config"]
    return _clean({"run_id": run_id, "config": c["config"], "model": c["model"], "sample_id": c["sample_id"],
                   "sample": {k: v for k, v in c["sample_meta"].items() if k != "params"}, "plan": {
                       k: v for k, v in r["plan"].items() if k != "requests"},
                   "status": r["status"] if running else rep["status"], "report": rep, "running": bool(running)})


CASE_COLS = ["case_id", "anon_id", "origin", "target_month", "h", "existing_method", "existing", "naive", "actual",
             "series_key", "unit", "p12_origin", "n3_origin", "last_value", "role"]


def cases(run_id: str, mode: str | None, status: str | None, limit: int) -> dict:
    df = R.case_table(run_id)
    modes = R.load(run_id)["cfg"].modes
    if mode and status:
        df = df[df[f"status_{mode}"] == status] if status != "failed" else \
            df[~df[f"status_{mode}"].isin(["ok"])]
    cols = [c for c in CASE_COLS if c in df.columns] + [f"{p}_{m}" for m in modes for p in ("llm", "status", "reason")]
    rows = df[cols].head(limit).astype(object).where(df[cols].head(limit).notna(), None).to_dict("records")
    return _clean({"n": int(len(df)), "modes": modes, "rows": rows})


def summary(benchmark: str) -> dict:
    """Completed live runs of one benchmark, primary (anonymous) modes only: each LLM's error next to the existing
    model's and "no change" on the same cases, for the short "we also tried LLMs" note beside the forecasts."""
    key = "mae_pp" if benchmark == "skills" else "mae_doublings"
    rows, full = [], None
    for r in R.runs():
        if r["benchmark"] != benchmark or r["dry_run"] or r["state"] != "completed":
            continue
        rep = R.evaluate(r["run_id"]) if not (R.root() / "runs" / r["run_id"] / "report.json").exists() else \
            json.loads((R.root() / "runs" / r["run_id"] / "report.json").read_text(encoding="utf-8"))
        cfg = R.load(r["run_id"])["cfg"]
        full = full or rep["full_sample"]
        for mode, res in rep["primary"].items():
            o = res.get("overall") or {}
            if not o:
                continue
            rows.append({"run_id": r["run_id"], "model": r["model"], "reasoning": cfg.reasoning or "off", "mode": mode,
                         "horizons": cfg.horizons, "n_valid": res["n_valid"], "n_cases": res["n_cases"],
                         "llm": o["llm"].get(key), "existing": o["existing"].get(key), "naive": o["naive"].get(key),
                         "llm_lower_error": (res.get("verdict") or {}).get("llm_lower_error"),
                         "bootstrap": rep["bootstrap"].get(mode), "cost_usd": rep["usage"].get("cost_usd")})
    rows.sort(key=lambda x: (x["llm"] is None, x["llm"]))
    return _clean({"benchmark": benchmark, "metric": key, "units": "pp" if benchmark == "skills" else "doublings",
                   "full_sample": {k: (v or {}).get(key) for k, v in (full or {}).items()},
                   "n_runs": len({x["run_id"] for x in rows}), "any_better": any(x["llm_lower_error"] for x in rows),
                   "total_cost_usd": sum({x["run_id"]: x["cost_usd"] or 0 for x in rows}.values()), "rows": rows})
