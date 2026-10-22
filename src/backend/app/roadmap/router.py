from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.roadmap import service
from app.roadmap.schemas import Roadmap, RoadmapCreate

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("", response_model=Roadmap)
def get_roadmap(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    onet_code: str = Query(..., description="O*NET code, e.g. 15-2051.00"),
    db: Client = Depends(get_supabase_admin),
):
    """This profile's roadmap for a role: sections, then units, then skill nodes with status and prerequisites. 404 if none yet."""
    return service.get_roadmap(db, str(profile_id), onet_code)


@router.post("", response_model=Roadmap, status_code=201)
def create_roadmap(body: RoadmapCreate, db: Client = Depends(get_supabase_admin)):
    """Build and store a role's roadmap for a profile with the AI model (AI_MODEL_MODE).

    Takes the role's skills with importance above 2, has the model keep the worthwhile ones, group them
    into sections and units, and set prerequisites. Needs SUPABASE_SERVICE_KEY. Returns 404 if the profile
    does not exist, and 409 if it already has a roadmap for the role unless replace=true.
    """
    return service.create_roadmap(db, str(body.profile_id), body.onet_code, body.replace)


@router.post("/complete/{roadmap_detail_id}", response_model=Roadmap)
def complete_node(
    roadmap_detail_id: UUID,
    profile_id: UUID = Query(description="The profile the roadmap belongs to"),
    db: Client = Depends(get_supabase_admin),
):
    """Mark a node completed (status completed, completed_at now) and return the updated roadmap.

    The roadmap's section/unit then move to the first unit that still has open nodes, its status becomes
    in_progress, and nodes up to that unit whose required prerequisites are done become available. When the last
    node is completed only the status changes, to completed. Calling it again on a completed node changes nothing;
    a locked node is refused with 409. 404 if the node is not on this profile's roadmap. Needs SUPABASE_SERVICE_KEY.
    """
    return service.complete_node(db, str(profile_id), str(roadmap_detail_id))
