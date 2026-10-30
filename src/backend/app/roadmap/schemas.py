from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.challenge.schemas import Challenge


class Source(BaseModel):
    """One place to learn a skill (a row of skill_sources)."""

    source_type: Literal["project", "certificate", "video", "activity"] = Field(
        description="project = build something, certificate = a credential or course, video = watch, activity = practise"
    )
    rank: int = Field(description="1 = first pick")
    title: str
    url: str


class Node(BaseModel):
    roadmap_detail_id: str = Field(description="Id of this node, used by POST /roadmap/complete/{roadmap_detail_id}")
    skill_id: str
    skill_name: str
    skill_type: Literal["skill", "knowledge", "tech"]
    importance: float | None = Field(None, description="1-5")
    level: float | None = Field(None, description="0-7, null for tech (software)")
    skill_group: str | None = Field(None, description="The area this skill belongs to, e.g. 'Web Development'; null until migration 0012 is applied")
    source: str | None = Field(None, description="URL of the learning material")
    sources: list[Source] = Field(default_factory=list, description="Where to learn it, best first; empty if none are known")
    status: Literal["locked", "available", "completed"]
    completed_at: datetime | None = None
    previous_nodes: list[str] = Field(description="skill_ids that come before this node")
    previous_nodes_required: bool = Field(description="true: previous nodes must be completed first")


class Unit(BaseModel):
    unit: int
    nodes: list[Node]


class Section(BaseModel):
    section: int
    title: str | None = Field(None, description="What this section covers, e.g. 'Web Fundamentals'; null for a roadmap built before this was tracked")
    units: list[Unit]


class CurrentStep(BaseModel):
    section: int
    unit: int


class Roadmap(BaseModel):
    profile_id: str = Field(description="The profile this roadmap and its progress belong to")
    onet_code: str
    title: str
    description: str | None = None
    roadmap_id: str | None = Field(None, description="null until a roadmap has been built for this role")
    status: Literal["locked", "available", "in_progress", "completed"] | None = None
    current: CurrentStep | None = Field(None, description="The step the learner is on")
    sections: list[Section]
    challenges: list[Challenge] = Field(
        default_factory=list, description="The challenges tied to this roadmap, oldest first; tech roles only, empty for the others"
    )


class RoadmapCreate(BaseModel):
    profile_id: UUID = Field(description="The profile_id returned from POST /profile")
    onet_code: str = Field(description="O*NET code, e.g. 15-2051.00")
    replace: bool = Field(False, description="Rebuild if a roadmap already exists (discards its progress)")
    priority_skills: list[str] = Field(default_factory=list, max_length=30, description="Skill names to bring forward, e.g. from the What-If simulator; the plan's skills don't change, only the order of its sections and units")


class RoadmapSummary(BaseModel):
    """One of a profile's roadmaps in brief: which role, how far along."""

    onet_code: str
    title: str
    status: Literal["locked", "available", "in_progress", "completed"]
    total: int = Field(description="Skill nodes in the roadmap")
    completed: int = Field(description="Skill nodes finished so far")


class LearnedSkill(BaseModel):
    """A skill the learner has completed on a roadmap."""

    skill_name: str
    skill_type: Literal["skill", "knowledge", "tech"]
    skill_group: str | None = Field(None, description="The area it belongs to, e.g. 'Web Development'")
    completed_at: datetime = Field(description="When it was completed; the latest if it was completed on more than one roadmap")
