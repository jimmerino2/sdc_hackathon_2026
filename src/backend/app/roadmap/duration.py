"""How long a roadmap step takes.

Every step gets a time and says where it came from:

  stated     the first learning resource of the skill (best rank first) whose own page states a length of at least
             STATED_MIN_MINUTES, read by pipeline/fetch_durations.py (a video's length, a course's "N hours to complete").
             Shorter pieces are skipped: a 10-minute clip does not teach a skill.
  estimated  a written formula, used when no resource states a usable length:

                 minutes = BASE[kind] x (0.5 + level / 7)      rounded to 15 minutes

             kind is the type of the skill's first resource (project, certificate, video or activity), or, with no
             resource, the usual type for the skill (tools: project, abilities: activity, knowledge: video).
             level is the skill's O*NET level (0-7), so a deeper skill takes longer; tools have no level and use 1.0.

The BASE hours are our own assumption, not a measurement, which is why those steps are labelled estimates.
"""
from __future__ import annotations

STATED_MIN_MINUTES = 60
# Study time in minutes for a skill of middling depth, by the kind of resource that teaches it. Our assumption.
BASE_MINUTES = {"project": 360, "certificate": 600, "video": 120, "activity": 180}
DEFAULT_KIND = {"tech": "project", "skill": "activity", "knowledge": "video"}
ROUND_TO = 15


def formula_minutes(kind: str, level: float | None) -> int:
    """The written formula: BASE[kind] x (0.5 + level / 7), to the nearest quarter hour; tools (no level) count 1.0."""
    factor = 1.0 if level is None else 0.5 + float(level) / 7
    return max(ROUND_TO, round(BASE_MINUTES[kind] * factor / ROUND_TO) * ROUND_TO)


def estimate(skill_type: str, level: float | None, sources: list) -> tuple[int, str, str | None]:
    """(minutes, basis, title of the resource whose length was used) for one skill.

    `sources` are the skill's resources, best first (objects with source_type, title and duration_minutes).
    """
    for s in sources:
        stated = getattr(s, "duration_minutes", None)
        if stated and stated >= STATED_MIN_MINUTES:
            return int(stated), "stated", s.title
    kind = sources[0].source_type if sources else DEFAULT_KIND.get(skill_type, "activity")
    return formula_minutes(kind, level), "estimated", None
