"""Skill-emergence signals: evidence from outside a skill's own job-ad series, kept separate from the job-demand
baseline (backtest.py's served method at H months).

Evidence, all at an origin month t from data up to t only (package month m is complete, and so available, at the
end of m, like an HN month):
  adoption  a package's downloads relative to a skill-neutral reference basket (taxonomy/skill_signals.json), as
            3-month sums: log growth over 6 and 12 months and the change in 6-month growth (acceleration). A
            package counts only with >= MIN_DOWNLOADS_3M downloads in both windows compared; a skill's value is
            the download-weighted mean over its packages. Missing (no package, too small, incomplete months) is
            missing: the model gets 0 plus a has_adoption = 0 flag, so missing is never read as "no growth".
  related   the change in logit job-ad share of the skill's related skills (config, else its curated category),
            each pooled over every IT cell, 6 months on 6 and 12 on 12; the skill itself is never included.

Models (one horizon, H). Each adds a ridge correction in logit share to the baseline's forecast, refit every
REFIT months on rows whose target had been observed by then (as backtest._ridges):
  control   own-series features only (the cell's recent deviation and yearly change, the skill's pooled change)
  hybrid    control's features plus adoption and related-skill features
The hybrid counts as an improvement only if it beats both the baseline and the control (backtest.select rules
on validation, then the test gate). Otherwise the published "adjusted" forecast stays empty.
Radar: logistic models of a significant rise (>= RISE_PP and beyond sampling noise, backtest._moves) within H
months, for cells with >= RADAR_MIN_N3 ads in the last 3 months (smaller cells are low evidence: their rises
are mostly noise rebounds). own (control features) vs hybrid; an alert is a probability above the threshold that
maximised F1 on rows observed by the refit. Scored by precision, recall, false-positive rate and average precision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

from . import backtest as B, models as M, store, taxonomy as T
from .sources import packages as P

H = 6
MIN_DOWNLOADS_3M = 30_000
RISE_PP = 2.0
RADAR_MIN_N3 = 60
RIDGE_ALPHAS = (10.0, 100.0, 1000.0)
OWN = ("x_dev", "x_yoy", "own_g6")
EXT = ("ad_g6", "ad_g12", "ad_acc", "has_adoption", "rel_g6", "rel_g12")


def related_map(skills: list[str], cfg: dict) -> dict[str, list[str]]:
    cat = {s.id: s.category for s in T.curated()}
    present = set(skills)
    out = {}
    for s in skills:
        rel = cfg["skills"].get(s, {}).get("related")
        if rel is None:
            rel = [o for o in present if cat.get(o) == cat.get(s) and cat.get(s)]
        out[s] = sorted({r for r in rel if r in present and r != s})
    return out


def _sum3(x: np.ndarray) -> np.ndarray:
    """3-month sums; NaN unless all 3 months are present (a missing month never becomes zero)."""
    return x + M.shift(x, 1) + M.shift(x, 2)


def adoption(dl: pd.DataFrame, cfg: dict, skills: list[str], months: pd.PeriodIndex) -> dict:
    """Arrays [skill, month] of g6, g12, acc and the latest 3-month downloads, plus per-package detail."""
    mi = {str(m): i for i, m in enumerate(months)}
    S, Tn = len(skills), len(months)
    piv = {}
    for (src, pkg), g in dl.groupby(["source", "package"]):
        a = np.full(Tn, np.nan)
        for m, v in zip(g["month"], g["downloads"]):
            if m in mi:
                a[mi[m]] = v
        piv[(src, pkg)] = a
    ref = {}
    for src in ("pypi", "npm"):
        arr = [piv[(src, p)] for p in cfg["reference"][src] if (src, p) in piv]
        ref[src] = np.sum(arr, axis=0) if arr else np.full(Tn, np.nan)  # NaN where any reference month is missing
    out = {k: np.full((S, Tn), np.nan) for k in ("g6", "g12", "acc", "dl3")}
    detail = {}
    for i, s in enumerate(skills):
        num = {k: np.zeros(Tn) for k in ("g6", "g12", "acc")}
        den = {k: np.zeros(Tn) for k in ("g6", "g12", "acc")}
        dl3_tot = np.zeros(Tn)
        for src in ("pypi", "npm"):
            for pkg in cfg["skills"].get(s, {}).get(src, []):
                if (src, pkg) not in piv:
                    continue
                d3 = _sum3(piv[(src, pkg)][None])[0]
                r3 = _sum3(ref[src][None])[0]
                ok3 = d3 >= MIN_DOWNLOADS_3M
                rel = np.where(ok3 & (r3 > 0), np.log(np.maximum(d3, 1)) - np.log(np.maximum(r3, 1)), np.nan)
                g6 = rel - M.shift(rel[None], 6)[0]
                g12 = rel - M.shift(rel[None], 12)[0]
                acc = g6 - M.shift(g6[None], 6)[0]
                w = np.where(ok3, d3, 0.0)
                for k, v in (("g6", g6), ("g12", g12), ("acc", acc)):
                    f = np.isfinite(v)
                    num[k] += np.where(f, w * np.nan_to_num(v), 0)
                    den[k] += np.where(f, w, 0)
                dl3_tot += np.nan_to_num(d3)
                detail[(s, src, pkg)] = {"d3": d3, "g6": g6, "g12": g12}
        for k in ("g6", "g12", "acc"):
            out[k][i] = np.where(den[k] > 0, num[k] / np.maximum(den[k], 1e-9), np.nan)
        out["dl3"][i] = np.where(dl3_tot > 0, dl3_tot, np.nan)
    out["detail"] = detail
    return out


def related(Ks: np.ndarray, Ns: np.ndarray, skills: list[str], rel: dict[str, list[str]]) -> dict:
    """Arrays [skill, month]: mean change in logit share of the related skills (pooled over cells), and the
    skill's own pooled 6-month change (a control feature, never mixed into 'related')."""
    k6, n6 = M.wsum(Ks, 6), M.wsum(Ns, 6)
    k12, n12 = M.wsum(Ks, 12), M.wsum(Ns, 12)
    l6 = M.logit((k6 + 0.5) / (n6 + 1))
    l12 = M.logit((k12 + 0.5) / (n12 + 1))
    g6 = l6 - M.shift(l6, 6)
    g12 = l12 - M.shift(l12, 12)
    idx = {s: i for i, s in enumerate(skills)}
    out = {"rel_g6": np.full(g6.shape, np.nan), "rel_g12": np.full(g6.shape, np.nan), "own_g6": g6}
    w = np.sqrt(np.nan_to_num(k12))
    for s, rs in rel.items():
        j = [idx[r] for r in rs]
        if not j:
            continue
        for k, g in (("rel_g6", g6), ("rel_g12", g12)):
            ww = np.where(np.isfinite(g[j]) & (np.nan_to_num(k12[j]) >= 5), w[j], 0)
            out[k][idx[s]] = np.where(ww.sum(0) > 0, (ww * np.nan_to_num(g[j])).sum(0) / np.maximum(ww.sum(0), 1e-9), np.nan)
    return out


class Signals:
    """Every feature at every (series, month) of a backtest Panel."""

    def __init__(self, p: B.Panel, dl: pd.DataFrame, cfg: dict):
        self.p, self.cfg = p, cfg
        self.skills = sorted(p.series["skill_id"].unique())
        sk = p.f["skill"]
        pool = M.pooled(p.f)
        self.rel = related_map(self.skills, cfg)
        r = related(pool["K"], pool["N"], self.skills, self.rel)
        a = adoption(dl, cfg, self.skills, p.months)
        self.ad, self.r = a, r
        F = {"x_dev": p.f["x_dev"], "x_yoy": p.f["x_yoy"], "own_g6": r["own_g6"][sk],
             "ad_g6": a["g6"][sk], "ad_g12": a["g12"][sk], "ad_acc": a["acc"][sk],
             "rel_g6": r["rel_g6"][sk], "rel_g12": r["rel_g12"][sk]}
        F["has_adoption"] = np.isfinite(F["ad_g6"]).astype(float)
        self.F = F

    def X(self, names, rows, cols) -> np.ndarray:
        return np.column_stack([np.nan_to_num(self.F[c][rows, cols]) for c in names])

    def coverage(self, rows, cols) -> dict:
        return {"rows": int(len(rows)),
                "with_adoption": int(np.isfinite(self.F["ad_g6"][rows, cols]).sum()),
                "with_related": int(np.isfinite(self.F["rel_g6"][rows, cols]).sum())}


def relationship(sg: Signals, last_origin: int) -> dict:
    """How each evidence feature has related to the next H months' change in a skill's job-ad share, pooled over
    every IT cell (where sampling noise is smallest): weighted correlation and slope over origins whose target
    ended by `last_origin` + H, i.e. origins <= last_origin. Monthly origins overlap, so the effective sample is far smaller than n."""
    pool = M.pooled(sg.p.f)
    k6, n6 = M.wsum(pool["K"], 6), M.wsum(pool["N"], 6)
    l6 = M.logit((k6 + 0.5) / (n6 + 1))
    fut = np.full(l6.shape, np.nan)
    fut[:, :-H] = l6[:, H:] - l6[:, :-H]
    feats = {"adoption_g6": sg.ad["g6"], "adoption_g12": sg.ad["g12"], "adoption_acc": sg.ad["acc"],
             "related_g6": sg.r["rel_g6"], "related_g12": sg.r["rel_g12"], "own_pooled_g6": sg.r["own_g6"]}
    out = {}
    for name, x in feats.items():
        cols = np.arange(12, max(12, last_origin + 1))
        xs, ys, ws = [], [], []
        for t in cols:
            ok = np.isfinite(x[:, t]) & np.isfinite(fut[:, t]) & (k6[:, t] >= 30)
            xs.append(x[ok, t]); ys.append(fut[ok, t]); ws.append(np.sqrt(k6[ok, t]))
        X, Y, W = (np.concatenate(a) if a else np.array([]) for a in (xs, ys, ws))
        if len(X) < 50 or np.var(X) == 0:
            out[name] = {"n": int(len(X)), "corr": None, "slope": None}
            continue
        c = np.cov(X, Y, aweights=W)
        out[name] = {"n": int(len(X)), "corr": float(c[0, 1] / np.sqrt(c[0, 0] * c[1, 1])), "slope": float(c[0, 1] / c[0, 0])}
    return out


def _base_rows(bt: pd.DataFrame, served: str) -> pd.DataFrame:
    b = bt[(bt["h"] == H) & bt["method"].isin([served, "persistence"])]
    w = b.pivot_table(index=["series", "origin_idx"], columns="method", values="forecast").reset_index()
    meta = b[b["method"] == served].drop(columns=["method", "forecast"])
    w = meta.merge(w, on=["series", "origin_idx"]).rename(columns={served: "baseline"})
    return w.sort_values(["origin_idx", "series"]).reset_index(drop=True)


def _refits(cols: np.ndarray, force: int | None = None) -> np.ndarray:
    """Each origin's refit point (every REFIT months); origins at `force` get their own refit there."""
    c0 = B.MIN_HISTORY - 1
    ref = cols - (cols - c0) % B.REFIT
    if force is not None:
        ref = np.where(cols == force, force, ref)
    return ref


def corrections(sg: Signals, rows_df: pd.DataFrame, names, alpha: float, force: int | None = None) -> tuple[np.ndarray, dict]:
    """Baseline + ridge correction at every row, refit on rows whose target was observed by each refit point.
    Fitted in share points (least squares, so unbiased in the target's own units): each feature, a change in
    log or logit terms, is scaled by p(1 - p) of the baseline forecast p, which converts it to share points, and
    p(1 - p) itself replaces the intercept. Returns forecasts and the last refit's coefficients (logit units)."""
    r, c = rows_df["series"].to_numpy(), rows_df["origin_idx"].to_numpy()
    p = rows_df["baseline"].to_numpy()
    v = (p * (1 - p))[:, None]
    X = np.hstack([sg.X(names, r, c) * v, v])
    y = rows_df["actual"].to_numpy() - p
    w = np.minimum(rows_df["actual_n"].to_numpy(), 300)
    ref = _refits(c, force)
    pred = p.copy()
    coef = {}
    for rp in sorted(set(ref.tolist())):
        past = c + H <= rp
        if past.sum() < B.MIN_RIDGE_ROWS:
            continue
        sc = StandardScaler(with_mean=False).fit(X[past])
        m = Ridge(alpha=alpha, fit_intercept=False).fit(sc.transform(X[past]), y[past], sample_weight=w[past])
        sel = ref == rp
        pred[sel] = np.clip(p[sel] + m.predict(sc.transform(X[sel])), 0, 1)
        coef = {"refit_origin": int(rp),
                "coef_logit": dict(zip([*names, "intercept"], map(float, m.coef_ / sc.scale_)))}
    return pred, coef


def _rise(rows_df: pd.DataFrame) -> np.ndarray:
    _, sig = B._moves(rows_df.assign(forecast=0.0), RISE_PP)
    return sig & (rows_df["actual"] > rows_df["p3_origin"]).to_numpy()


def radar(sg: Signals, rows_df: pd.DataFrame, names, force: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Rolling logistic probability of a significant rise and the alert (above the past-F1-best threshold)."""
    r, c = rows_df["series"].to_numpy(), rows_df["origin_idx"].to_numpy()
    X = np.column_stack([sg.X(names, r, c), np.log1p(np.nan_to_num(rows_df["n3_origin"].to_numpy())),
                         M.logit(np.clip(rows_df["p3_origin"].to_numpy(), 1e-3, 1 - 1e-3))])
    y = _rise(rows_df)
    ref = _refits(c, force)
    prob, alert = np.full(len(r), np.nan), np.zeros(len(r), bool)
    for rp in sorted(set(ref.tolist())):
        past = c + H <= rp
        if past.sum() < B.MIN_RIDGE_ROWS or y[past].sum() < 20:
            continue
        sc = StandardScaler().fit(X[past])
        m = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(X[past]), y[past])
        pp = m.predict_proba(sc.transform(X[past]))[:, 1]
        thr = _best_threshold(pp, y[past])
        sel = ref == rp
        prob[sel] = m.predict_proba(sc.transform(X[sel]))[:, 1]
        alert[sel] = prob[sel] >= thr
    return prob, alert


def _best_threshold(p: np.ndarray, y: np.ndarray) -> float:
    best, thr = -1.0, 1.0
    for t in np.unique(np.quantile(p, np.linspace(0.5, 0.995, 60))):
        a = p >= t
        tp = (a & y).sum()
        f1 = 2 * tp / max(a.sum() + y.sum(), 1)
        if f1 > best:
            best, thr = f1, float(t)
    return thr


def radar_metrics(prob: np.ndarray, alert: np.ndarray, y: np.ndarray) -> dict:
    ok = np.isfinite(prob)
    p, a, y = prob[ok], alert[ok], y[ok]
    tp, fp = int((a & y).sum()), int((a & ~y).sum())
    return {"n": int(ok.sum()), "positives": int(y.sum()), "alerts": tp + fp, "true_alerts": tp,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / y.sum() if y.sum() else None,
            "false_positive_rate": fp / (~y).sum() if (~y).sum() else None,
            "base_rate": float(y.mean()) if len(y) else None,
            "average_precision": float(average_precision_score(y, p)) if y.any() and (~y).any() else None}


def _bootstrap_ap(prob_a, prob_b, y, series, seed=0) -> float:
    """Share of series-bootstrap resamples in which a's average precision beats b's."""
    ok = np.isfinite(prob_a) & np.isfinite(prob_b)
    pa, pb, yy, ss = prob_a[ok], prob_b[ok], y[ok], series[ok]
    if not yy.any() or yy.all():
        return 0.0
    uniq, inv = np.unique(ss, return_inverse=True)
    groups = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    wins = n = 0
    for _ in range(B.BOOTSTRAP):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(uniq), len(uniq))])
        if yy[idx].any() and (~yy[idx]).any():
            n += 1
            wins += average_precision_score(yy[idx], pa[idx]) > average_precision_score(yy[idx], pb[idx])
    return wins / max(n, 1)


def evaluate(p: B.Panel, bt: pd.DataFrame, ev: dict, dl: pd.DataFrame, cfg: dict) -> tuple[dict, Signals, dict]:
    served = ev["horizons"][str(H)]["served"]
    sg = Signals(p, dl, cfg)
    rows = _base_rows(bt, served)
    # ridge strength per model: the selection score on training-period targets (as backtest.tune)
    tune = rows[(rows["role"] == "train") & (rows["origin_idx"] + H >= p.T - 24 - B.TUNE_MONTHS)]
    models, alphas = {"control": OWN, "hybrid": OWN + EXT}, {}
    for name, cols in models.items():
        sc = {}
        for a in RIDGE_ALPHAS:
            f, _ = corrections(sg, rows, cols, a)
            t = rows.assign(forecast=f).loc[tune.index]
            sc[a] = B.score(t.assign(method=name), tune.assign(forecast=tune["persistence"]))["score"]
        alphas[name] = min(sc, key=sc.get)
    fc, coefs = {"baseline": rows["baseline"].to_numpy()}, {}
    for name, cols in models.items():
        fc[name], coefs[name] = corrections(sg, rows, cols, alphas[name])
    long = pd.concat([rows.assign(method=m, forecast=v) for m, v in
                      {**fc, "persistence": rows["persistence"].to_numpy()}.items()], ignore_index=True)
    long = long.drop(columns=["baseline", "persistence"])
    out = {"horizon": H, "baseline_method": served, "alphas": alphas, "coefficients": coefs, "roles": {}}
    big = rows["n3_origin"].to_numpy() >= 200
    for role in ("validation", "test"):
        g = long[long["role"] == role]
        naive = g[g["method"] == "persistence"]
        sc = {m: B.metrics(gm, naive, detail=True) for m, gm in g.groupby("method")}
        r = rows[rows["role"] == role]
        sub = {}
        for lab, mask in (("large_cells_200plus", big[r.index]), ("small_cells_under_200", ~big[r.index])):
            gg = g[g.set_index(["series", "origin_idx"]).index.isin(r[mask].set_index(["series", "origin_idx"]).index)]
            nn = gg[gg["method"] == "persistence"]
            sub[lab] = {m: B.metrics(gm, nn, detail=True)["moves"] for m, gm in gg.groupby("method")} if len(nn) else {}
        cov = sg.coverage(r["series"].to_numpy(), r["origin_idx"].to_numpy())
        out["roles"][role] = {"scores": sc, "by_cell_size": sub, "coverage": cov}
    val = out["roles"]["validation"]["scores"]
    cand = {m: val[m] for m in ("persistence", "baseline", "control", "hybrid")}
    best = min(("baseline", "control", "hybrid"), key=lambda m: cand[m]["selection_score"])
    beats = {m: B._beats(long[long["role"] == "validation"], "hybrid", m, None)
             for m in ("baseline", "control")} if best == "hybrid" else {}
    test = out["roles"]["test"]["scores"]
    adjusted = (best == "hybrid" and all(v >= B.CONFIDENCE for v in beats.values())
                and test["hybrid"]["mae_pp"] <= test["baseline"]["mae_pp"]
                and test["hybrid"]["selection_score"] <= test["baseline"]["selection_score"])
    out["adjusted_forecast"] = {"best_on_validation": best, "hybrid_beats_in_bootstrap": beats,
                                "validated": bool(adjusted),
                                "rule": "hybrid lowest validation selection score, beats baseline and control in "
                                        f">= {B.CONFIDENCE:.0%} of series resamples, and no worse on test (MAE "
                                        "and selection score)"}
    # radar
    ok = rows["n3_origin"].to_numpy() >= RADAR_MIN_N3
    rr = rows[ok].reset_index(drop=True)
    y = _rise(rr)
    probs = {name: radar(sg, rr, cols) for name, cols in (("own", OWN), ("hybrid", OWN + EXT))}
    rad = {"rise_pp": RISE_PP, "min_ads_3m": RADAR_MIN_N3, "roles": {}}
    for role in ("validation", "test"):
        s = (rr["role"] == role).to_numpy()
        rad["roles"][role] = {name: radar_metrics(pr[s], al[s], y[s]) for name, (pr, al) in probs.items()}
        adm = s & sg.F["has_adoption"][rr["series"], rr["origin_idx"]].astype(bool)
        rad["roles"][role]["with_adoption_only"] = {name: radar_metrics(pr[adm], al[adm], y[adm])
                                                    for name, (pr, al) in probs.items()}
    v = (rr["role"] == "validation").to_numpy()
    rad["hybrid_beats_own_ap_in_bootstrap"] = _bootstrap_ap(probs["hybrid"][0][v], probs["own"][0][v], y[v],
                                                            rr["series"].to_numpy()[v])
    tv, to = rad["roles"]["test"]["hybrid"], rad["roles"]["test"]["own"]
    rad["validated"] = bool(rad["hybrid_beats_own_ap_in_bootstrap"] >= B.CONFIDENCE and tv["average_precision"]
                            and to["average_precision"] and tv["average_precision"] >= to["average_precision"])
    out["radar"] = rad
    out["relationship"] = {"period": f"targets ending by {p.months[p.T - 25]} (training)",
                           "features": relationship(sg, p.T - 25 - H)}
    out["coverage"] = {"skills_with_adoption_indicators": sorted(s for s in sg.skills if cfg["skills"].get(s, {}).get("pypi") or cfg["skills"].get(s, {}).get("npm")),
                       "package_months": {src: [dl.loc[dl["source"] == src, "month"].min(), dl.loc[dl["source"] == src, "month"].max()]
                                          for src in ("pypi", "npm") if (dl["source"] == src).any()}}
    state = {"rows": rows, "alphas": alphas, "radar_rows": rr}
    return out, sg, state


def latest(p: B.Panel, sg: Signals, fc: pd.DataFrame, ev_sig: dict, state: dict, dl: pd.DataFrame) -> pd.DataFrame:
    """Per published (cell, skill) at H: the baseline, the evidence, the radar (if validated) and the adjusted
    forecast (if validated), plus the scenario's basis."""
    t0 = p.T - 1
    f = fc[fc["h"] == H].copy()
    key = {(c, o, s): i for i, (c, o, s) in enumerate(p.series[["country", "occupation", "skill_id"]].itertuples(index=False, name=None))}
    rows = np.array([key[(c, o, s)] for c, o, s in zip(f["country"], f["occupation"], f["skill_id"])])
    cols = np.full(len(rows), t0)
    F = sg.F
    f["adoption_g6"], f["adoption_g12"] = F["ad_g6"][rows, cols], F["ad_g12"][rows, cols]
    f["adoption_acc"] = F["ad_acc"][rows, cols]
    f["related_g6"], f["related_g12"] = F["rel_g6"][rows, cols], F["rel_g12"][rows, cols]
    f["own_pooled_g6"] = F["own_g6"][rows, cols]
    f["evidence_cell"] = np.where(f["last_ads_3m"] >= 200, "large", np.where(f["last_ads_3m"] >= RADAR_MIN_N3, "medium", "low"))
    # the radar / adjusted model refit on every row observed by t0
    hist = state["rows"]
    rows_df = pd.DataFrame({"series": rows, "origin_idx": cols, "baseline": f["forecast"].to_numpy(),
                            "actual_k": 0.0, "actual_n": 1.0, "n3_origin": f["last_ads_3m"].to_numpy(),
                            "p3_origin": f["baseline_share"].to_numpy(), "actual": 0.0})
    both = pd.concat([hist, rows_df], ignore_index=True)
    both["origin_idx"] = both["origin_idx"].astype(int)
    if ev_sig["adjusted_forecast"]["validated"]:
        adj, _ = corrections(sg, both, OWN + EXT, state["alphas"]["hybrid"], force=t0)
        f["adjusted_forecast"] = adj[len(hist):]
    else:
        f["adjusted_forecast"] = np.nan
    if ev_sig["radar"]["validated"]:
        rr = both[(both["n3_origin"] >= RADAR_MIN_N3).to_numpy()].reset_index(drop=True)
        pr, al = radar(sg, rr, OWN + EXT, force=t0)
        new = rr["origin_idx"].to_numpy() == t0
        m = dict(zip(rr.loc[new, "series"], zip(pr[new], al[new])))
        f["rise_probability"] = [m.get(r, (np.nan, False))[0] for r in rows]
        f["rise_alert"] = [bool(m.get(r, (np.nan, False))[1]) for r in rows]
    else:
        f["rise_probability"], f["rise_alert"] = np.nan, False
    f["signal"] = _signal_label(f)
    return f


def _signal_label(f: pd.DataFrame) -> np.ndarray:
    """Evidence summary (not a forecast): adoption and related demand both up / both down / mixed / none."""
    a, r = f["adoption_g6"].to_numpy(), f["related_g6"].to_numpy()
    up = lambda x: np.isfinite(x) & (x >= 0.1)
    dn = lambda x: np.isfinite(x) & (x <= -0.1)
    return np.select([up(a) & up(r), up(a) & dn(r) | dn(a) & up(r), up(a) | up(r), dn(a) & dn(r), dn(a) | dn(r)],
                     ["accelerating", "contradictory", "some_acceleration", "slowing", "some_slowing"], "no_signal")


def indicators(sg: Signals, dl: pd.DataFrame, cfg: dict, last_month: str) -> pd.DataFrame:
    """Per skill x package at the last complete month: latest 3-month downloads, growth vs 6 and 12 months
    before, history length, freshness and evidence quality."""
    rows = []
    mi = {str(m): i for i, m in enumerate(sg.p.months)}
    t0 = mi[last_month]
    for (s, src, pkg), d in sg.ad["detail"].items():
        g = dl[(dl["source"] == src) & (dl["package"] == pkg)]
        latest_obs = g["month"].max() if len(g) else None
        hist = int(np.isfinite(d["d3"][: t0 + 1]).sum())
        d3 = d["d3"][t0]
        q = ("strong" if np.isfinite(d3) and d3 >= 1e6 and hist >= 24 else
             "moderate" if np.isfinite(d3) and d3 >= 1e5 and hist >= 12 else "weak")
        rows.append({"skill_id": s, "source": src, "package": pkg, "latest_month": latest_obs,
                     "downloads_3m": d3, "growth_vs_6m_before": d["g6"][t0], "growth_vs_12m_before": d["g12"][t0],
                     "window": f"3 months to {last_month} vs the 3 months 6 and 12 months earlier, relative to "
                               f"the {src} reference basket",
                     "months_of_history": hist, "quality": q,
                     "fresh": latest_obs is not None and latest_obs >= last_month,
                     "url": (f"https://clickpy.clickhouse.com/dashboard/{pkg}" if src == "pypi"
                             else f"https://www.npmjs.com/package/{pkg}")})
    return pd.DataFrame(rows)
