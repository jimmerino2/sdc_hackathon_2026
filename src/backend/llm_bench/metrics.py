"""Scores, using each benchmark's existing definitions.

Skills (as occupational.backtest.metrics): errors in percentage points of share. A case is a material move when
|actual - 12-month share at the origin| >= 2 pp; direction accuracy is the share of material moves whose forecast moved
the same way from the 12-month share. Rising / falling bias: mean signed error on material rises / falls. Stable:
mean absolute error on the rest. Groups: ads in the 3 months before the origin (<60, 60-199, >=200, as the interval
buckets) and 12-month share level.
Capability (as the capability engine's point scores): errors on log2 minutes (doublings), typical factor 2^MAE, and on
minutes; MASE against naive.

Every comparison is paired: a method is scored only on the cases where the LLM mode being compared produced a valid
value, and the existing model and naive are scored on exactly those cases too.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MATERIAL_PP = 2.0
VOLUME = ((0, 60, "<60 ads"), (60, 200, "60-199 ads"), (200, np.inf, ">=200 ads"))
LEVEL = ((0, 0.005, "<0.5%"), (0.005, 0.02, "0.5-2%"), (0.02, 0.05, "2-5%"), (0.05, 0.10, "5-10%"), (0.10, 1.01, ">=10%"))


def _f(x):
    return None if x is None or not np.isfinite(x) else float(x)


def skill_scores(f: np.ndarray, a: np.ndarray, p12: np.ndarray, naive: np.ndarray | None = None) -> dict:
    err = (f - a) * 100
    d = {"n": int(len(f)), "mae_pp": _f(np.abs(err).mean()) if len(f) else None,
         "bias_pp": _f(err.mean()) if len(f) else None, "rmse_pp": _f(np.sqrt((err ** 2).mean())) if len(f) else None}
    move = (a - p12) * 100
    mat = np.abs(move) >= MATERIAL_PP
    d["n_material"] = int(mat.sum())
    d["direction_acc"] = _f((np.sign(f[mat] - p12[mat]) == np.sign(a[mat] - p12[mat])).mean()) if mat.any() else None
    d["stable_mae_pp"] = _f(np.abs(err[~mat]).mean()) if (~mat).any() else None
    up, down = mat & (move > 0), mat & (move < 0)
    d["rising_n"], d["falling_n"] = int(up.sum()), int(down.sum())
    d["rising_bias_pp"] = _f(err[up].mean()) if up.any() else None
    d["falling_bias_pp"] = _f(err[down].mean()) if down.any() else None
    if naive is not None and len(f):
        nm = np.abs((naive - a) * 100).mean()
        d["mae_ratio_vs_naive"] = _f(np.abs(err).mean() / nm) if nm > 0 else None
    return d


def cap_scores(f: np.ndarray, a: np.ndarray, naive: np.ndarray | None = None) -> dict:
    e = np.log2(f) - np.log2(a)
    d = {"n": int(len(f))}
    if not len(f):
        return d
    mae = float(np.abs(e).mean())
    d.update(mae_doublings=mae, median_ae_doublings=float(np.median(np.abs(e))), bias_doublings=float(e.mean()),
             rmse_doublings=float(np.sqrt((e ** 2).mean())), typical_factor=float(2 ** mae),
             mae_minutes=float(np.abs(f - a).mean()), median_ape=float(np.median(np.abs(f - a) / a)),
             bias_minutes=float((f - a).mean()))
    if naive is not None:
        nm = float(np.abs(np.log2(naive) - np.log2(a)).mean())
        d["mase_vs_naive"] = _f(mae / nm) if nm > 0 else None
    return d


def _groups(df: pd.DataFrame, by: str, labels) -> list[tuple[str, pd.DataFrame]]:
    out = []
    for lo, hi, name in labels:
        g = df[(df[by] >= lo) & (df[by] < hi)]
        if len(g):
            out.append((name, g))
    return out


def compare(benchmark: str, df: pd.DataFrame, mode: str) -> dict:
    """df: one row per case with existing, naive, actual, llm (NaN where the LLM failed) and strata."""
    ok = df[df["llm"].notna()]

    def score(g: pd.DataFrame) -> dict:
        if benchmark == "skills":
            p12 = g["p12_origin"].to_numpy(float)
            a, nv = g["actual"].to_numpy(float), g["naive"].to_numpy(float)
            return {m: skill_scores(g[c].to_numpy(float), a, p12, nv) for m, c in
                    (("llm", "llm"), ("existing", "existing"), ("naive", "naive"))}
        a, nv = g["actual"].to_numpy(float), g["naive"].to_numpy(float)
        return {m: cap_scores(g[c].to_numpy(float), a, nv) for m, c in
                (("llm", "llm"), ("existing", "existing"), ("naive", "naive"))}

    out = {"mode": mode, "n_cases": int(len(df)), "n_valid": int(len(ok)), "overall": score(ok) if len(ok) else {},
           "by_h": {str(h): score(g) for h, g in ok.groupby("h")},
           "by_origin": {str(o): score(g) for o, g in ok.groupby("origin")}}
    if benchmark == "skills":
        out["by_volume"] = {n: score(g) for n, g in _groups(ok, "n3_origin", VOLUME)}
        out["by_level"] = {n: score(g) for n, g in _groups(ok, "p12_origin", LEVEL)}
    if len(ok):
        out["verdict"] = verdict(benchmark, out["overall"])
    return out


def verdict(benchmark: str, s: dict) -> dict:
    """Lower error than the existing model on the paired cases? Direction too, for skills. No claim beyond that."""
    key = "mae_pp" if benchmark == "skills" else "mae_doublings"
    llm, ex = s["llm"].get(key), s["existing"].get(key)
    v = {"metric": key, "llm": llm, "existing": ex,
         "llm_lower_error": None if llm is None or ex is None else llm < ex}
    if benchmark == "skills":
        v["llm_better_direction"] = (None if s["llm"].get("direction_acc") is None or s["existing"].get("direction_acc") is None
                                     else s["llm"]["direction_acc"] > s["existing"]["direction_acc"])
    return v


def paired_bootstrap(benchmark: str, df: pd.DataFrame, n: int = 2000, seed: int = 0) -> dict | None:
    """90% interval of mean |error|(LLM) - mean |error|(existing) over resampled cases: is the gap more than noise?"""
    ok = df[df["llm"].notna()]
    if len(ok) < 10:
        return None
    if benchmark == "skills":
        el, ee = np.abs(ok["llm"] - ok["actual"]) * 100, np.abs(ok["existing"] - ok["actual"]) * 100
    else:
        el = np.abs(np.log2(ok["llm"]) - np.log2(ok["actual"]))
        ee = np.abs(np.log2(ok["existing"]) - np.log2(ok["actual"]))
    d = (el - ee).to_numpy()
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return {"mean_diff": float(d.mean()), "p05": float(np.quantile(means, 0.05)), "p95": float(np.quantile(means, 0.95)),
            "units": "pp" if benchmark == "skills" else "doublings", "n": int(len(d)),
            "note": "LLM minus existing; negative = LLM closer. Cases share origins, so this interval is optimistic."}
