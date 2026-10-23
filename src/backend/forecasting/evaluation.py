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
        now = F.latest_rows(spec, s)
        if now.empty:
            continue
        lvl = now["lvl"].to_numpy()
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
                    d = cls().fit(train, h, feats, spec.trend_steps).predict(now)
                    rows.append(pd.DataFrame({
                        "origin": s.origin, "last_period": spec.label(s.last), "vintage_kind": s.kind,
                        "vintage": s.vintage, "h": h, "target_period": spec.label(target), "role": role(s, h, split),
                        "candidate": c, "feature_set": fs_name, "unit": now["unit"].to_numpy(),
                        "segment": [spec.segment(u) for u in now["unit"]], "last_value": 100 * F.expit(lvl),
                        "pred": 100 * F.expit(lvl + d), "pred_logit_change": d, "actual": obs, "n_train": len(train)}))
    out = pd.concat(rows, ignore_index=True)
    out["error"] = out["pred"] - out["actual"]
    out["logit_resid"] = F.logit(out["actual"] / 100) - (F.logit(out["last_value"] / 100) + out["pred_logit_change"])
    out.loc[out["actual"].isna(), "logit_resid"] = np.nan
    return out


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual"])
    if d.empty:
        return {"n": 0, "n_origins": 0, "mae_pp": None, "rmse_pp": None, "bias_pp": None}
    return {"n": int(len(d)), "n_origins": int(d["origin"].nunique()),
            "mae_pp": float(d["error"].abs().mean()), "rmse_pp": float(np.sqrt((d["error"] ** 2).mean())),
            "bias_pp": float(d["error"].mean())}


def select(bt: pd.DataFrame, min_selection_origins: int = 12) -> pd.DataFrame:
    """Per horizon: selection-period scores, the chosen candidate, and its one holdout score next to naive."""
    out = []
    base = bt[bt["feature_set"] == "all"]
    for h, g in base.groupby("h"):
        sel = g[g["role"] == "selection"]
        n_sel = sel.dropna(subset=["actual"])["origin"].nunique()
        scores = {c: metrics(sel[sel["candidate"] == c]) for c in CANDIDATES if c in set(g["candidate"])}
        valid = {c: v["mae_pp"] for c, v in scores.items() if v["mae_pp"] is not None}
        chosen = "naive"  # nothing scorable -> the baseline, never an untested model
        if valid:
            best = min(valid.values())
            chosen = min((c for c, m in valid.items() if m <= best * (1 + NEAR_BEST)),
                         key=lambda c: CANDIDATES[c].complexity)
        hold = g[g["role"] == "holdout"]
        for c, v in scores.items():
            hv = metrics(hold[hold["candidate"] == c])
            out.append({"h": h, "candidate": c, "is_baseline": c in BASELINES, "chosen": c == chosen,
                        "selection_mae_pp": v["mae_pp"], "selection_rmse_pp": v["rmse_pp"],
                        "selection_n_origins": v["n_origins"], "holdout_mae_pp": hv["mae_pp"],
                        "holdout_rmse_pp": hv["rmse_pp"], "holdout_bias_pp": hv["bias_pp"],
                        "holdout_n_origins": hv["n_origins"], "holdout_n": hv["n"],
                        "insufficient_history": n_sel < min_selection_origins})
    t = pd.DataFrame(out)
    naive = t[t["candidate"] == "naive"].set_index("h")
    t["selection_mase_vs_naive"] = t["selection_mae_pp"] / t["h"].map(naive["selection_mae_pp"])
    t["holdout_mase_vs_naive"] = t["holdout_mae_pp"] / t["h"].map(naive["holdout_mae_pp"])
    return t


def interval_quantiles(bt: pd.DataFrame, roles: tuple[str, ...], q=(0.1, 0.9)) -> pd.DataFrame:
    """Empirical quantiles of out-of-sample logit residuals per candidate and horizon (split conformal)."""
    d = bt[(bt["feature_set"] == "all") & bt["role"].isin(roles)].dropna(subset=["logit_resid"])
    return d.groupby(["candidate", "h"])["logit_resid"].quantile(list(q)).unstack()


def coverage(bt: pd.DataFrame, qs: pd.DataFrame) -> pd.DataFrame:
    """Share of holdout outcomes inside the 10-90% range built from selection-period residuals only."""
    d = bt[(bt["feature_set"] == "all") & (bt["role"] == "holdout")].dropna(subset=["logit_resid"])
    rows = []
    for (c, h), g in d.groupby(["candidate", "h"]):
        if (c, h) not in qs.index:
            continue
        lo, hi = qs.loc[(c, h)]
        rows.append({"candidate": c, "h": h, "holdout_coverage_80": float(g["logit_resid"].between(lo, hi).mean()),
                     "n": len(g)})
    return pd.DataFrame(rows)


def ablation_table(bt: pd.DataFrame) -> pd.DataFrame:
    """Selection-period MAE of each feature-using model with each feature group removed (holdout shown, not used)."""
    rows = []
    d = bt[bt["candidate"].isin([c for c, k in CANDIDATES.items() if k.uses_features])]
    for (c, fs, h), g in d.groupby(["candidate", "feature_set", "h"]):
        sel, hold = metrics(g[g["role"] == "selection"]), metrics(g[g["role"] == "holdout"])
        rows.append({"candidate": c, "feature_set": fs, "h": h, "selection_mae_pp": sel["mae_pp"],
                     "holdout_mae_pp": hold["mae_pp"], "selection_n_origins": sel["n_origins"]})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    full = t[t["feature_set"] == "all"].set_index(["candidate", "h"])["selection_mae_pp"]
    t["selection_mae_change_vs_all"] = [None if m is None or full.get((c, h)) is None else m - full.get((c, h))
                                        for m, c, h in zip(t["selection_mae_pp"], t["candidate"], t["h"])]
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
