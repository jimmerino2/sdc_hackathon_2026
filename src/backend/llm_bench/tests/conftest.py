"""The benchmark tests need no network, key or spend: OpenRouter is replaced by httpx.MockTransport, and runs are
written to a temporary LLM_BENCH_DIR. Cases are built from the tracked occupational and capability tables.

Run from src/backend:  python -m pytest llm_bench/tests
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/backend


@pytest.fixture
def bench_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_BENCH_DIR", str(tmp_path / "bench"))
    monkeypatch.setenv("OPENROUTER_BENCH_API_KEY", "test-key-not-real")
    monkeypatch.setenv("OPENROUTER_BENCH_MIN_INTERVAL_S", "0")
    from llm_bench import openrouter
    openrouter._cache.clear()
    return tmp_path / "bench"


@pytest.fixture(scope="session")
def skills_built():
    from llm_bench import cases as K
    from occupational import backtest as B
    p, reg = K.skill_panel()
    bt = B.run_backtest(p)
    cs = K.skill_cases(horizons=(3, 12), n_series=12, n_origins=2, seed=7, few_shot_k=3, panel=(p, reg), bt=bt)
    return p, reg, bt, cs


@pytest.fixture(scope="session")
def cap_built():
    from llm_bench import cases as K
    return K.capability_cases(horizons=(3, 6, 12), few_shot_k=3)
