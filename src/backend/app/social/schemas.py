from uuid import UUID

from pydantic import BaseModel, Field


class Player(BaseModel):
    """Someone on the leaderboard."""

    profile_id: str
    name: str
    bee: str = Field(description="Their companion bee, which is their picture")
    pollen: int
    rank: int = Field(description="1 = most pollen; ties are ordered by name")
    is_me: bool


class Friend(BaseModel):
    profile_id: str
    name: str
    bee: str
    email_hint: str = Field(description="Their email with the domain hidden, e.g. 'jun@...'")
    friendship_id: str


class Incoming(BaseModel):
    """A request waiting for the learner to accept."""

    friendship_id: str
    name: str
    bee: str
    email: str = Field(description="The requester's email")


class Sent(BaseModel):
    """A request the learner sent that hasn't been accepted."""

    friendship_id: str
    email: str
    signed_up: bool = Field(description="false: nobody has an account with this email yet")


class Social(BaseModel):
    pollen: int = Field(description="The learner's own pollen")
    leaderboard: list[Player] = Field(description="The learner and their friends, most pollen first")
    friends: list[Friend]
    incoming: list[Incoming]
    sent: list[Sent]


class RequestIn(BaseModel):
    profile_id: UUID = Field(description="The learner sending the request")
    email: str = Field(min_length=3, max_length=254, description="The friend's email; they need a Jobee account")


class Decision(BaseModel):
    profile_id: UUID = Field(description="The learner answering")
