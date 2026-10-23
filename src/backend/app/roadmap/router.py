from uuid import UUID

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_supabase_admin
from app.roadmap import service
from app.roadmap.schemas import LearnedSkill, Roadmap, RoadmapCreate, RoadmapSummary

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("/summary", response_model=list[RoadmapSummary])
def roadmap_summary(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    db: Client = Depends(get_supabase_admin),
):
    """Every roadmap the profile has, newest first, with its status and progress (completed of total nodes). An empty list if it has none."""
    return service.list_roadmaps(db, str(profile_id))


@router.get("/learned", response_model=list[LearnedSkill])
def learned_skills(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    db: Client = Depends(get_supabase_admin),
):
    """The skills the profile has completed on its roadmaps, each once, ordered by skill group then name. An empty list if it has completed none."""
    return service.learned_skills(db, str(profile_id))


@router.get("", response_model=Roadmap)
def get_roadmap(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    onet_code: str | None = Query(None, description="O*NET code, e.g. 15-2051.00. Leave out for the profile's most recently built roadmap"),
    db: Client = Depends(get_supabase_admin),
):
    """A profile's roadmap: sections, then units, then skill nodes with status and prerequisites.

    With onet_code it is that role's roadmap; without it, the most recently built one (what a returning user
    resumes). 404 if there is none.
    """
    return service.get_roadmap(db, str(profile_id), onet_code)


@router.post("", response_model=Roadmap, status_code=201)
def create_roadmap(body: RoadmapCreate, db: Client = Depends(get_supabase_admin)):
    """Build and store a role's roadmap for a profile.

    If any profile already has a roadmap for the role, its plan (skills, sections, units, prerequisites) is copied
    and the new roadmap starts with nothing completed; this is instant. Otherwise (or with replace=true) the AI
    model (AI_MODEL_MODE) takes the role's skills with importance above 2, keeps the worthwhile ones, groups them
    into sections and units, and sets prerequisites; that takes about 10 seconds. Needs SUPABASE_SERVICE_KEY. Returns 404 if the profile
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
