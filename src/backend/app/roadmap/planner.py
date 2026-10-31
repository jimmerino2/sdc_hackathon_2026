"""Turns a role's skills into a roadmap plan (sections -> units -> nodes with prerequisites) using an LLM."""
import json
import re
from dataclasses import dataclass, field

from fastapi import HTTPException
from openai import OpenAI

from app.config import get_settings

MAX_OUTPUT_TOKENS = 12000  # a 50-node plan is ~4k tokens; the rest is headroom for model reasoning
MIN_IMPORTANCE = 2.25  # candidates must be strictly above this; the model then trims further
MAX_SKILLS = 20  # a roadmap holds at most this many skills
MIN_SKILLS = 12  # what the model aims for at the low end

SYSTEM_PROMPT = f"""You design learning roadmaps. Given a job role and its candidate skills, produce a roadmap a person can follow to prepare for the role.

Each candidate skill has: id, name, type (skill = general ability, knowledge = subject area, tech = software/tool), importance (1-5, how much O*NET says the role needs it), level (0-7, how deep; null for tech) and forecast_demand (0-1, the share of current US job ads for this role that name the skill, 6 months out; null when it isn't tracked, which is most skills - treat null as no signal either way, not as low demand).

Do this in order:
1. Re-evaluate which skills to keep. Drop near-duplicates, skills too generic to be worth a dedicated step, and low-value tools. A focused roadmap is better than an exhaustive one (aim for {MIN_SKILLS}-{MAX_SKILLS} skills, never more than {MAX_SKILLS}, fewer if the role has fewer worthwhile ones). Weigh forecast_demand heavily, not just as a tie-breaker: it is live evidence from current job ads, so a skill with meaningfully positive forecast_demand (say, above 0.05) should almost always be kept and should usually outrank a similar-importance skill with no forecast_demand data, even if that means cutting a slightly-higher-importance skill that forecast_demand doesn't cover. Importance stays the primary signal only when forecast_demand is null (most skills) or negligible.
2. Group the kept skills into sections by real subject-matter coherence, not a fixed stage template - never sort skills into generic buckets like "foundations" / "core" / "applied" / "advanced" by skill type alone (that produces nonsense, e.g. a general-purpose language stranded alone in an early section while the specific stack the role actually uses sits three sections later). Instead, look at what the skills are actually for and group skills that are learned and used together (e.g. all of a web stack in one section, all of a cloud/deployment toolchain in another), choosing whatever number of sections (3 or more) and whatever order genuinely fits this role and this exact skill set - order sections so that a section's skills don't depend on a later section's, but otherwise structure it freely around the role's real shape, not a template. Give every section a short title (2-5 words) naming what it covers (e.g. "Web Fundamentals", "Cloud & Deployment", "Data Pipelines") - never a generic label like "Foundations" or "Section 1". Split each section into units (small themed groups of 3-6 skills); use level and importance to place basics before advanced material within a section.
3. For each skill, list previous_nodes: ids of kept skills that should be learned before it. Only list a real dependency, not everything earlier. previous_nodes may ONLY reference another skill placed earlier in the very same unit - never a skill in an earlier unit or section, even when a real dependency exists. The roadmap only draws a dependency line within a unit, so a cross-unit prerequisite would be silently invisible; if a skill genuinely depends on something from an earlier unit or section, either place them in the same unit instead, or drop the link and rely on section/unit order alone.
4. Set previous_nodes_required to true if the previous nodes must be completed first, false if they are only recommended.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{{"sections":[{{"title":"<short section title>","units":[{{"nodes":[{{"skill_id":"<id>","previous_nodes":["<id>"],"previous_nodes_required":true}}]}}]}}]}}
Use only ids from the candidate list. Each skill may appear at most once. Hard limit: {MAX_SKILLS} skills in total."""


SELECT_PROMPT = f"""You choose which skills a learner should study to prepare for a job role. Given the role and its candidate skills, pick the ones worth including in their roadmap.

Each candidate skill has: id, name, type (skill = general ability, knowledge = subject area, tech = software/tool), importance (1-5, how much O*NET says the role needs it), level (0-7, how deep; null for tech) and forecast_demand (0-1, the share of current US job ads for this role that name the skill, 6 months out; null when it isn't tracked, which is most skills - treat null as no signal either way, not as low demand).

Drop near-duplicates, skills too generic to be worth a dedicated step, and low-value tools. A focused list is better than an exhaustive one (aim for {MIN_SKILLS}-{MAX_SKILLS} skills, never more than {MAX_SKILLS}, fewer if the role has fewer worthwhile ones). Weigh forecast_demand heavily, not just as a tie-breaker: it is live evidence from current job ads, so a skill with meaningfully positive forecast_demand (say, above 0.05) should almost always be kept. Importance stays the primary signal only when forecast_demand is null or negligible.

Only choose the skills. Do not group, order or label them.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{{"skills":["<id>","<id>"]}}
Use only ids from the candidate list. Each skill may appear at most once."""

SELECT_LEARNER_PROMPT = """

The learner is described in the user message. Choose for them:
- `have` on a candidate is how well they already know it (0.33 basic, 0.67 good, 1 strong); no `have` means they don't know it yet.
- Leave out skills with `have` of 0.67 or more: they know those already. Spend the list on what they lack or know only at a basic level.
- Pitch it at their stage: for a beginner (under = undergraduate, fresh = fresh graduate, working = working beginner) include the fundamentals of whatever they lack."""

_STEPS = SYSTEM_PROMPT[SYSTEM_PROMPT.index("2. Group"):].replace("Hard limit: ", "Every skill in the list must appear. Hard limit: ")
ORGANIZE_PROMPT = (
    "You design learning roadmaps. Given a job role and the skills already chosen for the learner, arrange them into a roadmap a person can follow.\n\n"
    "The skills are already chosen: use every one of them exactly once. Do not drop any and do not add any.\n\n"
    "Do this in order:\n"
    + _STEPS.replace("2. Group", "1. Group", 1).replace("3. For each", "2. For each", 1).replace("4. Set", "3. Set", 1)
)

LEARNER_PROMPT = """

The learner this roadmap is for is described in the user message. Personalise the plan to them:
- `have` on a candidate is how well they already know it (0.33 basic, 0.67 good, 1 strong); no `have` means they don't know it yet.
- Skills with `have` of 0.67 or more are already theirs and will be shown as done. Keep one only when it is a foundation the unfinished skills build on (so it can be a prerequisite); otherwise leave it out and use the room for skills they lack.
- Spend the plan on their gaps: prefer skills they lack or know only at a basic level, and place their gaps in the earliest sections so they start learning something new straight away.
- Pitch it at their stage: for a beginner (under = undergraduate, fresh = fresh graduate, working = working beginner) start from the fundamentals of whatever they lack."""

OWNED_LEVEL = 0.67  # a skill known at this level (Good) or above counts as already done


@dataclass
class PlanNode:
    skill_id: str
    previous_nodes: list[str] = field(default_factory=list)
    previous_nodes_required: bool = True


@dataclass
class PlanSection:
    title: str
    units: list[list[PlanNode]] = field(default_factory=list)  # unit_index -> nodes, in learning order


Plan = list[PlanSection]


def candidates(skills: list[dict]) -> list[dict]:
    """Skills important enough to be considered."""
    return [s for s in skills if s["importance"] is not None and s["importance"] > MIN_IMPORTANCE]


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start : end + 1])


def sanitize(raw: dict, valid_ids: set[str]) -> Plan:
    """Keep only what is safe to store: known ids, each once, prerequisites that point strictly backwards
    within the same unit (the roadmap only ever draws a dependency line within a unit; the model is told
    this too, but a cross-unit reference is dropped here rather than trusted, same as a bad id).

    Dropping a bad prerequisite is safe (the node just has fewer constraints); a backwards-only,
    same-unit-only rule also guarantees the dependency graph has no cycles. Empty units and sections
    are removed.
    """
    seen: set[str] = set()
    plan: Plan = []
    for sec in raw.get("sections", []):
        units: list[list[PlanNode]] = []
        for unit in sec.get("units", []):
            nodes: list[PlanNode] = []
            unit_seen: set[str] = set()  # ids placed so far in this unit only
            for n in unit.get("nodes", []):
                sid = n.get("skill_id") if isinstance(n, dict) else None
                if sid not in valid_ids or sid in seen:
                    continue
                prev = n.get("previous_nodes") or []
                prev = list(dict.fromkeys(p for p in prev if p in unit_seen))  # same unit, already placed => strictly earlier
                nodes.append(PlanNode(sid, prev, bool(n.get("previous_nodes_required", True)) or not prev))  # nothing to require
                seen.add(sid)
                unit_seen.add(sid)
            if nodes:
                units.append(nodes)
        if units:
            title = sec.get("title")
            plan.append(PlanSection(title.strip() if isinstance(title, str) and title.strip() else f"Section {len(plan) + 1}", units))
    if not plan:
        raise ValueError("plan has no usable nodes")
    return plan


def _thinking_options(mode: str, base_url: str) -> dict | None:
    """Extra request body that sets how much the model thinks before answering (ROADMAP_REASONING).

    Thinking is the slow part: with it on, a roadmap took about 73 s, most of it hidden reasoning; with it off
    about 10 s. OpenRouter takes a `reasoning` object; other OpenAI-compatible gateways (Grafilab) take the
    chat-template switch, which only has an on/off form, so "low" there keeps the model's default.
    """
    if "openrouter.ai" in base_url:
        reasoning = {"off": {"enabled": False}, "low": {"effort": "low"}}.get(mode)
        return {"reasoning": reasoning} if reasoning else None
    if mode == "off":
        return {"chat_template_kwargs": {"enable_thinking": False}}
    return None


def _complete(messages: list[dict]) -> str:
    settings = get_settings()
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)
    extra = _thinking_options(settings.roadmap_reasoning, settings.openrouter_base_url)
    res = client.chat.completions.create(
        model=settings.openrouter_model, messages=messages, max_tokens=MAX_OUTPUT_TOKENS, extra_body=extra,
        temperature=0,  # the same learner and role should give the same plan
    )
    return res.choices[0].message.content


def _chat_json(messages: list[dict], parse, what: str):
    """Ask the model and parse its JSON reply with `parse`; one retry when the reply is unusable. 502 if it fails twice."""
    error = None
    for _ in range(2):
        try:
            reply = _complete(messages)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"model call failed: {e}")
        try:
            return parse(_extract_json(reply))
        except (ValueError, AttributeError) as e:
            error = e
            messages = messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"That reply was unusable ({e}). Reply again with only the JSON object in the required shape."},
            ]
    raise HTTPException(status_code=502, detail=f"model returned an unusable {what}: {error}")


def _require_openrouter():
    settings = get_settings()
    if settings.ai_model_mode != "OPENROUTER":
        raise HTTPException(status_code=503, detail=f"unsupported AI_MODEL_MODE {settings.ai_model_mode!r}")
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not set")


def _listing(skills: list[dict], learner: dict | None) -> list[dict]:
    have = (learner or {}).get("have", {})
    return [
        {"id": s["skill_id"], "name": s["skill_name"], "type": s["skill_type"], "importance": s["importance"], "level": s["level"],
         "forecast_demand": s.get("forecast_demand"), **({"have": have[s["skill_id"]]} if have.get(s["skill_id"]) else {})}
        for s in skills
    ]


def sanitize_selection(raw: dict, valid_ids: set[str]) -> list[str]:
    """The chosen ids in the model's order: known ids only, each once, at most MAX_SKILLS."""
    out: list[str] = []
    for sid in raw.get("skills", []):
        if isinstance(sid, str) and sid in valid_ids and sid not in out:
            out.append(sid)
    if not out:
        raise ValueError("no usable skills")
    return out[:MAX_SKILLS]


def select_skills(role_title: str, role_description: str | None, skills: list[dict], learner: dict | None = None) -> list[str]:
    """Which of the role's skills this learner should study (ids). Only the choice: no sections, order or prerequisites."""
    _require_openrouter()
    who = f"\nLearner stage: {learner['stage']}" if learner else ""
    messages = [
        {"role": "system", "content": SELECT_PROMPT + (SELECT_LEARNER_PROMPT if learner else "")},
        {"role": "user", "content": f"Role: {role_title}\n{role_description or ''}{who}\n\nCandidate skills:\n{json.dumps(_listing(skills, learner))}"},
    ]
    valid = {s["skill_id"] for s in skills}
    return _chat_json(messages, lambda raw: sanitize_selection(raw, valid), "skill list")


def fallback_selection(skills: list[dict], have: dict[str, float]) -> list[str]:
    """When the model can't be used: the role's most important skills the learner doesn't already know well."""
    open_ = [s for s in skills if have.get(s["skill_id"], 0) < OWNED_LEVEL]
    open_.sort(key=lambda s: (0 if (s.get("forecast_demand") or 0) > 0.05 else 1, -(s["importance"] or 0), s["skill_name"]))
    return [s["skill_id"] for s in open_[:MAX_SKILLS]]


def complete_plan(plan: Plan, skills: list[dict]) -> Plan:
    """The plan with any skill the model left out added in units at the end, so every chosen skill is on the roadmap."""
    placed = {n.skill_id for sec in plan for unit in sec.units for n in unit}
    left = [s["skill_id"] for s in sorted(skills, key=lambda s: -(s["importance"] or 0)) if s["skill_id"] not in placed]
    if not left:
        return plan
    extra = [[PlanNode(sid) for sid in left[i:i + 5]] for i in range(0, len(left), 5)]
    if not plan:
        return [PlanSection("What to learn", extra)]
    return [*plan[:-1], PlanSection(plan[-1].title, [*plan[-1].units, *extra])]


def organize_plan(role_title: str, role_description: str | None, skills: list[dict], learner: dict | None = None) -> Plan:
    """Arrange skills that are already chosen into sections, units and prerequisites. Nothing is dropped or added."""
    _require_openrouter()
    messages = [
        {"role": "system", "content": ORGANIZE_PROMPT},
        {"role": "user", "content": f"Role: {role_title}\n{role_description or ''}\n\nSkills to arrange (use every one):\n{json.dumps(_listing(skills, learner))}"},
    ]
    valid = {s["skill_id"] for s in skills}
    plan = _chat_json(messages, lambda raw: sanitize(raw, valid), "roadmap")
    return complete_plan(plan, skills)


def fallback_plan(skills: list[dict]) -> Plan:
    """When the model can't be used: one section each for skills, tools and knowledge, most important first, no prerequisites."""
    names = {"skill": "Core skills", "tech": "Tools and technology", "knowledge": "Subject knowledge"}
    plan: Plan = []
    for kind, title in names.items():
        ids = [s["skill_id"] for s in sorted(skills, key=lambda s: (-(s["importance"] or 0), s["skill_name"])) if s["skill_type"] == kind]
        if ids:
            plan.append(PlanSection(title, [[PlanNode(sid) for sid in ids[i:i + 4]] for i in range(0, len(ids), 4)]))
    return plan


def build_plan(role_title: str, role_description: str | None, skills: list[dict], learner: dict | None = None) -> Plan:
    """Plan the role's roadmap. `learner` ({"stage": ..., "have": {skill_id: proficiency}}) tailors it to one person."""
    if get_settings().ai_model_mode == "OPENROUTER":
        return _plan_with_openrouter(role_title, role_description, skills, learner)
    raise HTTPException(status_code=503, detail=f"unsupported AI_MODEL_MODE {get_settings().ai_model_mode!r}")


def _plan_with_openrouter(role_title: str, role_description: str | None, skills: list[dict], learner: dict | None = None) -> Plan:
    if not get_settings().openrouter_api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not set")
    have = (learner or {}).get("have", {})
    listing = [
        {"id": s["skill_id"], "name": s["skill_name"], "type": s["skill_type"], "importance": s["importance"], "level": s["level"],
         "forecast_demand": s.get("forecast_demand"), **({"have": have[s["skill_id"]]} if have.get(s["skill_id"]) else {})}
        for s in skills
    ]
    who = f"\nLearner stage: {learner['stage']}" if learner else ""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + (LEARNER_PROMPT if learner else "")},
        {"role": "user", "content": f"Role: {role_title}\n{role_description or ''}{who}\n\nCandidate skills:\n{json.dumps(listing)}"},
    ]
    valid_ids = {s["skill_id"] for s in skills}
    error = None
    for _ in range(2):  # one retry on unparseable or empty output
        try:
            reply = _complete(messages)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"model call failed: {e}")
        try:
            return sanitize(_extract_json(reply), valid_ids)
        except (ValueError, AttributeError) as e:
            error = e
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"That reply was unusable ({e}). Reply again with only the JSON object in the required shape."},
            ]
    raise HTTPException(status_code=502, detail=f"model returned an unusable roadmap: {error}")
