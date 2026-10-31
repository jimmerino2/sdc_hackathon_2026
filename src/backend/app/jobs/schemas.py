from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.interests.schemas import SdgFocus
from app.resume.schemas import SkillScore


class RecommendRequest(BaseModel):
    """The candidate's skills, loaded from their profile."""

    top_skills: list[SkillScore] = Field(min_length=1, description="The candidate's strongest skills")
    skills: list[SkillScore] = Field(default_factory=list, description="Every skill found; top_skills are added if missing")


class ScoreComponent(BaseModel):
    """One part of the match: its score, the weight it is given and what it adds to the raw score."""

    key: Literal["skills", "outlook", "interests", "education"]
    score: float = Field(description="This part's score, 0-1")
    weight: float = Field(description="Configured weight; the weights add up to 1.05, so use `share` when showing one")
    share: float = Field(description="The share of the score this part really carries; the shares add up to 1")
    points: float = Field(description="score x share: what this part adds to raw_score")


class MatchBreakdown(BaseModel):
    """How a match was made up (scoring.breakdown), the one calculation behind the cards, role page and simulator."""

    components: list[ScoreComponent]
    raw_score: float = Field(description="The components' points added up, 0-1, before the curve")
    curve: float = Field(description="The shown match is raw_score ** curve; it lifts every score and keeps their order")
    match_percent: int = Field(ge=0, le=100, description="The match shown: raw_score ** curve, as a whole percent")


class ScenarioOutlook(BaseModel):
    scenario: Literal["Rapid AI", "Baseline", "Slow"]
    tab: str = Field(description="Label for the screen's tab: 'AI accelerates', 'AI holds steady' or 'AI slows down'")
    change_pct: float = Field(description="Expected change in job postings by `forecast_for`, e.g. 38.0 means +38%")
    range_low_pct: float
    range_high_pct: float
    trend: Literal["growing", "stable", "shrinking"]
    forecast_for: str = Field(description="Month the change is measured at, YYYY-MM")
    match_percent: int | None = Field(None, ge=0, le=100, description="The role's overall match under this scenario: the same score, with the outlook part taken from this scenario; null on sets saved before scenario scores existed")
    rank: int | None = Field(None, description="The role's place among the matches under this scenario, 1 = best; ties keep the order of the headline ranking")
    breakdown: MatchBreakdown | None = Field(None, description="How match_percent was made up; null on a saved set that can't be reconciled with today's formula")


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


class InterestReason(BaseModel):
    """Why a role fits one of the learner's interests, through one SDG they share. Written by the LLM once, then kept."""

    sdg: int = Field(ge=1, le=17, description="The goal the interest and the role share")
    interest_id: int
    interest: str = Field(description="The interest's name, e.g. 'Sports & Fitness'")
    reason: str = Field(description="One short sentence linking the interest, the goal and the role's work")


class MatchParts(BaseModel):
    """The parts of the match that don't depend on the AI scenario, each 0-1 (the score is 10% education, 25% interests, 35% skills, 35% outlook)."""

    education: float = Field(description="The learner's career stage, as 0-1")
    interests: float | None = Field(None, description="How well the learner's interests point at the SDGs the role serves, relative to the best role; null if they picked no interests")
    skills: float = Field(description="Share of the role's key-skill importance the learner covers, at their proficiency")


class SkillFit(BaseModel):
    """One of a role's key skills and how it counted towards the skills part of the match."""

    name: str
    importance_share: float = Field(description="This skill's share of the role's key-skill importance, 0-1 (importance counts double for a trending skill)")
    trending: bool = Field(False, description="Its demand is forecast to rise on the Occupations page, so it counts double in the skills part of the match")
    proficiency: float = Field(description="What it counted at: 0 missing, 0.33 Basic, 0.67 Good, 1 Strong")
    via: str | None = Field(None, description="The learner's skill it was counted through (e.g. Python for Programming); null if they hold it directly or lack it")


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
    skill_fit: list[SkillFit] = Field(default_factory=list, description="Each key skill and how it counted; empty on sets saved before this existed")


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
    stage: str | None = Field(None, description="The career stage behind the education part; null on sets saved before this was recorded")


class SimulatedSkill(SkillScore):
    """A skill the learner wants to try out, at the score of the proficiency they imagine."""


class SimulateRequest(BaseModel):
    profile_id: UUID = Field(description="The profile_id returned from POST /profile")
    skills: list[SimulatedSkill] = Field(default_factory=list, max_length=20, description="Skills to try, by O*NET name; empty gives the baseline and the skill options")
    horizon: Literal[3, 6, 9, 12] = 12
    focus_role: str | None = Field(None, description="O*NET code of the role the skill options are for; leave out for the best match under AI accelerates")


class SkillChange(BaseModel):
    name: str
    before: float = Field(description="Proficiency it counted at before, 0 = missing")
    after: float = Field(description="Proficiency it counts at now")
    via: str | None = Field(None, description="The simulated skill it is counted through, if not the skill itself")


class ScenarioComparison(BaseModel):
    """One role under one AI future, current profile against simulated profile."""

    scenario: Literal["Rapid AI", "Baseline", "Slow"]
    tab: str
    current_percent: int
    simulated_percent: int
    change: int = Field(description="simulated_percent - current_percent")
    current_rank: int
    simulated_rank: int
    current: MatchBreakdown | None = None
    simulated: MatchBreakdown | None = None
    outlook: ScenarioOutlook | None = Field(None, description="The forecast under this scenario; its breakdown is the simulated one")
    explanation: str = Field(description="Why the match moved, built from the difference between the two breakdowns")


class RoleComparison(BaseModel):
    onet_code: str
    title: str
    icon: str
    skills_owned_before: int
    skills_owned_after: int
    skills_total: int
    skills_gained: list[SkillChange] = Field(description="Key skills that count for more than before")
    skills_replaced: list[str] = Field(description="Key skills O*NET rates the same as a simulated one, which it took the place of")
    skills_remaining: list[str] = Field(description="Key skills still missing on the simulated profile")
    skill_fit: list[SkillFit] = Field(default_factory=list, description="How each key skill counts on the simulated profile")
    sdg_reasons: list[SdgReason] = Field(default_factory=list, description="The SDGs the role serves, as on the role cards")
    scenarios: list[ScenarioComparison]


class ScenarioSummary(BaseModel):
    """The headline comparison under one AI future."""

    scenario: Literal["Rapid AI", "Baseline", "Slow"]
    tab: str
    current_top: str
    simulated_top: str
    current_top_percent: int
    simulated_top_percent: int


class SkillGain(BaseModel):
    """What adding a skill alone would do under one AI future, worked out with the matching engine."""

    scenario: Literal["Rapid AI", "Baseline", "Slow"]
    average_change: float = Field(description="Average change in match points across all the roles")
    best_change: int = Field(description="The biggest change for one role")
    best_role: str = Field(description="The role with that change")


class SkillDemand(BaseModel):
    """What the occupational pipeline says about the skill. Share of sampled Hacker News job ads; never Malaysian vacancies."""

    occupation: str
    direction: Literal["rising", "falling", "flat"]
    last_share: float | None
    forecast: float
    target_month: str
    evidence: Literal["high", "medium", "low"]


class SkillOption(BaseModel):
    name: str
    current: float = Field(description="The learner's proficiency in it now, 0 = don't have it")
    trial: float = Field(description="The proficiency the gains are worked out at")
    roles_listing: int = Field(description="How many of the matched roles list the skill in O*NET")
    gap_roles: list[str] = Field(description="Roles where it is a key skill the learner is missing")
    gains: list[SkillGain]
    demand: SkillDemand | None = Field(None, description="Null when the skill isn't tracked for an occupation with forecasts")
    rising: bool = Field(False, description="Its demand is forecast to rise for this role on the Occupations page, so it is listed first; if it is one of the role's key skills it counts double in the match")
    emerging: bool = Field(False, description="The job-ad pipeline saw a rise that clears its evidence minimum (an observed rise, not a forecast)")


class SimulateResponse(BaseModel):
    profile_id: str
    horizon_months: int
    coverage_before: float = Field(description="Share of all the roles' key skills the learner has now")
    coverage_after: float = Field(description="The same share on the simulated profile")
    summary: list[ScenarioSummary]
    roles: list[RoleComparison] = Field(description="Every matched role, best simulated match first under AI accelerates")
    focus_role: str = Field(description="O*NET code of the role the options are for")
    options: list[SkillOption] = Field(description="The skills O*NET links to the focus role, each measured on its own against the current profile for that role, best first; only sent when no skills are being tried")
