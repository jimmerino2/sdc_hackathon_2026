"""One description of every forecast Jobee shows: where it comes from, what it measures, how it was tested, what it
can't tell you. The AI outlook, Occupations and role pages all read this, so the explanations live in one place.

Numbers are read from the pipelines' own outputs when asked for; only definitions and limitations are written here.
What an output doesn't hold stays None and the page says "Not available". Nothing here computes a forecast.
"""
from datetime import datetime

from app.forecast import service as role_forecast
from app.occupational import service as occupational
from app.outlook import service as outlook
from forecasting import contracts
from forecasting.registry import SOURCES

COVERAGE_NOTE = ("Some of Jobee's labour-market forecasts use US historical data because the available Malaysian vacancy data "
                 "does not provide sufficiently consistent historical coverage for the same forecasting methodology. These "
                 "forecasts should therefore be interpreted as broader labour-market signals rather than direct predictions "
                 "of Malaysian vacancy growth.")
MALAYSIA_ROLE = ("No Malaysian source (DOSM, TalentCorp/MyCOL or MASCO) trains or validates these forecasts. DOSM's online vacancy "
                 "counts are kept in Jobee's data as display context only.")

METHOD_NAMES = {
    "naive": "No change", "drift": "Continue last year's trend", "damped_drift": "Trend, slowing down",
    "pooled_mean": "Average recent change across series", "local_trend": "Local trend model", "ridge": "Ridge regression",
    "lightgbm": "LightGBM", "ensemble": "Ensemble of tested methods", "persistence": "No change", "yoy": "Last year's pace repeats",
    "adaptive": "Adaptive blend of recent and long-run shares", "ewma": "Exponentially weighted average",
}
STATUS_TEXT = {
    "validated": "Passed: beat the no-change baseline on held-back data.",
    "baseline": "Baseline selected: no method beat the no-change baseline when methods were chosen.",
    "not_demonstrably_better": "Baseline shown: the chosen method was not demonstrably better than no change.",
    "baseline_retained": "Baseline selected: the chosen method did not outperform no change on held-back data.",
}
ERROR_BAND = "Historical error band"
EMPIRICAL = ("The 10th to 90th percentile of this pipeline's past out-of-sample errors, placed around the forecast. It shows how "
             "far similar forecasts have missed, and isn't a statistical confidence interval.")

# What the outputs don't say: the definition of each target and what it leaves out.
OUTLOOK_TEXT = {
    "btos_ai_use_rate": {
        "title": "Business AI adoption", "population": "US businesses answering the Census Business Trends and Outlook Survey", "denominator": "US businesses in the sector",
        "value_type": "Percentage of firms", "frequency": "Every two weeks", "geography": "United States only",
        "limitations": ["Measures firms, not workers or occupations.", "The question wording changed in Nov 2025, so the two wordings are separate series."],
    },
    "worker_genai_use_rate": {
        "title": "Worker AI adoption", "population": "Employed US adults in the Real-Time Population Survey", "denominator": "Employed US adults in the occupation group",
        "value_type": "Percentage of workers", "frequency": "Quarterly", "geography": "United States only",
        "limitations": ["Self-reported use, with small samples per occupation group.", "Too few quarters exist for a strong backtest."],
    },
    "frontier_time_horizon": {
        "title": "AI capability", "population": "Frontier AI models measured by METR", "denominator": "None: a length of task, not a share",
        "value_type": "Absolute value, in minutes of skilled human work", "frequency": "Monthly", "geography": "Global (models, not a labour market)",
        "limitations": ["It is the task length a model completes at 50% success, not general AI intelligence.",
                        "Measured on METR's software tasks.",
                        "It does not translate into a share of any occupation that can be automated."],
    },
}


def _date(value) -> str | None:
    return str(value)[:10] if value else None


def _months(first: str, last: str) -> int:
    a, b = datetime.strptime(first, "%Y-%m"), datetime.strptime(last, "%Y-%m")
    return (b.year - a.year) * 12 + b.month - a.month + 1


def _horizon_rows(target: str, reg: dict) -> tuple[list[dict], list[dict], dict]:
    """(served model per horizon, its test against the baseline, the newest evaluation), from each horizon's own run."""
    config, tests, newest = [], [], {}
    for h, e in sorted(reg["promoted"].items(), key=lambda kv: int(kv[0])):
        ev = outlook._json(outlook.OUTPUT_DIR / target / "runs" / e["run_id"] / "evaluation.json")
        newest = max(newest, ev, key=lambda x: x.get("made_at", ""))
        row = next((s for s in ev.get("selection", []) if s["h"] == int(h) and s["candidate"] == e["model"]), {})
        naive = next((s for s in ev.get("selection", []) if s["h"] == int(h) and s["candidate"] == "naive"), {})
        cover = next((c for c in ev.get("holdout_interval_coverage_80", []) if c["h"] == int(h) and c["candidate"] == e["model"]), {})
        config.append({"h": int(h), "model": METHOD_NAMES.get(e["model"], e["model"]), "is_baseline": e["model"] == "naive",
                       "status": e["status"], "status_text": STATUS_TEXT.get(e["status"]),
                       "chosen_model": METHOD_NAMES.get(e.get("chosen_model"), e.get("chosen_model"))})
        tests.append({"h": int(h), "model_error": row.get("holdout_mae"), "baseline": "No change", "baseline_error": naive.get("holdout_mae"),
                      "outperformed": None if e["model"] == "naive" or not row or not naive else row.get("holdout_mae") < naive.get("holdout_mae"),
                      "n": row.get("holdout_n"), "origins": row.get("holdout_n_origins"), "coverage_80": cover.get("holdout_coverage_80")})
    return config, tests, newest


def _outlook_info(target: str) -> dict:
    t, text = contracts.TARGETS[target], OUTLOOK_TEXT[target]
    reg = outlook._json(outlook.OUTPUT_DIR / target / "model_registry.json")
    source = SOURCES[t.label_source]
    config, tests, ev = _horizon_rows(target, reg)
    f = outlook._csv(outlook.OUTPUT_DIR / target / "latest_forecast.csv")
    interval = str(f["interval"].iloc[0]) if len(f) else None
    points = outlook.engine(target).get("backtest", {}).get("point", [])  # the capability engine keeps its own coverage
    for row, c in ((r, c) for r, c in zip(tests, config)):
        if row["coverage_80"] is None:
            row["coverage_80"] = next((p.get("coverage_80") for p in points if p["h"] == row["h"] and p["role"] == "holdout" and p["candidate"] == "ensemble"), None)
    health = next(iter(ev.get("source_health", {}).values()), {})
    simulated = bool(interval) and "predictive" in interval
    origins = ev.get("origins", {})
    return {
        "id": target, "title": text["title"],
        "provenance": {"source": source.name, "url": source.url, "geography": text["geography"], "population": text["population"],
                       "period": source.coverage, "last_updated": _date(health.get("last_available_at")), "coverage": list(source.limitations)},
        "measure": {"metric": t.definition, "unit": t.unit, "denominator": text["denominator"], "value_type": text["value_type"]},
        "configuration": {"frequency": text["frequency"], "horizon_unit": t.horizon_unit, "issued": _date(ev.get("made_at")),
                          "last_observation": str(f["last_observed_period"].iloc[0]) if len(f) else None, "horizons": config,
                          "selection_rule": ev.get("selection_rule")},
        "reliability": {"method": "Point-in-time backtest: each method forecast past periods using only the data published then",
                        "window": f"{origins.get('first')} to {origins.get('last')}" if origins else None,
                        "origins": origins.get("total"), "origins_detail": origins.get("by_kind"),
                        "held_back_origins": ev.get("split", {}).get("holdout_origins"), "error_unit": "doublings" if target == "frontier_time_horizon" else "percentage points",
                        "horizons": tests},
        "uncertainty": {"label": "80% predictive interval" if simulated else ERROR_BAND,
                        "how": "Simulated from 5,000 possible futures of the forecasting engine." if simulated else EMPIRICAL, "detail": interval},
        "limitations": text["limitations"],
    }


def _role_info() -> dict:
    m = role_forecast._meta()
    jobs = role_forecast._jobs()
    tests, config = [], []
    for h, v in sorted(m["by_horizon"].items(), key=lambda kv: int(kv[0])):
        s = v["holdout"]["scores"]
        pace, flat = s.get("yoy (last year's pace repeats)", {}), s.get("flat (index unchanged)", {})
        first, last = v["holdout"]["origins"]
        tests.append({"h": int(h), "model_error": pace.get("MAE"), "baseline": "Postings unchanged", "baseline_error": flat.get("MAE"),
                      "outperformed": pace["MAE"] < flat["MAE"] if pace and flat else None, "n": None, "origins": _months(first, last), "coverage_80": None,
                      "machine_learning_error": s.get("LightGBM", {}).get("MAE")})
        config.append({"h": int(h), "model": METHOD_NAMES["yoy"], "is_baseline": True, "status": v["model_status"],
                       "status_text": "Baseline selected: LightGBM did not beat simple baselines in backtesting, so last year's pace is shown.",
                       "chosen_model": METHOD_NAMES["yoy"]})
    source = SOURCES["indeed_postings"]
    published = {s.id: s for s in role_forecast.sources()}
    tracker = published["indeed_ai_tracker"]
    return {
        "id": "role_postings", "title": "Role postings outlook",
        "provenance": {"source": source.name, "url": source.url, "geography": "United States, standing in for Malaysia", "population": "Job postings on Indeed, by sector",
                       "period": source.coverage, "last_updated": _date(jobs["as_of_date"].iloc[0]) if len(jobs) else None, "coverage": list(source.limitations),
                       "license": published["indeed_postings"].license,
                       "also_uses": [{"source": tracker.name, "url": tracker.url, "used_for": tracker.used_for, "license": tracker.license, "last_updated": tracker.as_of}]},
        "measure": {"metric": "Expected change in the role's sector postings index, blended across its sectors", "unit": "percent change from today",
                    "denominator": "The sector's postings index today", "value_type": "Growth rate of postings (not a vacancy count)"},
        "configuration": {"frequency": "Monthly", "horizon_unit": "month", "issued": _date(jobs["as_of_date"].iloc[0]) if len(jobs) else None,
                          "last_observation": str(jobs["forecast_from"].iloc[0]) if len(jobs) else None, "horizons": config, "selection_rule": m.get("headline_method")},
        "reliability": {"method": "Holdout backtest on sector postings; compared with simple baselines", "window": f"{config and m['by_horizon'][str(config[-1]['h'])]['holdout']['origins'][0]} to {m['by_horizon'][str(config[0]['h'])]['holdout']['origins'][1]}",
                        "origins": None, "origins_detail": None, "held_back_origins": None, "error_unit": "index points", "horizons": tests},
        "uncertainty": {"label": ERROR_BAND, "how": EMPIRICAL, "detail": "10-90% of backtest errors of the shown method, same width for every sector"},
        "limitations": ["A role has no postings history of its own: its number is its sector's trend.",
                        "Indeed postings are not hires or employment.",
                        "AI futures shift growth by the role's AI exposure using an assumed effect that was not learned from data."],
    }


def _skill_info() -> dict:
    m = occupational.meta()
    ev = occupational.doc("latest/evaluation.json")
    tests, config = [], []
    for h, v in sorted(m["headline"].items(), key=lambda kv: int(kv[0])):
        is_base = v["served"] == "persistence"
        tests.append({"h": int(h), "model_error": v["test_mae_pp"], "baseline": "No change", "baseline_error": v["persistence_test_mae_pp"],
                      "outperformed": None if is_base or v["test_mae_pp"] is None else v["test_mae_pp"] < v["persistence_test_mae_pp"],
                      "n": v["test_n"], "origins": None, "coverage_80": v["coverage_80"]})
        config.append({"h": int(h), "model": METHOD_NAMES.get(v["served"], v["served"]), "is_baseline": is_base, "status": v["status"],
                       "status_text": STATUS_TEXT.get(v["status"]), "chosen_model": METHOD_NAMES.get(v["chosen_on_validation"], v["chosen_on_validation"])})
    split = m["split"]
    return {
        "id": "skill_demand", "title": "Skill demand",
        "provenance": {"source": "Hacker News “Who is hiring?” posts", "url": "https://news.ycombinator.com/submitted?id=whoishiring",
                       "geography": f"{len(m['taxonomy']['countries'])} countries, mostly US; no Malaysian series", "population": "Tech job ads posted on Hacker News, four occupations",
                       "period": f"{m['history_start']} to {m['last_complete_month']}", "last_updated": _date(m["made_at"]),
                       "coverage": [f"{m['counts']['eligible']:,} eligible ads of {m['counts']['ads']:,} read", f"{m['partial_month']} is still collecting and isn't used"]},
        "measure": {"metric": "Share of sampled Hacker News job advertisements mentioning a particular skill", "unit": "percent of ads",
                    "denominator": "Eligible Hacker News ads for that occupation and country, pooled over 3 months",
                    "value_type": "Mentions in job advertisements. Not the share of all jobs, not Malaysian vacancies, not a vacancy count"},
        "configuration": {"frequency": "Monthly", "horizon_unit": "month", "issued": _date(m["made_at"]), "last_observation": m["last_complete_month"],
                          "horizons": config, "selection_rule": "Lowest error on validation months; the test months only check the choice"},
        "reliability": {"method": "Train, validation and untouched test periods", "window": split.get("test_targets"), "origins": None, "origins_detail": None,
                        "held_back_origins": None, "error_unit": "percentage points", "horizons": tests},
        "uncertainty": {"label": ERROR_BAND, "how": "Built from past errors of the method. The coverage figures below show how often the band held the actual value.", "detail": None},
        "limitations": ["Tech companies and US startups are over-represented: a dated record, not the whole labour market.",
                        "An ad hiring for several occupations counts for each of them.",
                        "Adzuna is a cross-check on current ads only. It never trains a model.",
                        f"Rules in force: at least {ev['rules'].get('min_target_ads')} ads to test a forecast."],
    }


def _emerging_info() -> dict:
    reg = occupational.doc("taxonomy/skill_registry.json")
    th = reg["thresholds"]
    strong, weak = th["strong"], th["weak"]
    return {
        "source": "Hacker News “Who is hiring?” posts",
        "kind": "An observed rise in job ads, not a forecast",
        "rule": f"A skill's share in the last {th['recent_months']} months is compared with the {th['base_months']} months before, ranked by the lower bound of its growth.",
        "strong": f"Strong evidence: at least {strong['recent_ads']} recent ads from {strong['employers']} employers across {strong['months_present']} months.",
        "weak": f"Weak evidence: at least {weak['recent_ads']} recent ads from {weak['employers']} employers across {weak['months_present']} months. Treat these as leads only.",
        "history": f"A skill counts as newly detected only if first seen in the last {th['new_months']} months.",
        "built": _date(reg.get("built_at")),
    }


def _scenarios() -> dict:
    m = role_forecast._meta()
    effect = m.get("scenario_effect_assumption_12m", {})
    return {
        "summary": ("The three AI futures are assumptions about possible developments, not predictions. They shift a role's 12-month postings "
                    "growth by the assumed effect times how far the role's AI exposure is from the average role. The effect is an assumption, "
                    "not learned from data."),
        "futures": [{"scenario": k, "tab": tab, "effect_12m": effect.get(k)} for k, tab in (("Rapid AI", "AI accelerates"), ("Baseline", "AI holds steady"), ("Slow", "AI slows down"))],
        "chances": ("Where a percentage is shown next to a future, it comes from the chosen AI metric's own forecast: the chance that metric grows faster, "
                    "at the same pace or slower than over the past year. It says nothing about job postings, and when that metric has no such "
                    "forecast no chance is shown."),
    }


def describe() -> dict:
    """Everything the transparency panels show. A pipeline whose output is missing is left out; the others still answer."""
    forecasts: dict[str, dict] = {}
    for target in outlook.targets():
        if target in OUTLOOK_TEXT:
            forecasts[target] = _outlook_info(target)
    forecasts["role_postings"] = _role_info()
    emerging = None
    try:
        forecasts["skill_demand"] = _skill_info()
        emerging = _emerging_info()
    except occupational.NotBuilt as e:
        print(f"Occupational methodology unavailable ({e})")
    return {"forecasts": forecasts, "emerging": emerging, "scenarios": _scenarios(),
            "geography": {"note": COVERAGE_NOTE, "malaysia": MALAYSIA_ROLE}}
