"""Monte Carlo of AI adoption at work, per SOC major group and per job, under three scenarios, 3-12 months ahead.

Input : data/processed/ai_adoption.csv        quarterly adoption rate per SOC major group (00 = all workers),
                                              with respondents per quarter
        data/processed/ai_adoption_jobs.csv   each job's pooled rate and its group's pooled rate
Output: ml/output/ai_adoption_mc.csv          group x scenario x horizon: p10 / p25 / p50 / p75 / p90
        ml/output/ai_adoption_mc_jobs.csv     the same per job
        ml/output/ai_adoption_mc_meta.json    parameters, seed, fitted trends, backtest coverage

Independent of the job-postings forecast (train_lgbm.py). The scenario odds are not set here: they come from
ml/ai_signal_score.py, which reweights these three scenarios every week.

Method, all on the logit of the rate (so paths stay within 0-1 and slow down near the top):
  1. Survey noise: a quarter's reading has variance p(1-p)/n x DEFF (n = respondents, DEFF = design effect).
  2. Trend: national slope from a weighted line through the all-workers series. Each group's own slope is
     shrunk toward the national one (empirical Bayes): a group with few respondents or a jumpy series ends
     up close to the national trend. A backtest earlier showed group-only trends are mostly noise.
  3. Level: a Kalman filter (local level with that drift) gives today's true level and its uncertainty,
     separating real change from sampling noise. Its process noise Q is fitted by maximum likelihood,
     shared by all groups.
  4. Paths: N paths per group and scenario, each drawing a starting level and a slope from their
     uncertainty, then stepping one quarter at a time with process noise Q.

Scenarios (assumptions, not learned; drift per quarter in logit units, b_g = group slope, b_nat = national):
  AI accelerates   b_g + 0.5 x b_nat     adoption grows faster than today
  AI holds         b_g                   today's pace continues
  AI declines      b_g - 1.5 x b_nat     adoption slips back
Jobs keep their gap to their group on the logit scale: job path = group path + (logit(job) - logit(group)).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATA_DIR = HERE.parents[2] / "data" / "processed"
HORIZONS = [3, 6, 9, 12]  # months; the series is quarterly, so 1-4 steps
N_PATHS = 10_000
DEFF = 3.0  # survey design effect: weighting makes the sample act smaller than n. Set so the backtest's
            # 10-90% ranges hold ~80% of readings (1.5 gave 72%, 3.0 gives 80%, 4.0 gives 84%)
NATIONAL = "00"
SCENARIOS = {"AI accelerates": 0.5, "AI holds": 0.0, "AI declines": -1.5}  # x b_nat added to the group slope
QUANTILES = {"p10": 0.10, "p25": 0.25, "p50": 0.50, "p75": 0.75, "p90": 0.90}
MIN_HISTORY = 4  # quarters needed before a backtest origin
Q_GRID = np.geomspace(1e-4, 0.2, 40)


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def obs_var(p: np.ndarray, n: float) -> np.ndarray:
    """Sampling variance of a reading on the logit scale (delta method)."""
    p = np.clip(p, 0.01, 0.99)
    return DEFF / (n * p * (1 - p))


def weighted_slope(x: np.ndarray, var: np.ndarray) -> tuple[float, float]:
    """Slope per quarter of a weighted least-squares line, and its standard error."""
    t = np.arange(len(x))
    w = 1 / var
    tm = np.sum(w * t) / w.sum()
    xm = np.sum(w * x) / w.sum()
    sxx = np.sum(w * (t - tm) ** 2)
    b = np.sum(w * (t - tm) * (x - xm)) / sxx
    resid = x - (xm + b * (t - tm))
    scale = max(1.0, np.sum(w * resid ** 2) / max(len(x) - 2, 1))  # widen if the data are noisier than n says
    return float(b), float(np.sqrt(scale / sxx))


def kalman(x: np.ndarray, r: np.ndarray, drift: float, q: float) -> tuple[float, float, float]:
    """Local level with known drift. Returns (filtered level, its variance, log-likelihood)."""
    level, var, ll = x[0], r[0], 0.0
    for t in range(1, len(x)):
        level, var = level + drift, var + q
        s = var + r[t]
        innov = x[t] - level
        ll += -0.5 * (np.log(2 * np.pi * s) + innov ** 2 / s)
        k = var / s
        level, var = level + k * innov, (1 - k) * var
    return float(level), float(var), ll


def fit(wide: pd.DataFrame, n: pd.Series) -> dict:
    """Trends, shrinkage, process noise and filtered levels from the history in `wide` (groups x quarters)."""
    x = {g: logit(wide.loc[g].to_numpy()) for g in wide.index}
    r = {g: obs_var(wide.loc[g].to_numpy(), n[g]) for g in wide.index}
    b_nat, se_nat = weighted_slope(x[NATIONAL], r[NATIONAL])
    groups = [g for g in wide.index if g != NATIONAL]
    raw = {g: weighted_slope(x[g], r[g]) for g in groups}
    d = np.array([raw[g][0] - b_nat for g in groups])
    se2 = np.array([raw[g][1] ** 2 for g in groups])
    tau2 = max(0.0, float(np.var(d) - se2.mean()))  # spread of true group differences
    shrink = {g: tau2 / (tau2 + raw[g][1] ** 2) for g in groups}
    slope = {g: b_nat + shrink[g] * (raw[g][0] - b_nat) for g in groups} | {NATIONAL: b_nat}
    slope_se = {g: float(np.sqrt(se_nat ** 2 + shrink[g] * raw[g][1] ** 2)) for g in groups} | {NATIONAL: se_nat}
    q = max(Q_GRID, key=lambda q: sum(kalman(x[g], r[g], slope[g], q)[2] for g in wide.index))
    levels = {g: kalman(x[g], r[g], slope[g], q)[:2] for g in wide.index}
    return {"b_nat": b_nat, "q": float(q), "tau2": tau2, "slope": slope, "slope_se": slope_se,
            "shrink": shrink, "raw_slope": {g: raw[g][0] for g in groups}, "levels": levels}


def simulate(level: float, level_var: float, slope: float, slope_se: float, b_nat: float, q: float,
             shift: float, steps: int, rng: np.random.Generator) -> np.ndarray:
    """Logit paths, shape (N_PATHS, steps), for one group and scenario."""
    x0 = rng.normal(level, np.sqrt(level_var), N_PATHS)
    b = rng.normal(slope, slope_se, N_PATHS) + shift * b_nat
    noise = rng.normal(0, np.sqrt(q), (N_PATHS, steps)).cumsum(axis=1)
    return x0[:, None] + b[:, None] * np.arange(1, steps + 1) + noise


def backtest(wide: pd.DataFrame, n: pd.Series, rng: np.random.Generator) -> dict:
    """From each past origin, does the 'AI holds' 10-90% range contain the next survey readings?

    The simulated true rate gets survey noise added before the check, since the reading is noisy too.
    Also scores the p50 against 'last reading repeats', for reference only (accuracy is not the goal).
    """
    hits = {h: [] for h in HORIZONS}
    err_mc, err_flat = {h: [] for h in HORIZONS}, {h: [] for h in HORIZONS}
    for k in range(MIN_HISTORY, wide.shape[1]):
        f = fit(wide.iloc[:, :k], n)
        for g in wide.index:
            level, var = f["levels"][g]
            paths = simulate(level, var, f["slope"][g], f["slope_se"][g], f["b_nat"], f["q"], 0.0, 4, rng)
            for h in HORIZONS:
                step = h // 3
                if k - 1 + step >= wide.shape[1]:
                    continue
                actual = wide.loc[g].iloc[k - 1 + step]
                p = sigmoid(paths[:, step - 1])
                reading = sigmoid(logit(p) + rng.normal(0, np.sqrt(obs_var(p, n[g]))))
                lo, hi = np.quantile(reading, [0.10, 0.90])
                hits[h].append(lo <= actual <= hi)
                err_mc[h].append(abs(np.median(p) - actual))
                err_flat[h].append(abs(wide.loc[g].iloc[k - 1] - actual))
    return {str(h): {"coverage_10_90": round(float(np.mean(hits[h])), 3), "n": len(hits[h]),
                     "mae_pts_p50": round(float(np.mean(err_mc[h])) * 100, 2),
                     "mae_pts_last_reading": round(float(np.mean(err_flat[h])) * 100, 2)}
            for h in HORIZONS if hits[h]}


def summarise(rates: np.ndarray) -> dict:
    return {k: round(float(np.quantile(rates, q)), 4) for k, q in QUANTILES.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_DIR))
    ap.add_argument("--out-dir", default=str(HERE / "output"))
    ap.add_argument("--skip-backtest", action="store_true")
    args = ap.parse_args()
    data, out_dir = Path(args.data), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    series = pd.read_csv(data / "ai_adoption.csv", dtype={"soc_major": str})
    wide = series.pivot(index="soc_major", columns="quarter", values="adoption_rate").sort_index(axis=1)
    assert not wide.isna().any().any(), "every group needs every quarter"
    n = series.drop_duplicates("soc_major").set_index("soc_major")["respondents_per_quarter"].astype(float)
    names = series.drop_duplicates("soc_major").set_index("soc_major")["soc_major_name"]
    latest = pd.Period(wide.columns[-1], freq="M")
    as_of = str(series["as_of_date"].max())
    seed = int(latest.strftime("%Y%m"))  # same data -> same paths
    rng = np.random.default_rng(seed)

    f = fit(wide, n)
    rows, paths_by_group = [], {}
    for g in wide.index:
        level, var = f["levels"][g]
        paths_by_group[g] = {}
        for scenario, shift in SCENARIOS.items():
            paths = simulate(level, var, f["slope"][g], f["slope_se"][g], f["b_nat"], f["q"], shift, 4, rng)
            paths_by_group[g][scenario] = paths
            for h in HORIZONS:
                rows.append({"soc_major": g, "soc_major_name": names[g], "scenario": scenario, "horizon_m": h,
                             "forecast_from": str(latest), "forecast_for": str(latest + h),
                             "rate_now": round(float(sigmoid(level)), 4),
                             **summarise(sigmoid(paths[:, h // 3 - 1])), "as_of_date": as_of})
    out = pd.DataFrame(rows)
    assert out[list(QUANTILES)].apply(lambda c: c.between(0, 1)).all().all()
    out.to_csv(out_dir / "ai_adoption_mc.csv", index=False)

    jobs = pd.read_csv(data / "ai_adoption_jobs.csv", dtype={"soc_major": str}).dropna(subset=["adoption_rate"])
    job_rows = []
    for j in jobs.itertuples():
        offset = logit(j.adoption_rate) - logit(j.group_pooled_rate)
        now = sigmoid(f["levels"][j.soc_major][0] + offset)
        for scenario, paths in paths_by_group[j.soc_major].items():
            for h in HORIZONS:
                job_rows.append({"onet_code": j.onet_code, "title": j.title, "soc_major": j.soc_major,
                                 "scenario": scenario, "horizon_m": h, "forecast_from": str(latest),
                                 "forecast_for": str(latest + h), "rate_now": round(float(now), 4),
                                 **summarise(sigmoid(paths[:, h // 3 - 1] + offset)), "as_of_date": as_of})
    job_out = pd.DataFrame(job_rows)
    job_out.to_csv(out_dir / "ai_adoption_mc_jobs.csv", index=False)

    meta = {
        "data_as_of": as_of,
        "quarters": [str(c) for c in wide.columns],
        "target": "share of employed US adults (18-64) in the group who use generative AI for their job",
        "seed": seed,
        "n_paths": N_PATHS,
        "design_effect": DEFF,
        "scenarios": {s: f"group slope + {shift} x national slope (logit per quarter)" for s, shift in SCENARIOS.items()},
        "national_slope_logit_per_quarter": round(f["b_nat"], 4),
        "process_noise_q": round(f["q"], 5),
        "between_group_slope_variance": round(f["tau2"], 5),
        "groups": {g: {"name": names[g], "raw_slope": round(f["raw_slope"].get(g, f["b_nat"]), 4),
                       "slope": round(f["slope"][g], 4), "shrink_to_own": round(f["shrink"].get(g, 1.0), 3),
                       "rate_now": round(float(sigmoid(f["levels"][g][0])), 4),
                       "latest_reading": round(float(wide.loc[g].iloc[-1]), 4)} for g in wide.index},
        "backtest_ai_holds": None if args.skip_backtest else backtest(wide, n, np.random.default_rng(seed)),
    }
    (out_dir / "ai_adoption_mc_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote ai_adoption_mc.csv ({len(out)} rows = {wide.shape[0]} groups x {len(SCENARIOS)} scenarios x "
          f"{len(HORIZONS)} horizons), ai_adoption_mc_jobs.csv ({len(job_out)} rows), ai_adoption_mc_meta.json -> {out_dir}")
    print(f"  national slope {f['b_nat']:.4f} logit/quarter, process noise q {f['q']:.5f}, tau2 {f['tau2']:.5f}")
    if meta["backtest_ai_holds"]:
        for h, s in meta["backtest_ai_holds"].items():
            print(f"  backtest {h:>2}m: 10-90% range covered {s['coverage_10_90']:.0%} of {s['n']} readings "
                  f"(target ~80%); p50 error {s['mae_pts_p50']} pts vs last reading {s['mae_pts_last_reading']} pts")


if __name__ == "__main__":
    main()
