"""Rolling-origin backtest, locked holdout, metrics, model selection and source ablations, for any TargetSpec.

At each origin (spec.origins) and horizon h, every candidate is fitted on that origin's snapshot only and predicts
last + h for each unit. It is scored against spec.truth (the latest data) in percentage points. Pairs whose outcome
is not published are unavailable, never zero error.

Split, decided before any model is scored:
  holdout   the last spec.holdout_share of origins that can be scored at the longest horizon (at least
            spec.min_holdout), and every later origin. Never used to choose or tune anything.
  selection every earlier origin, *purged*: an (origin, h) pair is dropped when last + h lies after the last period
            observed at the first holdout origin, so selection never sees an outcome from the holdout period.
Selection rule (fixed in advance): lowest mean absolute error in pp over the selection pairs; a simpler candidate
within NEAR_BEST of the best wins. The chosen model is then scored once on the holdout, next to the naive baseline.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import features as F
from .models import BASELINES, CANDIDATES

NEAR_BEST = 0.02
REGIME_TOL = 0.25  # a change in the rate of improvement counts only beyond +-25% of the trailing rate
REGIME_TOL_FLOOR = 0.02  # ... and beyond this absolute amount per period (model scale), so a flat trend is not
                         # called accelerating on noise
REGIMES = ("acceleration", "stable", "slowdown")


@dataclass
class Split:
    holdout_start: pd.Timestamp  # origin time of the first holdout origin
    holdout_last: object  # last period observed at that origin: selection may only score outcomes up to here
    n_selection: int
    n_holdout: int


def check_chronological(snaps: list[F.Snapshot]) -> None:
    assert all(a.origin < b.origin for a, b in zip(snaps, snaps[1:])), "origins must be strictly increasing"
    assert all(a.last <= b.last for a, b in zip(snaps, snaps[1:])), "observed periods must not go backwards"


def make_split(spec, snaps: list[F.Snapshot], latest_period) -> Split:
    scorable = [s for s in snaps if s.last + max(spec.horizons) <= latest_period]
    if len(scorable) < spec.min_holdout + 1:
        raise ValueError(f"{spec.id}: only {len(scorable)} origins can be scored at h={max(spec.horizons)}")
    k = max(spec.min_holdout, int(round(spec.holdout_share * len(scorable))))
    first = scorable[-k]
    sel = [s for s in snaps if s.origin < first.origin]
    return Split(first.origin, first.last, len(sel), len(snaps) - len(sel))


def role(s: F.Snapshot, h: int, split: Split) -> str:
    if s.origin >= split.holdout_start:
        return "holdout"
    return "selection" if s.last + h <= split.holdout_last else "purged"


def backtest(spec, snaps: list[F.Snapshot], y_true: pd.Series, split: Split, candidates=None,
             feature_sets=None) -> pd.DataFrame:
    """One row per origin x horizon x candidate x feature set x unit, with prediction, outcome and split role."""
    candidates = candidates or list(CANDIDATES)
    feature_sets = feature_sets or {"all": spec.features}
    rows = []
    for s in snaps:
        panel = spec.panel(s)  # the snapshot's own series, for models that read it (local_trend)
        now = F.latest_rows(spec, s)
        if now.empty:
            continue
        lvl = now["lvl"].to_numpy()
        inv = spec.scale.from_model
        for h in spec.horizons:
            train = F.labelled(spec, s, h)
            if train.empty:
                continue
            target = s.last + h
            obs = np.array([y_true.get((target, u), np.nan) for u in now["unit"]])
            for fs_name, feats in feature_sets.items():
                for c in candidates:
                    cls = CANDIDATES[c]
                    if fs_name != "all" and not cls.uses_features:
                        continue  # baselines do not change under an ablation
                    d = cls().fit(train, h, feats, spec.trend_steps, panel).predict(now)
                    rows.append(pd.DataFrame({
                        "origin": s.origin, "last_period": spec.label(s.last), "vintage_kind": s.kind,
                        "vintage": s.vintage, "h": h, "target_period": spec.label(target), "role": role(s, h, split),
                        "candidate": c, "feature_set": fs_name, "unit": now["unit"].to_numpy(),
                        "segment": [spec.segment(u) for u in now["unit"]], "last_value": inv(lvl),
                        "lvl": lvl, "trend": now["trend"].to_numpy(), "pred": inv(lvl + d), "pred_change": d, "actual": obs, "n_train": len(train)}))
    out = pd.concat(rows, ignore_index=True)
    if spec.errors_on_model_scale:  # e.g. doublings: a 20% miss counts the same at 10 and at 1,000 minutes
        out["error"] = (out["lvl"] + out["pred_change"]) - spec.scale.to_model(out["actual"].to_numpy())
    else:
        out["error"] = out["pred"] - out["actual"]
    out["resid"] = spec.scale.to_model(out["actual"].to_numpy()) - (out["lvl"] + out["pred_change"])  # model scale
    out.loc[out["actual"].isna(), "resid"] = np.nan
    return out


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual"])
    if d.empty:
        return {"n": 0, "n_origins": 0, "mae": None, "rmse": None, "bias": None}
    return {"n": int(len(d)), "n_origins": int(d["origin"].nunique()),
            "mae": float(d["error"].abs().mean()), "rmse": float(np.sqrt((d["error"] ** 2).mean())),
            "bias": float(d["error"].mean())}


def select(bt: pd.DataFrame, min_selection_origins: int = 12) -> pd.DataFrame:
    """Per horizon: selection-period scores, the chosen candidate, and its one holdout score next to naive."""
    out = []
    base = bt[bt["feature_set"] == "all"]
    for h, g in base.groupby("h"):
        sel = g[g["role"] == "selection"]
        n_sel = sel.dropna(subset=["actual"])["origin"].nunique()
        scores = {c: metrics(sel[sel["candidate"] == c]) for c in CANDIDATES if c in set(g["candidate"])}
        valid = {c: v["mae"] for c, v in scores.items() if v["mae"] is not None}
        chosen = "naive"  # nothing scorable -> the baseline, never an untested model
        if valid:
            best = min(valid.values())
            chosen = min((c for c, m in valid.items() if m <= best * (1 + NEAR_BEST)),
                         key=lambda c: CANDIDATES[c].complexity)
        hold = g[g["role"] == "holdout"]
        for c, v in scores.items():
            hv = metrics(hold[hold["candidate"] == c])
            out.append({"h": h, "candidate": c, "is_baseline": c in BASELINES, "chosen": c == chosen,
                        "selection_mae": v["mae"], "selection_rmse": v["rmse"],
                        "selection_n_origins": v["n_origins"], "holdout_mae": hv["mae"],
                        "holdout_rmse": hv["rmse"], "holdout_bias": hv["bias"],
                        "holdout_n_origins": hv["n_origins"], "holdout_n": hv["n"],
                        "insufficient_history": n_sel < min_selection_origins})
    t = pd.DataFrame(out)
    naive = t[t["candidate"] == "naive"].set_index("h")
    t["selection_mase_vs_naive"] = t["selection_mae"] / t["h"].map(naive["selection_mae"])
    t["holdout_mase_vs_naive"] = t["holdout_mae"] / t["h"].map(naive["holdout_mae"])
    if "drift" in set(t["candidate"]):  # for trending series "no change" is weak; trend extrapolation is the bar
        drift = t[t["candidate"] == "drift"].set_index("h")
        t["holdout_mase_vs_drift"] = t["holdout_mae"] / t["h"].map(drift["holdout_mae"])
    return t


def interval_quantiles(bt: pd.DataFrame, roles: tuple[str, ...], q=(0.1, 0.9)) -> pd.DataFrame:
    """Empirical quantiles of out-of-sample residuals (model scale) per candidate and horizon (split conformal)."""
    d = bt[(bt["feature_set"] == "all") & bt["role"].isin(roles)].dropna(subset=["resid"])
    return d.groupby(["candidate", "h"])["resid"].quantile(list(q)).unstack()


def coverage(bt: pd.DataFrame, qs: pd.DataFrame) -> pd.DataFrame:
    """Share of holdout outcomes inside the 10-90% range built from selection-period residuals only."""
    d = bt[(bt["feature_set"] == "all") & (bt["role"] == "holdout")].dropna(subset=["resid"])
    rows = []
    for (c, h), g in d.groupby(["candidate", "h"]):
        if (c, h) not in qs.index:
            continue
        lo, hi = qs.loc[(c, h)]
        rows.append({"candidate": c, "h": h, "holdout_coverage_80": float(g["resid"].between(lo, hi).mean()),
                     "n": len(g)})
    return pd.DataFrame(rows)


def ablation_table(bt: pd.DataFrame) -> pd.DataFrame:
    """Selection-period MAE of each feature-using model with each feature group removed (holdout shown, not used)."""
    rows = []
    d = bt[bt["candidate"].isin([c for c, k in CANDIDATES.items() if k.uses_features])]
    for (c, fs, h), g in d.groupby(["candidate", "feature_set", "h"]):
        sel, hold = metrics(g[g["role"] == "selection"]), metrics(g[g["role"] == "holdout"])
        rows.append({"candidate": c, "feature_set": fs, "h": h, "selection_mae": sel["mae"],
                     "holdout_mae": hold["mae"], "selection_n_origins": sel["n_origins"]})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    full = t[t["feature_set"] == "all"].set_index(["candidate", "h"])["selection_mae"]
    t["selection_mae_change_vs_all"] = [None if m is None or full.get((c, h)) is None else m - full.get((c, h))
                                        for m, c, h in zip(t["selection_mae"], t["candidate"], t["h"])]
    return t


def breakdown(bt: pd.DataFrame, sel: pd.DataFrame) -> list[dict]:
    """Chosen model and naive, by role x vintage kind x segment: where the scores come from."""
    out = []
    d = bt[bt["feature_set"] == "all"]
    for h in sorted(d["h"].unique()):
        chosen = sel[(sel["h"] == h) & sel["chosen"]]["candidate"].iloc[0]
        for (r, k, seg), g in d[d["h"] == h].groupby(["role", "vintage_kind", "segment"]):
            for c in sorted({chosen, "naive"}):
                m = metrics(g[g["candidate"] == c])
                if m["n"]:
                    out.append({"h": int(h), "role": r, "vintage_kind": k, "segment": seg, "candidate": c, **m})
    return out


def regime_bounds(trend: np.ndarray, h: int, trend_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Change over the next h periods (model scale) beyond which the rate counts as faster / slower than the
    trailing rate (trend / trend_steps per period), with tolerance REGIME_TOL (relative) and REGIME_TOL_FLOOR."""
    rate = np.nan_to_num(np.asarray(trend, dtype=float)) / trend_steps
    tol = np.maximum(REGIME_TOL * np.abs(rate), REGIME_TOL_FLOOR)
    return (rate - tol) * h, (rate + tol) * h


def regime_of(change: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return np.where(change > hi, "acceleration", np.where(change < lo, "slowdown", "stable"))


def regime_probs(pred_change: np.ndarray, resid: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """P(acceleration, stable, slowdown) per row: the forecast change plus each earlier out-of-sample residual,
    counted against the row's bounds. Rows sum to 1."""
    sims = np.asarray(pred_change)[:, None] + np.asarray(resid)[None, :]
    acc = (sims > np.asarray(hi)[:, None]).mean(axis=1)
    slow = (sims < np.asarray(lo)[:, None]).mean(axis=1)
    return np.column_stack([acc, 1 - acc - slow, slow])


def regime_scores(spec, bt: pd.DataFrame, sel: pd.DataFrame) -> list[dict]:
    """Brier score of the regime probabilities on the holdout, for the chosen model, against climatology (the
    selection period's regime frequencies) and a uniform 1/3 each. Probabilities use selection residuals only."""
    out = []
    d = bt[bt["feature_set"] == "all"]
    for h in spec.horizons:
        chosen = sel[(sel["h"] == h) & sel["chosen"]]["candidate"].iloc[0]
        g = d[(d["h"] == h) & (d["candidate"] == chosen)].dropna(subset=["resid"])
        selr, hold = g[g["role"] == "selection"], g[g["role"] == "holdout"]
        if selr.empty or hold.empty:
            out.append({"h": int(h), "candidate": chosen, "n": 0, "brier_model": None, "brier_climatology": None,
                        "brier_uniform": None})
            continue

        def realised(x):
            lo, hi = regime_bounds(x["trend"].to_numpy(), h, spec.trend_steps)
            change = spec.scale.to_model(x["actual"].to_numpy()) - x["lvl"].to_numpy()
            return regime_of(change, lo, hi), lo, hi

        sel_reg, _, _ = realised(selr)
        hold_reg, lo, hi = realised(hold)
        onehot = np.column_stack([hold_reg == r for r in REGIMES]).astype(float)
        p_model = regime_probs(hold["pred_change"].to_numpy(), selr["resid"].to_numpy(), lo, hi)
        clim = np.array([(sel_reg == r).mean() for r in REGIMES])
        brier = lambda p: float(np.mean(np.sum((p - onehot) ** 2, axis=1)))
        out.append({"h": int(h), "candidate": chosen, "n": int(len(hold)), "brier_model": brier(p_model),
                    "brier_climatology": brier(np.tile(clim, (len(hold), 1))),
                    "brier_uniform": brier(np.full((len(hold), 3), 1 / 3)),
                    "holdout_regime_counts": {r: int((hold_reg == r).sum()) for r in REGIMES}})
    return out
