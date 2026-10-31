"""Retrain the forecast model on the quarters the learner keeps, in memory.

The model and the job forecast are the ones ml/train_lgbm.py builds (same code); only the data changes: the excluded
quarters are left out, and so is every sample that touches one of their months (see train_lgbm.run_horizon). Nothing is
written to ml/output. A retrain takes 2-3 seconds, so results are kept by the set of excluded quarters and at most
MAX_PARALLEL run at once.
"""
import re
import sys
import threading
import time
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.forecast import signals

ML_DIR = Path(__file__).resolve().parents[2] / "ml"
PROCESSED_DIR = signals.PROCESSED_DIR
MAX_PARALLEL = 2
MAX_CACHED = 32
OUTCOME_MONTHS = 3  # the shortest horizon: a month's outcome is known this many months later


class RetrainError(ValueError):
    """The chosen quarter can't be used; the message can be shown to the learner."""


@dataclass
class Retrained:
    jobs: pd.DataFrame
    sector_index: pd.DataFrame  # rows = month, columns = sector; only the months that were kept
    excluded: list[str]  # the quarters left out, oldest first
    forecast_from: str
    trained_rows: int  # rows the 12-month model learned from
    holdout_origins: list[str]
    model_status: str
    source: str
    seconds: float


_cache: dict[frozenset[str], Retrained] = {}
_locks: dict[frozenset[str], threading.Lock] = {}
_guard = threading.Lock()
_slots = threading.Semaphore(MAX_PARALLEL)


def _ml():
    """ml/train_lgbm.py is a script folder, not a package."""
    if str(ML_DIR) not in sys.path:
        sys.path.insert(0, str(ML_DIR))
    import train_lgbm

    return train_lgbm


def quarter_months(quarter: str) -> list[str]:
    """'2026-Q2' -> ['2026-04', '2026-05', '2026-06']."""
    m = re.fullmatch(r"(\d{4})-Q([1-4])", quarter or "")
    if not m:
        raise RetrainError(f"{quarter!r} isn't a quarter like 2026-Q2.")
    first = (int(m.group(2)) - 1) * 3 + 1
    return [f"{m.group(1)}-{first + i:02d}" for i in range(3)]


def _add_months(month: str, n: int) -> str:
    return str(pd.Period(month, freq="M") + n)


def sector_months_set(df: pd.DataFrame) -> set[str]:
    return set(signals.sector_months(df)["month"])


def quarters(df: pd.DataFrame) -> list[dict]:
    """The quarters the data covers, oldest first: months present and whether their outcome is known yet."""
    months = sorted(sector_months_set(df))
    latest = months[-1]
    out = []
    for q in dict.fromkeys(signals.year_quarter(m) for m in months):
        in_q = [m for m in months if signals.year_quarter(m) == q]
        out.append({
            "quarter": q,
            "months": len(in_q),
            "first_month": in_q[0],
            "last_month": in_q[-1],
            "has_outcome": _add_months(in_q[0], OUTCOME_MONTHS) <= latest,
        })
    return out


def _train(excluded: frozenset[str]) -> Retrained:
    df, source = signals.load_signals()
    have = {q["quarter"] for q in quarters(df)}
    unknown = sorted(excluded - have)
    if unknown:
        raise RetrainError(f"No data for {', '.join(unknown)}.")
    months = frozenset(m for q in excluded for m in quarter_months(q))
    t0 = time.perf_counter()
    ml = _ml()
    try:
        trained = ml.train_all(Namespace(holdout=12, trees=300, post_only=False), PROCESSED_DIR, signals=df.reset_index(drop=True),
                               verbose=False, exclude_months=months)
    except (ValueError, KeyError, AssertionError, IndexError) as e:
        raise RetrainError("Too little data is left to train on. Keep more quarters.") from e
    kept = signals.sector_months(df)
    wide = kept[~kept["month"].isin(months)].pivot(index="month", columns="sector", values="value").sort_index()
    h12 = trained["by_horizon"]["12"]
    return Retrained(
        jobs=trained["jobs"], sector_index=wide, excluded=sorted(excluded), forecast_from=str(trained["jobs"]["forecast_from"].iloc[0]),
        trained_rows=h12["train_rows"], holdout_origins=h12["holdout"]["origins"], model_status=h12["model_status"],
        source=source, seconds=round(time.perf_counter() - t0, 2),
    )


def retrain(excluded: list[str] | frozenset[str]) -> tuple[Retrained, bool]:
    """The model retrained without the excluded quarters (e.g. ['2020-Q1', '2026-Q3']; empty = all the data), and whether it was already done.

    Raises RetrainError for a quarter that isn't valid or when too little data is left.
    """
    key = frozenset(excluded)
    for q in key:
        quarter_months(q)  # validates the format before any work
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:  # two people choosing the same quarters train once
        if key in _cache:
            return _cache[key], True
        with _slots:
            result = _train(key)
        with _guard:
            if len(_cache) >= MAX_CACHED:
                _cache.pop(next(iter(_cache)))
            _cache[key] = result
        return result, False


def cached_default() -> Retrained | None:
    return _cache.get(frozenset())


def clear() -> None:
    """Forget every retrain and the data they used."""
    with _guard:
        _cache.clear()
    signals.clear()
