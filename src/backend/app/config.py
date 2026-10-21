from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env", extra="ignore")

    supabase_url: str = ""
    supabase_key: str = ""  # publishable key
    supabase_service_key: str = ""  # service-role key, only for endpoints that write
    ai_model_mode: Literal["OPENROUTER"] = "OPENROUTER"  # what builds roadmaps (POST /roadmap)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://llm.grafilab.ai/v1"
    # Model reasoning for roadmap generation: "off" ~12s, "low" ~60s with better ordering, "default" ~2min
    roadmap_reasoning: Literal["off", "low", "default"] = "off"
    openrouter_model: str = "grafilab/deepseek-v4-flash"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
