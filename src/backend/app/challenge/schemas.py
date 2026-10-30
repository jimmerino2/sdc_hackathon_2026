from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TechArea(BaseModel):
    area: str = Field(description="What part of the project it covers, e.g. 'Frontend', 'Database'")
    skills: list[str] = Field(description="O*NET skill names from the roadmap, e.g. 'Hypertext markup language HTML'")


class RubricCriterion(BaseModel):
    key: str = Field(description="Matches CriterionResult.key")
    criterion: str
    description: str = Field(description="What earns a high score")
    weight: int = Field(ge=0, le=100, description="Share of the total score; a challenge's weights add up to 100")


class CriterionResult(BaseModel):
    key: str
    score: int = Field(ge=0, le=100)
    why: str = Field(description="Why it got this score, citing the repo")
    improve: str = Field(description="What to do to score higher")


class StageResult(BaseModel):
    """How an earlier stage ended."""

    stage: int
    title: str
    repo_url: str | None = None
    score: float | None = None
    summary: str | None = None
    judged_at: datetime | None = None


class Challenge(BaseModel):
    """A project in two stages for a tech role, optionally tied to the role's roadmap. Stage 1 is built from the
    foundational skills (the roadmap's sections 1-2, or the role's lower-level skills); passing it lets Robbee rewrite
    it into a harder stage 2. The brief and result fields describe the current stage."""

    challenge_id: str
    onet_code: str
    role_title: str
    roadmap_id: str | None = Field(None, description="The roadmap it is tied to, if any")
    stage: Literal[1, 2]
    sections: list[int] = Field(description="The roadmap sections the current stage draws on; empty without a roadmap")
    title: str
    description: str = Field(description="The brief: what to build and how it serves the goal; may hold '- ' bullet lines")
    twist: str | None = Field(None, description="Stage 2: what Robbee changed, one line")
    sdg: int = Field(ge=1, le=17)
    sdg_name: str
    interests: list[str] = Field(description="Names of the learner's interests it is themed on")
    tech_stack: list[TechArea]
    rubric: list[RubricCriterion]
    status: Literal["open", "judging", "passed", "advancing"] = Field(
        description="passed: the current stage scored PASS_SCORE+ (at stage 1 Robbee's rewrite is due); advancing: it is being written"
    )
    pass_score: int = Field(description="The score that passes a stage")
    history: list[StageResult] = Field(default_factory=list, description="Earlier stages, oldest first")
    completed_at: datetime | None = Field(None, description="When stage 2 was passed")
    created_at: datetime
    repo_url: str | None = None
    result: list[CriterionResult] | None = Field(None, description="The latest judgement, one per rubric criterion")
    score: float | None = Field(None, description="Weighted total of the latest judgement, 0-100")
    summary: str | None = None
    files_read: list[str] = Field(default_factory=list, description="The repo files the judge read")
    attempts: int = 0
    judged_at: datetime | None = None


class Challenges(BaseModel):
    challenges: list[Challenge] = Field(description="All the profile's challenges, newest first")
    stingers: int = Field(description="Stingers earned: one per passed stage")
    stingers_available: int = Field(description="Earned stingers not yet spent on Robbee")


class SubmitResult(BaseModel):
    challenge: Challenge
    passed: bool = Field(description="This submission passed the stage")
    stinger_awarded: bool
    stingers: int = Field(description="The learner's stinger total after this submission")
    stingers_available: int = Field(description="Earned stingers not yet spent on Robbee")


class ChallengeRole(BaseModel):
    """A tech role a challenge can be started for."""

    onet_code: str
    title: str
    icon: str | None = None
    suggested: bool = Field(description="One of the roles last suggested to the learner")
    challenges: int = Field(description="How many challenges the learner already has for it")


class ProfileRef(BaseModel):
    profile_id: UUID = Field(description="The profile the challenge belongs to")


class ChallengeCreate(ProfileRef):
    onet_code: str = Field(description="A tech role's O*NET code, e.g. 15-1252.00")


class ChallengeSubmit(BaseModel):
    profile_id: UUID = Field(description="The profile the challenge belongs to")
    repo_url: str = Field(description="A public GitHub repository, e.g. https://github.com/octocat/hello-world")
