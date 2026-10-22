from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.deps import bearer, get_current_user
from app.auth.schemas import UserOut
from app.resume import service, storage
from app.resume.schemas import ResumeOut

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("", response_model=ResumeOut)
def upload_resume(
    file: UploadFile = File(description="The resume as a PDF (max 10 MB)"),
    source: Literal["auto", "openjev", "llm", "openai", "grafilab"] = Query(
        "auto",
        description="Which engine reads the skills. auto = OpenJev with fallback to the gateway LLM; openjev or llm = only that one, no fallback ('openai' and 'grafilab' mean the gateway LLM)",
    ),
    user: UserOut = Depends(get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    """Upload a resume PDF (login required). Saves the file and the skills to Supabase; returns the skills found with a score each, and the top 5."""
    data = file.file.read(service.MAX_BYTES + 1)  # one byte over the limit is enough to reject it
    try:
        result = service.extract_pdf_text(data)
    except service.ResumeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    engine = "llm" if source in ("openai", "grafilab") else source
    skills = service.extract_skills(result["text"], engine)
    try:
        resume_id = storage.save_resume(creds.credentials, user.id, data, file.filename, result, skills)
    except storage.SaveError as e:
        raise HTTPException(502, str(e))
    return ResumeOut(
        resume_id=resume_id,
        filename=file.filename,
        page_count=result["page_count"],
        char_count=result["char_count"],
        top_skills=skills["top_skills"],
        skills=skills["skills"],
        error=skills["error"],
        engine=skills["engine"],
    )
