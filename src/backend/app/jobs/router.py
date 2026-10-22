from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.jobs import service
from app.jobs.schemas import RecommendRequest, RecommendResponse
from app.profile import service as profiles
from app.resume.vocab import TOP_N

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/recommend", response_model=RecommendResponse)
def recommend(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    source: Literal["auto", "openjev", "llm", "openai", "grafilab"] = Query(
        "auto",
        description="auto = OpenJev, falling back to the gateway LLM (Grafilab) if OPENJEV_URL is unset or OpenJev fails; openjev or llm = only that one, no fallback ('openai' and 'grafilab' mean the gateway LLM)",
    ),
    horizon: Literal[3, 6, 9, 12] = Query(12, description="Months ahead for the posting change"),
    db: Client = Depends(get_supabase_admin),
):
    """The tech roles that fit the profile best (up to 10; 8 tech roles are matched for now), each with an icon, a match %, a short reason, skills overlap and the forecast under each AI scenario.

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
    engine = "llm" if source in ("openai", "grafilab") else source
    try:
        result = service.recommend(req, str(profile_id), engine, horizon)
    except service.RecommendError as e:
        raise HTTPException(502, str(e))
    try:  # keep it so GET /jobs/suggested can show it again; failing to save must not lose the result
        profiles.save_suggestions(db, profile_id, result.model_dump(mode="json"))
    except profiles.ProfileError as e:
        print(f"Suggestions not saved: {e.message}")
    return result


@router.get("/suggested", response_model=RecommendResponse)
def suggested(profile_id: UUID = Query(description="The profile_id returned from POST /profile"), db: Client = Depends(get_supabase_admin)):
    """The roles last suggested to this profile by GET /jobs/recommend, as they were then (nothing is recomputed). 404 if the profile does not exist or has no suggestions yet."""
    try:
        saved = profiles.get_suggestions(db, profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    if not saved:
        raise HTTPException(404, "No roles have been suggested for this profile yet.")
    return RecommendResponse(**saved)
