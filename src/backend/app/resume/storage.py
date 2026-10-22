import uuid

from supabase import ClientOptions, create_client

from app.config import get_settings

BUCKET = "resumes"


class SaveError(Exception):
    """The resume could not be saved to Supabase."""


def _client(access_token: str):
    """A client acting as the logged-in user, so the row-level security policies apply to every call."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
    )


def save_resume(access_token: str, user_id: str, data: bytes, filename: str, parsed: dict, skills: dict) -> str:
    """Store the PDF in the private bucket and write one resume row with its skills as arrays. Returns the resume id.

    The file goes up first; if a database write then fails, the file is removed so nothing is left orphaned.
    """
    db = _client(access_token)
    resume_id = str(uuid.uuid4())
    path = f"{user_id}/{resume_id}.pdf"
    try:
        db.storage.from_(BUCKET).upload(path, data, {"content-type": "application/pdf"})
    except Exception as e:
        raise SaveError(f"The file could not be stored: {getattr(e, 'message', type(e).__name__)}") from e

    engine = skills["engine"]
    top = skills["top_skills"] or []
    try:
        db.table("resumes").insert({
            "resume_id": resume_id,
            "user_id": user_id,
            "filename": filename,
            "storage_path": path,
            "page_count": parsed["page_count"],
            "char_count": parsed["char_count"],
            "skills": skills["skills"] or [],
            "top_skills": top,
            "engine": engine["source"],
            "model": engine["model"],
            "candidates": engine["candidates"],
            "seconds": engine["seconds"],
            "error": skills["error"],
        }).execute()
    except Exception as e:
        try:
            db.table("resumes").delete().eq("resume_id", resume_id).execute()
            db.storage.from_(BUCKET).remove([path])
        except Exception:
            pass
        raise SaveError(f"The resume could not be saved: {getattr(e, 'message', type(e).__name__)}") from e
    return resume_id


def load_skills(access_token: str, resume_id: str | None = None) -> dict | None:
    """The user's saved skills: their newest resume, or the one with this id. None if there is no such resume.

    Reads as the logged-in user, so row-level security guarantees it is theirs. Returns
    {"resume_id", "filename", "skills", "top_skills"}.
    """
    query = _client(access_token).table("resumes").select("resume_id, filename, skills, top_skills")
    if resume_id:
        query = query.eq("resume_id", resume_id)
    try:
        rows = query.order("created_at", desc=True).limit(1).execute().data
    except Exception as e:
        raise SaveError(f"The resume could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    return rows[0] if rows else None
