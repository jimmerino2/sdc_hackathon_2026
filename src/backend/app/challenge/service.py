"""Challenges (table roadmap_challenge, migration 0020) and the stingers they pay (stinger_award). A challenge belongs
to a profile and a tech role, any number per role, and optionally to that role's roadmap. One is written when a tech
role's roadmap is built; more are started from the Challenges page. Each is judged when the learner submits a repo
and rewritten by Robbee into a harder stage 2 once stage 1 is passed."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from supabase import Client

from app.challenge import generator, judge, repo
from app.challenge.generator import Skill
from app.challenge.schemas import Challenge, ChallengeRole, Challenges, SubmitResult
from app.config import get_settings
from app.interests import service as interests_service
from app.interests.sdg import SDG_NAMES
from app.jobs.service import TECH_ROLES
from app.profile import service as profiles
from app.roadmap import planner
from app.roadmap.schemas import Roadmap
from app.hive import service as hive

STALE_BUSY = timedelta(minutes=5)  # a judgement or rewrite this old was lost (e.g. a restart), so it may start again
CHALLENGE_COLUMNS = (
    "challenge_id,profile_id,onet_code,roadmap_id,stage,sections,title,description,twist,sdg,interest_ids,tech_stack,"
    "rubric,status,repo_url,result,score,summary,files_read,attempts,history,judged_at,completed_at,created_at,"
    "onet_roles(title)"
)


def _goals(db: Client, interests: list, onet_code: str) -> list[tuple[int, float]]:
    """(sdg, share) the learner's interests point at, biggest first; the role's own goals if they picked none."""
    focus = interests_service.sdg_focus(interests)
    if focus:
        return [(f.sdg, f.value) for f in focus]
    rows = db.table("onet_roles").select("sdg").eq("onet_code", onet_code).limit(1).execute().data
    role_goals = sorted((rows[0].get("sdg") or []) if rows else [], key=lambda g: -g["value"])
    return [(g["sdg"], g["value"]) for g in role_goals] or [(9, 1.0)]  # Industry, Innovation and Infrastructure


# ---------- the skills a challenge draws on: its roadmap's sections when linked, else the role's own skills ----------

def _roadmap_stages(roadmap: Roadmap) -> tuple[list[Skill], list[int], list[Skill], list[int]]:
    """(stage 1 skills, their sections, stage 2's new skills, their sections) from a roadmap: sections 1-2, then the rest."""
    by_section = {
        s.section: [Skill(n.skill_id, n.skill_name, n.skill_type, n.skill_group, n.importance, n.level) for u in s.units for n in u.nodes]
        for s in roadmap.sections
    }
    first, later = generator.stage_sections(list(by_section))
    return [n for s in first for n in by_section[s]], first, [n for s in later for n in by_section[s]], later


def _role_stages(db: Client, onet_code: str) -> tuple[list[Skill], list[int], list[Skill], list[int]]:
    """The same from the role's onet_role_skills, split by level (no sections)."""
    rows = (db.table("onet_role_skills").select("skill_id,skill_name,skill_type,importance,level,skill_group")
            .eq("onet_code", onet_code).execute().data)
    skills = [Skill(r["skill_id"], r["skill_name"], r["skill_type"], r.get("skill_group"), r["importance"], r["level"])
              for r in planner.candidates(rows)]
    first, new = generator.role_split(skills)
    return first, [], new, []


def _stages(db: Client, profile_id: str, onet_code: str, roadmap_id: str | None):
    """The challenge's skills, from its roadmap if it is linked to one that still exists, else from the role."""
    from app.roadmap import service as roadmaps  # roadmap.service imports this module

    if roadmap_id:
        try:
            roadmap = roadmaps.get_roadmap(db, profile_id, onet_code)
            if roadmap.roadmap_id == roadmap_id and roadmap.sections:
                return _roadmap_stages(roadmap)
        except HTTPException:
            pass
    return _role_stages(db, onet_code)


# ---------- writing a challenge ----------

def _write(db: Client, profile_id: str, onet_code: str, roadmap: Roadmap | None) -> dict | None:
    """Write a stage 1 for this role (on the roadmap's first sections if given) and store it; None if the model
    failed. It is told the titles of the learner's other challenges for the role, so it doesn't repeat one."""
    role = db.table("onet_roles").select("title,description").eq("onet_code", onet_code).limit(1).execute().data
    if not role:
        raise HTTPException(status_code=404, detail=f"no role {onet_code!r}")
    profile = profiles.get_profile(db, profile_id)
    interests = interests_service.by_ids(db, profile.interests)
    skills, sections, _, _ = _roadmap_stages(roadmap) if roadmap else _role_stages(db, onet_code)
    if not skills:
        return None
    mine = db.table("roadmap_challenge").select("title,history").eq("profile_id", profile_id).eq("onet_code", onet_code).execute().data
    avoid = list(dict.fromkeys(t for r in mine for t in [r["title"], *(h["title"] for h in r["history"] or [])]))
    written = generator.write_stage1(role[0]["title"], role[0]["description"], profile.stage, interests,
                                     _goals(db, interests, onet_code), skills, avoid)
    if not written:
        return None
    row = {**written, "profile_id": profile_id, "onet_code": onet_code, "sections": sections,
           "roadmap_id": roadmap.roadmap_id if roadmap else None, "model": get_settings().openrouter_model}
    return db.table("roadmap_challenge").insert(row).execute().data[0]


def generate_for_roadmap(db: Client, profile_id: str, roadmap: Roadmap) -> None:
    """Write the challenge that comes with a tech role's roadmap. Best effort: a failure is logged and the roadmap
    simply has no challenge (more can be started from the Challenges page)."""
    if roadmap.onet_code not in TECH_ROLES or not roadmap.roadmap_id or not roadmap.sections:
        return
    try:
        if not _write(db, profile_id, roadmap.onet_code, roadmap):
            print(f"No challenge written for roadmap {roadmap.roadmap_id}")
    except Exception as e:
        print(f"Challenge not written for roadmap {roadmap.roadmap_id} ({type(e).__name__}: {getattr(e, 'message', e)})")


def create(db: Client, profile_id: str, onet_code: str) -> Challenge:
    """Start a new challenge for a tech role, linked to the profile's roadmap for it if there is one. Takes 20-40
    seconds. 422 for a role that isn't a tech role, 404 for an unknown profile, 502 if the model fails."""
    from app.roadmap import service as roadmaps

    if onet_code not in TECH_ROLES:
        raise HTTPException(status_code=422, detail="Challenges are for tech roles only.")
    try:
        profiles.get_profile(db, profile_id)
    except profiles.ProfileError as e:
        raise HTTPException(e.status_code, e.message) from e
    try:
        roadmap = roadmaps.get_roadmap(db, profile_id, onet_code)
        roadmap = roadmap if roadmap.roadmap_id and roadmap.sections else None
    except HTTPException:
        roadmap = None
    try:
        row = _write(db, profile_id, onet_code, roadmap)
    except HTTPException:
        raise  # an unknown role
    except Exception as e:  # the model or the database
        print(f"Challenge not written for {onet_code} ({type(e).__name__}: {getattr(e, 'message', e)})")
        row = None
    if not row:
        raise HTTPException(status_code=502, detail="Jobee couldn’t write a challenge just now. Try again in a moment.")
    return _row_out(db, _owned(db, profile_id, row["challenge_id"]))


# ---------- reading ----------

def _out(row: dict, interest_names: dict[int, str]) -> Challenge:
    return Challenge(
        **{k: row[k] for k in ("challenge_id", "onet_code", "roadmap_id", "stage", "sections", "title", "description",
                               "twist", "sdg", "tech_stack", "rubric", "status", "repo_url", "result", "score", "summary",
                               "attempts", "judged_at", "completed_at", "created_at")},
        role_title=(row.get("onet_roles") or {}).get("title") or row["onet_code"],
        sdg_name=SDG_NAMES[row["sdg"]],
        interests=[interest_names[i] for i in row["interest_ids"] if i in interest_names],
        files_read=row["files_read"] or [],
        history=row["history"] or [],
        pass_score=judge.pass_score(),
    )


def _interest_names(db: Client, rows: list[dict]) -> dict[int, str]:
    ids = sorted({i for r in rows for i in r["interest_ids"]})
    try:
        return {i.id: i.interest for i in interests_service.by_ids(db, ids)}
    except interests_service.InterestError:
        return {}


def _row_out(db: Client, row: dict) -> Challenge:
    return _out(row, _interest_names(db, [row]))


def for_roadmap(db: Client, roadmap: Roadmap) -> list[Challenge]:
    """The challenges linked to the roadmap, oldest first. A missing table (migration 0020 not applied) or a failed
    read gives none instead of breaking the roadmap."""
    if not roadmap.roadmap_id:
        return []
    try:
        rows = (db.table("roadmap_challenge").select(CHALLENGE_COLUMNS).eq("roadmap_id", roadmap.roadmap_id)
                .order("created_at").execute().data)
    except Exception as e:
        print(f"roadmap_challenge could not be read ({type(e).__name__}); the roadmap will have no challenge")
        return []
    names = _interest_names(db, rows)
    return [_out(r, names) for r in rows]


def stingers(db: Client, profile_id: str, unspent: bool = False) -> int:
    """Stingers earned, or only the ones not yet spent on Robbee (unspent)."""
    query = db.table("stinger_award").select("challenge_id", count="exact").eq("profile_id", profile_id)
    return (query.is_("spent_at", "null") if unspent else query).execute().count or 0


def list_for_profile(db: Client, profile_id: str) -> Challenges:
    """Every challenge the profile has, newest first, and the stingers earned."""
    rows = (db.table("roadmap_challenge").select(CHALLENGE_COLUMNS).eq("profile_id", profile_id)
            .order("created_at", desc=True).execute().data)
    names = _interest_names(db, rows)
    return Challenges(challenges=[_out(r, names) for r in rows], stingers=stingers(db, profile_id), stingers_available=stingers(db, profile_id, unspent=True))


def roles(db: Client, profile_id: str) -> list[ChallengeRole]:
    """The tech roles a challenge can be started for: the profile's suggested roles first, then the rest by title."""
    rows = db.table("onet_roles").select("onet_code,title,icon").in_("onet_code", sorted(TECH_ROLES)).execute().data
    try:
        saved = profiles.get_suggestions(db, profile_id) or {}
    except profiles.ProfileError:
        saved = {}
    suggested = [j.get("onet_code") for j in (saved.get("jobs") or []) if isinstance(j, dict)]
    counts: dict[str, int] = {}
    for r in db.table("roadmap_challenge").select("onet_code").eq("profile_id", profile_id).execute().data:
        counts[r["onet_code"]] = counts.get(r["onet_code"], 0) + 1
    rank = {code: i for i, code in enumerate(suggested)}
    out = [ChallengeRole(onet_code=r["onet_code"], title=r["title"], icon=r.get("icon"), suggested=r["onet_code"] in rank,
                         challenges=counts.get(r["onet_code"], 0)) for r in rows]
    return sorted(out, key=lambda r: (rank.get(r.onet_code, len(rank)), r.title))


def _owned(db: Client, profile_id: str, challenge_id: str) -> dict:
    """The challenge row; 404 unless it belongs to this profile."""
    rows = db.table("roadmap_challenge").select(CHALLENGE_COLUMNS).eq("challenge_id", challenge_id).limit(1).execute().data
    if not rows or rows[0]["profile_id"] != profile_id:
        raise HTTPException(status_code=404, detail="no such challenge on this profile")
    return rows[0]


def _stale(now: datetime) -> str:
    return (now - STALE_BUSY).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- judging and Robbee's rewrite ----------

def submit(db: Client, profile_id: str, challenge_id: str, repo_url: str) -> SubmitResult:
    """Judge a repo against the current stage and keep the result (only the latest is kept). A score of pass_score() or more
    passes the stage and awards a stinger; at stage 2 it also completes the challenge. A completed challenge may be
    resubmitted to improve its score: it stays complete and pays no more stingers.

    It can be done at any time, whatever the roadmap progress. 404 if the challenge isn't this profile's, 409 if
    stage 1 is already passed (Robbee's rewrite is due) or a submission is being judged, 422 for a link that isn't a
    readable public GitHub repo, 502/503 if GitHub or the model fail; on a failure the previous result stays.
    """
    row = _owned(db, profile_id, challenge_id)
    complete = row["stage"] == 2 and bool(row["completed_at"])
    if row["status"] == "advancing" or (row["status"] == "passed" and not complete):
        raise HTTPException(status_code=409, detail="You’ve already passed this stage.")
    try:
        repo.parse_url(repo_url)
    except repo.RepoError as e:
        raise HTTPException(e.status_code, e.message) from e

    # Claim it: only one judgement at a time, unless the last one was lost.
    now = datetime.now(timezone.utc)
    idle = "status.eq.passed" if complete else "status.eq.open"
    settled = "passed" if complete else "open"
    claimed = (db.table("roadmap_challenge").update({"status": "judging", "busy_since": now.isoformat()})
               .eq("challenge_id", challenge_id).eq("stage", row["stage"])
               .or_(f"{idle},and(status.eq.judging,busy_since.lt.{_stale(now)})")
               .execute().data)
    if not claimed:
        raise HTTPException(status_code=409, detail="That challenge is already being judged. Give it a minute.")

    def release():
        db.table("roadmap_challenge").update({"status": settled, "busy_since": None}).eq("challenge_id", challenge_id).execute()

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

    passed = score >= judge.pass_score()
    judged_at = datetime.now(timezone.utc).isoformat()
    db.table("roadmap_challenge").update({
        "status": "passed" if passed or complete else "open",
        "busy_since": None,
        "repo_url": snap.url,
        "result": result,
        "score": score,
        "summary": summary,
        "files_read": [p for p, _ in snap.files],
        "attempts": row["attempts"] + 1,
        "judged_at": judged_at,
        "completed_at": row["completed_at"] or (judged_at if passed and row["stage"] == 2 else None),
        "model": get_settings().openrouter_model,
    }).eq("challenge_id", challenge_id).execute()
    awarded = False
    if passed and not complete:  # a resubmitted, completed challenge already has its stingers
        awarded = bool(db.table("stinger_award").upsert(
            {"challenge_id": challenge_id, "stage": row["stage"], "profile_id": profile_id, "score": score},
            on_conflict="challenge_id,stage", ignore_duplicates=True,
        ).execute().data)
    return SubmitResult(challenge=_row_out(db, _owned(db, profile_id, challenge_id)), passed=passed, stinger_awarded=awarded, stingers=stingers(db, profile_id), stingers_available=stingers(db, profile_id, unspent=True))


def advance(db: Client, profile_id: str, challenge_id: str) -> Challenge:
    """Robbee's rewrite: turn a passed stage 1 into a harder stage 2 written from the more advanced skills (the
    roadmap's later sections, or the role's other skills). Takes 20-40 seconds. Stage 1's final result moves into
    history. Already at stage 2 returns the challenge as it is.

    404 if the challenge isn't this profile's, 409 if stage 1 isn't passed or the rewrite is already being written,
    502 if the model fails twice (stage 1 stays passed, so it can be tried again).
    """
    row = _owned(db, profile_id, challenge_id)
    if row["stage"] == 2:
        return _row_out(db, row)
    if row["status"] not in ("passed", "advancing"):
        raise HTTPException(status_code=409, detail="Pass stage 1 first.")

    now = datetime.now(timezone.utc)
    claimed = (db.table("roadmap_challenge").update({"status": "advancing", "busy_since": now.isoformat()})
               .eq("challenge_id", challenge_id).eq("stage", 1)
               .or_(f"status.eq.passed,and(status.eq.advancing,busy_since.lt.{_stale(now)})")
               .execute().data)
    if not claimed:
        raise HTTPException(status_code=409, detail="Robbee is already rewriting this one. Give it a minute.")

    try:
        earlier, _, new, sections = _stages(db, profile_id, row["onet_code"], row["roadmap_id"])
        role_title = (row.get("onet_roles") or {}).get("title") or row["onet_code"]
        written = generator.write_stage2(role_title, profiles.get_profile(db, profile_id).stage, row, new, earlier)
    except Exception as e:
        print(f"Stage 2 not written for challenge {challenge_id} ({type(e).__name__}: {e})")
        written = None
    if not written:
        db.table("roadmap_challenge").update({"status": "passed", "busy_since": None}).eq("challenge_id", challenge_id).execute()
        raise HTTPException(status_code=502, detail="Robbee couldn’t rewrite the brief just now. Try again in a moment.")

    done = {k: row[k] for k in ("stage", "title", "repo_url", "score", "summary", "judged_at")}
    db.table("roadmap_challenge").update({
        **written,
        "sections": sections,
        "stage": 2,
        "status": "open",
        "busy_since": None,
        "history": (row["history"] or []) + [done],
        # repo_url stays: a challenge is built in one repo across both stages. The scorecard starts over.
        "result": None, "score": None, "summary": None, "files_read": [], "attempts": 0, "judged_at": None,
        "model": get_settings().openrouter_model,
    }).eq("challenge_id", challenge_id).eq("status", "advancing").execute()
    hive.log_twist(db, profile_id, challenge_id)
    return _row_out(db, _owned(db, profile_id, challenge_id))
