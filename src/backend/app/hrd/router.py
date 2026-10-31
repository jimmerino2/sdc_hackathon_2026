from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase
from app.hrd import service
from app.hrd.schemas import Programme

router = APIRouter(prefix="/hrd", tags=["hrd"])


@router.get("/programmes", response_model=list[Programme])
def list_programmes(
    skill: str = Query(description="An O*NET skill name, e.g. 'Critical Thinking' (as in onet_role_skills.skill_name)"),
    limit: int = Query(5, ge=1, le=20, description="How many courses to return"),
    db: Client = Depends(get_supabase),
):
    """HRD Corp-claimable courses that teach the skill, best first: ones a person can enrol in before in-house workshops, then cheaper first.

    The fees come from HRD Corp's public BizMatch course list on the day in `fetched`. The employer claims the cost from
    HRD Corp, not the learner. An empty list if there is none, or if the table hasn't been loaded.
    """
    return service.programmes_for(db, skill, limit)
