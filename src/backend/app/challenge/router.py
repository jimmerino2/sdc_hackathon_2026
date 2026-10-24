from uuid import UUID

from fastapi import APIRouter, Depends
from supabase import Client

from app.challenge import service
from app.challenge.schemas import Challenge, ChallengeSubmit
from app.deps import get_supabase_admin

router = APIRouter(prefix="/roadmap/challenge", tags=["roadmap"])


@router.post("/{challenge_id}/submit", response_model=Challenge)
def submit_challenge(challenge_id: UUID, body: ChallengeSubmit, db: Client = Depends(get_supabase_admin)):
    """Judge a public GitHub repo against a Bonus Quest and return the challenge with its score.

    The repo's tree and its most telling files (README, manifests, then code that shows the challenge's stack) are
    read and the AI model scores each rubric criterion 0-100 with the reason and what to improve; the total is the
    weighted average. Only the latest submission is kept. Takes 15-60 seconds. 404 if the challenge isn't on this
    profile's roadmap, 409 while it is locked or already being judged, 422 for a link that isn't a public GitHub repo
    with code in it. Needs SUPABASE_SERVICE_KEY.
    """
    return service.submit(db, str(body.profile_id), str(challenge_id), body.repo_url)
