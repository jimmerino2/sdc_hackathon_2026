from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Member(BaseModel):
    profile_id: str
    name: str
    bee: str = Field(description="Their companion bee")
    stings: int = Field(description="Stingers they have spent this round")
    is_me: bool


class Fight(BaseModel):
    """The learner's lobby: Robbee's HP and how many rounds the party has won."""

    fight_id: str
    hp: int = Field(description="Robbee's HP, 100 down to 0; a kill resets it to 100")
    kills: int = Field(description="Rounds this party has won")
    stings_dealt: int = Field(description="Stings landed this round")
    stings_to_kill: int = Field(description="Stings it takes to kill him from full HP")
    max_party: int


class Invite(BaseModel):
    """An invite to someone else's party."""

    invite_id: str
    from_name: str
    from_bee: str
    party_size: int
    hp: int = Field(description="The inviting party's Robbee HP")


class Outgoing(BaseModel):
    """An invite out from the learner's own party, not answered yet."""

    invite_id: str
    profile_id: str
    name: str
    bee: str


class Invitable(BaseModel):
    profile_id: str
    name: str
    bee: str


class Event(BaseModel):
    event_id: str
    kind: Literal["sting", "twist", "defeat", "join", "leave"]
    profile_id: str
    name: str
    is_me: bool
    challenge_title: str | None = None
    pollen: int = Field(description="Pollen it paid the actor; show it for the learner's own events")
    created_at: datetime


class PartyBee(BaseModel):
    name: str
    bee: str


class Reward(BaseModel):
    """A kill the learner hasn't dismissed: the popup shows once."""

    reward_id: str
    pollen: int = Field(description="Kill pollen paid to the learner; 0 if they were in the party but didn't sting")
    round: int
    party: list[PartyBee] = Field(description="The party at the kill, one entry per member (1 to 4)")


class Hive(BaseModel):
    fight: Fight
    members: list[Member] = Field(description="The party, oldest member first")
    stingers_available: int = Field(description="Unspent stingers")
    pollen: int = Field(description="The learner's pollen")
    invites: list[Invite] = Field(description="Parties that invited the learner")
    outgoing: list[Outgoing]
    invitable: list[Invitable] = Field(description="Friends who aren't in the party and haven't been invited")
    events: list[Event] = Field(description="Recent hits, newest first")
    reward: Reward | None = Field(None, description="The oldest kill popup not yet dismissed")


class StingResult(BaseModel):
    hive: Hive
    defeated: bool = Field(description="This sting was the killing blow")
    pollen: int = Field(description="Pollen this sting paid")
    kill_pollen: int = Field(description="Pollen the kill paid the learner, if it was the killing blow")


class ProfileRef(BaseModel):
    profile_id: UUID = Field(description="The learner")


class InviteIn(ProfileRef):
    to_profile_id: UUID = Field(description="A friend to invite to the party")
