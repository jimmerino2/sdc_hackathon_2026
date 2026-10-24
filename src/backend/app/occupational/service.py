"""Read the occupational pipeline's local outputs (data/occupational_forecasting/) for the API.

Nothing here computes a forecast; files are re-read when they change, so a new run shows up without a restart.
Independent of app/outlook and app/forecast (no shared data or models).
"""
from __future__ import annotations

import math
from functools import lru_cache

import pandas as pd

from occupational import store, taxonomy as T


class NotBuilt(RuntimeError):
    pass


@lru_cache(maxsize=32)
def _csv(rel: str, mtime: float) -> pd.DataFrame:
    return store.read_table(rel, dtype={"month": str, "origin_month": str, "target_month": str}, keep_default_na=True)


@lru_cache(maxsize=16)
def _json(rel: str, mtime: float):
    return store.read_json(rel)


def table(rel: str) -> pd.DataFrame:
    p = store.path(rel)
    if not p.exists():
        raise NotBuilt(rel)
    return _csv(rel, p.stat().st_mtime)


def doc(rel: str):
    p = store.path(rel)
    if not p.exists():
        raise NotBuilt(rel)
    return _json(rel, p.stat().st_mtime)


def records(df: pd.DataFrame) -> list[dict]:
    out = []
    for r in df.to_dict("records"):
        out.append({k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()})
    return out


def _clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def _registry() -> dict[str, dict]:
    return {e["skill_id"]: e for e in doc("taxonomy/skill_registry.json")["skills"]}


def meta() -> dict:
    m = doc("manifest.json")
    ev = doc("latest/evaluation.json")
    fc = table("latest/forecast.csv.gz")
    cells = fc.groupby(["occupation", "country"])["ads_12m"].max().reset_index()
    asof = table("latest/asof.csv.gz")
    tot = table("datasets/demand_totals.csv")
    full = tot[~tot["is_partial"].astype(bool)]
    headline = {}
    for h, v in ev["horizons"].items():
        test = v["scores"].get("test", {})
        served, naive = test.get(v["served"], {}), test.get("persistence", {})
        headline[h] = {"served": v["served"], "chosen_on_validation": v["chosen_on_validation"], "status": v["status"],
                       "test_mae_pp": served.get("mae_pp"), "persistence_test_mae_pp": naive.get("mae_pp"),
                       "test_n": served.get("n"), "coverage_80": v["interval_test"].get(v["served"], {}).get("coverage_80"),
                       "interval_width_pp": v["interval_test"].get(v["served"], {}).get("mean_width_pp")}
    return _clean({
        "run_id": m["run_id"], "made_at": m["made_at"], "model_version": m["model_version"],
        "data_version": m["data_version"], "taxonomy_version": m["taxonomy_version"],
        "registry_version": m["registry_version"], "last_complete_month": m["last_complete_month"],
        "partial_month": m["partial_month"], "history_start": m["history_start"],
        "history_months": sorted(full["month"].unique().tolist()),
        "horizons": [int(h) for h in ev["horizons"]], "headline": headline,
        "taxonomy": T.describe(),
        "cells": records(cells.rename(columns={"ads_12m": "ads_last_12m"})),
        "asof_origins": sorted(asof.loc[asof["role"] == "test", "origin_month"].unique().tolist()),
        "source_health": m["source_health"], "counts": m["counts"], "split": ev["split"],
        "target": ev["target"], "rules": ev["rules"], "post_hoc_methods": ev.get("post_hoc_methods", []),
    })


def _cell(country: str, occupation: str, h: int) -> dict:
    acc = table("latest/cell_accuracy.csv")
    a = acc[(acc["country"] == country) & (acc["occupation"] == occupation) & (acc["h"] == h)]
    tot = table("datasets/demand_totals.csv")
    t = tot[(tot["country"] == country) & (tot["occupation"] == occupation)].sort_values("month")
    full = t[~t["is_partial"].astype(bool)]
    return {"ads_last_12m": int(full["n_ads"].tail(12).sum()), "ads_last_month": int(full["n_ads"].iloc[-1]) if len(full) else 0,
            "accuracy": records(a.drop(columns=["country", "occupation", "h"]).sort_values("mae_pp"))}


def skills(country: str, occupation: str, h: int, origin: str | None = None) -> dict:
    reg = _registry()
    em = table("datasets/emerging.csv")
    em = em[(em["country"] == country) & (em["occupation"] == occupation)].set_index("skill_id")
    if origin:
        a = table("latest/asof.csv.gz")
        ev = doc("latest/evaluation.json")
        served = ev["horizons"][str(h)]["served"]
        a = a[(a["country"] == country) & (a["occupation"] == occupation) & (a["h"] == h) &
              (a["origin_month"] == origin) & (a["method"] == served)]
        rows = [{"skill_id": r["skill_id"], "skill_name": reg.get(r["skill_id"], {}).get("name", r["skill_id"]),
                 "forecast": r["forecast"], "actual": r["actual"], "actual_ads": r["actual_n"],
                 "share_12m": r["p12_origin"], "share_3m": r.get("p3_origin"), "target_month": r["target_month"],
                 "model": served}
                for r in records(a)]
        return _clean({"mode": "asof", "origin": origin, "rows": sorted(rows, key=lambda r: -(r["forecast"] or 0)),
                       "cell": _cell(country, occupation, h)})
    fc = table("latest/forecast.csv.gz")
    f = fc[(fc["country"] == country) & (fc["occupation"] == occupation) & (fc["h"] == h)]
    out = []
    for r in records(f):
        e = reg.get(r["skill_id"], {})
        w = em.loc[r["skill_id"]] if r["skill_id"] in em.index else None
        out.append({**r, "category": e.get("category"), "in_onet": e.get("in_onet"), "origin": e.get("origin"),
                    "change_pp_recent_vs_base": None if w is None else w["change_pp"],
                    "growth_lb_pp": None if w is None else w["growth_lb_pp"],
                    "growth_ub_pp": None if w is None else w.get("growth_ub_pp")})
    out.sort(key=lambda r: -(r["share_12m"] or 0))
    return _clean({"mode": "latest", "rows": out, "cell": _cell(country, occupation, h)})


def skill_detail(skill_id: str, country: str, occupation: str) -> dict:
    reg = _registry()
    if skill_id not in reg:
        raise KeyError(skill_id)
    tot = table("datasets/demand_totals.csv")
    cnt = table("datasets/demand_counts.csv.gz")
    t = tot[(tot["country"] == country) & (tot["occupation"] == occupation)].set_index("month").sort_index()
    c = cnt[(cnt["country"] == country) & (cnt["occupation"] == occupation) & (cnt["skill_id"] == skill_id)]
    c = c.set_index("month")["n_ads_skill"].reindex(t.index, fill_value=0)
    hist = pd.DataFrame({"month": t.index, "n_ads": t["n_ads"].values, "n_ads_skill": c.values,
                         "is_partial": t["is_partial"].astype(bool).values})
    full = hist[~hist["is_partial"]]
    k3, n3 = full["n_ads_skill"].rolling(3).sum(), full["n_ads"].rolling(3).sum()
    hist.loc[full.index, "share_3m"] = k3 / n3.where(n3 > 0)
    hist["share_month"] = hist["n_ads_skill"] / hist["n_ads"].where(hist["n_ads"] > 0)
    fc = table("latest/forecast.csv.gz")
    f = fc[(fc["country"] == country) & (fc["occupation"] == occupation) & (fc["skill_id"] == skill_id)]
    bt = table("latest/asof.csv.gz")
    b = bt[(bt["country"] == country) & (bt["occupation"] == occupation) & (bt["skill_id"] == skill_id)]
    snaps = table("datasets/adzuna_snapshots.csv") if store.exists("datasets/adzuna_snapshots.csv") else pd.DataFrame()
    if len(snaps):
        snaps = snaps[(snaps["country"] == country) & (snaps["occupation"] == occupation) & (snaps["skill_id"] == skill_id)]
    return _clean({"skill": reg[skill_id], "country": country, "occupation": occupation,
                   "history": records(hist), "forecast": records(f.sort_values("h")),
                   "backtest": records(b.sort_values(["h", "origin_month"])),
                   "adzuna": records(snaps) if len(snaps) else [], "examples": examples(skill_id, country, occupation)})


def examples(skill_id: str, country: str, occupation: str, n: int = 5) -> list[dict]:
    """The most recent ads in the cell that name the skill (links to the source), for checking the counts."""
    ads = table("normalized/ads.csv.gz")
    sk = table("normalized/ad_skills.csv.gz")
    ids = set(sk.loc[sk["skill_id"] == skill_id, "ad_id"])
    a = ads[ads["ad_id"].isin(ids) & ads["countries"].fillna("").str.split("|").map(lambda c: country in c) &
            ads["occupations"].fillna("").str.split("|").map(lambda o: occupation in o)]
    a = a.sort_values("posted_at", ascending=False).head(n)
    return records(a[["source", "month", "employer", "title_raw", "url"]].fillna(""))


def emerging(country: str, occupation: str) -> dict:
    em = table("datasets/emerging.csv")
    e = em[(em["country"] == country) & (em["occupation"] == occupation)].sort_values("growth_lb_pp", ascending=False)
    reg = _registry()
    rows = []
    for r in records(e):
        g = reg.get(r["skill_id"], {})
        rows.append({**r, "first_seen_any": g.get("first_seen") or r.get("first_seen"), "reason": g.get("reason"),
                     "possible_alias_of": g.get("possible_alias_of"), "evidence": g.get("evidence"),
                     "aliases_seen": g.get("aliases_seen", [])})
    regd = doc("taxonomy/skill_registry.json")
    ev = doc("latest/evaluation.json")
    return _clean({"rows": rows, "registry": {"version": regd["version"], "built_at": regd["built_at"],
                                              "thresholds": regd["thresholds"], "changes": regd.get("changes", [])[:50],
                                              "statuses": pd.Series([s["status"] for s in regd["skills"]]).value_counts().to_dict()},
                   "backcheck": ev.get("discovery_backcheck")})


def adoption(occupation: str) -> dict:
    def opt(rel):
        return table(rel) if store.exists(rel) else pd.DataFrame()
    w = opt("adoption/worker_ai_usage.csv")
    sig = opt("adoption/employer_ai_tool_signal.csv")
    exp = opt("adoption/task_exposure.csv")
    return _clean({
        "worker_usage": records(w[w["occupation"] == occupation]) if len(w) else [],
        "worker_usage_context": records(opt("adoption/worker_ai_usage_context.csv")),
        "employer_signal": records(sig[(sig["occupation"] == occupation) & (sig["month"] >= "2018-01")]) if len(sig) else [],
        "task_exposure": records(exp[exp["occupation"] == occupation]) if len(exp) else [],
        **doc("adoption/sources.json")})


def signals(country: str, occupation: str) -> dict:
    """The skill-emergence engine's output for one cell. Evidence and scenarios are never presented as forecasts:
    `adjusted_forecast` / `rise_probability` are filled only when that model passed its backtest."""
    ev = doc("latest/evaluation.json")
    sev = ev.get("signals") or {"status": "not_built"}
    if sev.get("status") != "ok" or not store.exists("latest/signals.csv.gz"):
        return _clean({"status": sev.get("status", "not_built"), "error": sev.get("error"), "rows": []})
    reg = _registry()
    rows = table("latest/signals.csv.gz")
    rows = rows[(rows["country"] == country) & (rows["occupation"] == occupation)]
    ind = table("latest/signal_indicators.csv") if store.exists("latest/signal_indicators.csv") else pd.DataFrame()
    by_skill = {s: records(g.drop(columns=["skill_id"])) for s, g in ind.groupby("skill_id")} if len(ind) else {}
    cfg = store.read_json("taxonomy/skill_signals.json")
    out = []
    for r in records(rows):
        out.append({**r, "skill_name": reg.get(r["skill_id"], {}).get("name", r["skill_id"]),
                    "indicators": by_skill.get(r["skill_id"], []),
                    "related_skills": [reg.get(s, {}).get("name", s) for s in cfg["skills"].get(r["skill_id"], {}).get("related", [])]})
    out.sort(key=lambda r: (r["signal"] != "accelerating", -(r["adoption_g6"] or -9)))
    test = sev["roles"]["test"]["scores"]
    summary = {m: {k: test[m].get(k) for k in ("n", "mae_pp", "bias_pp", "direction_acc", "selection_score")}
               for m in ("baseline", "control", "hybrid") if m in test}
    return _clean({"status": "ok", "horizon": sev["horizon"], "baseline_method": sev["baseline_method"],
                   "adjusted_forecast": sev["adjusted_forecast"], "radar": {k: sev["radar"][k] for k in
                   ("validated", "hybrid_beats_own_ap_in_bootstrap", "rise_pp", "min_ads_3m")},
                   "radar_test": sev["radar"]["roles"]["test"], "test_summary": summary,
                   "relationship": sev["relationship"], "coverage": sev["coverage"],
                   "package_health": sev.get("package_health"), "sources": cfg["sources"], "rows": out})


def evaluation() -> dict:
    return _clean({**doc("latest/evaluation.json"), "cell_accuracy": records(table("latest/cell_accuracy.csv"))})
