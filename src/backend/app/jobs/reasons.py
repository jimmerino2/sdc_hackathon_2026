"""Why a role fits each of a learner's interests, in one short sentence per (role, goal, interest).

The pairs come from the data (the role's SDGs and the goals behind the interests, as in service._sdg_reasons); the
LLM only words them. A sentence is written the first time anyone opens that role with that interest picked and kept
in role_interest_reasons (migration 0015), so later visits read it back without calling the model.
"""
import json

from supabase import Client

from app.config import get_settings
from app.interests import service as interests_service
from app.interests.schemas import Interest
from app.interests.sdg import SDG_NAMES
from app.jobs.schemas import InterestReason
from app.llm import service as llm
from app.profile import service as profiles

MAX_CHARS = 240  # a longer answer is cut, so one bad reply can't flood the card

SYSTEM = "You write short, warm career explanations for students and return JSON only."

PROMPT = """A learner is looking at the role "{title}".
What the role does: {description}

Each pair below links one of the learner's interests to a UN Sustainable Development Goal this role's work serves.
For each pair, write ONE sentence (at most 25 words) telling the learner, as "you", how someone who enjoys that
interest could serve that goal in this role. Be concrete about the role's actual work. Don't repeat the goal's
number, don't start with "As a", and don't promise jobs or salaries.

PAIRS:
{pairs}

Return one JSON object, nothing else:
{{"reasons": [{{"sdg": 3, "interest_id": 5, "reason": "..."}}]}}"""


class ReasonError(Exception):
    """The reasons could not be worked out."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _role(db: Client, onet_code: str) -> dict:
    try:
        data = db.table("onet_roles").select("onet_code,title,description,sdg").eq("onet_code", onet_code).limit(1).execute().data
    except Exception as e:
        raise ReasonError(502, f"The role could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    if not data:
        raise ReasonError(404, "No such role.")
    return data[0]


def _pairs(role: dict, picked: list[Interest]) -> list[tuple[int, Interest]]:
    """(goal, interest) for every goal of the role that one of the interests points at, biggest goal first."""
    out = []
    for g in sorted(role.get("sdg") or [], key=lambda g: -g["value"]):
        weight = lambda i: next((w.value for w in i.sdg if w.sdg == g["sdg"]), 0.0)  # noqa: E731
        out += [(g["sdg"], i) for i in sorted(picked, key=lambda i: -weight(i)) if weight(i) > 0]
    return out


def _write(role: dict, missing: list[tuple[int, Interest]]) -> dict[tuple[int, int], str]:
    """Ask the LLM for the missing sentences. Pairs it skips or garbles are left out."""
    pairs = "\n".join(f'- sdg {g} "{SDG_NAMES[g]}" + interest_id {i.id} "{i.interest}" ({i.description})' for g, i in missing)
    prompt = PROMPT.format(title=role["title"], description=role.get("description") or "(no description)", pairs=pairs)
    raw = llm.complete(prompt, system=SYSTEM, max_tokens=150 + 80 * len(missing), thinking=False)
    data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    wanted = {(g, i.id) for g, i in missing}
    out = {}
    for item in data.get("reasons") or []:
        try:
            key = (int(item["sdg"]), int(item["interest_id"]))
        except (KeyError, TypeError, ValueError):
            continue
        text = " ".join(str(item.get("reason") or "").split())[:MAX_CHARS]
        if key in wanted and text:
            out[key] = text
    return out


def interest_reasons(db: Client, profile_id, onet_code: str) -> list[InterestReason]:
    """A sentence for each of the role's goals the learner's interests point at, written by the LLM on first use
    and kept. If the model fails, the sentences already kept are still returned and the rest are left out."""
    try:
        profile = profiles.get_profile(db, profile_id)
    except profiles.ProfileError as e:
        raise ReasonError(e.status_code, e.message) from e
    role = _role(db, onet_code)
    try:
        picked = interests_service.by_ids(db, profile.interests)
    except interests_service.InterestError as e:
        raise ReasonError(502, str(e)) from e
    pairs = _pairs(role, picked)
    if not pairs:
        return []

    try:
        rows = (db.table("role_interest_reasons").select("sdg,interest_id,reason").eq("onet_code", onet_code)
                .in_("interest_id", sorted({i.id for _, i in pairs})).execute().data)
    except Exception as e:
        raise ReasonError(502, f"The reasons could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    known = {(r["sdg"], r["interest_id"]): r["reason"] for r in rows}

    missing = [(g, i) for g, i in pairs if (g, i.id) not in known]
    if missing:
        try:
            written = _write(role, missing)
        except Exception as e:  # the cards still show the interests without a sentence
            print(f"Interest reasons not written for {onet_code} ({type(e).__name__}: {e})")
            written = {}
        if written:
            model = get_settings().openrouter_model
            try:
                db.table("role_interest_reasons").upsert(
                    [{"onet_code": onet_code, "sdg": g, "interest_id": i, "reason": t, "model": model} for (g, i), t in written.items()],
                    ignore_duplicates=True,
                ).execute()
            except Exception as e:  # shown this time anyway; written again next time
                print(f"Interest reasons not saved for {onet_code} ({getattr(e, 'message', type(e).__name__)})")
        known.update(written)

    return [InterestReason(sdg=g, interest_id=i.id, interest=i.interest, reason=known[(g, i.id)]) for g, i in pairs if (g, i.id) in known]
