from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.deps import get_supabase_admin
from app.interests import service
from app.interests.schemas import Interest

router = APIRouter(prefix="/interests", tags=["interests"])


@router.get("", response_model=list[Interest])
def list_interests(db: Client = Depends(get_supabase_admin)):
    """The interests a learner can pick during onboarding, each with its icon and the SDGs it serves (sdg: [{sdg, value}], values adding up to 1)."""
    try:
        return service.list_interests(db)
    except service.InterestError as e:
        raise HTTPException(502, str(e))
