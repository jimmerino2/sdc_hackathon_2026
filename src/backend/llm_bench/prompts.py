"""Prompts and response validation.

Modes
  zero         primary: anonymous numbers only (series ids, month offsets; no skill, country, model or benchmark names)
  few          primary: zero + earlier solved forecasts as examples (in-context learning, no weight updates)
  zero_named   exploratory: real names and calendar months; the model may recall what actually happened
  few_named    exploratory: few-shot with real names
Exploratory results are reported apart and never used to pick a winner.

A batch holds cases with one origin (batch_key), so every history and example in a prompt was available at that
origin. Few-shot examples: each case's nearest examples, taken round-robin (each case's best first) up to max_examples.

The reply must be JSON: {"predictions": [{"series_id": "...", "forecast_value": <number>}]}. Values are checked
against the target's valid range; a missing, non-numeric, duplicated or out-of-range value is recorded as such and
never replaced.
"""
from __future__ import annotations

import json
import math
import re

import pandas as pd

PROMPT_VERSION = "2026-10-29.1"
MODES = ("zero", "few", "zero_named", "few_named")
PRIMARY = ("zero", "few")
EXPLORATORY = ("zero_named", "few_named")

SYSTEM = ("You are a careful quantitative forecaster. You receive numerical time series and must return point "
          "forecasts as JSON only. No tools or web access are available. Do not explain your reasoning.")

TASKS = {
    "skills": {
        "anon": ("Each series counts job ads in one anonymous market segment. eligible_ads[i] is the number of eligible "
                 "job ads in the segment in month i; ads_naming_skill[i] is how many of those ads name one particular "
                 "anonymous skill (null when the month had no eligible ads: no observation, not zero demand)."),
        "named": ("Each series counts Hacker News 'Who is hiring?' job ads for one occupation in one country. "
                  "eligible_ads[i] is the number of eligible ads in month i; ads_naming_skill[i] is how many name the "
                  "skill (null when the month had no eligible ads)."),
        "target": ("forecast_value = the percentage of eligible ads naming the skill, pooled over the 3 months ending "
                   "h months after the series' last month: 100 * sum(ads_naming_skill) / sum(eligible_ads) over months "
                   "h-2, h-1 and h (month 0 = the last month shown)."),
        "units": "percent, 0 to 100 (e.g. 4.2 means 4.2% of ads)",
    },
    "capability": {
        "anon": ("Each series is the running record (frontier) of a positive metric: the highest value achieved by any "
                 "item released so far. It never decreases. frontier_change_points lists [month, value] where the "
                 "record changed; it holds between points. measured_items are individual items' values with 95% "
                 "intervals. Growth is often multiplicative, so think on a log scale."),
        "named": ("Each series is the frontier METR 50% task-completion time horizon in minutes: the longest horizon "
                  "of any AI model released so far, as measured by the named METR suite version and published in "
                  "Epoch AI's data at that time. frontier_change_points lists [month, minutes] where the record changed; "
                  "measured_items are individual models with 95% intervals."),
        "target": "forecast_value = the frontier value at month h after the series' last month (month 0).",
        "units": "same units as the series values (positive)",
    },
}


def to_target(benchmark: str, v: float) -> float:
    """Reply units -> the target's own units (skills: percent -> share)."""
    return v / 100 if benchmark == "skills" else v


def valid_range(benchmark: str, case: dict) -> tuple[float, float]:
    if benchmark == "skills":
        return 0.0, 100.0
    return 1e-6, float(case["last_value"]) * 2 ** 12  # 12 doublings above the last record: generous, still finite


def batches(cases: pd.DataFrame, size: int) -> list[pd.DataFrame]:
    """Cases with the same origin (batch_key), in anonymous-id order, chunked."""
    out = []
    for _, g in cases.sort_values(["batch_key", "anon_id"]).groupby("batch_key", sort=True):
        out.extend(g.iloc[i:i + size] for i in range(0, len(g), size))
    return out


def _examples(batch: pd.DataFrame, named: bool, max_examples: int) -> list[dict]:
    col = "examples_named" if named else "examples_anon"
    lists = [json.loads(x) for x in batch[col]]
    ids = [json.loads(x) for x in batch["example_ids"]]
    chosen, seen = [], set()
    for rank in range(max((len(x) for x in lists), default=0)):
        for exs, keys in zip(lists, ids):
            if rank < len(exs) and len(chosen) < max_examples:
                k = json.dumps(keys[rank], sort_keys=True)
                if k not in seen:
                    seen.add(k)
                    chosen.append(exs[rank])
    return [{"example_id": f"E{i + 1:02d}", **e} for i, e in enumerate(chosen)]


def messages(benchmark: str, mode: str, batch: pd.DataFrame, max_examples: int = 10) -> list[dict]:
    if mode not in MODES:
        raise ValueError(mode)
    named, few = mode.endswith("_named"), mode.startswith("few")
    t = TASKS[benchmark]
    series = []
    for r in batch.to_dict("records"):
        lo, hi = valid_range(benchmark, r)
        s = {"series_id": r["anon_id"], "forecast_horizon_months": int(r["h"]),
             **json.loads(r["input_named" if named else "input_anon"])}
        if benchmark == "capability":
            s["valid_range"] = [lo, round(hi, 3)]
        series.append(s)
    rules = ["Return exactly one prediction per series_id listed under series, and nothing else.",
             'Reply with JSON only: {"predictions": [{"series_id": "<id>", "forecast_value": <number>}]}.']
    if not named:
        rules.append("The series are anonymous. Forecast from the numbers given, not from guesses about what they are.")
    if few:
        rules.append("examples are earlier forecasts with their realised outcome, for calibration. Do not forecast them.")
    payload = {"description": t["named" if named else "anon"], "target": t["target"], "units": t["units"],
               **({"valid_range": [0, 100]} if benchmark == "skills" else {}), "rules": rules}
    if few:
        payload["examples"] = _examples(batch, named, max_examples)
    payload["series"] = series
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}]


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def extract_json(text: str):
    t = _FENCE.sub("", (text or "").strip())
    try:
        return json.loads(t)
    except ValueError:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            return json.loads(t[a:b + 1])
        raise


def parse(benchmark: str, content: str | None, batch: pd.DataFrame) -> list[dict]:
    """One record per case: status ok | invalid | missing | unparseable, the value in target units when ok."""
    recs = {r["anon_id"]: r for r in batch.to_dict("records")}
    out = {aid: {"case_id": r["case_id"], "status": "missing", "value": None, "raw": None, "reason": "no prediction"}
           for aid, r in recs.items()}
    try:
        obj = extract_json(content or "")
        preds = obj.get("predictions") if isinstance(obj, dict) else obj
        if not isinstance(preds, list):
            raise ValueError("no predictions list")
    except ValueError as e:
        for o in out.values():
            o.update(status="unparseable", reason=f"reply is not the expected JSON: {str(e)[:120]}")
        return list(out.values())
    seen: dict[str, int] = {}
    for p in preds:
        if not isinstance(p, dict):
            continue
        sid = str(p.get("series_id", "")).strip()
        if sid not in out:
            continue
        seen[sid] = seen.get(sid, 0) + 1
        o = out[sid]
        if seen[sid] > 1:
            o.update(status="invalid", value=None, reason="series_id returned more than once")
            continue
        raw = p.get("forecast_value")
        o["raw"] = raw
        v = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
        if v is None and isinstance(raw, str):
            try:
                v = float(raw.strip().rstrip("%"))
            except ValueError:
                v = None
        lo, hi = valid_range(benchmark, recs[sid])
        if v is None or not math.isfinite(v):
            o.update(status="invalid", reason=f"not a number: {raw!r}"[:120])
        elif not lo <= v <= hi:
            o.update(status="invalid", reason=f"{v} outside valid range [{lo:g}, {hi:g}]")
        else:
            o.update(status="ok", value=to_target(benchmark, float(v)), reason=None)
    return list(out.values())
