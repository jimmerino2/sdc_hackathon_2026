"""Walk through how ridge and LightGBM learn, on the real AI capability data. Read-only: writes nothing.

From src/backend:  python -m forecasting.demo_ridge_lightgbm
                   python -m forecasting.demo_ridge_lightgbm --h 6

Everything is in doublings: +1 means the 50% time horizon doubled.
"""
from __future__ import annotations

import argparse

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import features as F
from .models import LGB_PARAMS, LightGBMModel, RidgeModel
from .targets.capability_metr import SPEC

MEANING = {"lvl": "level now (log2 minutes)", "d1": "growth last 1 month", "d3": "growth last 3 months",
           "d6": "growth last 6 months", "d12": "growth last 12 months"}


def title(text: str) -> None:
    print(f"\n{'=' * 90}\n{text}\n{'=' * 90}")


def show_examples(train: pd.DataFrame, feats: list[str], h: int) -> None:
    title(f"STEP 1. THE EXAMPLES BOTH MODELS LEARN FROM ({len(train)} rows)")
    print(f"Each row is one past month. Inputs: what was known then. Answer ('target'): growth over the next {h} months.")
    print(train.groupby("unit").size().rename("rows per series").to_string())
    print("\nThe most recent 6 examples (blank = not enough history yet):")
    recent = train.sort_values("period").tail(6)
    print(recent.round({c: 2 for c in [*feats, "target"]})[["period", "unit", *feats, "target"]].to_string(index=False, na_rep=""))


def one_input_line(train: pd.DataFrame) -> None:
    title("STEP 2. RIDGE WITH ONE INPUT: A LINE THROUGH A SCATTER GRAPH")
    d = train.dropna(subset=["d3", "target"])
    x, y = d["d3"].to_numpy(), d["target"].to_numpy()
    print(f"x = growth last 3 months, y = growth next. {len(x)} points.\n")
    print("Total squared miss of a few lines:")
    b, a = np.polyfit(x, y, 1)
    for label, w, s in (("flat line at the average", 0.0, y.mean()), ("guess 1", 1.0, 0.0), ("best line", b, a)):
        print(f"  y = {s:5.2f} + {w:5.2f} x   ({label}): {((y - (s + w * x)) ** 2).sum():8.2f}")
    print("\nThe ridge penalty pulls the weight towards 0. Bigger alpha = trusts the pattern less:")
    dx, dy = x - x.mean(), y - y.mean()
    for alpha in (0, 1, 10, 100, 1000):
        print(f"  alpha {alpha:>5}: weight {(dx * dy).sum() / ((dx ** 2).sum() + alpha):6.3f}")


def ridge(train: pd.DataFrame, now: pd.Series, feats: list[str], h: int) -> float:
    title("STEP 3. REAL RIDGE MODEL: ONE WEIGHT PER INPUT")
    m = RidgeModel().fit(train, h, feats)
    imputer, scaler, model = (m.pipe[i] for i in range(3))
    print(f"alpha picked by training on earlier months and testing on later ones: {m.alpha}")
    names = imputer.get_feature_names_out(feats)
    z = scaler.transform(imputer.transform(pd.DataFrame([now[feats]], columns=feats)))[0]
    print("\nInputs are first rescaled to a common size, so a weight reads: 'one typical swing of this input moves the")
    print("forecast by this many doublings'. Weight x today's rescaled input = its share of the forecast:\n")
    print(f"  {'start value (average answer)':<44}{'':>8}{'':>10}{model.intercept_:>10.3f}")
    for n, w, v in zip(names, model.coef_, z):
        print(f"  {MEANING.get(n, n):<44}{w:>8.3f}{v:>10.2f}{w * v:>10.3f}")
    total = float(model.intercept_ + model.coef_ @ z)
    print(f"  {'FORECAST (added up)':<44}{'':>18}{total:>10.3f} doublings")
    print(f"\nCheck against the model itself: {float(m.predict(pd.DataFrame([now]))[0]):.3f}")

    print("\n'Tweaking the weights': sklearn solves ridge in one calculation, but stepping there shows the idea.")
    print("Start at 0, nudge each weight in the direction that shrinks the miss. It lands on the same weights:\n")
    Z = scaler.transform(imputer.transform(train[feats]))
    y = train["target"].to_numpy() - model.intercept_
    w = np.zeros(Z.shape[1])
    step = 1 / (np.linalg.eigvalsh(Z.T @ Z).max() + m.alpha)
    for i in range(1, 20001):
        w -= step * (Z.T @ (Z @ w - y) + m.alpha * w)
        if i in (1, 10, 100, 1000, 20000):
            print(f"  after {i:>5} nudges: squared miss {((Z @ w - y) ** 2).sum():8.2f}  weights {np.round(w, 3)}")
    print(f"  exact answer:                              weights {np.round(model.coef_, 3)}")
    return total


def walk(tree: pd.DataFrame, row: pd.Series) -> tuple[list[str], float]:
    """Follow one tree for one row -> (questions and answers, the number at the end point)."""
    nodes = tree.set_index("node_index")
    node = tree.loc[tree["node_depth"] == 1, "node_index"].iloc[0]
    path = []
    while pd.notna(nodes.loc[node, "split_feature"]):
        n = nodes.loc[node]
        v = row[n["split_feature"]]
        left = (n["missing_direction"] == "left") if pd.isna(v) else v <= n["threshold"]
        path.append(f"{MEANING.get(n['split_feature'], n['split_feature'])} <= {n['threshold']:.2f}? "
                    f"{'yes' if left else 'no'} (today {v:.2f})")
        node = n["left_child"] if left else n["right_child"]
    return path, float(nodes.loc[node, "value"])


def show_trees(booster: lgb.Booster, row: pd.Series, feats: list[str], n: int = 3) -> None:
    trees = booster.trees_to_dataframe()
    for i in range(n):
        t = trees[trees["tree_index"] == i]
        print(f"\nTree {i + 1} ({int(t['split_feature'].notna().sum())} questions):")
        path, value = walk(t, row)
        for p in path:
            print(f"    {p}")
        print(f"    end point: {value:+.4f}")


def lightgbm(train: pd.DataFrame, now: pd.Series, feats: list[str], h: int) -> float:
    title("STEP 4. REAL LIGHTGBM MODEL: 150 SMALL TREES")
    need = 2 * LGB_PARAMS["min_child_samples"]
    print(f"Each end point needs at least {LGB_PARAMS['min_child_samples']} examples, so training needs {need} rows. There are {len(train)}.")
    m = LightGBMModel().fit(train, h, feats)
    row = pd.DataFrame([now])[feats]
    if m.m is None:
        print(f"Too few rows, so the real model builds no trees: it forecasts the average change, {m.mean:.3f} doublings.")
        real = m.mean
    else:
        trees = m.m.booster_.trees_to_dataframe()
        print(f"Trees with at least one question: {trees[trees['split_feature'].notna()]['tree_index'].nunique()} of {m.m.n_estimators}")
        real = float(m.predict(pd.DataFrame([now]))[0])
        show_trees(m.m.booster_, now, feats)
        print(f"\nReal forecast: {real:.3f} doublings")

    title("STEP 5. HOW THE TREES ADD UP (end points relaxed to 5 examples, so this is a DEMO, not the served model)")
    params = {**LGB_PARAMS, "min_child_samples": 5}
    d = lgb.LGBMRegressor(**params).fit(train[feats], train["target"])
    b = d.booster_
    print("Each new tree is built on what the earlier trees still get wrong. Old trees never change.")
    print("Starting guess (the middle answer) is folded into tree 1's numbers; the 0.03 is already applied.")
    show_trees(b, now, feats)
    print(f"\n{'trees used':>10}{'avg miss on the examples':>28}{'forecast for today':>22}")
    X, y = train[feats], train["target"].to_numpy()
    for k in (1, 5, 10, 25, 50, 100, 150):
        print(f"{k:>10}{np.abs(b.predict(X, num_iteration=k) - y).mean():>28.3f}{b.predict(row, num_iteration=k)[0]:>22.3f}")
    print("\nWhich inputs the trees asked about most:")
    used = pd.Series(b.feature_importance("split"), index=feats).sort_values(ascending=False)
    print("\n".join(f"  {MEANING.get(k, k):<30}{v:>5} questions" for k, v in used.items()))
    return real


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=int, default=3, choices=SPEC.horizons, help="months ahead")
    h = ap.parse_args().h
    s = SPEC.origins(SPEC.load())[-1]
    train = F.labelled(SPEC, s, h)
    latest = F.latest_rows(SPEC, s)
    now = latest[latest["unit"] == "v1.1"].iloc[0]
    print(f"Latest complete month: {s.last}. Forecasting {h} months ahead for suite v1.1.")
    feats = SPEC.features
    show_examples(train, feats, h)
    one_input_line(train)
    r = ridge(train, now, feats, h)
    g = lightgbm(train, now, feats, h)
    title("RESULT")
    hours = 2 ** float(now["lvl"]) / 60
    print(f"Today: {hours:.1f} h")
    for name, v in (("Ridge", r), ("LightGBM", g)):
        print(f"{name:<10} growth {v:+.2f} doublings -> {hours * 2 ** v:.1f} h in {h} months")


if __name__ == "__main__":
    main()
