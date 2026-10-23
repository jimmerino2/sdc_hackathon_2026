from typing import Literal

from pydantic import BaseModel, Field

from app.interests.schemas import SdgFocus
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
    match_percent: int | None = Field(None, ge=0, le=100, description="The role's overall match under this scenario: the same score, with the outlook part taken from this scenario; null on sets saved before scenario scores existed")


class AiExposure(BaseModel):
    """How much AI already touches the job (Anthropic Economic Index), for the demand-vs-AI chart."""

    ai_exposure: float | None = Field(None, description="0-1 percentile of how much AI is used in this job's work")
    automation_share: float | None = Field(None, description="0-1 share of that AI use that automates the work (vs assisting)")


class ContextRole(AiExposure):
    """A non-matched role shown for contrast on the chart (e.g. Bookkeeping Clerks)."""

    onet_code: str
    title: str
    outlook: list[ScenarioOutlook]


class SdgReason(BaseModel):
    """One SDG a role's work serves, with the learner's interests it connects to (none: it comes from the role itself)."""

    sdg: int = Field(ge=1, le=17, description="UN Sustainable Development Goal number")
    name: str = Field(description="The goal's name, e.g. 'Industry, Innovation and Infrastructure'")
    value: float = Field(ge=0, le=1, description="How much of the role's work serves this goal; the role's goals add up to 1")
    interests: list[str] = Field(description="The learner's interests that point at this goal, strongest first; empty if none do")


class MatchParts(BaseModel):
    """The parts of the match that don't depend on the AI scenario, each 0-1 (the score is 10% education, 25% interests, 35% skills, 35% outlook)."""

    education: float = Field(description="The learner's career stage, as 0-1")
    interests: float | None = Field(None, description="How well the learner's interests point at the SDGs the role serves, relative to the best role; null if they picked no interests")
    skills: float = Field(description="Share of the role's key-skill importance the learner covers, at their proficiency")


class JobMatch(AiExposure):
    rank: int = Field(description="1 = best match")
    onet_code: str
    title: str
    icon: str = Field(description="Lucide icon name for the role, e.g. 'code'")
    match_percent: int = Field(ge=0, le=100, description="The role's overall match under the AI-accelerates scenario (see outlook[].match_percent for the others), worked out by formula from education, interests, skills and outlook")
    match_parts: MatchParts | None = Field(None, description="The scenario-independent parts of the match, for showing how it was made up")
    skills_owned: int = Field(description="How many of the role's key skills the candidate already has")
    skills_total: int = Field(description="How many key skills were checked for the role")
    skills_you_have: list[str] = Field(description="Key skills the candidate already has (shown as ticked chips)")
    skills_to_learn: list[str] = Field(description="Key skills the candidate is missing (shown as 'new' chips), most important first")
    description: str = Field(description="One short sentence on why the role fits")
    outlook: list[ScenarioOutlook] = Field(description="The forecast under each AI scenario, for the screen's three tabs")
    sdg_reasons: list[SdgReason] = Field(default_factory=list, description="For each SDG the role serves (up to 3), why it fits the learner's interests; empty if the role has no SDGs on record")


class Engine(BaseModel):
    source: str = Field(description="'formula': the match is arithmetic, no model is involved")
    model: str
    jobs_considered: int = Field(description="Roles scored")
    seconds: float


class RecommendResponse(BaseModel):
    profile_id: str = Field(description="The profile the skills were read from")
    jobs: list[JobMatch]
    context: list[ContextRole] = Field(description="Roles to show for contrast on the demand-vs-AI chart; not matches")
    horizon_months: int
    sdg_focus: list[SdgFocus] = Field(default_factory=list, description="The SDGs the learner's interests point at, biggest first, for the SDG view of the matches; empty if they picked no interests")
    note: str
    engine: Engine
    generated_at: str | None = Field(None, description="When these roles were worked out (UTC, ISO 8601); null on sets saved before this was recorded")
