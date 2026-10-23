from supabase import Client

from app.interests.schemas import Interest, SdgFocus
from app.interests.sdg import SDG_NAMES


class InterestError(Exception):
    """The interests could not be read."""


def list_interests(db: Client) -> list[Interest]:
    """Every interest a learner can pick, in the order they were added."""
    try:
        rows = db.table("interests").select("id,interest,description,icon,sdg").order("id").execute().data
    except Exception as e:
        raise InterestError(f"The interests could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    return [Interest(**r) for r in rows]


def by_ids(db: Client, ids: list[int]) -> list[Interest]:
    """The interests with these ids; ids that don't exist are left out. Same order as list_interests."""
    if not ids:
        return []
    try:
        rows = db.table("interests").select("id,interest,description,icon,sdg").in_("id", sorted(set(ids))).order("id").execute().data
    except Exception as e:
        raise InterestError(f"The interests could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    return [Interest(**r) for r in rows]


def sdg_focus(picked: list[Interest]) -> list[SdgFocus]:
    """The goals a learner's interests point at, biggest first, with shares that add up to 1.

    Each interest counts equally, so picking more interests spreads the focus rather than inflating it.
    """
    if not picked:
        return []
    total: dict[int, float] = {}
    for interest in picked:
        for w in interest.sdg:
            total[w.sdg] = total.get(w.sdg, 0.0) + w.value / len(picked)
    return [SdgFocus(sdg=g, name=SDG_NAMES[g], value=round(v, 4)) for g, v in sorted(total.items(), key=lambda kv: (-kv[1], kv[0]))]
