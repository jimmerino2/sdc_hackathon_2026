"""CLI for the LLM forecast benchmark. From src/backend, with the backend venv:

  python -m llm_bench.run models                          # free models that take JSON output, and the configured ones
  python -m llm_bench.run plan --benchmark skills         # sample, request count and cost estimate; sends nothing
  python -m llm_bench.run start --benchmark skills --dry-run          # whole pipeline with mock replies, no key needed
  python -m llm_bench.run start --benchmark skills --yes              # live: OPENROUTER_BENCH_MODEL (free by default)
  python -m llm_bench.run start --benchmark skills --model qwen/qwen3.5-9b --yes   # the inexpensive comparison
  python -m llm_bench.run resume <run_id> --yes           # continue a stopped run without repeating answered requests
  python -m llm_bench.run report <run_id>
  python -m llm_bench.run list
A live run needs --yes; without it the cost estimate is printed and nothing is sent.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, openrouter as OR, prompts as P, runner as R


def _cfg(a) -> R.RunConfig:
    s = config.settings()
    horizons = a.horizons or ([3] if a.benchmark == "skills" else [3, 6, 12])
    return R.RunConfig(benchmark=a.benchmark, horizons=horizons, n_series=a.series, n_origins=a.origins,
                       cap_roles=a.cap_roles, cap_max_origins=a.cap_max_origins, modes=a.modes,
                       model=a.model or s.model, batch_size=a.batch_size or s.batch_size,
                       max_output_tokens=a.max_output_tokens or s.max_output_tokens,
                       max_spend_usd=s.max_spend_usd if a.max_spend is None else a.max_spend,
                       few_shot_k=a.few_shot_k, max_examples=a.max_examples, seed=a.seed, dry_run=a.dry_run,
                       max_requests=a.max_requests, reasoning=a.reasoning or s.reasoning, concurrency=a.concurrency)


def _print_plan(e: dict) -> None:
    m = e["model"]
    price = "free" if m["free"] else (f"${m['prompt'] * 1e6:.3f} / ${m['completion'] * 1e6:.3f} per M tokens (in / out)"
                                      + (", OpenRouter reference x margin" if m.get("price_source") == "openrouter_reference" else "")
                                      if m["listed"] else "NO KNOWN PRICE: live runs refused")
    print(f"sample {e['sample_id']}: {e['n_cases']} cases ({e['sample'].get('benchmark')}), modes {', '.join(e['modes'])}")
    print(f"model {m['id']} via {m.get('gateway', 'openrouter')} ({price}); supports: {', '.join(x for x in m['supported'] if x in ('response_format', 'structured_outputs', 'temperature', 'seed', 'reasoning'))}")
    print(f"requests {e['n_requests']}, ~{e['est_prompt_tokens']:,} prompt tokens, at most {e['max_output_tokens_total']:,} output tokens")
    if e["max_cost_usd"] is not None:
        print(f"cost: expected ~${e['expected_cost_usd']:.4f}, at most ${e['max_cost_usd']:.4f}; budget ${e['budget_usd']:.2f}"
              f" -> {'fits' if e['within_budget'] else 'EXCEEDS budget: the run stops when the budget is reached'}")
    print("API key: " + ("set" if e["key_configured"] else "NOT set for this gateway; only --dry-run works"))


def _print_report(rep: dict) -> None:
    st, u = rep["status"], rep["usage"]
    print(f"run {rep['run_id']}  {rep['benchmark']}  {rep['label']}  state={st.get('state')}"
          + (f" ({st.get('stop_reason')})" if st.get("stop_reason") else ""))
    print(f"requests {u['requests_sent']}/{u['requests_planned']}  {u.get('by_status', {})}  retries {u.get('retries', 0)}  "
          f"tokens in {u.get('prompt_tokens', 0):,} out {u.get('completion_tokens', 0):,}  cost ${u.get('cost_usd', 0):.4f} "
          f"{u.get('cost_by_source', {})}")
    key = "mae_pp" if rep["benchmark"] == "skills" else "mae_doublings"
    fs = rep["full_sample"]
    print(f"full sample: existing {key}={fs['existing'].get(key)}, naive {fs['naive'].get(key)} (n={fs['existing']['n']})")
    for group in ("primary", "exploratory"):
        for mode, res in rep[group].items():
            o = res.get("overall") or {}
            line = f"  [{group}] {mode}: valid {res['n_valid']}/{res['n_cases']}"
            if o:
                parts = []
                for m in ("llm", "existing", "naive"):
                    x = o[m]
                    extra = f" dir {x['direction_acc']:.2f}" if x.get("direction_acc") is not None else ""
                    parts.append(f"{m} {x.get(key):.3f}{extra}")
                line += "  " + " | ".join(parts)
                b = rep["bootstrap"].get(mode)
                if b:
                    line += f"  (LLM-existing {b['mean_diff']:+.3f} {b['units']}, 90% {b['p05']:+.3f}..{b['p95']:+.3f})"
            print(line)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m llm_bench.run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "start"):
        p = sub.add_parser(name)
        p.add_argument("--benchmark", choices=["skills", "capability"], default="skills")
        p.add_argument("--horizons", type=int, nargs="+")
        p.add_argument("--series", type=int, default=100)
        p.add_argument("--origins", type=int, default=4)
        p.add_argument("--cap-roles", nargs="+", default=["holdout"], choices=["holdout", "selection"])
        p.add_argument("--cap-max-origins", type=int, default=0)
        p.add_argument("--modes", nargs="+", default=["zero", "few"], choices=list(P.MODES))
        p.add_argument("--model")
        p.add_argument("--batch-size", type=int)
        p.add_argument("--max-output-tokens", type=int)
        p.add_argument("--max-spend", type=float)
        p.add_argument("--few-shot-k", type=int, default=4)
        p.add_argument("--max-examples", type=int, default=10)
        p.add_argument("--seed", type=int, default=20261029)
        p.add_argument("--max-requests", type=int, default=0, help="pause after this many requests (smoke test)")
        p.add_argument("--concurrency", type=int, default=1, help="requests in flight at once")
        p.add_argument("--reasoning", choices=["off", "low", "default"],
                       help="model thinking; on Grafilab anything but off is the model's default thinking, which ignores "
                            "max_tokens: raise --max-output-tokens so the cost cap holds")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--yes", action="store_true", help="confirm a live run after reading the estimate")
    p = sub.add_parser("resume")
    p.add_argument("run_id")
    p.add_argument("--concurrency", type=int, help="override the run's setting")
    p.add_argument("--max-requests", type=int, help="override the run's setting (0 = no limit)")
    p.add_argument("--yes", action="store_true")
    sub.add_parser("report").add_argument("run_id")
    sub.add_parser("list")
    sub.add_parser("models")
    a = ap.parse_args(argv)

    if a.cmd == "models":
        s = config.settings()
        listing = OR.catalog(s.base_url, config.api_key(), s.price_margin)
        print(f"gateway {s.gateway} ({s.base_url})")
        if s.gateway == "openrouter":
            print("free models that accept JSON output:")
        for m in sorted(listing, key=lambda x: x["id"]):
            info = OR.model_info(listing, m["id"])
            if s.gateway == "grafilab":
                print(f"  {m['id']:<40} " + (f"~${info.prompt * 1e6:.3f} / ${info.completion * 1e6:.3f} per M (OpenRouter "
                                             f"{m.get('reference_id')} x {s.price_margin})" if info.listed else "no reference price"))
            elif info.free and "response_format" in info.supported:
                print(f"  {m['id']}  ctx {info.context_length}  {'structured' if 'structured_outputs' in info.supported else 'json'}")
        for label, mid in (("OPENROUTER_BENCH_MODEL", s.model), ("OPENROUTER_BENCH_COMPARE_MODEL", s.compare_model)):
            i = OR.model_info(listing, mid)
            print(f"{label}={mid}: " + ("not listed" if not i.listed else "free" if i.free else
                                         f"${i.prompt * 1e6:.3f} / ${i.completion * 1e6:.3f} per M tokens"))
        return 0
    if a.cmd == "list":
        for r in R.runs():
            print(f"{r['run_id']}  {r['benchmark']:<10} {r['model']:<36} {'dry' if r['dry_run'] else 'live'} "
                  f"{r['state']:<20} {r['done']}/{r['total']}  ${r['spent_usd'] or 0:.4f}")
        return 0
    if a.cmd == "report":
        _print_report(R.evaluate(a.run_id))
        return 0
    if a.cmd == "resume":
        cfg = R.load(a.run_id)["cfg"]
        if not cfg.dry_run and not a.yes:
            print("resume sends live requests: add --yes")
            return 2
        if a.max_requests is not None:
            R.set_max_requests(a.run_id, a.max_requests)
        R.execute(a.run_id, concurrency=a.concurrency)
        _print_report(R.evaluate(a.run_id))
        return 0

    cfg = _cfg(a)
    e = R.estimate(cfg)
    _print_plan(e)
    if a.cmd == "plan":
        return 0
    if not cfg.dry_run:
        if not e["key_configured"]:
            print("no OPENROUTER_BENCH_API_KEY: use --dry-run, or set the key in src/backend/.env")
            return 2
        if not a.yes:
            print("nothing sent. Re-run with --yes to start this live run.")
            return 2
    run_id = R.create(cfg)
    print(f"run {run_id} ...")
    R.execute(run_id)
    _print_report(R.evaluate(run_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
