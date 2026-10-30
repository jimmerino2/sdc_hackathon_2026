from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.hive import service
from app.hive.schemas import Hive, InviteIn, ProfileRef, StingResult

router = APIRouter(prefix="/hive", tags=["hive"])


@router.get("", response_model=Hive)
def read_hive(profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """The learner's lobby (Robbee's HP, the party), unspent stingers, invites, Recent hits and any kill popup not yet
    dismissed. A solo fight is created on the first call. Needs SUPABASE_SERVICE_KEY."""
    return service.get_hive(db, str(profile_id))


@router.post("/sting", response_model=StingResult)
def sting(body: ProfileRef, db: Client = Depends(get_supabase_admin)):
    """Spend one stinger: Robbee loses 20% HP and the learner gets 500 pollen. The killing blow resets him to 100% and
    pays 1,000 pollen to every party member who stung that round. 409 if the learner has no stinger."""
    return service.sting(db, str(body.profile_id))


@router.post("/invites", response_model=Hive, status_code=201)
def send_invite(body: InviteIn, db: Client = Depends(get_supabase_admin)):
    """Invite a friend to the party. 422 if they aren't a friend, 409 if the party (4 at most) is full, they are in it
    or they are already invited."""
    return service.invite(db, str(body.profile_id), str(body.to_profile_id))


@router.post("/invites/{invite_id}/accept", response_model=Hive)
def accept_invite(invite_id: UUID, body: ProfileRef, db: Client = Depends(get_supabase_admin)):
    """Join the inviting party, replacing the learner's own fight. 404 if the invite isn't valid, 409 if it is full."""
    return service.accept(db, str(body.profile_id), str(invite_id))


@router.delete("/invites/{invite_id}", response_model=Hive)
def remove_invite(invite_id: UUID, profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """Decline an invite, or cancel one the learner's party sent."""
    return service.remove_invite(db, str(profile_id), str(invite_id))


@router.post("/leave", response_model=Hive)
def leave_party(body: ProfileRef, db: Client = Depends(get_supabase_admin)):
    """Leave the party for a fresh solo fight (Robbee at 100%)."""
    return service.leave(db, str(body.profile_id))


@router.post("/rewards/{reward_id}/seen", response_model=Hive)
def dismiss_reward(reward_id: UUID, body: ProfileRef, db: Client = Depends(get_supabase_admin)):
    """Dismiss a kill popup so it doesn't show again."""
    return service.reward_seen(db, str(body.profile_id), str(reward_id))
