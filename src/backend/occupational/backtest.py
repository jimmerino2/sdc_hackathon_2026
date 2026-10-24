"""Rolling-origin backtest, model selection and the published forecast for skill demand.

Origins are month ends. A forecast made at origin t uses months <= t only (HN month t is complete, and so available,
on the 1st of t+1); its target is the 3-month share ending at t+h. Ridge is refit every REFIT months on rows whose
target window had ended by the refit origin.

Split by target month (chronological, no shuffling):
  test        targets in the last 12 complete months: untouched until the end, reported as is
  validation  targets in the 12 months before: chooses the method per horizon
  train       everything earlier (ridge fitting; method behaviour)
Gate (as in the industry pipeline, but separately implemented): the method chosen on validation is served unless
its test error is worse than persistence's; then persistence is served ("baseline_retained").

Which series count, decided with data available at the origin only:
  modelled  the cell (country x occupation) had >= MIN_CELL_N12 eligible ads in the last 12 months, and the skill
            was named at least once in that cell in the last 24 months
  scored    the target window has >= MIN_EVAL_N ads
  backtest  curated skills only. Discovered skills were found with today's data, so scoring them on the past would
            flatter whichever method follows a trend; they get forecasts, flagged as not backtested.
Intervals: 10th-90th percentile of past errors (actual - forecast, share points) for forecasts of a similar level
and evidence (ads in the last 3 months at the origin), per method and horizon; calibrated on validation and checked
on test. The published forecast is calibrated on
validation + test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import models as M

HORIZONS = (3, 6, 12)
MIN_HISTORY = 24
MIN_CELL_N12 = 20
MIN_EVAL_N = 20
REFIT = 6
MIN_RIDGE_ROWS = 2000
BUCKETS = (0, 60, 200, np.inf)
MATERIAL_PP = 2.0
VALIDATED_RATIO = 0.95  # "validated" needs >= 5% lower test error than persistence


class Panel:
    """Counts as arrays. months: complete months only; series: country x occupation x skill."""

    def __init__(self, totals: pd.DataFrame, counts: pd.DataFrame, registry: dict):
        t = totals[~totals["is_partial"].astype(bool)]
        self.months = pd.period_range(pd.Period(t["month"].min(), "M"), pd.Period(t["month"].max(), "M"), freq="M")
        cells = t[["country", "occupation"]].drop_duplicates().sort_values(["country", "occupation"])
        self.cells = list(cells.itertuples(index=False, name=None))
        ci = {c: i for i, c in enumerate(self.cells)}
        mi = {str(m): i for i, m in enumerate(self.months)}
        Nc = np.zeros((len(self.cells), len(self.months)))
        for r in t.itertuples():
            Nc[ci[(r.country, r.occupation)], mi[r.month]] = r.n_ads
        c = counts[counts["month"].isin(mi)]
        c = c.assign(cell=[ci.get((a, b), -1) for a, b in zip(c["country"], c["occupation"])])
        c = c[c["cell"] >= 0]
        keys = c[["cell", "skill_id"]].drop_duplicates().sort_values(["cell", "skill_id"]).reset_index(drop=True)
        si = {(a, b): i for i, (a, b) in enumerate(keys.itertuples(index=False, name=None))}
        K = np.zeros((len(keys), len(self.months)))
        np.add.at(K, ([si[(a, b)] for a, b in zip(c["cell"], c["skill_id"])], [mi[m] for m in c["month"]]),
                  c["n_ads_skill"].to_numpy(float))
        self.K, self.N = K, Nc[keys["cell"].to_numpy()]
        self.series = keys.assign(country=[self.cells[i][0] for i in keys["cell"]],
                                  occupation=[self.cells[i][1] for i in keys["cell"]])
        origin = {e["skill_id"]: e["origin"] for e in registry["skills"]}
        self.series["skill_origin"] = self.series["skill_id"].map(origin).fillna("curated")
        occs = sorted(self.series["occupation"].unique())
        skills = sorted(self.series["skill_id"].unique())
        self.f = M.features(self.K, self.N, self.series["skill_id"].map({s: i for i, s in enumerate(skills)}).to_numpy(),
                            self.series["occupation"].map({o: i for i, o in enumerate(occs)}).to_numpy(), len(occs))
        self.k24 = M.wsum(self.K, 24)

    @property
    def T(self) -> int:
        return len(self.months)

    def modelled(self, cols: np.ndarray, curated_only: bool) -> np.ndarray:
        """Boolean [series, len(cols)]: modelled at those origins."""
        ok = (np.nan_to_num(self.f["n12"][:, cols]) >= MIN_CELL_N12) & (np.nan_to_num(self.k24[:, cols]) >= 1)
        if curated_only:
            ok &= (self.series["skill_origin"] == "curated").to_numpy()[:, None]
        return ok

    def actual(self, rows, cols, h):
        k, n = M.wsum(self.K, M.WINDOW)[rows, cols + h], M.wsum(self.N, M.WINDOW)[rows, cols + h]
        return k, n


def _bucket(n3: np.ndarray) -> np.ndarray:
    return np.digitize(np.nan_to_num(n3), BUCKETS[1:-1])


def _ridges(p: Panel, h: int, refit_points: list[int]) -> dict[int, M.RidgeModel | None]:
    """Ridge fitted at each refit origin r on rows (s, t) with t + h <= r."""
    out = {}
    all_cols = np.arange(MIN_HISTORY - 1, p.T - h)
    ok_all = p.modelled(all_cols, curated_only=True)
    for r in refit_points:
        cols = all_cols[all_cols + h <= r]
        if not len(cols):
            out[r] = None
            continue
        ok = ok_all[:, :len(cols)]
        rows, cidx = np.nonzero(ok)
        cc = cols[cidx]
        _, n = p.actual(rows, cc, h)
        keep = n >= 5
        rows, cc, n = rows[keep], cc[keep], n[keep]
        if len(rows) < MIN_RIDGE_ROWS:
            out[r] = None
            continue
        y = M.ridge_target(p.f, p.K, p.N, rows, cc, h)
        out[r] = M.RidgeModel().fit(M.design(p.f, rows, cc), y, np.minimum(n, 300))
    return out


def run_backtest(p: Panel) -> pd.DataFrame:
    """Every scored prediction: series, origin, h, method, forecast, actual, role."""
    out = []
    for h in HORIZONS:
        cols_all = np.arange(MIN_HISTORY - 1, p.T - h)
        ok = p.modelled(cols_all, curated_only=True)
        rows, ci = np.nonzero(ok)
        cols = cols_all[ci]
        k, n = p.actual(rows, cols, h)
        scored = n >= MIN_EVAL_N
        rows, cols, k, n = rows[scored], cols[scored], k[scored], n[scored]
        refits = sorted({int(c - (c - cols_all[0]) % REFIT) for c in cols})
        ridges = _ridges(p, h, refits)
        base = pd.DataFrame({"series": rows, "origin_idx": cols, "h": h, "actual_k": k, "actual_n": n,
                             "n3_origin": p.f["n3"][rows, cols], "p12_origin": p.f["p12"][rows, cols]})
        tt = cols + h
        base["role"] = np.where(tt >= p.T - 12, "test", np.where(tt >= p.T - 24, "validation", "train"))
        for m in M.METHODS:
            if m in ("ridge", "blend"):
                pred = np.full(len(rows), np.nan)
                ref = cols - (cols - cols_all[0]) % REFIT
                for r, model in ridges.items():
                    sel = ref == r
                    if model is not None and sel.any():
                        pred[sel] = M.predict(m, p.f, rows[sel], cols[sel], h, model)
            else:
                pred = M.predict(m, p.f, rows, cols, h)
            out.append(base.assign(method=m, forecast=pred))
    b = pd.concat(out, ignore_index=True)
    b["actual"] = b["actual_k"] / b["actual_n"]
    # score every method on the same rows: drop (series, origin, h) where any method has no forecast. A method
    # with no forecast at all (ridge before it has MIN_RIDGE_ROWS to learn from) is left out instead.
    present = [m for m, g in b.groupby("method") if g["forecast"].notna().any()]
    b = b[b["method"].isin(present)]
    full = b.groupby(["series", "origin_idx", "h"])["forecast"].transform("count") == len(present)
    return b[full].reset_index(drop=True)


def metrics(g: pd.DataFrame, naive: pd.DataFrame | None = None) -> dict:
    err = (g["forecast"] - g["actual"]) * 100
    w = g["actual_n"]
    d = {"n": int(len(g)), "mae_pp": float(err.abs().mean()), "wmae_pp": float((err.abs() * w).sum() / w.sum()),
         "rmse_pp": float(np.sqrt((err ** 2).mean())), "bias_pp": float(err.mean())}
    mat = (g["actual"] - g["p12_origin"]).abs() * 100 >= MATERIAL_PP
    if mat.any():
        d["direction_acc"] = float((np.sign(g.loc[mat, "forecast"] - g.loc[mat, "p12_origin"]) ==
                                    np.sign(g.loc[mat, "actual"] - g.loc[mat, "p12_origin"])).mean())
        d["n_material"] = int(mat.sum())
    if naive is not None and len(naive):
        d["mae_ratio_vs_persistence"] = d["mae_pp"] / float(((naive["forecast"] - naive["actual"]).abs() * 100).mean())
    return d


LEVELS = (0, 0.005, 0.02, 0.05, 0.10, 0.20, 1.01)  # forecast share bins for the interval errors


def _level(f: np.ndarray) -> np.ndarray:
    return np.digitize(np.nan_to_num(f), LEVELS[1:-1])


def interval_quantiles(b: pd.DataFrame) -> dict:
    """10th / 90th percentile of (actual - forecast) in share points, per method x horizon x forecast level x
    evidence bucket; coarser keys are fallbacks for thin bins."""
    b = b.assign(res=b["actual"] - b["forecast"], lvl=_level(b["forecast"].to_numpy()),
                 bucket=_bucket(b["n3_origin"].to_numpy()))
    q = {}
    for keys, min_n in ((["method", "h", "lvl", "bucket"], 50), (["method", "h", "lvl"], 30), (["method", "h"], 1)):
        for k, g in b.groupby(keys):
            if len(g) >= min_n:
                q[tuple(int(x) if not isinstance(x, str) else x for x in k)] = (
                    float(g["res"].quantile(0.1)), float(g["res"].quantile(0.9)))
    return q


def apply_interval(q: dict, method: str, h: int, forecast: np.ndarray, n3: np.ndarray):
    lv, bk = _level(forecast), _bucket(n3)
    lo, hi = np.full(len(forecast), np.nan), np.full(len(forecast), np.nan)
    for i in range(len(forecast)):
        a = q.get((method, h, int(lv[i]), int(bk[i]))) or q.get((method, h, int(lv[i]))) or q.get((method, h))
        if a:
            lo[i], hi[i] = a
    return np.clip(forecast + lo, 0, 1), np.clip(forecast + hi, 0, 1)


def evaluate(b: pd.DataFrame) -> dict:
    """Selection on validation, test scores for every method, interval coverage on test, the gate."""
    out = {"horizons": {}}
    q_val = interval_quantiles(b[b["role"] == "validation"])
    for h in HORIZONS:
        bh = b[b["h"] == h]
        per = {}
        for role in ("train", "validation", "test"):
            g = bh[bh["role"] == role]
            naive = g[g["method"] == "persistence"]
            per[role] = {m: metrics(gm, naive) for m, gm in g.groupby("method")} if len(g) else {}
        val = per["validation"]
        chosen = min(val, key=lambda m: val[m]["mae_pp"]) if val else "persistence"
        test = per["test"]
        status, served = "baseline", chosen
        if chosen != "persistence" and test:
            ratio = test[chosen]["mae_pp"] / test["persistence"]["mae_pp"]
            if ratio > 1:
                status, served = "baseline_retained", "persistence"
            else:
                status = "validated" if ratio <= VALIDATED_RATIO else "not_demonstrably_better"
        cov = {}
        t = bh[bh["role"] == "test"]
        for m, gm in t.groupby("method"):
            lo, hi = apply_interval(q_val, m, h, gm["forecast"].to_numpy(), gm["n3_origin"].to_numpy())
            inside = (gm["actual"].to_numpy() >= lo) & (gm["actual"].to_numpy() <= hi)
            cov[m] = {"coverage_80": float(inside.mean()), "mean_width_pp": float(np.mean(hi - lo) * 100)}
        out["horizons"][str(h)] = {"chosen_on_validation": chosen, "served": served, "status": status,
                                   "scores": per, "interval_test": cov}
    return out


def cell_accuracy(b: pd.DataFrame, p: Panel, ev: dict) -> pd.DataFrame:
    """Test-period errors per country x occupation x horizon for every method, flagged served / persistence."""
    t = b[b["role"] == "test"].merge(p.series[["country", "occupation"]], left_on="series", right_index=True)
    rows = []
    for (c, o, h, m), g in t.groupby(["country", "occupation", "h", "method"]):
        naive = t[(t["country"] == c) & (t["occupation"] == o) & (t["h"] == h) & (t["method"] == "persistence")]
        d = metrics(g, naive)
        rows.append({"country": c, "occupation": o, "h": int(h), "method": m,
                     "served": m == ev["horizons"][str(h)]["served"], **d})
    return pd.DataFrame(rows)


def forecast(p: Panel, b: pd.DataFrame, ev: dict, min_n12: int = 10) -> tuple[pd.DataFrame, dict]:
    """The published forecast at the last complete month, with intervals from validation + test errors."""
    t0 = p.T - 1
    q = interval_quantiles(b[b["role"].isin(["validation", "test"])])
    rows_out, cards = [], {}
    eligible = (np.nan_to_num(p.f["n12"][:, t0]) >= min_n12) & (np.nan_to_num(p.k24[:, t0]) >= 1)
    rows = np.nonzero(eligible)[0]
    cols = np.full(len(rows), t0)
    for h in HORIZONS:
        served = ev["horizons"][str(h)]["served"]
        ridge = None
        if served in ("ridge", "blend"):
            ridge = _ridges(p, h, [t0])[t0]
            cards[str(h)] = ridge.card() if ridge else None
        pred = M.predict(served, p.f, rows, cols, h, ridge)
        lo, hi = apply_interval(q, served, h, pred, p.f["n3"][rows, cols])
        rows_out.append(pd.DataFrame({
            "series": rows, "h": h, "origin_month": str(p.months[t0]), "target_month": str(p.months[t0] + h),
            "forecast": pred, "low": lo, "high": hi, "model": served, "model_status": ev["horizons"][str(h)]["status"]}))
    fc = pd.concat(rows_out, ignore_index=True)
    s = p.series.loc[fc["series"]].reset_index(drop=True)
    fc = pd.concat([fc.reset_index(drop=True), s[["country", "occupation", "skill_id", "skill_origin"]]], axis=1)
    fc["last_share_3m"] = p.f["p3"][fc["series"], t0]
    fc["last_ads_3m"] = p.f["n3"][fc["series"], t0]
    fc["last_count_3m"] = p.f["k3"][fc["series"], t0]
    fc["share_12m"] = p.f["p12"][fc["series"], t0]
    fc["ads_12m"] = p.f["n12"][fc["series"], t0]
    fc["count_12m"] = p.f["k12"][fc["series"], t0]
    fc["evidence"] = np.select([fc["ads_12m"] >= 300, fc["ads_12m"] >= 100], ["high", "medium"], "low")
    fc["backtested"] = fc["skill_origin"] == "curated"
    chg = (fc["forecast"] - fc["share_12m"]) * 100
    thr = np.maximum(1.0, fc["share_12m"] * 100 * 0.15)
    fc["direction"] = np.select([chg >= thr, chg <= -thr], ["rising", "falling"], "flat")
    return fc.drop(columns=["series"]), cards


def asof_rows(b: pd.DataFrame, p: Panel, ev: dict) -> pd.DataFrame:
    """Validation + test predictions of the served method and persistence, for the page's 'as of' view."""
    keep = []
    for h in HORIZONS:
        served = ev["horizons"][str(h)]["served"]
        keep.append(b[(b["h"] == h) & b["role"].isin(["validation", "test"]) & b["method"].isin([served, "persistence"])])
    a = pd.concat(keep).merge(p.series[["country", "occupation", "skill_id"]], left_on="series", right_index=True)
    a["origin_month"] = [str(p.months[i]) for i in a["origin_idx"]]
    a["target_month"] = [str(p.months[i + h]) for i, h in zip(a["origin_idx"], a["h"])]
    return a[["country", "occupation", "skill_id", "origin_month", "target_month", "h", "method", "role", "forecast",
              "actual", "actual_k", "actual_n", "p12_origin"]]
