"""Rolling-origin backtest, model selection and the published forecast for skill demand.

Origins are month ends. A forecast made at origin t uses months <= t only (HN month t is complete, and so available,
on the 1st of t+1); its target is the 3-month share ending at t+h. Ridge is refit every REFIT months on rows whose
target window had ended by the refit origin.

Split by target month (chronological, no shuffling):
  test        targets in the last 12 complete months: untouched until the end, reported as is
  validation  targets in the 12 months before: chooses the method per horizon
  train       everything earlier (ridge fitting; method behaviour). Its last TUNE_MONTHS of targets tune the
              parameters of ewma / dtrend / adaptive (tune()), by the same selection score used on validation
Selection (per horizon, on validation): the lowest composite score (score(); WEIGHTS) among methods whose error is
no worse than persistence's and within MAE_TOLERANCE of the most accurate method. Then, conservatively, the
simplest eligible method (SIMPLICITY order) that the best does not beat in at least CONFIDENCE of BOOTSTRAP paired
resamples of series (all of a series' origins together) is served instead.
Gate (as in the industry pipeline, but separately implemented): the method chosen on validation is served unless
its test error is worse than persistence's; then persistence is served ("baseline_retained").

Direction is measured from the baseline (models.baseline: the last 3 months' share at the origin). A realised move
is "material" at a threshold when |actual - baseline| >= the threshold; "significant" when it is also beyond
sampling noise (z >= Z_SIG, binomial standard error of the two pooled shares). Small cells move by several points
from sampling alone, so the moving-skill parts of the selection score use significant moves; material-only
moves are reported too.

Which series count, decided with data available at the origin only:
  scope     occupations in the IT / software sector (SCOPE_SECTOR); run.py passes them to Panel
  modelled  the cell (country x occupation) had >= MIN_CELL_N12 eligible ads in the last 12 months, and the skill
            was named at least once in that cell in the last 24 months
  scored    the target window has >= MIN_EVAL_N ads
  backtest  curated skills only. Discovered skills were found with today's data, so scoring them on the past would
            flatter whichever method follows a trend; they get forecasts, flagged as not backtested.
Intervals: 10th-90th percentile of past errors (actual - forecast, share points) for forecasts of a similar level
and evidence (ads in the last 3 months at the origin), per method and horizon; calibrated on validation and checked
on test. The published forecast is calibrated on validation + test.
"""
from __future__ import annotations

import itertools

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
MOVE_PP = (1.0, 2.0)
Z_SIG = 1.96
VALIDATED_RATIO = 0.95  # "validated" needs >= 5% lower test error than persistence
SCOPE_SECTOR = "software_technology"
TUNE_MONTHS = 48

# Selection score: lower is better; every part is 0 for a perfect forecast and about 1 for persistence.
#   accuracy   MAE / persistence MAE, all scored forecasts: forecasts must stay accurate overall
#   moving     MAE / persistence MAE on significant moves (MATERIAL_PP): the skills users care about most
#   direction  1 - direction accuracy on those moves: did it call rise vs fall
#   bias       mean |signed error| of rising and of falling skills / persistence MAE on moves: a flat forecast
#              under-calls rises and over-calls falls, which this exposes
#   stability  worst origin quarter's MAE ratio to persistence, minus 1 (>= 0): no win from one good period
# Overall accuracy carries the most weight so a jumpy method cannot win on direction alone; moving-skill error,
# direction and bias together outweigh it, so a flat method cannot win on a tiny pooled-MAE edge.
WEIGHTS = {"accuracy": 0.35, "moving": 0.25, "direction": 0.2, "bias": 0.1, "stability": 0.1}
ALT_WEIGHTS = {"accuracy_heavy": {"accuracy": 0.6, "moving": 0.15, "direction": 0.1, "bias": 0.1, "stability": 0.05},
               "movement_heavy": {"accuracy": 0.2, "moving": 0.3, "direction": 0.3, "bias": 0.15, "stability": 0.05},
               "equal": dict.fromkeys(WEIGHTS, 0.2)}
MAE_TOLERANCE = 0.05
CONFIDENCE = 0.8
BOOTSTRAP = 200
SIMPLICITY = ("persistence", "mean12", "shrink", "ewma", "dtrend", "adaptive", "trend", "ridge", "blend")
GRID = {"ewma": {"hl": (1.0, 2.0, 3.0, 4.5, 6.0, 9.0, 12.0, 18.0), "kappa": (0.0, 10.0, 30.0, 100.0, 300.0)},
        "dtrend": {"W": (6, 9, 12, 18, 24), "phi": (0.8, 0.9, 0.95, 1.0), "consistency": (False, True)},
        "adaptive": {"W": (6, 12, 18, 24), "source": ("cell", "pooled"), "consistency": (False, True)}}
LEVEL = ("hl", "kappa")  # adaptive's level is ewma's: tuned there first, then held fixed


class Panel:
    """Counts as arrays. months: complete months only; series: country x occupation x skill."""

    def __init__(self, totals: pd.DataFrame, counts: pd.DataFrame, registry: dict, occupations=None):
        t = totals[~totals["is_partial"].astype(bool)]
        if occupations is not None:
            t = t[t["occupation"].isin(occupations)]
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


def _betas(p: Panel, h: int, q: dict, refit_points: list[int]) -> dict[int, np.ndarray]:
    """Adaptive's trend persistence per evidence band (BUCKETS of ads in the last 3 months), fitted at each refit
    origin r on rows (s, t) with t + h <= r (as _ridges)."""
    all_cols = np.arange(MIN_HISTORY - 1, p.T - h)
    rows, ci = np.nonzero(p.modelled(all_cols, curated_only=True))
    cols = all_cols[ci]
    k, n = p.actual(rows, cols, h)
    keep = n >= 5
    rows, cols, k, n = rows[keep], cols[keep], k[keep], n[keep]
    lvl, x = M.adaptive_parts(p.f, rows, cols, h, q)
    y = M.adaptive_target(p.f, k, n, rows, cols, lvl)
    w = np.minimum(n, 300)
    band = _bucket(p.f["n3"][rows, cols])
    out = {}
    for r in refit_points:
        past = cols + h <= r
        out[r] = np.array([M.fit_beta(x[past & (band == i)], y[past & (band == i)], w[past & (band == i)])
                           for i in range(len(BUCKETS) - 1)])
    return out


def _refit_predict(p: Panel, m: str, rows: np.ndarray, cols: np.ndarray, h: int, q: dict | None = None) -> np.ndarray:
    """Forecasts of a method whose fitted part is refit every REFIT months (ridge, blend, adaptive's beta); each
    origin uses the fit from its latest refit point, which saw only targets observed by then."""
    cols0 = MIN_HISTORY - 1
    ref = cols - (cols - cols0) % REFIT
    points = sorted(set(ref.tolist()))
    fits = _betas(p, h, q, points) if m == "adaptive" else _ridges(p, h, points)
    pred = np.full(len(rows), np.nan)
    for r, fit in fits.items():
        sel = ref == r
        if m == "adaptive":
            beta = fit[_bucket(p.f["n3"][rows[sel], cols[sel]])]
            pred[sel] = M.predict(m, p.f, rows[sel], cols[sel], h, params={**q, "beta": beta})
        elif fit is not None:
            pred[sel] = M.predict(m, p.f, rows[sel], cols[sel], h, fit)
    return pred


def _role(p: Panel, target: np.ndarray) -> np.ndarray:
    return np.where(target >= p.T - 12, "test", np.where(target >= p.T - 24, "validation", "train"))


def _scored(p: Panel, h: int) -> pd.DataFrame:
    """The (series, origin) pairs scored at horizon h, with the realised target and the baseline."""
    cols_all = np.arange(MIN_HISTORY - 1, p.T - h)
    ok = p.modelled(cols_all, curated_only=True)
    rows, ci = np.nonzero(ok)
    cols = cols_all[ci]
    k, n = p.actual(rows, cols, h)
    scored = n >= MIN_EVAL_N
    rows, cols, k, n = rows[scored], cols[scored], k[scored], n[scored]
    base = pd.DataFrame({"series": rows, "origin_idx": cols, "h": h, "actual_k": k, "actual_n": n,
                         "n3_origin": p.f["n3"][rows, cols], "p12_origin": p.f["p12"][rows, cols],
                         "p3_origin": M.baseline(p.f, rows, cols)})
    base["role"] = _role(p, cols + h)
    base["actual"] = base["actual_k"] / base["actual_n"]
    return base


def tune(p: Panel) -> dict:
    """Parameters of ewma / dtrend / adaptive per horizon: the grid point with the lowest selection score on
    training-period targets (the last TUNE_MONTHS before validation). Validation and test targets are not used."""
    out = {}
    for h in HORIZONS:
        base = _scored(p, h)
        tt = base["origin_idx"] + h
        tr = base[(base["role"] == "train") & (tt >= p.T - 24 - TUNE_MONTHS)].reset_index(drop=True)
        out[str(h)] = {"rows": int(len(tr))}
        if not len(tr):
            continue
        rows, cols = tr["series"].to_numpy(), tr["origin_idx"].to_numpy()
        naive = tr.assign(forecast=M.predict("persistence", p.f, rows, cols, h))
        for m, grid in GRID.items():
            tried = []
            for combo in itertools.product(*grid.values()):
                q = dict(zip(grid, combo))
                if m == "adaptive":
                    q.update({k: out[str(h)]["ewma"][k] for k in LEVEL})
                pred = _refit_predict(p, m, rows, cols, h, q) if m == "adaptive" else M.predict(m, p.f, rows, cols, h, params=q)
                s = score(tr.assign(forecast=pred), naive)
                tried.append((s["score"], q))
            best = min(tried, key=lambda x: x[0])
            out[str(h)][m] = {**best[1], "tune_score": round(best[0], 4), "grid_points": len(tried)}
    return out


def params_for(tuned: dict, h: int, method: str) -> dict | None:
    q = tuned.get(str(h), {}).get(method)
    return None if q is None else {k: v for k, v in q.items() if k in GRID[method] or k in LEVEL}


def run_backtest(p: Panel, tuned: dict | None = None) -> pd.DataFrame:
    """Every scored prediction: series, origin, h, method, forecast, actual, baseline, role. Methods that need
    tuned parameters are left out when `tuned` is None."""
    out = []
    for h in HORIZONS:
        base = _scored(p, h)
        rows, cols = base["series"].to_numpy(), base["origin_idx"].to_numpy()
        for m in M.METHODS:
            q = params_for(tuned or {}, h, m) if m in M.TUNED else None
            if m in M.TUNED and q is None:
                continue
            if m in ("ridge", "blend", "adaptive"):
                pred = _refit_predict(p, m, rows, cols, h, q)
            elif m in M.TUNED:
                pred = M.predict(m, p.f, rows, cols, h, params=q)
            else:
                pred = M.predict(m, p.f, rows, cols, h)
            out.append(base.assign(method=m, forecast=pred))
    b = pd.concat(out, ignore_index=True)
    # score every method on the same rows: drop (series, origin, h) where any method has no forecast. A method
    # with no forecast at all (ridge before it has MIN_RIDGE_ROWS to learn from) is left out instead.
    present = [m for m, g in b.groupby("method") if g["forecast"].notna().any()]
    b = b[b["method"].isin(present)]
    full = b.groupby(["series", "origin_idx", "h"])["forecast"].transform("count") == len(present)
    return b[full].reset_index(drop=True)


def _moves(g: pd.DataFrame, thr: float) -> tuple[np.ndarray, np.ndarray]:
    """(material, significant) masks of realised moves from the baseline of at least thr share points."""
    d = (g["actual"] - g["p3_origin"]).to_numpy()
    n0, n1 = np.nan_to_num(g["n3_origin"].to_numpy()), g["actual_n"].to_numpy()
    pool = np.clip((g["p3_origin"].to_numpy() * n0 + g["actual"].to_numpy() * n1) / np.maximum(n0 + n1, 1), 1e-4, 1 - 1e-4)
    se = np.sqrt(pool * (1 - pool) * (1 / np.maximum(n0, 1) + 1 / n1))
    mat = np.abs(d) * 100 >= thr
    return mat, mat & (np.abs(d) >= Z_SIG * se)


def _aligned(g: pd.DataFrame, naive: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    g = g.sort_values(["series", "origin_idx"]).reset_index(drop=True)
    if naive is not None and len(naive):
        naive = naive.sort_values(["series", "origin_idx"]).reset_index(drop=True)
        assert len(naive) == len(g)
    return g, naive


def _move_stats(g: pd.DataFrame, mask: np.ndarray) -> dict:
    err = (g["forecast"] - g["actual"]).to_numpy() * 100
    up = mask & (g["actual"] > g["p3_origin"]).to_numpy()
    down = mask & ~up
    pc = np.sign(g["forecast"] - g["p3_origin"]).to_numpy()
    ac = np.sign(g["actual"] - g["p3_origin"]).to_numpy()
    nan = float("nan")
    return {"n": int(mask.sum()), "n_rising": int(up.sum()), "n_falling": int(down.sum()),
            "mae_pp": float(np.abs(err[mask]).mean()) if mask.any() else nan,
            "mae_rising_pp": float(np.abs(err[up]).mean()) if up.any() else nan,
            "mae_falling_pp": float(np.abs(err[down]).mean()) if down.any() else nan,
            "bias_rising_pp": float(err[up].mean()) if up.any() else nan,
            "bias_falling_pp": float(err[down].mean()) if down.any() else nan,
            "direction_acc": float((pc[mask] == ac[mask]).mean()) if mask.any() else nan}


def score(g: pd.DataFrame, naive: pd.DataFrame, weights: dict | None = None) -> dict:
    """Composite selection score of forecasts g against persistence on the same rows (see WEIGHTS)."""
    w = weights or WEIGHTS
    g, naive = _aligned(g, naive)
    err, nerr = (g["forecast"] - g["actual"]).abs(), (naive["forecast"] - naive["actual"]).abs()
    _, sig = _moves(g, MATERIAL_PP)
    ms, ns = _move_stats(g, sig), _move_stats(naive, sig)
    parts = {"accuracy": float(err.mean() / max(nerr.mean(), 1e-12))}
    if sig.any():
        parts["moving"] = ms["mae_pp"] / max(ns["mae_pp"], 1e-12)
        parts["direction"] = 1 - ms["direction_acc"]
        parts["bias"] = np.nanmean([abs(ms["bias_rising_pp"]), abs(ms["bias_falling_pp"])]) / max(ns["mae_pp"], 1e-12)
    else:
        parts.update(moving=1.0, direction=1.0, bias=1.0)
    q = g["origin_idx"].to_numpy() // 3
    worst = 0.0
    for qq in np.unique(q):
        s = q == qq
        if s.sum() >= 50:
            worst = max(worst, float(err[s].mean() / max(nerr[s].mean(), 1e-12)) - 1)
    parts["stability"] = worst
    return {"score": float(sum(w[k] * parts[k] for k in w)), "parts": {k: round(float(v), 4) for k, v in parts.items()}}


def metrics(g: pd.DataFrame, naive: pd.DataFrame | None = None, detail: bool = False) -> dict:
    g, naive = _aligned(g, naive)
    err = (g["forecast"] - g["actual"]) * 100
    w = g["actual_n"]
    d = {"n": int(len(g)), "mae_pp": float(err.abs().mean()), "wmae_pp": float((err.abs() * w).sum() / w.sum()),
         "rmse_pp": float(np.sqrt((err ** 2).mean())), "bias_pp": float(err.mean())}
    mat, sig = _moves(g, MATERIAL_PP)
    if sig.any():
        d["direction_acc"] = _move_stats(g, sig)["direction_acc"]
    d["n_material"] = int(sig.sum())
    if naive is not None and len(naive):
        d["mae_ratio_vs_persistence"] = d["mae_pp"] / float(((naive["forecast"] - naive["actual"]).abs() * 100).mean())
        s = score(g, naive)
        d["selection_score"], d["score_parts"] = s["score"], s["parts"]
    if not detail:
        return d
    moves = {}
    for thr in MOVE_PP:
        mat, sig = _moves(g, thr)
        stable = (g["actual"] - g["p3_origin"]).abs().to_numpy() * 100 < thr
        moves[f"{thr:g}pp"] = {"material": _move_stats(g, mat), "significant": _move_stats(g, sig),
                               "stable": {"n": int(stable.sum()),
                                          "mae_pp": float(err[stable].abs().mean()) if stable.any() else None}}
    d["moves"] = moves
    # the published label, scored against the realised change from the same baseline
    lab = M.direction((g["forecast"] - g["p3_origin"]).to_numpy() * 100)
    act = M.direction((g["actual"] - g["p3_origin"]).to_numpy() * 100)
    d["label"] = {"threshold_pp": M.LABEL_PP, "accuracy_3class": float((lab == act).mean()),
                  **{f"n_{c}": int((lab == c).sum()) for c in ("rising", "falling", "flat")},
                  **{f"precision_{c}": float((act[lab == c] == c).mean()) if (lab == c).any() else None
                     for c in ("rising", "falling")},
                  **{f"right_sign_{c}": float(np.mean(np.sign((g["actual"] - g["p3_origin"]).to_numpy()[lab == c]) ==
                                                      (1 if c == "rising" else -1))) if (lab == c).any() else None
                     for c in ("rising", "falling")}}
    band = lambda col, edges, labels: pd.cut(g[col], edges, labels=labels, right=False)
    d["by_level"] = _bands(err, band("p3_origin", [0, 0.01, 0.05, 0.15, 1.01], ["<1%", "1-5%", "5-15%", ">=15%"]))
    d["by_volume"] = _bands(err, band("n3_origin", [0, 60, 200, 600, np.inf], ["<60", "60-199", "200-599", ">=600"]))
    by_q = {}
    for qq, s in g.groupby(g["origin_idx"] // 3).groups.items():
        e = err.loc[s].abs()
        r = {"n": int(len(s)), "mae_pp": float(e.mean())}
        if naive is not None and len(naive):
            r["mae_ratio_vs_persistence"] = float(e.mean() / ((naive.loc[s, "forecast"] - naive.loc[s, "actual"]).abs() * 100).mean())
        by_q[int(qq)] = r
    d["by_origin_quarter"] = by_q
    return d


def _bands(err: pd.Series, band: pd.Series) -> dict:
    return {str(k): {"n": int(len(e)), "mae_pp": float(e.abs().mean()), "bias_pp": float(e.mean())}
            for k, e in err.groupby(band, observed=True)}


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


def _beats(g: pd.DataFrame, a: str, b: str, weights: dict | None, seed: int = 0) -> float:
    """Share of paired bootstrap resamples of series in which method a scores lower than method b."""
    by = {m: x.sort_values(["series", "origin_idx"]).reset_index(drop=True) for m, x in g.groupby("method")}
    ids = by["persistence"]["series"].to_numpy()
    uniq, inv = np.unique(ids, return_inverse=True)
    groups = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(BOOTSTRAP):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(uniq), len(uniq))])
        sub = {m: by[m].iloc[idx].assign(series=np.arange(len(idx))) for m in (a, b, "persistence")}
        wins += score(sub[a], sub["persistence"], weights)["score"] < score(sub[b], sub["persistence"], weights)["score"]
    return wins / BOOTSTRAP


def select(val: dict, weights: dict | None = None, g: pd.DataFrame | None = None) -> tuple[str, dict]:
    """The method served by the selection rule (module docstring), from validation metrics per method and, for the
    conservative check, the validation rows g. Returns (method, {simpler method: share of resamples best wins})."""
    if not val:
        return "persistence", {}
    sc = {m: (score_of(v, weights) if weights else v["selection_score"]) for m, v in val.items()}
    best_mae = min(v["mae_pp"] for v in val.values())
    ok = [m for m, v in val.items() if v["mae_ratio_vs_persistence"] <= 1 and v["mae_pp"] <= best_mae * (1 + MAE_TOLERANCE)]
    ok = ok or ["persistence"]
    best = min(ok, key=lambda m: sc[m])
    rank = lambda m: SIMPLICITY.index(m) if m in SIMPLICITY else len(SIMPLICITY)
    checks = {}
    if g is not None:
        for m in sorted((m for m in ok if rank(m) < rank(best)), key=rank):
            checks[m] = _beats(g, best, m, weights)
            if checks[m] < CONFIDENCE:
                return m, checks
    return best, checks


def score_of(v: dict, weights: dict) -> float:
    return float(sum(weights[k] * v["score_parts"][k] for k in weights))


def evaluate(b: pd.DataFrame, tuned: dict | None = None) -> dict:
    """Selection on validation, test scores for every method, interval coverage on test, the gate."""
    out = {"horizons": {}}
    q_val = interval_quantiles(b[b["role"] == "validation"])
    for h in HORIZONS:
        bh = b[b["h"] == h]
        per = {}
        for role in ("train", "validation", "test"):
            g = bh[bh["role"] == role]
            naive = g[g["method"] == "persistence"]
            per[role] = {m: metrics(gm, naive, detail=role != "train") for m, gm in g.groupby("method")} if len(g) else {}
        val = per["validation"]
        chosen, checks = select(val, g=bh[bh["role"] == "validation"])
        sensitivity = {name: select(val, w)[0] for name, w in ALT_WEIGHTS.items()}
        sensitivity["mae_only"] = min(val, key=lambda m: val[m]["mae_pp"]) if val else "persistence"
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
            _, sig = _moves(gm, MATERIAL_PP)
            vol = _bucket(gm["n3_origin"].to_numpy())
            cov[m] = {"coverage_80": float(inside.mean()), "mean_width_pp": float(np.mean(hi - lo) * 100),
                      "coverage_80_significant_moves": float(inside[sig].mean()) if sig.any() else None,
                      "coverage_80_by_volume": {f"{BUCKETS[i]:g}-{BUCKETS[i + 1]:g}": float(inside[vol == i].mean())
                                                for i in range(len(BUCKETS) - 1) if (vol == i).any()}}
        out["horizons"][str(h)] = {"chosen_on_validation": chosen, "served": served, "status": status,
                                   "best_score_on_validation": min(val, key=lambda m: val[m]["selection_score"]) if val else None,
                                   "bootstrap_best_beats": checks,
                                   "params": {m: params_for(tuned or {}, h, m) for m in M.TUNED},
                                   "selection_sensitivity": sensitivity, "scores": per, "interval_test": cov}
    return out


def cell_accuracy(b: pd.DataFrame, p: Panel, ev: dict) -> pd.DataFrame:
    """Test-period errors per country x occupation x horizon for every method, flagged served / persistence."""
    t = b[b["role"] == "test"].merge(p.series[["country", "occupation"]], left_on="series", right_index=True)
    rows = []
    for (c, o, h, m), g in t.groupby(["country", "occupation", "h", "method"]):
        naive = t[(t["country"] == c) & (t["occupation"] == o) & (t["h"] == h) & (t["method"] == "persistence")]
        d = metrics(g, naive)
        d.pop("score_parts", None)
        rows.append({"country": c, "occupation": o, "h": int(h), "method": m,
                     "served": m == ev["horizons"][str(h)]["served"], **d})
    return pd.DataFrame(rows)


def forecast(p: Panel, b: pd.DataFrame, ev: dict, tuned: dict | None = None, min_n12: int = 10) -> tuple[pd.DataFrame, dict]:
    """The published forecast at the last complete month, with intervals from validation + test errors."""
    t0 = p.T - 1
    q = interval_quantiles(b[b["role"].isin(["validation", "test"])])
    rows_out, cards = [], {}
    eligible = (np.nan_to_num(p.f["n12"][:, t0]) >= min_n12) & (np.nan_to_num(p.k24[:, t0]) >= 1)
    rows = np.nonzero(eligible)[0]
    cols = np.full(len(rows), t0)
    for h in HORIZONS:
        served = ev["horizons"][str(h)]["served"]
        ridge, prm = None, params_for(tuned or {}, h, served) if served in M.TUNED else None
        if served in ("ridge", "blend"):
            ridge = _ridges(p, h, [t0])[t0]
            cards[str(h)] = ridge.card() if ridge else None
        if served == "adaptive":
            fit = _betas(p, h, prm, [t0])[t0]
            cards[str(h)] = {**prm, "beta_by_ads_3m": {f"{BUCKETS[i]:g}-{BUCKETS[i + 1]:g}": float(b) for i, b in enumerate(fit)}}
            prm = {**prm, "beta": fit[_bucket(p.f["n3"][rows, cols])]}
        pred = M.predict(served, p.f, rows, cols, h, ridge, params=prm)
        lo, hi = apply_interval(q, served, h, pred, p.f["n3"][rows, cols])
        rows_out.append(pd.DataFrame({
            "series": rows, "h": h, "origin_month": str(p.months[t0]), "target_month": str(p.months[t0] + h),
            "forecast": pred, "low": lo, "high": hi, "model": served, "model_status": ev["horizons"][str(h)]["status"],
            "baseline_share": M.baseline(p.f, rows, cols)}))
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
    fc["change_pp"] = (fc["forecast"] - fc["baseline_share"]) * 100
    fc["direction"] = M.direction(fc["change_pp"].to_numpy())
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
              "actual", "actual_k", "actual_n", "p12_origin", "p3_origin"]]
