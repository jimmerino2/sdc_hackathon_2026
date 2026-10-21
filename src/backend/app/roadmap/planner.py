"""Turns a role's skills into a roadmap plan (sections -> units -> nodes with prerequisites) using an LLM."""
import json
import re
from dataclasses import dataclass, field

from fastapi import HTTPException
from openai import OpenAI

from app.config import get_settings

MAX_OUTPUT_TOKENS = 12000  # a 50-node plan is ~4k tokens; the rest is headroom for model reasoning
MIN_IMPORTANCE = 2.0  # candidates must be strictly above this; the model then trims further

SYSTEM_PROMPT = """You design learning roadmaps. Given a job role and its candidate skills, produce a roadmap a person can follow to prepare for the role.

Each candidate skill has: id, name, type (skill = general ability, knowledge = subject area, tech = software/tool), importance (1-5, how much the role needs it) and level (0-7, how deep; null for tech).

Do this in order:
1. Re-evaluate which skills to keep. Drop near-duplicates, skills too generic to be worth a dedicated step, and low-value tools. A focused roadmap is better than an exhaustive one (aim for 25-35 skills, never more than 35, fewer if the role has fewer worthwhile ones). Keep high-importance skills.
2. Group the kept skills into 3 or 4 sections, ordered as stages (e.g. foundations -> core knowledge -> applied skills and tools -> advanced), and each section into units (small themed groups of 3-6 skills). Use level and importance to place basics before advanced material.
3. For each skill, list previous_nodes: ids of kept skills that should be learned before it. Only list a real dependency, not everything earlier. previous_nodes may only reference skills placed in an earlier unit/section or earlier in the same unit.
4. Set previous_nodes_required to true if the previous nodes must be completed first, false if they are only recommended.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{"sections":[{"units":[{"nodes":[{"skill_id":"<id>","previous_nodes":["<id>"],"previous_nodes_required":true}]}]}]}
Use only ids from the candidate list. Each skill may appear at most once. Hard limit: 35 skills in total."""


@dataclass
class PlanNode:
    skill_id: str
    previous_nodes: list[str] = field(default_factory=list)
    previous_nodes_required: bool = True


# plan[section_index][unit_index] -> nodes, in learning order
Plan = list[list[list[PlanNode]]]


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
    """Keep only what is safe to store: known ids, each once, prerequisites that point strictly backwards.

    Dropping a bad prerequisite is safe (the node just has fewer constraints); a backwards-only rule
    also guarantees the dependency graph has no cycles. Empty units and sections are removed.
    """
    seen: set[str] = set()
    plan: Plan = []
    for sec in raw.get("sections", []):
        units: list[list[PlanNode]] = []
        for unit in sec.get("units", []):
            nodes: list[PlanNode] = []
            for n in unit.get("nodes", []):
                sid = n.get("skill_id") if isinstance(n, dict) else None
                if sid not in valid_ids or sid in seen:
                    continue
                prev = n.get("previous_nodes") or []
                prev = list(dict.fromkeys(p for p in prev if p in seen))  # already placed => strictly earlier
                nodes.append(PlanNode(sid, prev, bool(n.get("previous_nodes_required", True)) or not prev))  # nothing to require
                seen.add(sid)
            if nodes:
                units.append(nodes)
        if units:
            plan.append(units)
    if not plan:
        raise ValueError("plan has no usable nodes")
    return plan


def _complete(messages: list[dict]) -> str:
    settings = get_settings()
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)
    # OpenRouter-specific parameter; other gateways may not accept it
    reasoning = {"off": {"enabled": False}, "low": {"effort": "low"}}.get(settings.roadmap_reasoning)
    extra = {"reasoning": reasoning} if reasoning and "openrouter.ai" in settings.openrouter_base_url else None
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
        {"id": s["skill_id"], "name": s["skill_name"], "type": s["skill_type"], "importance": s["importance"], "level": s["level"]}
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
