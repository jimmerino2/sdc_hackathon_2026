import json
import queue
import threading
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from supabase import Client

from app.deps import get_supabase_admin
from app.roadmap import service
from app.roadmap.schemas import LearnedSkill, Roadmap, RoadmapCreate, RoadmapSummary, SkillSelection, SkillSelectionIn

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

KEEPALIVE_SECONDS = 10


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


@router.post("/skills", response_model=SkillSelection)
def suggest_skills(body: SkillSelectionIn, db: Client = Depends(get_supabase_admin)):
    """Step one of a roadmap: which skills to include, as a plain list. No sections, no order, nothing saved.

    The AI model (AI_MODEL_MODE) picks from the role's O*NET skills, seeing what the learner already knows, and leaves out
    skills they know well. If it can't be used the role's most important skills the learner lacks are returned instead
    (`source` says which). The learner can adjust the list (the What-If simulator shows what it does to their matches), then
    send it back to POST /roadmap as `skills` to have it arranged. 404 if the profile or role doesn't exist.
    """
    return service.suggest_skills(db, str(body.profile_id), body.onet_code)


@router.post("", response_model=Roadmap, status_code=201)
def create_roadmap(body: RoadmapCreate, db: Client = Depends(get_supabase_admin)):
    """Build and store a role's roadmap for a profile.

    If any profile already has a roadmap for the role, its plan (skills, sections, units, prerequisites) is copied
    and the new roadmap starts with nothing completed; this is instant. Otherwise (or with replace=true) the AI
    model (AI_MODEL_MODE) takes the role's skills with importance above 2, keeps the worthwhile ones, groups them
    into sections and units, and sets prerequisites; that takes about 10 seconds. For the tech roles the AI then writes the learner's Bonus
    Quests (one project per two sections, themed on their interests' SDGs), about 10 seconds more. Needs SUPABASE_SERVICE_KEY. Returns 404 if the profile
    does not exist, and 409 if it already has a roadmap for the role unless replace=true. With priority_skills, the sections and units holding those skills come first (needs migration 0023; ignored without it).
    """
    return service.create_roadmap(db, str(body.profile_id), body.onet_code, body.replace, body.priority_skills, skills=body.skills)


@router.post("/stream")
def create_roadmap_stream(body: RoadmapCreate, db: Client = Depends(get_supabase_admin)):
    """Same as POST /roadmap, but answers as server-sent events so a page can show progress during the build.

    Each event is a line `data: {json}` with a `type`: `role` (title, onet_code), `plan` (reused: true when the plan
    was copied instead of asked of the model), `roadmap` (the stored roadmap, before the Bonus Quests are written,
    which is the slow part for tech roles) and finally `result` (the same roadmap with its challenges; same fields as
    the POST /roadmap response) or `failed` (status, message; the codes POST /roadmap would have answered with).
    """
    events: queue.Queue = queue.Queue()
    done = object()

    def work():
        try:
            events.put({"type": "result", **service.create_roadmap(db, str(body.profile_id), body.onet_code, body.replace, body.priority_skills, on_event=events.put, skills=body.skills).model_dump(mode="json")})
        except HTTPException as e:
            events.put({"type": "failed", "status": e.status_code, "message": str(e.detail)})
        except Exception as e:  # keeps the stream from hanging
            events.put({"type": "failed", "status": 500, "message": type(e).__name__})
        events.put(done)

    def stream():
        threading.Thread(target=work, daemon=True).start()
        while True:
            try:
                item = events.get(timeout=KEEPALIVE_SECONDS)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if item is done:
                return
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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


@router.delete("", status_code=204)
def delete_roadmap(
    profile_id: UUID = Query(description="The profile the roadmap belongs to"),
    onet_code: str = Query(description="O*NET code of the role whose roadmap to delete, e.g. 15-2051.00"),
    db: Client = Depends(get_supabase_admin),
):
    """Delete the profile's roadmap for a role, including its nodes and any progress on them. 404 if it has none.

    Other roadmaps on the profile are untouched; the role can be built again afterwards with POST /roadmap.
    """
    service.delete_roadmap(db, str(profile_id), onet_code)
    return Response(status_code=204)
