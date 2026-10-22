from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Node(BaseModel):
    roadmap_detail_id: str = Field(description="Id of this node, used by POST /roadmap/complete/{roadmap_detail_id}")
    skill_id: str
    skill_name: str
    skill_type: Literal["skill", "knowledge", "tech"]
    importance: float | None = Field(None, description="1-5")
    level: float | None = Field(None, description="0-7, null for tech (software)")
    source: str | None = Field(None, description="URL of the learning material")
    status: Literal["locked", "available", "completed"]
    completed_at: datetime | None = None
    previous_nodes: list[str] = Field(description="skill_ids that come before this node")
    previous_nodes_required: bool = Field(description="true: previous nodes must be completed first")


class Unit(BaseModel):
    unit: int
    nodes: list[Node]


class Section(BaseModel):
    section: int
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


class RoadmapCreate(BaseModel):
    profile_id: UUID = Field(description="The profile_id returned from POST /profile")
    onet_code: str = Field(description="O*NET code, e.g. 15-2051.00")
    replace: bool = Field(False, description="Rebuild if a roadmap already exists (discards its progress)")
