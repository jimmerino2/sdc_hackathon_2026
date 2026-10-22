from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase, get_supabase_admin
from app.roadmap import service
from app.roadmap.schemas import Roadmap, RoadmapCreate

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("", response_model=Roadmap)
def get_roadmap(
    onet_code: str = Query(..., description="O*NET code, e.g. 15-2051.00"),
    db: Client = Depends(get_supabase),
):
    """A role's roadmap: sections, then units, then skill nodes with status and prerequisites."""
    return service.get_roadmap(db, onet_code)


@router.post("", response_model=Roadmap, status_code=201)
def create_roadmap(body: RoadmapCreate, db: Client = Depends(get_supabase_admin)):
    """Build and store a role's roadmap with the AI model (AI_MODEL_MODE).

    Takes the role's skills with importance above 2, has the model keep the worthwhile ones, group them
    into sections and units, and set prerequisites. Needs SUPABASE_SERVICE_KEY. Returns 409 if the role
    already has a roadmap unless replace=true.
    """
    return service.create_roadmap(db, body.onet_code, body.replace)


@router.post("/complete/{roadmap_detail_id}", response_model=Roadmap)
def complete_node(roadmap_detail_id: UUID, db: Client = Depends(get_supabase_admin)):
    """Mark a node completed (status completed, completed_at now) and return the updated roadmap.

    The roadmap's section/unit then move to the first unit that still has open nodes and its status becomes
    in_progress. When the last node is completed only the status changes, to completed. Calling it again on a
    completed node changes nothing. Needs SUPABASE_SERVICE_KEY.
    """
    return service.complete_node(db, str(roadmap_detail_id))
