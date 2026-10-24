"""Run the occupational pipeline end to end: ingest -> normalise -> skills -> emerging -> panel -> backtest -> forecast
-> adoption -> promote.

Usage (from src/backend):
    python -m occupational.run                 # fetch new HN threads / O*NET / survey files, then build everything
    python -m occupational.run --no-pull       # from the local raw cache only
    python -m occupational.run --adzuna        # also take today's Adzuna snapshot (uses up to 16 of the shared
                                               # 20 calls a day; run it on its own day as a habit, e.g. weekly)
Writes data/occupational_forecasting/ (see store.py). A run that fails, or produces no forecast, is recorded in
runs/run_log.jsonl and does not replace latest/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import adoption, backtest as B, demand, emerging, models as M, normalize, store, taxonomy as T
from .sources import adzuna, hn, onet, so_survey

HERE = Path(__file__).parent


def model_version() -> str:
    h = hashlib.sha256()
    for f in sorted([*HERE.glob("*.py"), *(HERE / "sources").glob("*.py")]):
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def _log(msg: str, t0: float) -> None:
    print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)


def ingest(pull: bool, take_adzuna: bool) -> dict:
    health = {"onet": onet.fetch(pull), "hn_whoishiring": hn.fetch(pull), "so_dev_survey": so_survey.fetch(pull)}
    health["adzuna"] = adzuna.collect() if take_adzuna else {"source": "adzuna", "status": "not_requested_this_run"}
    T.reset_caches()
    return health


def build(health: dict, now: datetime, t0: float) -> dict:
    raw = pd.concat([hn.load_ads(), adzuna.load_ads()], ignore_index=True)
    if raw.empty:
        raise RuntimeError("no ads in the raw cache")
    ads = normalize.normalize(raw)
    _log(f"normalised {len(ads)} ads ({int(ads['eligible'].sum())} eligible)", t0)
    store.write_table("normalized/ads.csv.gz", ads[normalize.META_COLS])
    text = ads.set_index("ad_id")["text"]
    store.write_table("normalized/ads_text.csv.gz", ads[["ad_id", "text"]])

    current = pd.Period(now.strftime("%Y-%m"), freq="M")
    hn_months = pd.PeriodIndex(ads.loc[ads["source"] == "hn_whoishiring", "month"], freq="M")
    last = min(current - 1, hn_months.max())
    known = normalize.extract_known(ads)
    _log(f"known skills: {len(known)} ad-skill matches", t0)
    cands = emerging.extract(ads, text)
    _log(f"candidate terms: {cands['key'].nunique()} kinds after filters", t0)
    reg, cand_rows = emerging.build_registry(ads, text, cands, last, data_version="pending")
    ad_skills = pd.concat([known, cand_rows], ignore_index=True).drop_duplicates()
    store.write_table("normalized/ad_skills.csv.gz", ad_skills)

    totals, counts = demand.hn_panel(ads, ad_skills, current)
    store.write_table("datasets/demand_totals.csv", totals)
    store.write_table("datasets/demand_counts.csv.gz", counts)
    store.write_table("datasets/coverage.csv", demand.coverage(ads))
    snaps = demand.adzuna_snapshots(ads, ad_skills)
    store.write_table("datasets/adzuna_snapshots.csv", snaps, allow_empty=True)
    data_version = store.file_hash("datasets/demand_totals.csv", "datasets/demand_counts.csv.gz")
    emerging.mark_deprecated(reg, counts, last)
    reg["data_version"] = data_version
    store.write_json("taxonomy/skill_registry.json", reg)
    _log(f"registry v{reg['version']}: {emerging.tally(reg)}", t0)

    # emerging table: every tracked skill per cell, ranked by the lower bound of its share increase
    full = totals[~totals["is_partial"]]
    ws = emerging.window_stats(counts[counts["month"].isin(full["month"])], full, last)
    e = ads[ads["eligible"] & ads["occupations"].ne("") & ads["countries"].ne("") & (ads["source"] == "hn_whoishiring")]
    e = e.assign(country=e["countries"].str.split("|"), occupation=e["occupations"].str.split("|")).explode("country").explode("occupation")
    recent = e[pd.PeriodIndex(e["month"], freq="M") > last - emerging.RECENT].merge(ad_skills, on="ad_id")
    emp = recent.groupby(["country", "occupation", "skill_id"])["employer_key"].nunique().rename("employers").reset_index()
    ws = ws.merge(emp, on=["country", "occupation", "skill_id"], how="left").fillna({"employers": 0})
    info = pd.DataFrame(reg["skills"]).set_index("skill_id")
    ws = ws.join(info[["name", "status", "origin", "in_onet", "category"]], on="skill_id")
    occ_codes = {o.id: o.onet_codes for o in T.occupations()}
    keys = {s.id: s.keys for s in T.curated()}
    ws["in_onet_for_occupation"] = [
        T.in_onet(keys.get(sid, {T.key(sid[5:])} if sid.startswith("cand:") else set()), occ_codes.get(o, ()))
        for sid, o in zip(ws["skill_id"], ws["occupation"])]
    ws["confidence"] = [emerging.confidence(int(k), int(em), int(mp)) for k, em, mp in
                        zip(ws["k_recent"], ws["employers"], ws["months_present"])]
    ws["meets_evidence_minimum"] = (ws["k_recent"] >= emerging.WEAK["recent_ads"]) & \
        (ws["employers"] >= emerging.WEAK["employers"]) & (ws["months_present"] >= emerging.WEAK["months_present"])
    store.write_table("datasets/emerging.csv", ws.sort_values("growth_lb_pp", ascending=False))

    # discovery back-check: would the detector have found recent skills, and how early?
    as_of = list(pd.period_range(last - 54, last, freq="M")[::-3][::-1])
    bc = emerging.backcheck(ads, text, cands, as_of)
    store.write_table("datasets/discovery_backcheck.csv", bc)
    discovery = _backcheck_summary(bc, totals, counts)
    _log(f"discovery back-check: {sum(d['first_flagged'] is not None for d in discovery)} of {len(discovery)} "
         f"withheld skills flagged", t0)

    # skill-demand models
    panel = B.Panel(totals, counts, reg)
    _log(f"panel: {len(panel.series)} series, {len(panel.cells)} cells, months {panel.months[0]}..{panel.months[-1]}", t0)
    bt = B.run_backtest(panel)
    _log(f"backtest: {len(bt)} scored predictions", t0)
    ev = B.evaluate(bt)
    fc, cards = B.forecast(panel, bt, ev)
    _log(f"forecast: {len(fc)} rows", t0)
    acc = B.cell_accuracy(bt, panel, ev)
    asof = B.asof_rows(bt, panel, ev)
    names = info["name"].to_dict()
    fc["skill_name"] = fc["skill_id"].map(names).fillna(fc["skill_id"])
    fc["skill_status"] = fc["skill_id"].map(info["status"].to_dict())

    # adoption
    store.write_table("adoption/worker_ai_usage.csv", adoption.worker_usage(), allow_empty=True)
    store.write_table("adoption/worker_ai_usage_context.csv", adoption.rps_context(), allow_empty=True)
    store.write_table("adoption/task_exposure.csv", adoption.task_exposure(), allow_empty=True)
    store.write_table("adoption/employer_ai_tool_signal.csv", adoption.employer_signal(totals, counts), allow_empty=True)
    store.write_json("adoption/sources.json", {"sources": adoption.SOURCES, "not_found": adoption.NOT_FOUND})

    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + data_version[:6]
    split = {"test_targets": f"{panel.months[-12]}..{panel.months[-1]}",
             "validation_targets": f"{panel.months[-24]}..{panel.months[-13]}",
             "train_targets": f"..{panel.months[-25]}", "first_origin": str(panel.months[B.MIN_HISTORY - 1])}
    evaluation = {
        "run_id": run_id, "made_at": now.isoformat(), "model_version": model_version(), "data_version": data_version,
        "taxonomy_version": T.taxonomy_version(), "registry_version": reg["version"],
        "target": "Share of an occupation's eligible HN job ads in a country naming the skill, pooled over the 3 "
                  "months ending at the target month", "horizons_months": list(B.HORIZONS), "split": split,
        "rules": {"min_cell_ads_12m": B.MIN_CELL_N12, "min_target_ads": B.MIN_EVAL_N, "ridge_refit_months": B.REFIT,
                  "validated_ratio": B.VALIDATED_RATIO, "material_change_pp": B.MATERIAL_PP},
        "methods": {"persistence": "last 3 months' share", "mean12": "last 12 months' share",
                    "shrink": "3-month share shrunk to 12-month share by evidence", "trend": "damped logit trend",
                    "ridge": "pooled ridge regression on lagged shares, volume and cross-cell skill change",
                    "blend": "average of shrink and ridge"},
        "post_hoc_methods": list(M.POST_HOC),
        "last_complete_month": str(last), "n_series": int(len(panel.series)), "ridge_cards": cards,
        "discovery_backcheck": {"as_of_months": [str(m) for m in as_of], "withheld": list(emerging.WITHHELD),
                                "reference": "12-month share of US software-engineer ads first >= 2%",
                                "skills": discovery}, **ev}
    run_dir = f"runs/{run_id}"
    # validation + test rows only (train scores are in evaluation.json); gitignored, regenerable
    held = bt[bt["role"] != "train"]
    store.write_table(f"{run_dir}/backtest.csv.gz", held.drop(columns=["series"]).round(6).assign(
        **panel.series.loc[held["series"], ["country", "occupation", "skill_id"]].reset_index(drop=True).set_axis(held.index)))
    store.write_json(f"{run_dir}/evaluation.json", evaluation)
    store.write_table(f"{run_dir}/forecast.csv.gz", fc)
    store.write_table(f"{run_dir}/cell_accuracy.csv", acc)
    store.write_table(f"{run_dir}/asof.csv.gz", asof)
    if fc.empty or not all(str(h) in ev["horizons"] for h in B.HORIZONS):
        raise RuntimeError("run produced no forecast; latest/ left unchanged")
    _promote(run_dir)
    _prune_runs(keep=5)
    manifest = {
        "run_id": run_id, "made_at": now.isoformat(), "model_version": model_version(), "data_version": data_version,
        "taxonomy_version": T.taxonomy_version(), "registry_version": reg["version"], "last_complete_month": str(last),
        "partial_month": str(current), "history_start": str(panel.months[0]), "source_health": health,
        "counts": {"ads": int(len(ads)), "eligible": int(ads["eligible"].sum()),
                   "classified": int((ads["eligible"] & ads["occupations"].ne("")).sum()),
                   "series": int(len(panel.series)), "registry": emerging.tally(reg)},
        "served": {h: v["served"] for h, v in ev["horizons"].items()},
        "status": {h: v["status"] for h, v in ev["horizons"].items()}}
    store.write_json("manifest.json", manifest)
    return manifest


def _backcheck_summary(bc: pd.DataFrame, totals: pd.DataFrame, counts: pd.DataFrame, ref_share: float = 0.02) -> list:
    """Per withheld skill: first as-of month flagged (any status / newly_detected), and the month its 12-month share
    of US software-engineer ads first reached ref_share (the point it was plainly in demand)."""
    t = totals[(totals["country"] == "US") & (totals["occupation"] == "software_engineer") & ~totals["is_partial"]]
    t = t.set_index("month")["n_ads"].sort_index()
    out = []
    for sid, g in bc.groupby("skill_id"):
        c = counts[(counts["skill_id"] == sid) & (counts["country"] == "US") &
                   (counts["occupation"] == "software_engineer")].set_index("month")["n_ads_skill"]
        share12 = c.reindex(t.index, fill_value=0).rolling(12).sum() / t.rolling(12).sum()
        reached = share12[share12 >= ref_share]
        flagged, new = g[g["detected"]], g[g["status"] == "newly_detected"]
        out.append({"skill_id": sid, "name": g["name"].iloc[0],
                    "first_flagged": flagged["as_of"].min() if len(flagged) else None,
                    "first_newly_detected": new["as_of"].min() if len(new) else None,
                    "share_reached_2pct_us_swe": reached.index[0] if len(reached) else None,
                    "checks": int(len(g))})
    return out


def _prune_runs(keep: int) -> None:
    runs = sorted(p for p in store.path("runs").iterdir() if p.is_dir())
    for p in runs[:-keep]:
        shutil.rmtree(p)


def _promote(run_dir: str) -> None:
    src, dst = store.path(run_dir), store.path("latest")
    tmp = store.path(".latest.tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if dst.exists():
        shutil.rmtree(dst)
    tmp.rename(dst)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--adzuna", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    now = datetime.now(timezone.utc)
    record = {"started": now.isoformat(), "model_version": model_version()}
    try:
        health = ingest(not a.no_pull, a.adzuna)
        _log(f"ingest: {json.dumps({k: v.get('status') for k, v in health.items()})}", t0)
        m = build(health, now, t0)
        record.update(status="ok", run_id=m["run_id"], served=m["served"], model_status=m["status"])
        print(json.dumps({k: m[k] for k in ("run_id", "last_complete_month", "served", "status")}, indent=2))
        return 0
    except Exception as e:
        record.update(status="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
        print(record["trace"])
        return 1
    finally:
        record["seconds"] = round(time.time() - t0)
        p = store.path("runs", "run_log.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

