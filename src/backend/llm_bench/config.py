"""Benchmark settings: the environment first, then src/backend/.env (gitignored). The API key is never printed, logged
or written to a run folder.

The benchmark has its own OPENROUTER_BENCH_* variables. The gateway follows OPENROUTER_BENCH_BASE_URL: openrouter.ai
needs OPENROUTER_BENCH_API_KEY; Grafilab (https://llm.grafilab.ai/v1) uses OPENROUTER_BENCH_API_KEY if set, else the
app's OPENROUTER_API_KEY, which is a Grafilab key. The app's key is never sent to openrouter.ai.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
REPO = Path(__file__).resolve().parents[3]

DEFAULTS = {
    "OPENROUTER_BENCH_API_KEY": "",
    "OPENROUTER_BENCH_BASE_URL": "https://openrouter.ai/api/v1",
    "OPENROUTER_BENCH_MODEL": "google/gemma-4-31b-it:free",  # free first; any OpenRouter model id works
    "OPENROUTER_BENCH_COMPARE_MODEL": "qwen/qwen3.5-9b",  # inexpensive paid model for the second run
    "OPENROUTER_BENCH_MAX_SPEND_USD": "2.00",
    "OPENROUTER_BENCH_BATCH_SIZE": "10",
    "OPENROUTER_BENCH_MAX_OUTPUT_TOKENS": "2048",
    "OPENROUTER_BENCH_TIMEOUT_S": "120",
    "OPENROUTER_BENCH_MAX_RETRIES": "2",
    "OPENROUTER_BENCH_MIN_INTERVAL_S": "3.5",  # free models allow 20 requests a minute
    "OPENROUTER_BENCH_REASONING": "off",  # off | low | default: reasoning tokens cost money and add nothing parseable
    "OPENROUTER_BENCH_MYR_PER_USD": "4.0",  # Grafilab reports cost in MYR; a low rate over-counts USD (the safe side)
    "OPENROUTER_BENCH_PRICE_MARGIN": "1.5",  # Grafilab: OpenRouter's listed price for the same model x this margin
    "OPENROUTER_API_KEY": "",
}


def _from_env_file(name: str) -> str | None:
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip().removeprefix("export ").strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def env(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name].strip()
    v = _from_env_file(name)
    return v if v else DEFAULTS[name]


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    compare_model: str
    max_spend_usd: float
    batch_size: int
    max_output_tokens: int
    timeout_s: float
    max_retries: int
    min_interval_s: float
    reasoning: str
    myr_per_usd: float
    price_margin: float

    @property
    def gateway(self) -> str:
        return "grafilab" if "grafilab" in self.base_url else "openrouter"

    def public(self) -> dict:
        return {**asdict(self), "gateway": self.gateway}


def settings() -> Settings:
    return Settings(
        base_url=env("OPENROUTER_BENCH_BASE_URL").rstrip("/"), model=env("OPENROUTER_BENCH_MODEL"),
        compare_model=env("OPENROUTER_BENCH_COMPARE_MODEL"),
        max_spend_usd=float(env("OPENROUTER_BENCH_MAX_SPEND_USD")), batch_size=int(env("OPENROUTER_BENCH_BATCH_SIZE")),
        max_output_tokens=int(env("OPENROUTER_BENCH_MAX_OUTPUT_TOKENS")), timeout_s=float(env("OPENROUTER_BENCH_TIMEOUT_S")),
        max_retries=int(env("OPENROUTER_BENCH_MAX_RETRIES")), min_interval_s=float(env("OPENROUTER_BENCH_MIN_INTERVAL_S")),
        reasoning=env("OPENROUTER_BENCH_REASONING"), myr_per_usd=float(env("OPENROUTER_BENCH_MYR_PER_USD")),
        price_margin=float(env("OPENROUTER_BENCH_PRICE_MARGIN")))


def api_key() -> str:
    own = env("OPENROUTER_BENCH_API_KEY")
    if own or "grafilab" not in env("OPENROUTER_BENCH_BASE_URL"):
        return own
    return env("OPENROUTER_API_KEY")


def data_dir() -> Path:
    return Path(os.environ.get("LLM_BENCH_DIR") or REPO / "data" / "llm_bench")
