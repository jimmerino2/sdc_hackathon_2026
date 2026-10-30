"""How well a role fits a learner, worked out with arithmetic only.

    score = (0.10 * education + 0.25 * interests + 0.35 * skills + 0.35 * outlook) / 1.05      (each part 0-1)

The weights add up to 1.05, so the sum is divided by them: the shares that really apply are education 9.5%, interests
23.8%, skills 33.3% and outlook 33.3%. Anything shown to a learner must use those shares (see `shares`).

education  the learner's career stage: studying 1, fresh graduate 1.5, working 2.5, over the highest (2.5). The
           same for every role in the learner's job group (only tech roles are matched for now), so it lifts all of
           them together and never reorders them.
interests  for each interest the learner picked, its SDG scores times the role's SDG weights, summed over goals and
           interests; divided by the best role's sum, so the best interest match gets the whole share.
skills     the role's key skills weighted by O*NET importance, each counted at the learner's proficiency: Basic 0.33,
           Good 0.67, Strong 1. A skill they don't have counts 0.
outlook    the forecast's posting change for the chosen AI scenario as a multiplier (1x flat, up if rising, down if
           dropping, kept between 0.7x and 1.3x), stretched to 0-1.

With no interests picked, that part is left out and the others are scaled up to fill the 100%.

The shown match is score ** CURVE: it lifts every score (0.4 -> 0.53, 0.66 -> 0.75) without changing the order, and
0 and 1 stay put.
"""
from app.interests.schemas import Interest

W_EDUCATION, W_INTERESTS, W_SKILLS, W_OUTLOOK = 0.10, 0.25, 0.35, 0.35
STAGE_LEVEL = {"under": 1.0, "fresh": 1.5, "working": 2.5}
MULT_MIN, MULT_MAX = 0.7, 1.3  # the outlook multiplier is kept in this range
CURVE = 0.7  # below 1 lifts the match; lower lifts it more


def proficiency(score: float) -> float:
    """A stored skill score as one of the three proficiency steps (Basic 0.33, Good 0.67, Strong 1); 0 means no skill.

    Scores from the skill check and from older profiles (0.4, 0.7) or a resume (any 0-1 value) land on the nearest step.
    """
    if score <= 0:
        return 0.0
    if score <= 0.5:
        return 0.33
    if score <= 0.85:
        return 0.67
    return 1.0


def education(stage: str) -> float:
    """The learner's career stage as 0-1."""
    return STAGE_LEVEL.get(stage, STAGE_LEVEL["under"]) / max(STAGE_LEVEL.values())


def skills_fit(weights: dict[str, float], have: dict[str, float]) -> float:
    """Share of the role's key-skill importance the learner covers, each skill at their proficiency in it (0-1).

    weights: key skill -> O*NET importance. have: skill name in lower case -> proficiency (0 or missing = don't have it).
    """
    total = sum(weights.values())
    return sum(w * have.get(name.lower(), 0.0) for name, w in weights.items()) / total if total else 0.0


def interest_raw(picked: list[Interest], role_sdg: list[dict]) -> float:
    """How strongly the learner's interests point at the goals this role serves: Σ over interests and goals of
    (the interest's score for the goal) x (the role's weight for the goal). More interests picked, a bigger sum."""
    weight = {g["sdg"]: g["value"] for g in role_sdg}
    return sum(w.value * weight.get(w.sdg, 0.0) for i in picked for w in i.sdg)


def outlook_multiplier(change_pct: float) -> float:
    """1x as the base, above it if postings are rising and below it if they are dropping, kept between 0.7x and 1.3x."""
    return min(MULT_MAX, max(MULT_MIN, 1 + change_pct / 100))


def outlook_score(change_pct: float) -> float:
    """The outlook multiplier stretched to 0-1: 0.7x is 0, 1x is 0.5, 1.3x is 1."""
    return (outlook_multiplier(change_pct) - MULT_MIN) / (MULT_MAX - MULT_MIN)


def _parts(education_: float, skills: float, outlook: float, interests: float | None) -> list[tuple[str, float, float]]:
    """(part, its weight, its score). Without interests (None) that part is left out."""
    parts = [("skills", W_SKILLS, skills), ("outlook", W_OUTLOOK, outlook)]
    if interests is not None:
        parts.append(("interests", W_INTERESTS, interests))
    return [*parts, ("education", W_EDUCATION, education_)]


def shares(has_interests: bool = True) -> dict[str, float]:
    """The share of the score each part really carries: its weight over the sum of the weights in use. Adds up to 1."""
    parts = _parts(0, 0, 0, 0 if has_interests else None)
    total = sum(w for _, w, _ in parts)
    return {name: w / total for name, w, _ in parts}


def breakdown(education_: float, skills: float, outlook: float, interests: float | None) -> dict:
    """How a score is made up. `points` are each part's contribution to `raw_score` (they add up to it), and
    match_percent is what the page shows: raw_score ** CURVE as a whole percent, the same number as combine()."""
    parts = _parts(education_, skills, outlook, interests)
    total = sum(w for _, w, _ in parts)
    components = [{"key": name, "score": round(v, 4), "weight": w, "share": round(w / total, 4), "points": round(w * v / total, 4)}
                  for name, w, v in parts]
    raw = sum(w * v for _, w, v in parts) / total
    return {"components": components, "raw_score": round(raw, 4), "curve": CURVE, "match_percent": round(100 * raw ** CURVE)}


def combine(education_: float, skills: float, outlook: float, interests: float | None) -> float:
    """The weighted score, curved up, 0-1. Without interests (None) the other parts share the whole 100%."""
    parts = _parts(education_, skills, outlook, interests)
    return (sum(w * v for _, w, v in parts) / sum(w for _, w, _ in parts)) ** CURVE
