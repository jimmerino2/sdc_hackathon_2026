from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.deps import bearer, get_current_user
from app.auth.schemas import UserOut
from app.jobs import service
from app.jobs.schemas import RecommendRequest, RecommendResponse
from app.resume import storage
from app.resume.schemas import SkillScore

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/recommend", response_model=RecommendResponse)
def recommend(
    source: Literal["auto", "openjev", "llm", "openai", "grafilab"] = Query(
        "auto",
        description="auto = OpenJev, falling back to the gateway LLM (Grafilab) if OPENJEV_URL is unset or OpenJev fails; openjev or llm = only that one, no fallback ('openai' and 'grafilab' mean the gateway LLM)",
    ),
    horizon: Literal[3, 6, 9, 12] = Query(12, description="Months ahead for the posting change"),
    resume_id: str | None = Query(None, description="Which saved resume to use; default is the newest one"),
    user: UserOut = Depends(get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    """The 3 roles that fit the logged-in user best, each with a match %, a short reason, skills overlap and the forecast under each AI scenario.

    Nothing to send: the user comes from the bearer token, and their skills are read from their saved resume.
    """
    try:
        saved = storage.load_skills(creds.credentials, resume_id)
    except storage.SaveError as e:
        raise HTTPException(502, str(e))
    if saved is None:
        raise HTTPException(404, "No saved resume found. Upload one with POST /resume first.")
    if not saved["top_skills"]:
        raise HTTPException(409, "That resume has no skills (the skills step did not run). Upload it again.")
    req = RecommendRequest(
        top_skills=[SkillScore(**s) for s in saved["top_skills"]],
        skills=[SkillScore(**s) for s in saved["skills"] or []],
    )
    engine = "llm" if source in ("openai", "grafilab") else source
    try:
        return service.recommend(req, saved["resume_id"], engine, horizon)
    except service.RecommendError as e:
        raise HTTPException(502, str(e))
