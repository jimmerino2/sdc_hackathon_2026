import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from supabase import Client

from app.profile import service as profiles
from app.roadmap import planner
from app.roadmap.schemas import CurrentStep, LearnedSkill, Node, Roadmap, RoadmapSummary, Section, Source, Unit


def _role(db: Client, onet_code: str) -> dict:
    role = db.table("onet_roles").select("onet_code,title,description").eq("onet_code", onet_code).execute().data
    if not role:
        raise HTTPException(status_code=404, detail=f"unknown onet_code {onet_code!r}")
    return role[0]


# One request: the roadmap row, its role, and every node with the skill it points at (PostgREST embedding).
# onet_role_skills.source is not read: it needs migration 0002 and learning links now come from skill_sources.
ROADMAP_SELECT = (
    "roadmap_id,onet_code,section,unit,status,onet_roles(title,description),"
    "roadmap_detail(roadmap_detail_id,skill_id,section,unit,status,completed_at,previous_nodes,previous_nodes_required,"
    "onet_role_skills(skill_name,skill_type,importance,level))"
)


def _sources(db: Client, skill_names: list[str]) -> dict[str, list[Source]]:
    """Learning sources for these skills (table skill_sources, matched on skill_name), best first.

    A missing table or a failed read gives no sources instead of breaking the roadmap.
    """
    if not skill_names:
        return {}
    try:
        rows = (db.table("skill_sources").select("skill_name,source_type,rank,title,url")
                .in_("skill_name", sorted(set(skill_names))).order("rank").execute().data)
    except Exception as e:
        print(f"skill_sources could not be read ({type(e).__name__}); nodes will have no sources")
        return {}
    found: dict[str, list[Source]] = {}
    for r in rows:
        found.setdefault(r["skill_name"], []).append(Source(**{k: r[k] for k in ("source_type", "rank", "title", "url")}))
    return found


def _groups(db: Client, skill_names: list[str]) -> dict[str, str]:
    """The skill_group of each of these skills (onet_role_skills.skill_group, migration 0012).

    A column that is not there yet, or a failed read, gives no groups instead of breaking the roadmap.
    """
    if not skill_names:
        return {}
    try:
        rows = (db.table("onet_role_skills").select("skill_name,skill_group")
                .in_("skill_name", sorted(set(skill_names))).execute().data)
    except Exception as e:
        print(f"skill_group could not be read ({type(e).__name__}); nodes will have no group")
        return {}
    return {r["skill_name"]: r["skill_group"] for r in rows if r.get("skill_group")}


def learned_skills(db: Client, profile_id: str) -> list[LearnedSkill]:
    """The skills this profile has completed across all its roadmaps, once each, grouped by skill_group then name."""
    ids = [r["roadmap_id"] for r in db.table("roadmap").select("roadmap_id").eq("profile_id", profile_id).execute().data]
    if not ids:
        return []
    rows = (db.table("roadmap_detail").select("completed_at,onet_role_skills(skill_name,skill_type)")
            .in_("roadmap_id", ids).eq("status", "completed").execute().data)
    latest: dict[str, dict] = {}
    for r in rows:  # the same skill can be done on two roadmaps; keep the later one
        name = r["onet_role_skills"]["skill_name"]
        if name not in latest or r["completed_at"] > latest[name]["completed_at"]:
            latest[name] = {**r["onet_role_skills"], "completed_at": r["completed_at"]}
    groups = _groups(db, list(latest))
    out = [LearnedSkill(skill_group=groups.get(n), **v) for n, v in latest.items()]
    return sorted(out, key=lambda s: (s.skill_group is None, s.skill_group or "", s.skill_name))


def list_roadmaps(db: Client, profile_id: str) -> list[RoadmapSummary]:
    """Every roadmap this profile has, newest first, each with its status and how many nodes are done."""
    rows = (
        db.table("roadmap")
        .select("onet_code,status,created_at,onet_roles(title),roadmap_detail(status)")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return [
        RoadmapSummary(
            onet_code=r["onet_code"],
            title=r["onet_roles"]["title"],
            status=r["status"],
            total=len(r["roadmap_detail"]),
            completed=sum(1 for d in r["roadmap_detail"] if d["status"] == "completed"),
        )
        for r in rows
    ]


def get_roadmap(db: Client, profile_id: str, onet_code: str | None = None) -> Roadmap:
    """The profile's roadmap for a role, or its most recently built one when no role is given."""
    query = db.table("roadmap").select(ROADMAP_SELECT).eq("profile_id", profile_id)
    if onet_code:
        query = query.eq("onet_code", onet_code)
    rows = query.order("created_at", desc=True).limit(1).execute().data
    if not rows:
        what = f"for {onet_code!r} " if onet_code else ""
        raise HTTPException(status_code=404, detail=f"no roadmap {what}on this profile; build one with POST /roadmap")
    roadmap = rows[0]
    onet_code = roadmap["onet_code"]
    details = roadmap["roadmap_detail"]

    # Learning order inside a unit: prerequisites first (depth in the dependency graph), then most important.
    prev = {d["skill_id"]: d["previous_nodes"] for d in details}
    depth: dict[str, int] = {}

    def depth_of(skill_id: str) -> int:
        if skill_id not in depth:
            depth[skill_id] = 0  # guards against a cycle in hand-edited data
            depth[skill_id] = 1 + max((depth_of(p) for p in prev.get(skill_id, []) if p in prev), default=-1)
        return depth[skill_id]

    names = [d["onet_role_skills"]["skill_name"] for d in details]
    sources = _sources(db, names)
    groups = _groups(db, names)
    grouped: dict[int, dict[int, list[Node]]] = {}
    for d in details:
        node = Node(
            roadmap_detail_id=d["roadmap_detail_id"],
            skill_id=d["skill_id"],
            **d["onet_role_skills"],
            skill_group=groups.get(d["onet_role_skills"]["skill_name"]),
            sources=sources.get(d["onet_role_skills"]["skill_name"], []),
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
        profile_id=profile_id,
        onet_code=onet_code,
        title=roadmap["onet_roles"]["title"],
        description=roadmap["onet_roles"]["description"],
        roadmap_id=roadmap["roadmap_id"],
        status=roadmap["status"],
        current=CurrentStep(section=roadmap["section"], unit=roadmap["unit"]),
        sections=sections,
    )


def complete_node(db: Client, profile_id: str, roadmap_detail_id: str) -> Roadmap:
    """Mark one node completed, move the roadmap's current step to the first unit that still has open nodes,
    and unlock the nodes that are now reachable.

    When every node is completed the section/unit stay where they are and only the status becomes completed.
    """
    found = (
        db.table("roadmap_detail")
        .select("roadmap_id,onet_code,skill_id,status,roadmap(profile_id)")
        .eq("roadmap_detail_id", roadmap_detail_id)
        .limit(1)
        .execute()
        .data
    )
    if not found or (found[0]["roadmap"] or {}).get("profile_id") != profile_id:
        raise HTTPException(status_code=404, detail=f"no roadmap node {roadmap_detail_id!r} on this profile")
    node = found[0]
    if node["status"] == "locked":
        raise HTTPException(status_code=409, detail="that node is still locked; finish the ones before it first")
    if node["status"] != "completed":
        db.table("roadmap_detail").update(
            {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("roadmap_detail_id", roadmap_detail_id).execute()

    nodes = (db.table("roadmap_detail").select("skill_id,section,unit,status,previous_nodes,previous_nodes_required")
             .eq("roadmap_id", node["roadmap_id"]).execute().data)
    open_nodes = [(n["section"], n["unit"]) for n in nodes if n["status"] != "completed"]
    if open_nodes:
        section, unit = min(open_nodes)
        update = {"section": section, "unit": unit, "status": "in_progress"}
        # Unlock nodes up to the current unit whose required prerequisites are all completed.
        done = {n["skill_id"] for n in nodes if n["status"] == "completed"}
        unlock = [
            n["skill_id"] for n in nodes
            if n["status"] == "locked" and (n["section"], n["unit"]) <= (section, unit)
            and (not n["previous_nodes_required"] or set(n["previous_nodes"]) <= done)
        ]
        if unlock:
            (db.table("roadmap_detail").update({"status": "available"})
             .eq("roadmap_id", node["roadmap_id"]).in_("skill_id", unlock).execute())
    else:
        update = {"status": "completed"}
    db.table("roadmap").update(update).eq("roadmap_id", node["roadmap_id"]).execute()
    return get_roadmap(db, profile_id, node["onet_code"])


def create_roadmap(db: Client, profile_id: str, onet_code: str, replace: bool) -> Roadmap:
    """Have the model plan a roadmap from the role's skills, store it for this profile, and return it."""
    try:
        profiles.get_profile(db, profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message) from e
    role = _role(db, onet_code)

    def mine(query):
        """Limit a query to this profile's roadmap for the role."""
        return query.eq("profile_id", profile_id).eq("onet_code", onet_code)

    if mine(db.table("roadmap").select("roadmap_id")).limit(1).execute().data and not replace:
        raise HTTPException(status_code=409, detail="this profile already has a roadmap for that role; send replace=true to rebuild it")

    skills = db.table("onet_role_skills").select("skill_id,skill_name,skill_type,importance,level").eq("onet_code", onet_code).execute().data
    relevant = planner.candidates(skills)
    if not relevant:
        raise HTTPException(status_code=422, detail=f"no skills above importance {planner.MIN_IMPORTANCE} for {onet_code}")
    plan = planner.build_plan(role["title"], role["description"], relevant)

    # One roadmap row per role; its section/unit are the current step, starting at the first unit.
    roadmap_id = str(uuid.uuid4())
    roadmap = {"roadmap_id": roadmap_id, "profile_id": profile_id, "onet_code": onet_code, "section": 1, "unit": 1,
               "status": "available"}
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
    mine(db.table("roadmap").delete()).execute()  # details go with it (on delete cascade)
    try:
        db.table("roadmap").insert(roadmap).execute()
        db.table("roadmap_detail").insert(details).execute()
    except Exception as e:
        mine(db.table("roadmap").delete()).execute()
        raise HTTPException(status_code=502, detail=f"could not store roadmap: {e}")
    return get_roadmap(db, profile_id, onet_code)
