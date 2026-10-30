from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.resume.schemas import SkillScore


class ExperienceEntry(BaseModel):
    """One job, internship or project."""

    title: str = Field(description="Role or project name")
    organisation: str | None = Field(None, description="Company or school")
    start: str | None = Field(None, description="Start, e.g. 2024-06")
    end: str | None = Field(None, description="End, e.g. 2025-01; null if ongoing")
    summary: str | None = Field(None, description="What they did")


class ProfileIn(BaseModel):
    """Everything the caller sets. The id is generated."""

    email: str | None = Field(None, min_length=3, description="Optional email address; if given, one profile per email")
    name: str = Field(min_length=1, description="Full name")
    stage: Literal["under", "fresh", "working"] = Field(
        description="under = undergraduate, fresh = fresh graduate, working = working (beginner)"
    )
    interests: list[int] = Field(default_factory=list, description="Ids of the interests they picked (GET /interests), at most 3; they steer the job matches towards the SDGs those interests serve")
    skills: list[SkillScore] = Field(description="O*NET skill names, each with how strong it is (0-1)")
    experience: list[ExperienceEntry] = Field(description="Work / project experience")


class ProfileUpdate(BaseModel):
    """Fields to change; anything left out stays as it is. The email is changed through /profile/sync instead."""

    name: str | None = Field(None, min_length=1, description="Full name")
    stage: Literal["under", "fresh", "working"] | None = Field(
        None, description="under = undergraduate, fresh = fresh graduate, working = working (beginner)"
    )
    interests: list[int] | None = Field(None, description="Ids of the interests they picked (GET /interests), at most 3; replaces the current picks")
    skills: list[SkillScore] | None = Field(None, description="O*NET skill names, each with how strong it is (0-1)")
    experience: list[ExperienceEntry] | None = Field(None, description="Work / project experience")


Bee = Literal["Libbee", "Phoebee", "Tobee", "Barnabee"]
class ProfileOut(ProfileIn):
    bee: Bee = Field("Libbee", description="The learner's companion bee")
    total_pollen: int = Field(0, description="Pollen earned from stingers and boss kills; ranks the leaderboard")
    profile_id: UUID


class SyncIn(BaseModel):
    """Step 1 of binding an email to a profile: ask for a one-time code to be emailed."""

    profile_id: UUID = Field(description="The profile_id returned from POST /profile")
    email: str = Field(min_length=3, description="The email to bind; a code is sent to it")


class SyncVerifyIn(SyncIn):
    """Step 2: the code from the email."""

    token: str = Field(min_length=1, description="The one-time code from the email")


class LoginIn(BaseModel):
    """Step 1 of logging in: the email on an existing profile."""

    email: str = Field(min_length=3, description="The email the profile was synced with; a code is sent to it")


class LoginVerifyIn(LoginIn):
    """Step 2: the code from the email."""

    token: str = Field(min_length=1, description="The one-time code from the email")


class SyncOut(BaseModel):
    message: str
