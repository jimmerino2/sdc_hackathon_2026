"""Bonus Quests on a roadmap (table roadmap_challenge, migration 0016): written when a tech role's roadmap is built,
read with the roadmap, and judged when the learner submits a repo."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from supabase import Client

from app.challenge import generator, judge, repo
from app.challenge.schemas import Challenge
from app.config import get_settings
from app.interests import service as interests_service
from app.interests.sdg import SDG_NAMES
from app.jobs.service import TECH_ROLES
from app.profile import service as profiles
from app.roadmap.schemas import Node, Roadmap

STALE_JUDGING = timedelta(minutes=5)  # a judgement this old was lost (e.g. a restart), so a new submission may start
CHALLENGE_COLUMNS = (
    "challenge_id,roadmap_id,sections,title,description,sdg,interest_ids,tech_stack,rubric,status,repo_url,result,"
    "score,summary,files_read,attempts,judged_at"
)


def section_groups(sections: list[int]) -> list[list[int]]:
    """Sections paired in order (1-2, 3-4, ...); an odd last section joins the final group, so 3 sections make one."""
    ordered = sorted(sections)
    groups = [ordered[i : i + 2] for i in range(0, len(ordered), 2)]
    if len(groups) > 1 and len(groups[-1]) == 1:
        last = groups.pop()
        groups[-1] += last
    return groups


def _goals(db: Client, interests: list, onet_code: str) -> list[tuple[int, float]]:
    """(sdg, share) the learner's interests point at, biggest first; the role's own goals if they picked none."""
    focus = interests_service.sdg_focus(interests)
    if focus:
        return [(f.sdg, f.value) for f in focus]
    rows = db.table("onet_roles").select("sdg").eq("onet_code", onet_code).limit(1).execute().data
    role_goals = sorted((rows[0].get("sdg") or []) if rows else [], key=lambda g: -g["value"])
    return [(g["sdg"], g["value"]) for g in role_goals] or [(9, 1.0)]  # Industry, Innovation and Infrastructure


def generate_for_roadmap(db: Client, profile_id: str, roadmap: Roadmap) -> None:
    """Write and store the roadmap's challenges, if its role is a tech role. Best effort: a failure is logged and the
    roadmap simply has no challenges, since they are optional."""
    if roadmap.onet_code not in TECH_ROLES or not roadmap.roadmap_id or not roadmap.sections:
        return
    try:
        profile = profiles.get_profile(db, profile_id)
        interests = interests_service.by_ids(db, profile.interests)
        by_section: dict[int, list[Node]] = {s.section: [n for u in s.units for n in u.nodes] for s in roadmap.sections}
        groups = section_groups(list(by_section))
        written = generator.write(roadmap.title, roadmap.description, profile.stage, interests, _goals(db, interests, roadmap.onet_code), groups, by_section)
        if written:
            model = get_settings().openrouter_model
            db.table("roadmap_challenge").insert([{**c, "roadmap_id": roadmap.roadmap_id, "model": model} for c in written]).execute()
        if len(written) < len(groups):
            print(f"Only {len(written)} of {len(groups)} challenges written for roadmap {roadmap.roadmap_id}")
    except Exception as e:
        print(f"Challenges not written for roadmap {roadmap.roadmap_id} ({type(e).__name__}: {getattr(e, 'message', e)})")


def _out(row: dict, done_sections: set[int], interest_names: dict[int, str]) -> Challenge:
    return Challenge(
        **{k: row[k] for k in ("challenge_id", "sections", "title", "description", "sdg", "tech_stack", "rubric", "status",
                               "repo_url", "result", "score", "summary", "attempts", "judged_at")},
        after_section=max(row["sections"]),
        sdg_name=SDG_NAMES[row["sdg"]],
        interests=[interest_names[i] for i in row["interest_ids"] if i in interest_names],
        files_read=row["files_read"] or [],
        locked=not set(row["sections"]) <= done_sections,
    )


def _interest_names(db: Client, rows: list[dict]) -> dict[int, str]:
    ids = sorted({i for r in rows for i in r["interest_ids"]})
    try:
        return {i.id: i.interest for i in interests_service.by_ids(db, ids)}
    except interests_service.InterestError:
        return {}


def for_roadmap(db: Client, roadmap: Roadmap) -> list[Challenge]:
    """The roadmap's challenges in section order. A missing table (migration 0016 not applied) or a failed read gives
    none instead of breaking the roadmap."""
    if not roadmap.roadmap_id:
        return []
    try:
        rows = db.table("roadmap_challenge").select(CHALLENGE_COLUMNS).eq("roadmap_id", roadmap.roadmap_id).execute().data
    except Exception as e:
        print(f"roadmap_challenge could not be read ({type(e).__name__}); the roadmap will have no challenges")
        return []
    done = {s.section for s in roadmap.sections if all(n.status == "completed" for u in s.units for n in u.nodes)}
    names = _interest_names(db, rows)
    return sorted((_out(r, done, names) for r in rows), key=lambda c: c.sections)


def _done_sections(db: Client, roadmap_id: str) -> set[int]:
    nodes = db.table("roadmap_detail").select("section,status").eq("roadmap_id", roadmap_id).execute().data
    return {n["section"] for n in nodes} - {n["section"] for n in nodes if n["status"] != "completed"}


def submit(db: Client, profile_id: str, challenge_id: str, repo_url: str) -> Challenge:
    """Judge a repo against the challenge and keep the result (only the latest is kept).

    404 if the challenge isn't on this profile's roadmap, 409 if it is still locked or a submission is already being
    judged, 422 for a link that isn't a readable public GitHub repo, 502/503 if GitHub or the model fail; on a failure
    the previous result stays as it was.
    """
    rows = (db.table("roadmap_challenge").select(f"{CHALLENGE_COLUMNS},roadmap(profile_id)")
            .eq("challenge_id", challenge_id).limit(1).execute().data)
    if not rows or (rows[0]["roadmap"] or {}).get("profile_id") != profile_id:
        raise HTTPException(status_code=404, detail="no such challenge on this profile")
    row = rows[0]
    done = _done_sections(db, row["roadmap_id"])
    if not set(row["sections"]) <= done:
        raise HTTPException(status_code=409, detail="Finish every skill in this challenge’s sections to unlock it.")
    try:
        repo.parse_url(repo_url)
    except repo.RepoError as e:
        raise HTTPException(e.status_code, e.message) from e

    # Claim it: only one judgement at a time, unless the last one was lost.
    now = datetime.now(timezone.utc)
    claimed = (db.table("roadmap_challenge").update({"status": "judging", "submitted_at": now.isoformat()})
               .eq("challenge_id", challenge_id)
               .or_(f"status.neq.judging,submitted_at.lt.{(now - STALE_JUDGING).strftime('%Y-%m-%dT%H:%M:%SZ')}")
               .execute().data)
    if not claimed:
        raise HTTPException(status_code=409, detail="That challenge is already being judged. Give it a minute.")

    def release():
        db.table("roadmap_challenge").update({"status": "judged" if row["result"] else "open"}).eq("challenge_id", challenge_id).execute()

    try:
        snap = repo.fetch(repo_url, [s for a in row["tech_stack"] for s in a["skills"]])
        result, summary, score = judge.judge(row, snap)
    except repo.RepoError as e:
        release()
        raise HTTPException(e.status_code, e.message) from e
    except Exception as e:
        release()
        print(f"Challenge {challenge_id} not judged ({type(e).__name__}: {e})")
        raise HTTPException(status_code=502, detail="Jobee couldn’t judge that just now. Try again in a moment.") from e

    saved = db.table("roadmap_challenge").update({
        "status": "judged",
        "repo_url": snap.url,
        "result": result,
        "score": score,
        "summary": summary,
        "files_read": [p for p, _ in snap.files],
        "attempts": row["attempts"] + 1,
        "judged_at": datetime.now(timezone.utc).isoformat(),
        "model": get_settings().openrouter_model,
    }).eq("challenge_id", challenge_id).execute().data
    return _out(saved[0], done, _interest_names(db, saved))
