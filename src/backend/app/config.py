from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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
    # Model reasoning for writing and judging Bonus Quests (same options as roadmap_reasoning)
    challenge_reasoning: Literal["off", "low", "default"] = "off"
    # The weighted score (0-100) a challenge stage must reach to pass and earn a stinger
    challenge_pass_score: int = Field(85, ge=1, le=100)
    openrouter_model: str = "gemini/gemini-3.1-flash-lite-preview"  # every LLM call (roadmaps, quests, resume skills, chat) uses this
    llm_bench_runs_enabled: bool = False  # starting, stopping or resuming benchmark runs spends money; results stay public
    github_token: str = ""  # optional; reading a submitted repo without it is limited to 60 GitHub API calls an hour
    resume_prefilter: bool = True  # consider only tools named in the resume (plus the general skills); false = all ~260
    resume_thinking: bool = True  # false turns the model's hidden reasoning off: ~5 s instead of ~30 s, same skills on the resumes tried
    forecast_refresh_enabled: bool = False  # lets POST /forecast/refresh clear the forecast caches (a flood of them would force retrains)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
