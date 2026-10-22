from typing import Literal

from pydantic import BaseModel, Field

from app.resume.schemas import SkillScore


class RecommendRequest(BaseModel):
    """The candidate's skills, loaded from their profile."""

    top_skills: list[SkillScore] = Field(min_length=1, description="The candidate's strongest skills")
    skills: list[SkillScore] = Field(default_factory=list, description="Every skill found; top_skills are added if missing")


class ScenarioOutlook(BaseModel):
    scenario: Literal["Rapid AI", "Baseline", "Slow"]
    tab: str = Field(description="Label for the screen's tab: 'AI accelerates', 'AI holds steady' or 'AI slows down'")
    change_pct: float = Field(description="Expected change in job postings by `forecast_for`, e.g. 38.0 means +38%")
    range_low_pct: float
    range_high_pct: float
    trend: Literal["growing", "stable", "shrinking"]
    forecast_for: str = Field(description="Month the change is measured at, YYYY-MM")


class AiExposure(BaseModel):
    """How much AI already touches the job (Anthropic Economic Index), for the demand-vs-AI chart."""

    ai_exposure: float | None = Field(None, description="0-1 percentile of how much AI is used in this job's work")
    automation_share: float | None = Field(None, description="0-1 share of that AI use that automates the work (vs assisting)")


class ContextRole(AiExposure):
    """A non-matched role shown for contrast on the chart (e.g. Bookkeeping Clerks)."""

    onet_code: str
    title: str
    outlook: list[ScenarioOutlook]


class JobMatch(AiExposure):
    rank: int = Field(description="1 = best match")
    onet_code: str
    title: str
    icon: str = Field(description="Lucide icon name for the role, e.g. 'code'")
    match_percent: int = Field(ge=0, le=100, description="How well the candidate fits the role today, from the engine's fit estimate")
    skills_owned: int = Field(description="How many of the role's key skills the candidate already has")
    skills_total: int = Field(description="How many key skills were checked for the role")
    skills_you_have: list[str] = Field(description="Key skills the candidate already has (shown as ticked chips)")
    skills_to_learn: list[str] = Field(description="Key skills the candidate is missing (shown as 'new' chips), most important first")
    description: str = Field(description="One short sentence on why the role fits")
    outlook: list[ScenarioOutlook] = Field(description="The forecast under each AI scenario, for the screen's three tabs")


class Engine(BaseModel):
    source: str = Field(description="'openjev' or 'llm'")
    model: str
    jobs_considered: int = Field(description="Roles the engine scored (the best matches on skills out of all roles)")
    seconds: float


class RecommendResponse(BaseModel):
    profile_id: str = Field(description="The profile the skills were read from")
    jobs: list[JobMatch]
    context: list[ContextRole] = Field(description="Roles to show for contrast on the demand-vs-AI chart; not matches")
    horizon_months: int
    note: str
    engine: Engine
    generated_at: str | None = Field(None, description="When these roles were worked out (UTC, ISO 8601); null on sets saved before this was recorded")
