"""Forecast cases: the same targets, origins and realised values the existing models were scored on.

Skills demand (occupational/)
  target    share of a cell's eligible HN ads naming the skill, pooled over the 3 months ending at origin + h months
  origins   the test period of the occupational backtest (targets in the last 12 complete months). The backtest is
            rebuilt in memory by occupational.backtest from the tracked panel tables; its scores equal the committed
            latest/evaluation.json. (latest/backtest.csv.gz is gitignored and can be stale, so it is not read.)
  existing  the method served per horizon in latest/evaluation.json; persistence ("no change") for reference
  sample    up to n_series series (seeded), each at up to n_origins test origins spaced evenly over the test period.
            Eligibility is the backtest's own: modelled at the origin and >= 20 ads in the target window (a count of
            ads, not the outcome), so the LLM and the existing model are scored on identical rows.
AI capability (forecasting/, target frontier_time_horizon)
  target    frontier METR 50% time horizon (minutes) at the snapshot's last complete month + h, per METR suite (unit)
  origins   the served run's holdout origins (model_registry.json); errors on its log2 scale plus minutes
  existing  the capability engine's ensemble (served at 3, 6 and 12 months); naive ("no change") for reference
  inputs    the snapshot that origin used (capability_metr.origins): the same vintage and measurement-lag cut

Leakage rules
  * a case's inputs hold only months <= its origin (the last complete month at the origin)
  * few-shot examples are earlier forecasts whose target window had ended by the case's origin; for capability
    their outcome is read from the case's own snapshot, not from later vintages
  * truth lives in a separate table and is joined only in evaluation
  * anonymous inputs (the primary benchmark) give months as offsets from the origin and no skill, country,
    occupation, model or benchmark names; named inputs (exploratory) add them
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from occupational import backtest as B, models as OM, store as occ_store
from forecasting.targets import capability_metr as C
from forecasting.run import OUT as FC_OUT

SKILL_MONTHS = 36  # history shown per case
EXAMPLE_MONTHS = 24  # history shown per few-shot example
EXAMPLE_LOOKBACK = 24  # few-shot examples come from origins at most this many months before the latest eligible one
CAP_MODELS_MONTHS = 36  # measured models shown: released in the last 36 months before the snapshot's last month


@dataclass
class CaseSet:
    benchmark: str
    cases: pd.DataFrame  # inputs, baselines, strata; no outcomes
    truth: pd.DataFrame  # case_id -> realised values
    meta: dict


def _pct(x) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x) * 100, 3)


def _num(x, nd=3):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def anon_ids(case_ids: list[str], seed: int, prefix: str) -> dict[str, str]:
    """Stable anonymous ids: a seeded permutation, so the id says nothing about the series."""
    order = np.random.default_rng(seed).permutation(len(case_ids))
    return {cid: f"{prefix}{i + 1:04d}" for cid, i in zip(sorted(case_ids), order)}


# ---------------------------------------------------------------------------------------------- skills demand


def skill_panel():
    tot = occ_store.read_table("datasets/demand_totals.csv", dtype={"month": str})
    cnt = occ_store.read_table("datasets/demand_counts.csv.gz", dtype={"month": str})
    reg = occ_store.read_json("taxonomy/skill_registry.json")
    return B.Panel(tot, cnt, reg), reg


def _skill_history(p: B.Panel, row: int, col: int, months: int, named: bool) -> dict:
    lo = max(0, col - months + 1)
    k, n = p.K[row, lo:col + 1], p.N[row, lo:col + 1]
    f = p.f
    d = {"first_month": str(p.months[lo]) if named else -(col - lo),
         # a month with no eligible ads has no share: null, never zero demand
         "ads_naming_skill": [None if nn == 0 else int(kk) for kk, nn in zip(k, n)],
         "eligible_ads": [int(x) for x in n],
         "share_3m_pct": _pct(f["p3"][row, col]), "eligible_ads_3m": int(np.nan_to_num(f["n3"][row, col])),
         "share_12m_pct": _pct(f["p12"][row, col]), "eligible_ads_12m": int(np.nan_to_num(f["n12"][row, col])),
         "share_12m_a_year_earlier_pct": _pct(OM.expit(f["x_lvl"][row, col] - f["x_yoy"][row, col])
                                              if np.isfinite(f["x_yoy"][row, col]) else np.nan),
         "skill_change_across_all_cells_logit_yoy": _num(f["x_skill_yoy"][row, col])}
    if not named:
        d["months_note"] = "offsets from the origin month (0); arrays run from first_month to 0"
    return d


def _skill_label(p: B.Panel, row: int, names: dict) -> dict:
    s = p.series.iloc[row]
    return {"skill": names.get(s["skill_id"], s["skill_id"]), "country": s["country"], "occupation": s["occupation"]}


def skill_cases(horizons=(3,), n_series=100, n_origins=4, seed=20261029, few_shot_k=4,
                panel=None, bt: pd.DataFrame | None = None, evaluation: dict | None = None) -> CaseSet:
    p, reg = panel if panel is not None else skill_panel()
    names = {e["skill_id"]: e["name"] for e in reg["skills"]}
    bt = B.run_backtest(p) if bt is None else bt
    ev = evaluation or occ_store.read_json("latest/evaluation.json")
    wide = bt.pivot_table(index=["series", "origin_idx", "h"], columns="method", values="forecast").reset_index()
    first = bt[bt["method"] == "persistence"].set_index(["series", "origin_idx", "h"])
    keys = p.series.apply(lambda s: f"{s['country']}|{s['occupation']}|{s['skill_id']}", axis=1)
    rows = []
    for h in horizons:
        served = ev["horizons"][str(h)]["served"]
        te = first.reset_index()
        te = te[(te["h"] == h) & (te["role"] == "test")]
        origins = np.sort(te["origin_idx"].unique())
        pick = np.unique(origins[np.linspace(0, len(origins) - 1, min(n_origins, len(origins))).round().astype(int)])
        te = te[te["origin_idx"].isin(pick)]
        elig = sorted(set(keys.loc[te["series"].unique()]))
        rng = np.random.default_rng([seed, h])
        chosen = set(rng.choice(elig, size=min(n_series, len(elig)), replace=False)) if elig else set()
        te = te[keys.loc[te["series"]].isin(chosen).to_numpy()]
        for r in te.itertuples():
            rows.append({"series": r.series, "origin_idx": int(r.origin_idx), "h": h, "existing_method": served,
                         "actual": r.actual, "actual_k": r.actual_k, "actual_n": r.actual_n})
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("no eligible skill-demand cases")
    df = df.merge(wide, on=["series", "origin_idx", "h"], how="left")
    df["case_id"] = [f"sk|{keys[s]}|{p.months[t]}|h{h}" for s, t, h in zip(df["series"], df["origin_idx"], df["h"])]
    df["existing"] = [r[m] for r, m in zip(df.to_dict("records"), df["existing_method"])]
    df["naive"] = df["persistence"]
    df["origin"] = [str(p.months[t]) for t in df["origin_idx"]]
    df["target_month"] = [str(p.months[t + h]) for t, h in zip(df["origin_idx"], df["h"])]
    df["batch_key"] = [f"h{h}|{o}" for h, o in zip(df["h"], df["origin"])]
    df["n3_origin"] = p.f["n3"][df["series"], df["origin_idx"]]
    df["p12_origin"] = p.f["p12"][df["series"], df["origin_idx"]]
    df["p3_origin"] = p.f["p3"][df["series"], df["origin_idx"]]
    df["series_key"] = keys.loc[df["series"]].to_numpy()
    aid = anon_ids(df["case_id"].tolist(), seed, "S")
    df["anon_id"] = df["case_id"].map(aid)
    df["input_anon"] = [json.dumps(_skill_history(p, s, t, SKILL_MONTHS, False)) for s, t in zip(df["series"], df["origin_idx"])]
    df["input_named"] = [json.dumps({**_skill_label(p, s, names), **_skill_history(p, s, t, SKILL_MONTHS, True)})
                         for s, t in zip(df["series"], df["origin_idx"])]
    ex_anon, ex_named, ex_ids = _skill_examples(p, bt, df, few_shot_k, names)
    df["examples_anon"], df["examples_named"], df["example_ids"] = ex_anon, ex_named, ex_ids
    truth = df[["case_id", "actual", "actual_k", "actual_n"]].copy()
    methods = [m for m in OM.METHODS if m in df.columns]
    cases = df.drop(columns=["actual", "actual_k", "actual_n", "series"]).rename(columns={m: f"f_{m}" for m in methods})
    meta = {"target": ev["target"], "split": ev["split"], "evaluation_run": ev["run_id"],
            "served": {str(h): ev["horizons"][str(h)]["served"] for h in horizons}, "units": "share (0-1); errors in pp",
            "months": f"{p.months[0]}..{p.months[-1]}", "methods": methods}
    return CaseSet("skills", cases.reset_index(drop=True), truth, meta)


def _skill_examples(p: B.Panel, bt: pd.DataFrame, df: pd.DataFrame, k: int, names: dict):
    """Per case, up to k earlier forecasts (any curated series) whose 3-month target window had ended by the case's
    origin, nearest in (12-month level, recent deviation, yearly change). Deterministic: ties break on index."""
    out_a, out_n, out_ids = [], [], []
    if k <= 0:
        return ["[]"] * len(df), ["[]"] * len(df), ["[]"] * len(df)
    base = bt[bt["method"] == "persistence"][["series", "origin_idx", "h", "actual", "actual_n"]]
    feats = lambda s, t: np.column_stack([OM.logit(p.f["p12s"][s, t]), np.nan_to_num(p.f["x_dev"][s, t]),
                                          np.nan_to_num(p.f["x_yoy"][s, t])])
    for (h, t), g in df.groupby(["h", "origin_idx"], sort=False):
        pool = base[(base["h"] == h) & (base["origin_idx"] + h <= t) & (base["origin_idx"] >= t - h - EXAMPLE_LOOKBACK)]
        pool = pool.reset_index(drop=True)
        if pool.empty:
            for i in g.index:
                out_a.append((i, "[]")); out_n.append((i, "[]")); out_ids.append((i, "[]"))
            continue
        P = feats(pool["series"].to_numpy(), pool["origin_idx"].to_numpy())
        sd = P.std(0) + 1e-9
        Q = feats(g["series"].to_numpy(), np.full(len(g), t))
        for i, q in zip(g.index, Q):
            dist = (((P - q) / sd) ** 2).sum(1)
            top = np.argsort(dist, kind="stable")[:k]
            ea, en, ids = [], [], []
            for j in top:
                r = pool.iloc[j]
                s, t0 = int(r["series"]), int(r["origin_idx"])
                outcome = {"realised_share_pct": _pct(r["actual"]), "realised_eligible_ads": int(r["actual_n"])}
                hist_a = _skill_history(p, s, t0, EXAMPLE_MONTHS, False)
                hist_a["months_note"] = ("offsets from this example's own origin (0); its target window ended "
                                         f"{t - (t0 + h)} months before the current origin")
                ea.append({"forecast_horizon_months": h, "history": hist_a, "outcome": outcome})
                en.append({"forecast_horizon_months": h, **_skill_label(p, s, names), "origin": str(p.months[t0]),
                           "history": _skill_history(p, s, t0, EXAMPLE_MONTHS, True), "outcome": outcome})
                ids.append({"series": s, "origin_idx": t0, "target_idx": t0 + h})
            out_a.append((i, json.dumps(ea))); out_n.append((i, json.dumps(en))); out_ids.append((i, json.dumps(ids)))
    order = lambda xs: [v for _, v in sorted(xs)]
    return order(out_a), order(out_n), order(out_ids)


# ---------------------------------------------------------------------------------------------- AI capability


def capability_run() -> tuple[str, pd.DataFrame, dict]:
    out = FC_OUT / "frontier_time_horizon"
    reg = json.loads((out / "model_registry.json").read_text(encoding="utf-8"))
    runs = {v["run_id"] for v in reg["promoted"].values()}
    if len(runs) != 1:
        raise RuntimeError(f"capability horizons are served from different runs: {sorted(runs)}")
    run_id = runs.pop()
    bt = pd.read_csv(out / "runs" / run_id / "backtest.csv.gz")
    return run_id, bt, reg


def _steps(v: pd.DataFrame, last: pd.Period, named: bool, months: int | None = None) -> list:
    """The frontier as change points [month, value]: it holds between points. Months <= last only."""
    v = v[v["period"] <= last].sort_values("period")
    if months:
        v = v[v["period"] > last - months]
    pts, prev = [], None
    for per, val in zip(v["period"], v["value"]):
        if prev is None or abs(val - prev) > 1e-9:
            pts.append([str(per) if named else -(last - per).n, round(float(val), 3)])
            prev = val
    if pts and pts[-1][0] != (str(last) if named else 0) and len(v):
        pts.append([str(last) if named else 0, round(float(v["value"].iloc[-1]), 3)])
    return pts


def _cap_input(s, unit: str, last: pd.Period, named: bool, months: int | None = None) -> dict:
    v = s.values[s.values["unit"] == unit]
    m = s.extras["models"].get(unit, pd.DataFrame())
    if len(m):
        m = m.assign(period=m["release_date"].dt.to_period("M"))
        m = m[(m["period"] <= last) & (m["period"] > last - (months or CAP_MODELS_MONTHS))].sort_values(["period", "value"])
    meas = []
    for i, r in enumerate(m.itertuples() if len(m) else []):
        meas.append({"item": r.model if named else f"M{i + 1:02d}",
                     "released": str(r.period) if named else -(last - r.period).n,
                     "value": round(float(r.value), 3), "ci95": [_num(r.ci_low), _num(r.ci_high)]})
    d = {"frontier_change_points": _steps(v, last, named, months), "measured_items": meas}
    if named:
        d.update(snapshot_last_complete_month=str(last), snapshot_kind=s.kind)
    else:
        d["months_note"] = "offsets from the last complete month of the data (0)"
    return d


def capability_cases(horizons=(3, 6, 12), roles=("holdout",), max_origins=0, seed=20261029, few_shot_k=3,
                     data=None, snaps=None) -> CaseSet:
    run_id, bt, reg = capability_run()
    data = data or C.load()
    snaps = snaps or C.origins(data)
    by_origin = {pd.Timestamp(s.origin): s for s in snaps}
    e = bt[(bt["candidate"] == "ensemble") & bt["role"].isin(roles) & bt["actual"].notna() & bt["h"].isin(horizons)]
    naive = bt[bt["candidate"] == "naive"].set_index(["origin", "unit", "h"])["pred"]
    if max_origins:
        keep = sorted(e["origin"].unique())[-max_origins:]
        e = e[e["origin"].isin(keep)]
    rows = []
    for r in e.itertuples():
        s = by_origin[pd.Timestamp(r.origin)]
        last = pd.Period(r.last_period, "M")
        unit_last = s.values.loc[s.values["unit"] == r.unit, "period"].max()
        if unit_last != last:
            raise RuntimeError(f"snapshot at {r.origin} ends {unit_last} for {r.unit}, backtest says {last}")
        cid = f"cap|{r.unit}|{pd.Timestamp(r.origin).strftime('%Y-%m-%d')}|h{r.h}"
        ex_a, ex_n, ex_ids = _cap_examples(snaps, s, r.unit, last, int(r.h), few_shot_k)
        rows.append({"case_id": cid, "origin": str(pd.Timestamp(r.origin)), "origin_last_period": str(last),
                     "h": int(r.h), "unit": r.unit, "role": r.role, "target_month": r.target_period,
                     "snapshot_kind": s.kind, "last_value": r.last_value, "existing": r.pred, "existing_method": "ensemble",
                     "naive": naive.get((r.origin, r.unit, r.h), np.nan), "actual": r.actual,
                     "batch_key": f"{pd.Timestamp(r.origin).isoformat()}",
                     "input_anon": json.dumps(_cap_input(s, r.unit, last, False)),
                     "input_named": json.dumps({"metr_suite": r.unit, **_cap_input(s, r.unit, last, True)}),
                     "examples_anon": json.dumps(ex_a), "examples_named": json.dumps(ex_n), "example_ids": json.dumps(ex_ids)})
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("no eligible capability cases")
    df["anon_id"] = df["case_id"].map(anon_ids(df["case_id"].tolist(), seed, "A"))
    truth = df[["case_id", "actual"]].copy()
    meta = {"target": "frontier METR 50% time horizon (minutes), per METR suite version, at last complete month + h",
            "served_run": run_id, "served": {h: v["model"] for h, v in reg["promoted"].items()}, "roles": list(roles),
            "units": "minutes; errors on log2 scale (doublings) and in minutes"}
    return CaseSet("capability", df.drop(columns=["actual"]), truth, meta)


def _cap_examples(snaps, s, unit: str, last: pd.Period, h: int, k: int):
    """Earlier snapshots of the same unit whose last month + h <= this snapshot's last month. Outcome: this
    snapshot's frontier at that month (what was known at this origin). The k most recent, one per month."""
    if k <= 0:
        return [], [], []
    cur = s.values[s.values["unit"] == unit].set_index("period")["value"]
    seen, ea, en, ids = set(), [], [], []
    for s0 in sorted(snaps, key=lambda x: x.origin, reverse=True):
        if s0.origin >= s.origin:
            continue
        v0 = s0.values[s0.values["unit"] == unit]
        if v0.empty:
            continue
        l0 = v0["period"].max()
        tgt = l0 + h
        if tgt > last or l0 in seen or tgt not in cur.index or not np.isfinite(cur[tgt]):
            continue
        seen.add(l0)
        outcome = {"realised_value": round(float(cur[tgt]), 3)}
        a = _cap_input(s0, unit, l0, False, months=EXAMPLE_MONTHS)
        a["months_note"] = (f"offsets from this example's last complete month (0); its target month was {(last - tgt).n} "
                            "months before the current case's last complete month")
        ea.append({"forecast_horizon_months": h, "history": a, "outcome": outcome})
        en.append({"forecast_horizon_months": h, "metr_suite": unit, "history": _cap_input(s0, unit, l0, True, months=EXAMPLE_MONTHS),
                   "outcome": outcome})
        ids.append({"origin": str(s0.origin), "last_period": str(l0), "target_period": str(tgt), "seen_at": str(s.origin)})
        if len(ea) >= k:
            break
    return ea, en, ids


def sample_id(benchmark: str, params: dict, data_fingerprint: str) -> str:
    blob = json.dumps({"benchmark": benchmark, **params, "data": data_fingerprint}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:10]


def fingerprint(benchmark: str) -> str:
    if benchmark == "skills":
        return occ_store.file_hash("datasets/demand_totals.csv", "datasets/demand_counts.csv.gz",
                                   "taxonomy/skill_registry.json", "latest/evaluation.json")
    run_id, _, _ = capability_run()
    h = hashlib.sha256((FC_OUT / "frontier_time_horizon" / "runs" / run_id / "backtest.csv.gz").read_bytes())
    h.update((C.capability.OUT / "capability_vintages.csv").read_bytes())
    return run_id + ":" + h.hexdigest()[:10]
