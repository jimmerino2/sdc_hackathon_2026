"""Benchmark runs: fixed sample -> plan with cost estimate -> budgeted, resumable requests -> evaluation.

Storage (data/llm_bench/, override with LLM_BENCH_DIR; nothing outside it is written):
  samples/<sample_id>/       cases.csv.gz (inputs, baselines; no outcomes), truth.csv.gz, meta.json. Built once per
                             sample definition and reused, so every model is compared on identical cases.
  runs/<run_id>/config.json  run settings (never the key), model pricing as listed at the start, prompt version
                plan.json    every request: mode, batch, case ids, estimated prompt tokens, maximum cost
                requests.jsonl   one line per finished request: status, retries, tokens, cost and its source, reply
                predictions.jsonl one line per case per request: validated value or why not
                status.json  progress, spend, state and stop reason
                report.json  metrics (written by evaluate)
Resuming skips requests already answered (status ok), so paid requests are not repeated.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import cases as K, config, metrics as MX, openrouter as OR, prompts as P

STOP_STATES = ("completed", "stopped_budget", "rate_limited", "auth_or_payment", "too_many_failures", "stopped_by_user",
               "paused_request_limit", "output_cap_ignored", "failed")
OUTPUT_TOKENS_PER_CASE = 30  # expected reply size, for the expected (not maximum) cost


@dataclass
class RunConfig:
    benchmark: str = "skills"  # skills | capability
    horizons: list[int] = field(default_factory=lambda: [3])
    n_series: int = 100  # skills
    n_origins: int = 4  # skills: origins per series
    cap_roles: list[str] = field(default_factory=lambda: ["holdout"])  # capability: holdout, or + selection
    cap_max_origins: int = 0  # capability: 0 = all
    modes: list[str] = field(default_factory=lambda: ["zero", "few"])
    model: str = ""
    batch_size: int = 10
    max_output_tokens: int = 2048
    max_spend_usd: float = 2.0
    few_shot_k: int = 4  # examples ranked per case
    max_examples: int = 10  # examples per prompt
    seed: int = 20261029
    dry_run: bool = False
    max_requests: int = 0  # 0 = all; else pause after this many requests (a smoke test)
    reasoning: str = ""  # off | low | default; "" = OPENROUTER_BENCH_REASONING. Stored per run, so a resume keeps it
    concurrency: int = 1  # requests in flight at once; resume can override it

    def sample_params(self) -> dict:
        if self.benchmark == "skills":
            return {"horizons": sorted(self.horizons), "n_series": self.n_series, "n_origins": self.n_origins,
                    "seed": self.seed, "few_shot_k": self.few_shot_k, "case_version": 1}
        return {"horizons": sorted(self.horizons), "roles": sorted(self.cap_roles), "max_origins": self.cap_max_origins,
                "seed": self.seed, "few_shot_k": self.few_shot_k, "case_version": 1}

    @classmethod
    def from_dict(cls, d: dict) -> "RunConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def root() -> Path:
    return config.data_dir()


def _write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_jsonable, ensure_ascii=False)
    os.replace(tmp, p)


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    return str(o)


def _append(p: Path, obj) -> None:
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=_jsonable, ensure_ascii=False) + "\n")


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _clean(v):
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


# ---------------------------------------------------------------------------------------------- sample


def sample(cfg: RunConfig) -> tuple[str, pd.DataFrame, pd.DataFrame, dict]:
    """The fixed case sample for this definition, built once and reused."""
    sid = K.sample_id(cfg.benchmark, cfg.sample_params(), K.fingerprint(cfg.benchmark))
    d = root() / "samples" / sid
    if (d / "meta.json").exists():
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        return sid, pd.read_csv(d / "cases.csv.gz", dtype={"origin": str, "target_month": str}), \
            pd.read_csv(d / "truth.csv.gz"), meta
    if cfg.benchmark == "skills":
        cs = K.skill_cases(horizons=tuple(cfg.horizons), n_series=cfg.n_series, n_origins=cfg.n_origins, seed=cfg.seed,
                           few_shot_k=cfg.few_shot_k)
    elif cfg.benchmark == "capability":
        cs = K.capability_cases(horizons=tuple(cfg.horizons), roles=tuple(cfg.cap_roles), max_origins=cfg.cap_max_origins,
                                seed=cfg.seed, few_shot_k=cfg.few_shot_k)
    else:
        raise ValueError(f"unknown benchmark {cfg.benchmark}")
    d.mkdir(parents=True, exist_ok=True)
    cs.cases.to_csv(d / "cases.csv.gz", index=False)
    cs.truth.to_csv(d / "truth.csv.gz", index=False)
    meta = {"sample_id": sid, "benchmark": cfg.benchmark, "params": cfg.sample_params(), "n_cases": len(cs.cases),
            "built_at": datetime.now(timezone.utc).isoformat(), **cs.meta}
    _write_json(d / "meta.json", meta)
    return sid, pd.read_csv(d / "cases.csv.gz", dtype={"origin": str, "target_month": str}), cs.truth, meta


# ---------------------------------------------------------------------------------------------- plan


def request_key(model: str, mode: str, case_ids: list[str]) -> str:
    blob = json.dumps([model, mode, P.PROMPT_VERSION, sorted(case_ids)])
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def plan(cfg: RunConfig, cases: pd.DataFrame, info: OR.ModelInfo) -> dict:
    reqs = []
    for mode in cfg.modes:
        for b in P.batches(cases, cfg.batch_size):
            msgs = P.messages(cfg.benchmark, mode, b, cfg.max_examples)
            chars = sum(len(m["content"]) for m in msgs)
            tok = OR.estimate_tokens("".join(m["content"] for m in msgs))
            mx = OR.max_cost(info, tok, cfg.max_output_tokens) if info.listed else None
            exp = (tok * info.prompt + (OUTPUT_TOKENS_PER_CASE * len(b) + 30) * info.completion + info.request
                   if info.listed else None)
            reqs.append({"key": request_key(info.id, mode, b["case_id"].tolist()), "mode": mode,
                         "batch_key": b["batch_key"].iloc[0], "case_ids": b["case_id"].tolist(), "n_cases": len(b),
                         "prompt_chars": chars, "est_prompt_tokens": tok, "max_cost_usd": mx, "expected_cost_usd": exp})
    tot = lambda k: None if not info.listed else float(sum(r[k] for r in reqs))
    return {"requests": reqs, "n_requests": len(reqs), "n_cases": int(len(cases)), "modes": cfg.modes,
            "est_prompt_tokens": int(sum(r["est_prompt_tokens"] for r in reqs)),
            "max_output_tokens_total": cfg.max_output_tokens * len(reqs),
            "max_cost_usd": tot("max_cost_usd"), "expected_cost_usd": tot("expected_cost_usd"),
            "within_budget": None if not info.listed else tot("max_cost_usd") <= cfg.max_spend_usd,
            "model": info.public()}


def model_info(model: str, transport=None) -> OR.ModelInfo:
    s = config.settings()
    return OR.model_info(OR.catalog(s.base_url, config.api_key(), s.price_margin, transport=transport), model)


def estimate(cfg: RunConfig, transport=None) -> dict:
    cfg.model = cfg.model or config.settings().model
    sid, cases, _, meta = sample(cfg)
    info = model_info(cfg.model, transport)
    p = plan(cfg, cases, info)
    p.pop("requests")
    return {"sample_id": sid, "sample": {k: v for k, v in meta.items() if k != "params"}, **p,
            "budget_usd": cfg.max_spend_usd, "key_configured": bool(config.api_key())}


# ---------------------------------------------------------------------------------------------- run


def create(cfg: RunConfig, transport=None) -> str:
    s = config.settings()
    cfg.model = cfg.model or s.model
    cfg.reasoning = cfg.reasoning or s.reasoning
    sid, cases, truth, meta = sample(cfg)
    info = model_info(cfg.model, transport)
    if not info.listed and not cfg.dry_run:
        raise OR.ConfigError(f"{cfg.model} is not in OpenRouter's model list (price unknown); pick a listed model")
    p = plan(cfg, cases, info)
    now = datetime.now(timezone.utc)
    tag = hashlib.sha256(json.dumps([asdict(cfg), sid], default=str).encode()).hexdigest()[:6]
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + tag
    d = root() / "runs" / run_id
    d.mkdir(parents=True)
    _write_json(d / "config.json", {"run_id": run_id, "made_at": now.isoformat(), "config": asdict(cfg),
                                    "settings": {k: v for k, v in s.public().items() if k not in ("model", "compare_model")},
                                    "model": info.public(), "prompt_version": P.PROMPT_VERSION, "sample_id": sid,
                                    "sample_meta": meta, "primary_modes": [m for m in cfg.modes if m in P.PRIMARY],
                                    "exploratory_modes": [m for m in cfg.modes if m in P.EXPLORATORY]})
    _write_json(d / "plan.json", p)
    _write_json(d / "status.json", {"state": "planned", "done": 0, "total": p["n_requests"], "spent_usd": 0.0,
                                    "budget_usd": cfg.max_spend_usd, "updated_at": now.isoformat()})
    return run_id


def load(run_id: str) -> dict:
    d = root() / "runs" / run_id
    if not (d / "config.json").exists():
        raise FileNotFoundError(run_id)
    cfgj = json.loads((d / "config.json").read_text(encoding="utf-8"))
    return {"dir": d, "config": cfgj, "cfg": RunConfig.from_dict(cfgj["config"]),
            "plan": json.loads((d / "plan.json").read_text(encoding="utf-8")),
            "status": json.loads((d / "status.json").read_text(encoding="utf-8"))}


class MockClient:
    """Dry run: answers every series with its last observed value (no network, no spend). It exercises the prompt,
    parsing, validation, cost estimate and evaluation; its numbers are not an LLM's and are labelled mock."""

    def __init__(self, info: OR.ModelInfo, benchmark: str):
        self.info, self.benchmark = info, benchmark

    def complete(self, messages, max_output_tokens, budget, seed=7) -> OR.Result:
        payload = json.loads(messages[-1]["content"])
        preds = []
        for s in payload["series"]:
            if self.benchmark == "skills":
                v = s.get("share_3m_pct") if s.get("share_3m_pct") is not None else s.get("share_12m_pct") or 0.0
            else:
                v = s["frontier_change_points"][-1][1]
            preds.append({"series_id": s["series_id"], "forecast_value": v})
        content = json.dumps({"predictions": preds})
        pt = OR.estimate_tokens("".join(m["content"] for m in messages))
        ct = OR.estimate_tokens(content)
        cost = (pt * self.info.prompt + ct * self.info.completion) if self.info.listed else 0.0
        return OR.Result("ok", content=content, prompt_tokens=pt, completion_tokens=ct, cost_usd=0.0,
                         cost_source="none", max_cost_usd=cost, served_model="mock", params={"mock": True})

    def close(self):
        pass


def _status(d: Path, **kw) -> dict:
    p = d / "status.json"
    st = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    st.update(kw, updated_at=datetime.now(timezone.utc).isoformat())
    _write_json(p, st)
    return st


def execute(run_id: str, stop: threading.Event | None = None, transport=None, sleep=time.sleep,
            concurrency: int | None = None) -> dict:
    """Send the planned requests, skipping those already answered, up to `concurrency` at a time (default: the run's
    setting). Results are written on this thread as they finish. Stops sending on budget, rate limit, auth or payment
    errors, an ignored output cap, repeated failures, a user stop, or max_requests; requests already in flight are
    still recorded."""
    r = load(run_id)
    d, cfg, pl = r["dir"], r["cfg"], r["plan"]
    s = config.settings()
    sid = r["config"]["sample_id"]
    cases = pd.read_csv(root() / "samples" / sid / "cases.csv.gz", dtype={"origin": str, "target_month": str})
    by_id = cases.set_index("case_id", drop=False)
    info = OR.ModelInfo(**{k: (tuple(v) if k == "supported" else v) for k, v in r["config"]["model"].items() if k != "free"})
    done_reqs = _read_jsonl(d / "requests.jsonl")
    answered = {x["key"] for x in done_reqs if x["status"] == "ok"}
    spent = float(sum(x.get("cost_usd") or 0 for x in done_reqs))
    budget = OR.Budget(cfg.max_spend_usd, spent)
    workers = max(1, concurrency or cfg.concurrency)
    client = MockClient(info, cfg.benchmark) if cfg.dry_run else OR.Client(
        s.base_url, config.api_key(), info, timeout_s=s.timeout_s, max_retries=s.max_retries,
        min_interval_s=0 if transport else s.min_interval_s, reasoning=cfg.reasoning or s.reasoning, transport=transport, sleep=sleep,
        myr_per_usd=s.myr_per_usd)
    pending = deque(q for q in pl["requests"] if q["key"] not in answered)
    _status(d, state="running", done=len(answered), total=pl["n_requests"], spent_usd=budget.spent,
            remaining_usd=budget.remaining, stop_reason=None, concurrency=workers,
            started_at=datetime.now(timezone.utc).isoformat())
    state, reason, fails, submitted, n_done = "completed", None, 0, 0, len(answered)

    def send(q):
        batch = by_id.loc[q["case_ids"]].reset_index(drop=True)
        msgs = P.messages(cfg.benchmark, q["mode"], batch, cfg.max_examples)
        return batch, client.complete(msgs, cfg.max_output_tokens, budget, seed=cfg.seed)

    def halt_reason(res) -> tuple[str, str] | None:
        if res.status == "refused_budget":
            return "stopped_budget", res.error
        if res.status == "rate_limited":
            return "rate_limited", f"{res.error} (free models: about 20 a minute and a daily cap; resume later)"
        if res.output_cap_exceeded:
            return "output_cap_ignored", (f"reply used {res.completion_tokens} tokens, more than the "
                                          f"{cfg.max_output_tokens} cap: the cost limit cannot be trusted")
        if res.status == "http_error" and res.http_status in (401, 402, 403):
            return "auth_or_payment", res.error
        return None

    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="llm-bench") as pool:
            inflight: dict = {}
            while pending or inflight:
                while pending and len(inflight) < workers and state == "completed":
                    if stop is not None and stop.is_set():
                        state, reason = "stopped_by_user", "stopped from the benchmark page"
                    elif cfg.max_requests and submitted >= cfg.max_requests:
                        state, reason = "paused_request_limit", f"max_requests={cfg.max_requests} reached; resume to continue"
                    else:
                        q = pending.popleft()
                        inflight[pool.submit(send, q)] = q
                        submitted += 1
                if not inflight:
                    break
                finished, _ = wait(inflight, return_when=FIRST_COMPLETED)
                for fut in finished:
                    q = inflight.pop(fut)
                    batch, res = fut.result()
                    parsed = P.parse(cfg.benchmark, res.content, batch) if res.status == "ok" else []
                    _append(d / "requests.jsonl", {"key": q["key"], "mode": q["mode"], "batch_key": q["batch_key"],
                                                   "case_ids": q["case_ids"], "at": datetime.now(timezone.utc).isoformat(),
                                                   "model": info.id, **asdict(res),
                                                   "n_valid": sum(x["status"] == "ok" for x in parsed),
                                                   "spent_after_usd": budget.spent, "remaining_usd": budget.remaining})
                    for x in parsed or [{"case_id": c, "status": "request_failed", "value": None, "raw": None,
                                         "reason": res.error} for c in q["case_ids"]]:
                        if res.status == "refused_budget":
                            x = {**x, "status": "skipped_budget"}
                        _append(d / "predictions.jsonl", {"key": q["key"], "mode": q["mode"], **x})
                    n_done += res.status == "ok"
                    _status(d, done=n_done, spent_usd=budget.spent, remaining_usd=budget.remaining,
                            last_request_status=res.status)
                    fails = 0 if res.status == "ok" else fails + 1
                    h = halt_reason(res) or (("too_many_failures", f"3 requests in a row failed; last: {res.error}")
                                             if fails >= 3 else None)
                    if h and state == "completed":
                        state, reason = h  # stop sending; requests in flight are still recorded
    except Exception as e:  # keep what was saved; the run can be resumed
        state, reason = "failed", f"{type(e).__name__}: {e}"
        raise
    finally:
        client.close()
        reqs = _read_jsonl(d / "requests.jsonl")
        answered_now = {x["key"] for x in reqs if x["status"] == "ok"}
        left = [q for q in pl["requests"] if q["key"] not in answered_now]
        st = _status(d, state=state, stop_reason=reason, done=len(answered_now), spent_usd=budget.spent,
                     remaining_usd=budget.remaining, requests_not_completed=len(left),
                     cases_not_completed=int(sum(q["n_cases"] for q in left)),
                     finished_at=datetime.now(timezone.utc).isoformat())
        evaluate(run_id)
    return st


def set_max_requests(run_id: str, n: int) -> None:
    """Change a run's request limit (e.g. lift a smoke-test pause before resuming)."""
    p = root() / "runs" / run_id / "config.json"
    c = json.loads(p.read_text(encoding="utf-8"))
    c["config"]["max_requests"] = int(n)
    _write_json(p, c)


# ---------------------------------------------------------------------------------------------- evaluation


def predictions(run_id: str) -> pd.DataFrame:
    """Latest record per (case, mode)."""
    rows = _read_jsonl(root() / "runs" / run_id / "predictions.jsonl")
    if not rows:
        return pd.DataFrame(columns=["case_id", "mode", "status", "value", "raw", "reason"])
    df = pd.DataFrame(rows)
    return df.drop_duplicates(["case_id", "mode"], keep="last")[["case_id", "mode", "status", "value", "raw", "reason"]]


def case_table(run_id: str) -> pd.DataFrame:
    """Cases joined with truth (evaluation only) and every mode's prediction, wide."""
    r = load(run_id)
    sid = r["config"]["sample_id"]
    c = pd.read_csv(root() / "samples" / sid / "cases.csv.gz", dtype={"origin": str, "target_month": str})
    t = pd.read_csv(root() / "samples" / sid / "truth.csv.gz")
    df = c.merge(t, on="case_id", how="left")
    pr = predictions(run_id)
    for mode in r["cfg"].modes:
        m = pr[pr["mode"] == mode].set_index("case_id")
        df[f"llm_{mode}"] = df["case_id"].map(m["value"]).astype(float)
        df[f"status_{mode}"] = df["case_id"].map(m["status"]).fillna("not_attempted")
        df[f"reason_{mode}"] = df["case_id"].map(m["reason"])
    return df


def evaluate(run_id: str) -> dict:
    r = load(run_id)
    d, cfg = r["dir"], r["cfg"]
    df = case_table(run_id)
    reqs = _read_jsonl(d / "requests.jsonl")
    rq = pd.DataFrame(reqs)
    usage = {"requests_sent": int(len(rq)), "requests_planned": r["plan"]["n_requests"]}
    if len(rq):
        usage.update(by_status=rq["status"].value_counts().to_dict(), retries=int(rq["retries"].sum()),
                     prompt_tokens=int(rq["prompt_tokens"].fillna(0).sum()),
                     completion_tokens=int(rq["completion_tokens"].fillna(0).sum()),
                     reasoning_tokens=int(rq["reasoning_tokens"].fillna(0).sum()) if "reasoning_tokens" in rq else 0,
                     cost_usd=float(rq["cost_usd"].sum()),
                     cost_by_source=rq.groupby("cost_source")["cost_usd"].sum().to_dict(),
                     requests_without_usage=int(rq["prompt_tokens"].isna().sum()))
    usage.update(budget_usd=cfg.max_spend_usd, remaining_usd=cfg.max_spend_usd - usage.get("cost_usd", 0.0))
    out = {"run_id": run_id, "benchmark": cfg.benchmark, "model": cfg.model, "dry_run": cfg.dry_run,
           "label": "mock (last value; not an LLM)" if cfg.dry_run else cfg.model,
           "sample_id": r["config"]["sample_id"], "prompt_version": r["config"]["prompt_version"],
           "status": json.loads((d / "status.json").read_text(encoding="utf-8")), "usage": usage,
           "modes": {}, "primary": {}, "exploratory": {}, "bootstrap": {}}
    if cfg.benchmark == "skills":
        out["full_sample"] = {"existing": MX.skill_scores(df["existing"].to_numpy(float), df["actual"].to_numpy(float),
                                                          df["p12_origin"].to_numpy(float), df["naive"].to_numpy(float)),
                              "naive": MX.skill_scores(df["naive"].to_numpy(float), df["actual"].to_numpy(float),
                                                       df["p12_origin"].to_numpy(float))}
    else:
        out["full_sample"] = {"existing": MX.cap_scores(df["existing"].to_numpy(float), df["actual"].to_numpy(float),
                                                        df["naive"].to_numpy(float)),
                              "naive": MX.cap_scores(df["naive"].to_numpy(float), df["actual"].to_numpy(float))}
    for mode in cfg.modes:
        out["modes"][mode] = {"statuses": df[f"status_{mode}"].value_counts().to_dict(), "n_cases": int(len(df)),
                              "invalid_rate": float(df[f"status_{mode}"].isin(["invalid", "missing", "unparseable"]).mean()),
                              "request_failure_rate": float((df[f"status_{mode}"] == "request_failed").mean())}
        res = MX.compare(cfg.benchmark, df.assign(llm=df[f"llm_{mode}"]), mode)
        (out["primary"] if mode in P.PRIMARY else out["exploratory"])[mode] = res
        out["bootstrap"][mode] = MX.paired_bootstrap(cfg.benchmark, df.assign(llm=df[f"llm_{mode}"]))
    out = _clean(out)
    _write_json(d / "report.json", out)
    return out


def runs() -> list[dict]:
    d = root() / "runs"
    out = []
    for p in sorted(d.glob("*/config.json"), reverse=True) if d.exists() else []:
        c = json.loads(p.read_text(encoding="utf-8"))
        st_p = p.parent / "status.json"
        st = json.loads(st_p.read_text(encoding="utf-8")) if st_p.exists() else {}
        out.append({"run_id": c["run_id"], "made_at": c["made_at"], "benchmark": c["config"]["benchmark"],
                    "model": c["config"]["model"], "modes": c["config"]["modes"], "dry_run": c["config"]["dry_run"],
                    "horizons": c["config"]["horizons"], "sample_id": c["sample_id"], "free": c["model"].get("free"),
                    "state": st.get("state"), "done": st.get("done"), "total": st.get("total"),
                    "spent_usd": st.get("spent_usd"), "stop_reason": st.get("stop_reason")})
    return out
