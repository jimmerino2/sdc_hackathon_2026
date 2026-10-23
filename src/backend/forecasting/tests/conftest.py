"""Synthetic fixtures (clearly not real data): small vintage tables with known revisions, so leakage can be tested.

Run from src/backend:  python -m pytest forecasting/tests
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/backend, so tests also run from the repo root

GEOS = ["AA", "BB", "CC"]


def make_vintages(months: pd.PeriodIndex, vintages: list[tuple[str, str, int, float]], base: float = 2.0,
                  slope: float = 0.02) -> pd.DataFrame:
    """vintages: (vintage_id, available_at, n_months_published, revision_added). Values rise linearly."""
    rows = []
    for vid, when, n, rev in vintages:
        for gi, g in enumerate(GEOS):
            for i, m in enumerate(months[:n]):
                rows.append({"source_id": "synthetic", "vintage_id": vid, "blob_sha": vid, "available_at": when,
                             "source_file": "x.csv", "schema_version": "s", "geo": g, "month": str(m),
                             "value": base + gi * 0.5 + slope * i + rev, "numerator": np.nan, "denominator": np.nan,
                             "n_days": 28, "is_partial": False})
    df = pd.DataFrame(rows)
    df["available_at"] = pd.to_datetime(df["available_at"], utc=True)
    return df


@pytest.fixture
def months():
    return pd.period_range("2019-01", "2024-12", freq="M")


@pytest.fixture
def ai_v(months):
    # v1 publishes through 2024-03; v2 (two months later) revises all history up by 1 pp and adds two months
    n1 = list(months).index(pd.Period("2024-03", freq="M")) + 1
    return make_vintages(months, [("v1", "2024-04-29", n1, 0.0), ("v2", "2024-06-10", n1 + 2, 1.0)])


@pytest.fixture
def po_v(months):
    n = len(months) - 1
    return make_vintages(months, [("p1", "2021-02-24", 24, 0.0), ("p2", "2024-05-31", n, 0.0)], base=100, slope=0.5)
