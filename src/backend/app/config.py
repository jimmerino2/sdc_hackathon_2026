from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env", extra="ignore")

    supabase_url: str = ""
    supabase_key: str = ""  # publishable key
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.7-flash"
    openjev_url: str = ""
    openjev_token: str = ""
    resume_prefilter: bool = True  # both engines: consider only tools named in the resume (plus the general skills); false = all ~260
    openjev_threshold: float = 0.5  # a skill counts as present at or above this probability
    resume_model: str = ""  # model for resume skill extraction; empty = use openrouter_model
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
