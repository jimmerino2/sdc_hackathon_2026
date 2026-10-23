"""Rolling-origin backtest, locked holdout, metrics, model selection and source ablations.

Origins: one per last-observed month L. Real origins are AI-tracker vintages (the last one published for each L);
before the first vintage, reconstructed origins cover L = 2021-01 onwards (features.py explains the caveat).

At each origin and horizon h, every candidate is fitted on that origin's snapshot only and predicts L + h for each
country. It is scored against the *latest* vintage's value for L + h (the best current estimate), in percentage
points. Origins whose L + h is not yet published are not scored (unavailable, never zero error).

Split, decided before any model is scored:
  holdout   the last HOLDOUT_SHARE of origins that can be scored at the longest horizon (at least
            MIN_HOLDOUT), and every later origin. Never used to choose or tune anything.
  selection every earlier origin, *purged*: a (origin, h) pair is dropped when L + h lies after the last month
            observed at the first holdout origin, so selection never sees an outcome from the holdout period.
Selection rule (fixed in advance): lowest mean absolute error in pp over the selection pairs; a simpler candidate
within NEAR_BEST of the best wins. The chosen model is then scored once on the holdout, next to the naive baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import features as F
from .models import BASELINES, CANDIDATES

HORIZONS = (1, 3, 6)
HOLDOUT_SHARE = 0.2
MIN_HOLDOUT = 6
NEAR_BEST = 0.02
MIN_SELECTION_ORIGINS = 12  # fewer than this and the horizon is reported as insufficient history
FIRST_RECONSTRUCTED = pd.Period("2021-01", freq="M")


def origins(ai_v: pd.DataFrame, po_v: pd.DataFrame) -> list[F.Snapshot]:
    real = []
    for when in sorted(ai_v["available_at"].unique()):
        real.append(F.snapshot_real(ai_v, po_v, pd.Timestamp(when)))
    by_month = {}
    for s in real:  # the last vintage published for each L (later commits correct earlier ones)
        by_month[s.last_month] = s
    first_real = min(by_month)
    recon = [F.snapshot_reconstructed(ai_v, po_v, m)
             for m in pd.period_range(FIRST_RECONSTRUCTED, first_real - 1, freq="M")]
    out = recon + [by_month[m] for m in sorted(by_month)]
    assert all(a.origin < b.origin for a, b in zip(out, out[1:])), "origins must be strictly increasing"
    return out


def truth(ai_v: pd.DataFrame) -> pd.Series:
    """Latest vintage's complete months: (month, geo) -> percent."""
    latest = ai_v[(ai_v["available_at"] == ai_v["available_at"].max()) & ~ai_v["is_partial"].astype(bool)]
    return latest.set_index([pd.PeriodIndex(latest["month"], freq="M"), "geo"])["value"]


@dataclass
class Split:
    holdout_start: pd.Timestamp  # origin time of the first holdout origin
    holdout_last_month: pd.Period  # L at that origin: selection may only score outcomes up to here
    n_selection: int
    n_holdout: int
    notes: list[str] = field(default_factory=list)


def make_split(snaps: list[F.Snapshot], latest_month: pd.Period) -> Split:
    scorable = [s for s in snaps if s.last_month + max(HORIZONS) <= latest_month]
    k = max(MIN_HOLDOUT, int(round(HOLDOUT_SHARE * len(scorable))))
    first = scorable[-k]
    sel = [s for s in snaps if s.origin < first.origin]
    return Split(first.origin, first.last_month, len(sel), len(snaps) - len(sel))


def is_holdout(s: F.Snapshot, split: Split) -> bool:
    return s.origin >= split.holdout_start


def in_selection(s: F.Snapshot, h: int, split: Split) -> bool:
    return not is_holdout(s, split) and s.last_month + h <= split.holdout_last_month


def backtest(snaps: list[F.Snapshot], y_true: pd.Series, candidates=None, feature_sets=None) -> pd.DataFrame:
    """One row per origin x horizon x candidate x geo with prediction and outcome (pp).

    feature_sets maps a run label to the feature list given to feature-using models (ablations)."""
    candidates = candidates or list(CANDIDATES)
    feature_sets = feature_sets or {"all": F.ALL_FEATURES}
    rows = []
    for s in snaps:
        rows_now = F.latest_rows(s)
        for h in HORIZONS:
            train = F.labelled(s, h)
            target_month = s.last_month + h
            obs = np.array([y_true.get((target_month, g), np.nan) for g in rows_now["geo"]])
            for fs_name, feats in feature_sets.items():
                for c in candidates:
                    cls = CANDIDATES[c]
                    if fs_name != "all" and not cls.uses_features:
                        continue  # baselines do not change under an ablation
                    m = cls().fit(train, h, feats)
                    d = m.predict(rows_now)
                    pred = 100 * F.expit(rows_now["lvl"].to_numpy() + d)
                    last = 100 * F.expit(rows_now["lvl"].to_numpy())
                    rows.append(pd.DataFrame({
                        "origin": s.origin, "last_month": str(s.last_month), "vintage_kind": s.kind,
                        "ai_vintage": s.ai_vintage, "h": h, "target_month": str(target_month),
                        "candidate": c, "feature_set": fs_name, "geo": rows_now["geo"].to_numpy(),
                        "last_value": last, "pred": pred, "pred_logit_change": d,
                        "actual": obs, "n_train": len(train)}))
    out = pd.concat(rows, ignore_index=True)
    out["error"] = out["pred"] - out["actual"]
    out["logit_resid"] = F.logit(out["actual"] / 100) - (F.logit(out["last_value"] / 100) + out["pred_logit_change"])
    out.loc[out["actual"].isna(), "logit_resid"] = np.nan
    return out


def tag_split(bt: pd.DataFrame, snaps: list[F.Snapshot], split: Split) -> pd.DataFrame:
    by_origin = {s.origin: s for s in snaps}
    role = []
    for o, h in zip(bt["origin"], bt["h"]):
        s = by_origin[o]
        role.append("holdout" if is_holdout(s, split) else "selection" if in_selection(s, h, split) else "purged")
    return bt.assign(role=role)


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual"])
    if d.empty:
        return {"n": 0, "n_origins": 0, "mae_pp": None, "rmse_pp": None, "bias_pp": None}
    return {"n": int(len(d)), "n_origins": int(d["origin"].nunique()),
            "mae_pp": float(d["error"].abs().mean()), "rmse_pp": float(np.sqrt((d["error"] ** 2).mean())),
            "bias_pp": float(d["error"].mean())}


def select(bt: pd.DataFrame) -> pd.DataFrame:
    """Per horizon: selection-period scores, the chosen candidate, and its one holdout score next to naive."""
    out = []
    base = bt[bt["feature_set"] == "all"]
    for h, g in base.groupby("h"):
        sel = g[g["role"] == "selection"]
        n_sel_origins = sel.dropna(subset=["actual"])["origin"].nunique()
        scores = {c: metrics(sel[sel["candidate"] == c]) for c in CANDIDATES}
        best = min(v["mae_pp"] for v in scores.values() if v["mae_pp"] is not None)
        chosen = min((c for c, v in scores.items() if v["mae_pp"] is not None and v["mae_pp"] <= best * (1 + NEAR_BEST)),
                     key=lambda c: CANDIDATES[c].complexity)
        hold = g[g["role"] == "holdout"]
        for c, v in scores.items():
            hv = metrics(hold[hold["candidate"] == c])
            out.append({"h": h, "candidate": c, "is_baseline": c in BASELINES, "chosen": c == chosen,
                        "selection_mae_pp": v["mae_pp"], "selection_rmse_pp": v["rmse_pp"],
                        "selection_n_origins": v["n_origins"], "holdout_mae_pp": hv["mae_pp"],
                        "holdout_rmse_pp": hv["rmse_pp"], "holdout_bias_pp": hv["bias_pp"],
                        "holdout_n_origins": hv["n_origins"], "holdout_n": hv["n"],
                        "insufficient_history": n_sel_origins < MIN_SELECTION_ORIGINS})
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
    """Selection-period MAE of each feature-using model with each source group removed (holdout shown, not used)."""
    rows = []
    d = bt[bt["candidate"].isin([c for c, k in CANDIDATES.items() if k.uses_features])]
    for (c, fs, h), g in d.groupby(["candidate", "feature_set", "h"]):
        sel, hold = metrics(g[g["role"] == "selection"]), metrics(g[g["role"] == "holdout"])
        rows.append({"candidate": c, "feature_set": fs, "h": h, "selection_mae_pp": sel["mae_pp"],
                     "holdout_mae_pp": hold["mae_pp"], "selection_n_origins": sel["n_origins"]})
    t = pd.DataFrame(rows)
    full = t[t["feature_set"] == "all"].set_index(["candidate", "h"])["selection_mae_pp"]
    t["selection_mae_change_vs_all"] = t["selection_mae_pp"] - [full.get((c, h)) for c, h in zip(t["candidate"], t["h"])]
    return t
