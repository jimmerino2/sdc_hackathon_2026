import uuid

from fastapi import HTTPException
from supabase import Client

from app.roadmap import planner
from app.roadmap.schemas import CurrentStep, Node, Roadmap, Section, Unit


def _role(db: Client, onet_code: str) -> dict:
    role = db.table("onet_roles").select("onet_code,title,description").eq("onet_code", onet_code).execute().data
    if not role:
        raise HTTPException(status_code=404, detail=f"unknown onet_code {onet_code!r}")
    return role[0]


# One request: the roadmap row, its role, and every node with the skill it points at (PostgREST embedding).
ROADMAP_SELECT = (
    "roadmap_id,section,unit,status,onet_roles(title,description),"
    "roadmap_detail(skill_id,section,unit,status,completed_at,previous_nodes,previous_nodes_required,"
    "onet_role_skills(skill_name,skill_type,importance,level,source))"
)


def get_roadmap(db: Client, onet_code: str) -> Roadmap:
    rows = db.table("roadmap").select(ROADMAP_SELECT).eq("onet_code", onet_code).limit(1).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail=f"no roadmap for {onet_code!r}; build one with POST /roadmap")
    roadmap = rows[0]
    details = roadmap["roadmap_detail"]

    # Learning order inside a unit: prerequisites first (depth in the dependency graph), then most important.
    prev = {d["skill_id"]: d["previous_nodes"] for d in details}
    depth: dict[str, int] = {}

    def depth_of(skill_id: str) -> int:
        if skill_id not in depth:
            depth[skill_id] = 0  # guards against a cycle in hand-edited data
            depth[skill_id] = 1 + max((depth_of(p) for p in prev.get(skill_id, []) if p in prev), default=-1)
        return depth[skill_id]

    grouped: dict[int, dict[int, list[Node]]] = {}
    for d in details:
        node = Node(
            skill_id=d["skill_id"],
            **d["onet_role_skills"],
            status=d["status"],
            completed_at=d["completed_at"],
            previous_nodes=d["previous_nodes"],
            previous_nodes_required=d["previous_nodes_required"],
        )
        grouped.setdefault(d["section"], {}).setdefault(d["unit"], []).append(node)

    sections = [
        Section(
            section=sec,
            units=[
                Unit(unit=u, nodes=sorted(nodes, key=lambda n: (depth_of(n.skill_id), -(n.importance or 0))))
                for u, nodes in sorted(units.items())
            ],
        )
        for sec, units in sorted(grouped.items())
    ]
    return Roadmap(
        onet_code=onet_code,
        title=roadmap["onet_roles"]["title"],
        description=roadmap["onet_roles"]["description"],
        roadmap_id=roadmap["roadmap_id"],
        status=roadmap["status"],
        current=CurrentStep(section=roadmap["section"], unit=roadmap["unit"]),
        sections=sections,
    )


def create_roadmap(db: Client, onet_code: str, replace: bool) -> Roadmap:
    """Have the model plan a roadmap from the role's skills, store it, and return it."""
    role = _role(db, onet_code)
    if db.table("roadmap").select("roadmap_id").eq("onet_code", onet_code).limit(1).execute().data and not replace:
        raise HTTPException(status_code=409, detail="roadmap already exists; send replace=true to rebuild it")

    skills = db.table("onet_role_skills").select("skill_id,skill_name,skill_type,importance,level").eq("onet_code", onet_code).execute().data
    relevant = planner.candidates(skills)
    if not relevant:
        raise HTTPException(status_code=422, detail=f"no skills above importance {planner.MIN_IMPORTANCE} for {onet_code}")
    plan = planner.build_plan(role["title"], role["description"], relevant)

    # One roadmap row per role; its section/unit are the current step, starting at the first unit.
    roadmap_id = str(uuid.uuid4())
    roadmap = {"roadmap_id": roadmap_id, "onet_code": onet_code, "section": 1, "unit": 1, "status": "available"}
    details = []
    for si, section in enumerate(plan, start=1):
        for ui, nodes in enumerate(section, start=1):
            for n in nodes:
                open_now = si == 1 and ui == 1 and not (n.previous_nodes and n.previous_nodes_required)
                details.append(
                    {
                        "roadmap_id": roadmap_id,
                        "onet_code": onet_code,
                        "skill_id": n.skill_id,
                        "section": si,
                        "unit": ui,
                        "status": "available" if open_now else "locked",
                        "previous_nodes": n.previous_nodes,
                        "previous_nodes_required": n.previous_nodes_required,
                    }
                )

    # No transaction support in the client: if a write fails, remove the partial roadmap.
    db.table("roadmap").delete().eq("onet_code", onet_code).execute()  # details go with it (on delete cascade)
    try:
        db.table("roadmap").insert(roadmap).execute()
        db.table("roadmap_detail").insert(details).execute()
    except Exception as e:
        db.table("roadmap").delete().eq("onet_code", onet_code).execute()
        raise HTTPException(status_code=502, detail=f"could not store roadmap: {e}")
    return get_roadmap(db, onet_code)
