"""Turns a role's skills into a roadmap plan (sections -> units -> nodes with prerequisites) using an LLM."""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
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


def _complete(messages: list[dict], reasoning: str | None = None, max_tokens: int | None = None) -> str:
    """One model call. `reasoning` ("off", "low", ...) replaces ROADMAP_REASONING for this call, `max_tokens` the output limit."""
    settings = get_settings()
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)
    extra = _thinking_options(reasoning or settings.roadmap_reasoning, settings.openrouter_base_url)
    res = client.chat.completions.create(
        model=settings.openrouter_model, messages=messages, max_tokens=max_tokens or MAX_OUTPUT_TOKENS, extra_body=extra,
        temperature=0,  # the same learner and role should give the same plan
    )
    return res.choices[0].message.content


def _chat_json(messages: list[dict], parse, what: str, **options):
    """Ask the model and parse its JSON reply with `parse`; one retry when the reply is unusable. 502 if it fails twice.
    `options` (reasoning, max_tokens) go to _complete."""
    error = None
    for _ in range(2):
        try:
            reply = _complete(messages, **options)
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


# ---------- AI skills: one per section, first in the section's first unit; its skills wait for it ----------
GUIDE_PREFIX = "ai:"  # skill_id of an AI skill: "ai:" and a short hash of the role and the title, so the same title for the same role is the same skill
MAX_GUIDES = 8  # at most this many sections get one
GUIDE_MINUTES = 20  # how long one is planned to take; it has no resource that states a length
MAX_EXISTING = 30  # titles of the role's earlier AI skills shown to the model, so it can reuse one
MAX_DESCRIPTION, MAX_STEP, MAX_STEPS = 160, 90, 3  # an AI skill's details are kept short

GUIDE_MAX_TOKENS = 3000  # eight short AI skills fit well inside this
GUIDE_REASONING = "off"  # the model only has to name and describe them, so it answers without thinking first: speed over polish

# The sources of an AI skill are never written by the model, which would invent links. Each one gets the real ESCO page of up to
# SOURCE_LOOKUPS skills of its section (a page is used once in a roadmap, so they differ from skill to skill), then one of these
# skills taxonomies, handed out in turn by section so there is always at least one source. Entries are (title, url).
SOURCE_LOOKUPS = 2
TAXONOMY_SOURCES = [
    ("ESCO skills services and API", "https://esco.ec.europa.eu/en/use-esco/use-esco-services-api"),
    ("Lightcast skills taxonomy", "https://lightcast.io/taxonomies/skills-taxonomy"),
    ("WEF Global Skills Taxonomy", "https://initiatives.weforum.org/reskilling-revolution/gst"),
]


def _source(rank: int, title: str, url: str) -> dict:
    return {"source_type": "reference", "rank": rank, "title": title, "url": url, "duration_minutes": None}


def taxonomy_source(number: int, rank: int = 1) -> dict:
    """The taxonomy reference for a section (1, 2, 3, ... take the three in turn)."""
    title, url = TAXONOMY_SOURCES[(number - 1) % len(TAXONOMY_SOURCES)]
    return _source(rank, title, url)


def attach_sources(plan: Plan, guides: dict[int, dict], names: dict[str, str], find, page) -> dict[int, dict]:
    """The guides with their sources: the ESCO page of up to SOURCE_LOOKUPS of the section's skills, then a taxonomy reference.

    `find(name)` gives {"uri", "title"} or None and `page(uri)` the link (see esco.py); they are looked up together. A guide that
    already has sources (a reused one) keeps them. An ESCO page already used for another guide is left out, so each differs."""
    todo = {i: g for i, g in guides.items() if not g.get("sources")}
    picks = {i: [names[n.skill_id] for unit in plan[i - 1].units for n in unit if n.skill_id in names][:SOURCE_LOOKUPS] for i in todo}
    wanted = list(dict.fromkeys(n for ns in picks.values() for n in ns))
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(zip(wanted, pool.map(find, wanted)))
    used: set[str] = set()
    out = dict(guides)
    for i in sorted(todo):
        sources = []
        for name in picks[i]:
            hit = found.get(name)
            if hit and hit["uri"] not in used:
                used.add(hit["uri"])
                sources.append(_source(len(sources) + 1, f"ESCO: {hit['title']}", page(hit["uri"])))
        out[i] = {**todo[i], "sources": [*sources, taxonomy_source(i, len(sources) + 1)]}
    return out

GUIDE_PROMPT = """You write short "AI skills" for a learning roadmap. For each section you get its title and the skills in it. An AI skill teaches the learner how to use AI tools (a chat assistant, a coding assistant) to learn and simplify THOSE skills, so they learn faster and understand more, not so the AI does the work for them.

For every section write:
- title: a short name, at most 40 characters, e.g. "AI-assisted web basics". Name the area, not "AI skill". Two sections never share a title.
- description: ONE or two short plain sentences, under 150 characters in all, on how AI helps with this section's skills. Name a real skill from the section.
- steps: exactly 3, each under 80 characters and starting with a verb, e.g. "Ask an AI to explain loops, then explain them back." Make one check the AI's answer against a trusted source and one practise without it.

existing_titles lists AI skills already written for this role. When one of them fits a section, use its exact title for that section instead of a new one.

Rules: do not give URLs or name specific products as the only option. Write for a beginner. No hype.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{"guides":[{"section":1,"title":"...","description":"...","steps":["...","..."]}]}
Use only the section numbers you were given, once each."""


def is_guide(skill_id: str) -> bool:
    return skill_id.startswith(GUIDE_PREFIX)


def norm_title(title: str) -> str:
    """A title as compared for sameness: lower case, one space between words."""
    return " ".join(title.lower().split())


def ai_skill_id(onet_code: str, title: str) -> str:
    """The skill_id of the AI skill with this title for this role: the same title always gives the same id."""
    return GUIDE_PREFIX + hashlib.sha1(f"{onet_code}|{norm_title(title)}".encode()).hexdigest()[:12]


def _clean(value, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def sanitize_guides(raw: dict, sections: list[int]) -> dict[int, dict]:
    """The usable AI skills by section number: known sections only, each once, with a title and a description."""
    out: dict[int, dict] = {}
    for g in raw.get("guides", []):
        if not isinstance(g, dict):
            continue
        try:
            number = int(g.get("section"))
        except (TypeError, ValueError):
            continue
        title, description = _clean(g.get("title"), 40), _clean(g.get("description"), MAX_DESCRIPTION)
        steps = [s for s in (_clean(x, MAX_STEP) for x in g.get("steps") or []) if s][:MAX_STEPS]
        if number in sections and number not in out and title and description:
            out[number] = {"title": title, "description": description, "steps": steps}
    if not out:
        raise ValueError("no usable guides")
    return out


def fallback_guide(section_title: str, skill_names: list[str]) -> dict:
    """When the model can't be used: an AI skill built from the section's own title and skill names."""
    shown = ", ".join(skill_names[:3])
    return {
        "title": _clean(f"AI for {section_title}", 40),
        "description": _clean(f"Use an AI as a study buddy for {shown}: have it explain and quiz you, then check it against a trusted source.", MAX_DESCRIPTION),
        "steps": [
            _clean(f"Ask an AI to explain {skill_names[0]}, then explain it back.", MAX_STEP),
            "Answer its practice questions before it marks them.",
            "Check what it says against the official docs.",
        ],
    }


def write_guides(role_title: str, onet_code: str, plan: Plan, names: dict[str, str], existing: dict[str, dict] | None = None) -> dict[int, dict]:
    """An AI skill for each section of the plan (at most MAX_GUIDES), by section number, each {skill_id, title, description, steps}.

    `names` maps skill_id -> skill name; `existing` is the role's earlier AI skills by normalised title (see norm_title). A title that
    matches one of them takes that skill's stored description and steps, so nothing the model already wrote for the role is rewritten.
    Titles are made different across sections, since a roadmap holds each skill once. Never raises: if the model can't be used, every
    section gets the plain fallback, so a roadmap always has them.
    """
    existing = existing or {}
    sections = {i: [names[n.skill_id] for unit in sec.units for n in unit if n.skill_id in names] for i, sec in enumerate(plan[:MAX_GUIDES], start=1)}
    sections = {i: ns for i, ns in sections.items() if ns}
    if not sections:
        return {}
    fallback = {i: fallback_guide(plan[i - 1].title, ns) for i, ns in sections.items()}
    try:
        _require_openrouter()
        listing = {"sections": [{"section": i, "title": plan[i - 1].title, "skills": ns} for i, ns in sections.items()],
                   "existing_titles": [e["title"] for e in list(existing.values())[:MAX_EXISTING]]}
        messages = [{"role": "system", "content": GUIDE_PROMPT}, {"role": "user", "content": f"Role: {role_title}\n\n{json.dumps(listing)}"}]
        written = _chat_json(messages, lambda raw: sanitize_guides(raw, list(sections)), "AI skill list", reasoning=GUIDE_REASONING, max_tokens=GUIDE_MAX_TOKENS)
    except HTTPException as e:
        print(f"AI skills fell back ({e.detail})")
        written = {}
    out: dict[int, dict] = {}
    taken: set[str] = set()
    for i in sections:
        g = {**fallback[i], **written.get(i, {})}
        if norm_title(g["title"]) in taken:  # two sections with one title: the second is told apart by its number
            g["title"] = f"{g['title'][:36]} {i}"
        taken.add(norm_title(g["title"]))
        old = existing.get(norm_title(g["title"]))
        if old:
            g = {**g, "description": old["description"], "steps": old["steps"], "sources": old.get("sources") or []}
        out[i] = {**g, "skill_id": ai_skill_id(onet_code, g["title"])}
    return out


def with_guides(plan: Plan, guides: dict[int, dict]) -> Plan:
    """The plan with each guided section's AI skill as the first node of its first unit, and a required prerequisite of every other
    node in that unit. So the section's skills stay locked until it is done and, since a unit opens only when the one before it
    is finished, so does everything after them."""
    out: Plan = []
    for number, sec in enumerate(plan, start=1):
        if number not in guides or not sec.units:
            out.append(sec)
            continue
        gid = guides[number]["skill_id"]
        first = [PlanNode(n.skill_id, [gid, *n.previous_nodes], True) for n in sec.units[0]]
        out.append(PlanSection(sec.title, [[PlanNode(gid, [], True), *first], *sec.units[1:]]))
    return out
