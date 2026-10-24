"""Fixtures for the occupational pipeline tests. Every ad here is SYNTHETIC (made up for tests, never real data) and
lives in a temporary OCC_DATA_DIR, so the tests need no network, credentials or built data.

Run from src/backend:  python -m pytest occupational/tests
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/backend

from occupational import store, taxonomy as T  # noqa: E402

REAL_TAXONOMY = store.REPO / "data" / "occupational_forecasting" / "taxonomy"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "occ"
    (d / "taxonomy").mkdir(parents=True)
    for f in ("occupations.json", "geo.json", "curated_skills.csv", "registry_overrides.csv", "skill_signals.json"):
        shutil.copy(REAL_TAXONOMY / f, d / "taxonomy" / f)
    monkeypatch.setenv("OCC_DATA_DIR", str(d))
    T.reset_caches()
    yield d
    T.reset_caches()


def synthetic_hn_ads(months: int = 72, per_month: int = 40, seed: int = 0) -> pd.DataFrame:
    """SYNTHETIC HN-style ads. Python is steady (~50%), Django declines, and a made-up term 'Zorblang' appears in the
    last 9 months and grows: the emerging-skill detector should find it, and nothing should know it in advance."""
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Period("2019-01", freq="M")
    for i in range(months):
        m = start + i
        for j in range(per_month):
            occ = "Senior Software Engineer" if j % 4 else "Data Scientist"
            stack = ["Postgres", "React"]
            if rng.random() < 0.5:
                stack.append("Python")
            if rng.random() < max(0.05, 0.6 - i * 0.008):
                stack.append("Django")
            if i >= months - 9 and rng.random() < 0.08 + 0.04 * (i - (months - 9)):
                stack.append("Zorblang")
            company = f"Company{j:02d}"
            text = (f"{company} | {occ} | San Francisco, CA | Full-time\n"
                    f"We are building tools for teams. Our stack: {', '.join(stack)}, Kubernetes.\n"
                    "You will work closely with product and design. " + "Details about the role. " * 6)
            rows.append({"source": "hn_whoishiring", "source_id": f"{i}-{j}", "thread_id": f"t{i}", "month": str(m),
                         "posted_at": f"{m}-02T10:00:00Z", "retrieved_at": "2026-10-24T00:00:00+00:00",
                         "author": f"user{j}", "employer": company, "title_raw": text.split("\n")[0],
                         "location_raw": text.split("\n")[0], "text": text, "url": f"https://example.invalid/{i}-{j}"})
    return pd.DataFrame(rows)
