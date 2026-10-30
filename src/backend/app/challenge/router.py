from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.challenge import service
from app.challenge.schemas import Challenge, ChallengeCreate, ChallengeRole, Challenges, ChallengeSubmit, ProfileRef, SubmitResult
from app.deps import get_supabase_admin

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("/challenges", response_model=Challenges)
def list_challenges(profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """Every challenge the profile has (any number per tech role, newest first) and the stingers earned. Needs
    SUPABASE_SERVICE_KEY."""
    return service.list_for_profile(db, str(profile_id))


@router.get("/challenges/roles", response_model=list[ChallengeRole])
def challenge_roles(profile_id: UUID = Query(...), db: Client = Depends(get_supabase_admin)):
    """The tech roles a challenge can be started for: the profile's suggested roles first, then the rest by title,
    each with how many challenges the learner already has for it."""
    return service.roles(db, str(profile_id))


@router.post("/challenges", response_model=Challenge, status_code=201)
def create_challenge(body: ChallengeCreate, db: Client = Depends(get_supabase_admin)):
    """Start a new challenge for a tech role. It is tied to the profile's roadmap for the role if there is one (stage
    1 then draws on its sections 1-2), otherwise built from the role's foundational skills; it is told the learner's
    other challenges for the role so it doesn't repeat one. Takes 20-40 seconds. 422 for a role that isn't a tech
    role, 404 for an unknown profile or role, 502 if the model fails."""
    return service.create(db, str(body.profile_id), body.onet_code)


@router.post("/challenge/{challenge_id}/submit", response_model=SubmitResult)
def submit_challenge(challenge_id: UUID, body: ChallengeSubmit, db: Client = Depends(get_supabase_admin)):
    """Judge a public GitHub repo against the challenge's current stage.

    The repo's tree and its most telling files (README, manifests, then code that shows the stack) are read and the
    AI model scores each rubric criterion 0-100 with the reason and what to improve; the total is the weighted average.
    A total of 85+ passes the stage and awards a stinger; after a stage 1 pass, call /advance for Robbee's rewrite.
    A completed stage 2 can be resubmitted to improve the score; it stays complete and pays no more stingers.
    Open at any time, whatever the roadmap progress. Takes 15-60 seconds. 404 if the challenge isn't on this profile's
    roadmap, 409 if stage 1 is already passed or it is being judged, 422 for a link that isn't a public GitHub repo with code in it.
    """
    return service.submit(db, str(body.profile_id), str(challenge_id), body.repo_url)


@router.post("/challenge/{challenge_id}/advance", response_model=Challenge)
def advance_challenge(challenge_id: UUID, body: ProfileRef, db: Client = Depends(get_supabase_admin)):
    """Robbee rewrites a passed stage 1 into a harder stage 2 from the roadmap's later sections. Takes 20-40 seconds.
    Already at stage 2 returns it unchanged. 409 if stage 1 isn't passed yet or the rewrite is already running, 502 if
    the model fails (try again)."""
    return service.advance(db, str(body.profile_id), str(challenge_id))
