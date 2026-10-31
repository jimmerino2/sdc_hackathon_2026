from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.interests import service as interests_service
from app.jobs import reasons, service, simulator
from app.jobs.schemas import InterestReason, RecommendRequest, RecommendResponse, SimulateRequest, SimulateResponse
from app.profile import service as profiles
from app.resume.vocab import TOP_N

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/recommend", response_model=RecommendResponse)
def recommend(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    source: Literal["auto", "llm", "openai", "grafilab"] = Query(
        "auto", description="Ignored: roles are scored by formula now, with no model involved. Kept so older callers still work."
    ),
    horizon: Literal[3, 6, 9, 12] = Query(12, description="Months ahead for the posting change"),
    db: Client = Depends(get_supabase_admin),
):
    """The tech roles that fit the profile best (up to 10; 8 tech roles are matched for now), each with an icon, a match % (by formula from the learner's skills, interests, career stage and the role's outlook), skills overlap, the SDGs it serves and the forecast and match under each AI scenario.

    No login needed: the skills are read from the profile (POST /profile). 404 if there is no such profile; 409 if it has no skills.
    """
    try:
        profile = profiles.get_profile(db, profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    skills = sorted((s for s in profile.skills if s.score > 0), key=lambda s: -s.score)
    if not skills:
        raise HTTPException(409, "That profile has no skills yet. Add some with PATCH /profile/{profile_id}.")
    req = RecommendRequest(top_skills=skills[:TOP_N], skills=skills)
    try:  # interests only steer the ranking, so failing to read them must not stop the matching
        picked = interests_service.by_ids(db, profile.interests)
    except interests_service.InterestError as e:
        print(f"Interests not used: {e}")
        picked = []
    result = service.recommend(req, str(profile_id), profile.stage, horizon, picked)
    try:  # keep it so GET /jobs/suggested can show it again; failing to save must not lose the result
        profiles.save_suggestions(db, profile_id, result.model_dump(mode="json"))
    except profiles.ProfileError as e:
        print(f"Suggestions not saved: {e.message}")
    return result


@router.get("/reasons", response_model=list[InterestReason])
def interest_reasons(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    onet_code: str = Query(description="The role, e.g. 15-2051.00"),
    db: Client = Depends(get_supabase_admin),
):
    """Why the role fits each of the learner's interests: one short sentence per SDG the role and an interest share. Written by the LLM the first time, then kept (role_interest_reasons), so call it only when the role's details are opened. Empty if no interest points at the role's goals; a sentence the LLM failed to write is left out. 404 if there is no such profile or role."""
    try:
        return reasons.interest_reasons(db, profile_id, onet_code)
    except reasons.ReasonError as e:
        raise HTTPException(e.status_code, e.message)


@router.get("/suggested", response_model=RecommendResponse)
def suggested(profile_id: UUID = Query(description="The profile_id returned from POST /profile"), db: Client = Depends(get_supabase_admin)):
    """The roles last suggested to this profile by GET /jobs/recommend, as they were then (nothing is recomputed). 404 if the profile does not exist or has no suggestions yet."""
    try:
        saved = profiles.get_suggestions(db, profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    if not saved:
        raise HTTPException(404, "No roles have been suggested for this profile yet.")
    return service.with_breakdowns(RecommendResponse(**saved))


@router.post("/simulate", response_model=SimulateResponse)
def simulate(body: SimulateRequest, db: Client = Depends(get_supabase_admin)):
    """What if the learner had these skills? Runs the same matching as GET /jobs/recommend on the profile as it is and on a copy with the skills added, and returns both under every AI scenario, why each role moved, and which skills would help most. Nothing is saved: the profile and its suggested roles are left alone. 404 if there is no such profile; 409 if it has no skills; 422 if a skill isn't one the roles use or the focus role isn't a matched role. Without skills it also lists the skills O*NET links to the focus role (default: the best match) as options."""
    try:
        profile = profiles.get_profile(db, body.profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    skills = [s for s in profile.skills if s.score > 0]
    if not skills:
        raise HTTPException(409, "That profile has no skills yet. Add some with PATCH /profile/{profile_id}.")
    try:
        picked = interests_service.by_ids(db, profile.interests)
    except interests_service.InterestError as e:
        print(f"Interests not used: {e}")
        picked = []
    try:
        return simulator.simulate(str(body.profile_id), skills, profile.stage, picked, body.skills, body.horizon, body.focus_role)
    except simulator.UnknownSkill as e:
        raise HTTPException(422, f"Not a skill the roles use: {e}")
    except simulator.UnknownRole as e:
        raise HTTPException(422, f"Not one of the matched roles: {e}")
