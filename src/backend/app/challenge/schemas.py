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


class Challenge(BaseModel):
    """A Bonus Quest: an optional project built from the skills of a couple of roadmap sections."""

    challenge_id: str
    sections: list[int] = Field(description="The sections it covers")
    after_section: int = Field(description="Shown after this section (the last one it covers)")
    title: str
    description: str = Field(description="The brief: what to build and how it serves the goal; may hold '- ' bullet lines")
    sdg: int = Field(ge=1, le=17)
    sdg_name: str
    interests: list[str] = Field(description="Names of the learner's interests it is themed on")
    tech_stack: list[TechArea]
    rubric: list[RubricCriterion]
    locked: bool = Field(description="true until every skill in its sections is completed")
    status: Literal["open", "judging", "judged"]
    repo_url: str | None = None
    result: list[CriterionResult] | None = Field(None, description="The latest judgement, one per rubric criterion")
    score: float | None = Field(None, description="Weighted total of the latest judgement, 0-100")
    summary: str | None = None
    files_read: list[str] = Field(default_factory=list, description="The repo files the judge read")
    attempts: int = 0
    judged_at: datetime | None = None


class ChallengeSubmit(BaseModel):
    profile_id: UUID = Field(description="The profile the roadmap belongs to")
    repo_url: str = Field(description="A public GitHub repository, e.g. https://github.com/octocat/hello-world")
