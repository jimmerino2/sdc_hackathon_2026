"""Turns a role's skills into a roadmap plan (sections -> units -> nodes with prerequisites) using an LLM."""
import json
import re
from dataclasses import dataclass, field

from fastapi import HTTPException
from openai import OpenAI

from app.config import get_settings

MAX_OUTPUT_TOKENS = 12000  # a 50-node plan is ~4k tokens; the rest is headroom for model reasoning
MIN_IMPORTANCE = 2.25  # candidates must be strictly above this; the model then trims further
MAX_SKILLS = 40  # the previous cap (35) plus 5, so the model has room to also act on forecast_demand

SYSTEM_PROMPT = f"""You design learning roadmaps. Given a job role and its candidate skills, produce a roadmap a person can follow to prepare for the role.

Each candidate skill has: id, name, type (skill = general ability, knowledge = subject area, tech = software/tool), importance (1-5, how much O*NET says the role needs it), level (0-7, how deep; null for tech) and forecast_demand (0-1, the share of current US job ads for this role that name the skill, 6 months out; null when it isn't tracked, which is most skills - treat null as no signal either way, not as low demand).

Do this in order:
1. Re-evaluate which skills to keep. Drop near-duplicates, skills too generic to be worth a dedicated step, and low-value tools. A focused roadmap is better than an exhaustive one (aim for 25-{MAX_SKILLS} skills, never more than {MAX_SKILLS}, fewer if the role has fewer worthwhile ones). Weigh forecast_demand heavily, not just as a tie-breaker: it is live evidence from current job ads, so a skill with meaningfully positive forecast_demand (say, above 0.05) should almost always be kept and should usually outrank a similar-importance skill with no forecast_demand data, even if that means cutting a slightly-higher-importance skill that forecast_demand doesn't cover. Importance stays the primary signal only when forecast_demand is null (most skills) or negligible.
2. Group the kept skills into sections by real subject-matter coherence, not a fixed stage template - never sort skills into generic buckets like "foundations" / "core" / "applied" / "advanced" by skill type alone (that produces nonsense, e.g. a general-purpose language stranded alone in an early section while the specific stack the role actually uses sits three sections later). Instead, look at what the skills are actually for and group skills that are learned and used together (e.g. all of a web stack in one section, all of a cloud/deployment toolchain in another), choosing whatever number of sections (3 or more) and whatever order genuinely fits this role and this exact skill set - order sections so that a section's skills don't depend on a later section's, but otherwise structure it freely around the role's real shape, not a template. Give every section a short title (2-5 words) naming what it covers (e.g. "Web Fundamentals", "Cloud & Deployment", "Data Pipelines") - never a generic label like "Foundations" or "Section 1". Split each section into units (small themed groups of 3-6 skills); use level and importance to place basics before advanced material within a section.
3. For each skill, list previous_nodes: ids of kept skills that should be learned before it. Only list a real dependency, not everything earlier. previous_nodes may ONLY reference another skill placed earlier in the very same unit - never a skill in an earlier unit or section, even when a real dependency exists. The roadmap only draws a dependency line within a unit, so a cross-unit prerequisite would be silently invisible; if a skill genuinely depends on something from an earlier unit or section, either place them in the same unit instead, or drop the link and rely on section/unit order alone.
4. Set previous_nodes_required to true if the previous nodes must be completed first, false if they are only recommended.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{{"sections":[{{"title":"<short section title>","units":[{{"nodes":[{{"skill_id":"<id>","previous_nodes":["<id>"],"previous_nodes_required":true}}]}}]}}]}}
Use only ids from the candidate list. Each skill may appear at most once. Hard limit: {MAX_SKILLS} skills in total."""


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
        model=settings.openrouter_model, messages=messages, max_tokens=MAX_OUTPUT_TOKENS, extra_body=extra
    )
    return res.choices[0].message.content


def build_plan(role_title: str, role_description: str | None, skills: list[dict]) -> Plan:
    if get_settings().ai_model_mode == "OPENROUTER":
        return _plan_with_openrouter(role_title, role_description, skills)
    raise HTTPException(status_code=503, detail=f"unsupported AI_MODEL_MODE {get_settings().ai_model_mode!r}")


def _plan_with_openrouter(role_title: str, role_description: str | None, skills: list[dict]) -> Plan:
    if not get_settings().openrouter_api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not set")
    listing = [
        {"id": s["skill_id"], "name": s["skill_name"], "type": s["skill_type"], "importance": s["importance"], "level": s["level"],
         "forecast_demand": s.get("forecast_demand")}
        for s in skills
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Role: {role_title}\n{role_description or ''}\n\nCandidate skills:\n{json.dumps(listing)}"},
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
