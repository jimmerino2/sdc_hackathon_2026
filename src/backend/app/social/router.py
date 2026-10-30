from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.social import service
from app.social.schemas import Decision, RequestIn, Social

router = APIRouter(prefix="/social", tags=["social"])


@router.get("", response_model=Social)
def read_social(profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """The leaderboard (the learner and their friends, most pollen first), the friends, the requests waiting for the
    learner and the ones they sent. Needs SUPABASE_SERVICE_KEY."""
    return service.get_social(db, str(profile_id))


@router.post("/requests", response_model=Social, status_code=201)
def send_request(body: RequestIn, db: Client = Depends(get_supabase_admin)):
    """Send a friend request to an email (they need a Jobee account, now or later). If they already asked, this
    accepts theirs. 422 for a bad or own email, 409 if already friends, already asked or the learner has no email."""
    return service.request_friend(db, str(body.profile_id), body.email)


@router.post("/requests/{friendship_id}/accept", response_model=Social)
def accept_request(friendship_id: UUID, body: Decision, db: Client = Depends(get_supabase_admin)):
    """Accept a request addressed to the learner's email."""
    return service.accept(db, str(body.profile_id), str(friendship_id))


@router.delete("/requests/{friendship_id}", response_model=Social)
def remove_request(friendship_id: UUID, profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """Decline a request, cancel one the learner sent, or unfriend: whichever side the learner is on."""
    return service.remove(db, str(profile_id), str(friendship_id))
