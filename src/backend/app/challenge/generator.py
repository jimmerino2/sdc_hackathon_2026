"""Writes a challenge with an LLM: stage 1, a project built from a role's foundational skills (a roadmap's first
sections, or the role's own skills) and themed on one of the learner's SDGs through their interests; and stage 2,
Robbee's harder rewrite of that same project once stage 1 is passed. Each comes with a weighted rubric to judge it by."""
import json
from dataclasses import dataclass

from app.challenge.model import ask
from app.interests.schemas import Interest
from app.interests.sdg import SDG_NAMES
from app.roadmap.planner import _extract_json

MAX_OUTPUT_TOKENS = 8000  # a challenge is ~800 tokens; the rest is headroom for reasoning
MIN_CRITERIA, MAX_CRITERIA = 3, 6
MAX_TITLE, MAX_DESCRIPTION, MAX_CRITERION, MAX_CRITERION_DESCRIPTION, MAX_TWIST = 120, 1600, 80, 400, 200
MAX_STACK = {1: 4, 2: 6}  # roadmap skills per stage: stage 1 stays small, stage 2 may grow
MAX_SUPPORTING, MAX_TOOL = 2, 40  # tools off the roadmap the project may need, e.g. PowerShell for a Windows-admin script

# profiles.stage, in words the model can pitch a project at
STAGES = {
    "under": "an undergraduate student, new to building projects",
    "fresh": "a fresh graduate building a first portfolio",
    "working": "a working adult switching careers, a beginner at coding",
}

STACK_RULES = """Build it mainly from the given skills. When skills are alternatives for the same job (the same group, e.g. React and Vue.js, or two databases), pick only one. Leave out generic abilities and anything that cannot show in code (browsers, chat apps). When the skills are tools rather than languages (office suites, operating systems, directory or ticketing products), make a project that automates, extends or works with those tools (scripts, a small web tool, an import/export or reporting pipeline) and list them in the stack. If the project needs a language or framework that is not among the skills, name at most 2 in supporting_tools (common ones such as Python, PowerShell, HTML/CSS/JavaScript); otherwise leave it empty. Group the chosen skills into areas such as Frontend, Backend, Database, Data analysis, Machine learning, Automation, Security, Testing, Tooling."""

RUBRIC_RULES = """Rubric: 4 criteria (5 at most), each judgeable from the repository's code and README alone, with integer weights adding up to 100. Always include one criterion on how well the project serves the chosen goal and one on how well it uses the stack. Each description says what earns a high score."""

STAGE1_PROMPT = f"""You design a portfolio project (a "Challenge") for someone learning towards a tech role. It rewards finishing the first part of a learning roadmap and gives them a reason to build something real instead of only ticking skills off.

You get the role, who the learner is (learner_stage), the learner's interests (each tied to UN Sustainable Development Goals), the learner's goals with how strongly their interests point at each, the foundational skills the challenge covers, and the titles of challenges the learner already has for this role (avoid).

Write ONE project, clearly different from every project in avoid (a different problem or different people helped, not a renamed copy):
1. Deliverable: ALWAYS a code repository, judged only from its files. Never a spreadsheet, a document, slides or a configured third-party product (a ServiceNow instance, an Excel workbook).
2. Stack: a small, coherent stack a beginner could actually build, at most 4 of the skills. {STACK_RULES}
3. Purpose: the project must tackle a concrete problem for one of the learner's goals (prefer goals with a higher share), seen through one or more of their interests. What the app itself does must serve that goal for real people (who it helps and how, said in the description); the learner gaining skills or a job does not count.
4. Scope: keep it SIMPLE: a beginner at the learner's stage should finish it in a weekend, following tutorials where needed. One small app, script or notebook with one core job; no authentication, deployment, microservices, real-time features or machine learning unless the skills are about exactly that. The description is 2-3 plain-language sentences on what to build and why, then exactly 3 key features as lines starting with "- ".
5. {RUBRIC_RULES} A working, readable project that does what the brief asks should score well.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{{"title":"...","description":"Two or three sentences.\\n- feature one\\n- feature two\\n- feature three","sdg":3,"interest_ids":[5],"tech_stack":[{{"area":"Frontend","skill_ids":["<id>"]}}],"supporting_tools":[],"rubric":[{{"criterion":"...","description":"...","weight":30}}]}}
Use only skill ids, sdg numbers and interest ids from the input."""

STAGE2_PROMPT = f"""You are Robbee, the Hornet Foreman: a demanding manager who rewrites a learner's project brief right after they pass it. The learner just built the stage 1 project below and scored well. Now the client has changed their mind, and you write the stage 2 brief: the SAME project (same purpose, same goal, same people it helps), but clearly HARDER.

You get the role, who the learner is, the stage 1 brief with its stack and rubric, what the judge said about their submission, the role's more advanced skills (new_skills) and the foundational skills stage 1 drew on (earlier_skills).

Write the stage 2 project:
1. Deliverable: still a code repository, judged only from its files. It may extend the stage 1 repo or be a rebuild.
2. Harder, and it MUST be: do at least two of these: swap part of the stack for new_skills (e.g. "rebuild the frontend in React", "move the data into PostgreSQL"); widen the scope with 2 more substantial features; raise the bar on quality (validation, error handling, tests, structure). Prefer new_skills where they fit; you may also reuse earlier_skills. At most 6 roadmap skills. {STACK_RULES}
   AI feature (required, this is round 2's theme): one of the added features MUST be an AI-assisted one that calls a hosted language-model API (for example summarising, classifying, answering questions or suggesting next steps), chosen to help the same people the project already serves. Name the API client in supporting_tools. Use the API, do not train a model. The code reads its key from an environment variable, never commits one, and still runs sensibly without it (a clear message or a plain fallback), because the judge reads the code only. Treat the model's output as unchecked: validate or label it, and show it as a suggestion.
3. Still achievable: a motivated learner at their stage should finish it in one to two weeks. Don't pile on deployment, authentication or microservices unless the new skills are about exactly that.
4. The description is 2-3 sentences on what changed and why the client wants it, then 4-5 key features as lines starting with "- ".
5. twist: ONE short line (under 20 words) in Robbee's voice saying what changed, and it must name the AI feature, e.g. "Rebuild the site with React and add an AI assistant that suggests appointment times."
6. {RUBRIC_RULES} The criteria are stricter than stage 1's: a high score needs the new stack used properly and the added features working, not just the stage 1 project again. One criterion judges the AI feature: a real model call, a key kept out of the code, a fallback without it, and the output checked or labelled before it is shown.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{{"title":"...","twist":"...","description":"Two or three sentences.\\n- feature one\\n- feature two\\n- feature three\\n- feature four","tech_stack":[{{"area":"Frontend","skill_ids":["<id>"]}}],"supporting_tools":[],"rubric":[{{"criterion":"...","description":"...","weight":30}}]}}
Use only skill ids from the input. Keep the stage 1 title's subject recognisable (it may gain a word or two)."""


@dataclass(frozen=True)
class Skill:
    """A skill a challenge may use: a roadmap node's, or one of the role's onet_role_skills."""

    skill_id: str
    skill_name: str
    skill_type: str
    skill_group: str | None
    importance: float | None
    level: float | None


def _skill(n: Skill) -> dict:
    return {"id": n.skill_id, "name": n.skill_name, "type": n.skill_type, "group": n.skill_group, "importance": n.importance}


def _weights(raw: list[float]) -> list[int]:
    """Integer weights proportional to raw that add up to exactly 100 (largest remainder)."""
    total = sum(raw)
    exact = [w * 100 / total for w in raw] if total > 0 else [100 / len(raw)] * len(raw)
    out = [int(x) for x in exact]
    for i in sorted(range(len(raw)), key=lambda i: exact[i] - out[i], reverse=True)[: 100 - sum(out)]:
        out[i] += 1
    return out


def _line(value, limit: int) -> str:
    """One line of model text, whitespace collapsed, cut to limit."""
    return " ".join(str(value or "").split())[:limit]


def _block(value, limit: int) -> str:
    """Model text that may keep its line breaks (the brief's "- " feature lines), cut to limit."""
    lines = (" ".join(line.split()) for line in str(value or "").splitlines())
    return "\n".join(line for line in lines if line)[:limit]


def stage_sections(sections: list[int]) -> tuple[list[int], list[int]]:
    """(stage 1's sections, stage 2's) of a roadmap: stage 1 takes sections 1-2, stage 2 the rest. A roadmap with no
    sections after 2 gives stage 2 all of them, so it is harder in scope instead of in new skills."""
    ordered = sorted(sections)
    first, rest = ordered[:2], ordered[2:]
    return first, rest or ordered


FOUNDATION_SHARE = 0.5  # without a roadmap, the lower-level half of a role's skills is stage 1's
MAX_ROLE_SKILLS = 30    # the role's most important skills considered, so the prompt stays small


def role_split(skills: list[Skill]) -> tuple[list[Skill], list[Skill]]:
    """(stage 1's skills, stage 2's new skills) for a challenge with no roadmap: the role's most important skills,
    split by level so stage 1 gets the foundational half and stage 2 the more advanced rest."""
    top = sorted(skills, key=lambda s: -(s.importance or 0))[:MAX_ROLE_SKILLS]
    by_level = sorted(top, key=lambda s: (s.level or 0, -(s.importance or 0)))
    cut = max(1, round(len(by_level) * FOUNDATION_SHARE))
    return by_level[:cut], by_level[cut:] or by_level


def sanitize(c, stage: int, nodes: dict[str, Skill], allowed: set[str], allowed_sdgs: list[int], interest_ids: set[int]) -> dict | None:
    """The challenge if it is safe to store: skills from allowed (the roadmap skills this stage may use), a goal the
    learner has, the learner's interests, and a rubric whose weights add up to 100. None if it has no usable skills,
    too few criteria or no title or brief."""
    if not isinstance(c, dict):
        return None
    title, description = _line(c.get("title"), MAX_TITLE), _block(c.get("description"), MAX_DESCRIPTION)
    if not title or not description:
        return None

    seen: set[str] = set()
    stack = []
    for area in c.get("tech_stack") or []:
        if not isinstance(area, dict):
            continue
        ids = []
        for s in area.get("skill_ids") or []:
            if len(seen) < MAX_STACK[stage] and isinstance(s, str) and s in allowed and s not in seen:
                ids.append(s)
                seen.add(s)
        if ids:
            stack.append({"area": _line(area.get("area"), 40) or "Stack", "skills": [nodes[s].skill_name for s in ids], "ids": ids})
    if not stack:
        return None
    # A supporting tool that is a roadmap skill after all (e.g. JavaScript from an earlier section) is kept as that skill.
    by_name = {nodes[sid].skill_name.lower(): sid for sid in allowed}
    tools = [t for t in dict.fromkeys(_line(t, MAX_TOOL) for t in c.get("supporting_tools") or []) if t][:MAX_SUPPORTING]
    known = [by_name[t.lower()] for t in tools if t.lower() in by_name and by_name[t.lower()] not in seen]
    seen.update(known)
    tools = [nodes[sid].skill_name for sid in known] + [t for t in tools if t.lower() not in by_name]
    if tools:
        stack.append({"area": "Supporting", "skills": tools, "ids": known})

    rubric = [r for r in c.get("rubric") or [] if isinstance(r, dict) and _line(r.get("criterion"), MAX_CRITERION)][:MAX_CRITERIA]
    if len(rubric) < MIN_CRITERIA:
        return None
    raw_weights = []
    for r in rubric:
        try:
            raw_weights.append(max(float(r.get("weight") or 0), 0.0))
        except (TypeError, ValueError):
            raw_weights.append(0.0)

    try:
        sdg = int(c.get("sdg"))
    except (TypeError, ValueError):
        sdg = 0
    picked = []
    for i in c.get("interest_ids") or []:
        try:
            picked.append(int(i))
        except (TypeError, ValueError):
            pass

    return {
        "title": title,
        "description": description,
        "twist": _line(c.get("twist"), MAX_TWIST) or None,
        "sdg": sdg if sdg in allowed_sdgs else allowed_sdgs[0],
        "interest_ids": [i for i in dict.fromkeys(picked) if i in interest_ids],
        "tech_stack": [{"area": a["area"], "skills": a["skills"]} for a in stack],
        "skill_ids": [s for a in stack for s in a["ids"]],
        "rubric": [
            {"key": f"c{k}", "criterion": _line(r.get("criterion"), MAX_CRITERION),
             "description": _line(r.get("description"), MAX_CRITERION_DESCRIPTION), "weight": w}
            for k, (r, w) in enumerate(zip(rubric, _weights(raw_weights)), start=1)
        ],
    }


def _ask_for(messages: list[dict], check) -> dict | None:
    """The model's challenge, checked by check(raw) -> dict | None, with one retry when it is unusable."""
    for _ in range(2):
        reply = ask(messages, MAX_OUTPUT_TOKENS)
        try:
            got = check(_extract_json(reply))
            problem = None if got else "the challenge was missing a title, brief, usable skills or 3+ rubric criteria"
        except (ValueError, AttributeError) as e:
            got, problem = None, str(e)
        if got:
            return got
        messages = messages + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": f"That reply was not usable ({problem}). Reply again with only the JSON object, in the required shape."},
        ]
    return None


def write_stage1(role_title: str, role_description: str | None, stage: str, interests: list[Interest], goals: list[tuple[int, float]],
                 skills: list[Skill], avoid: list[str]) -> dict | None:
    """Stage 1 over these skills, pitched at the learner's stage (profiles.stage) and unlike the projects titled in
    avoid; None if the model gets it wrong twice. goals is (sdg, share), biggest first; the challenge's goal is always
    one of them."""
    nodes = {n.skill_id: n for n in skills}
    payload = {
        "role": role_title,
        "role_description": role_description or "",
        "learner_stage": STAGES.get(stage, STAGES["fresh"]),
        "learner_interests": [{"id": i.id, "interest": i.interest, "description": i.description, "sdgs": [w.sdg for w in i.sdg]} for i in interests],
        "learner_goals": [{"sdg": g, "name": SDG_NAMES[g], "share": round(v, 2)} for g, v in goals],
        "skills": [_skill(n) for n in nodes.values()],
        "avoid": avoid,
    }
    messages = [{"role": "system", "content": STAGE1_PROMPT}, {"role": "user", "content": json.dumps(payload)}]
    allowed_sdgs, interest_ids = [g for g, _ in goals], {i.id for i in interests}
    got = _ask_for(messages, lambda raw: sanitize(raw, 1, nodes, set(nodes), allowed_sdgs, interest_ids))
    return {**got, "twist": None} if got else None


def write_stage2(role_title: str, stage: str, current: dict, new: list[Skill], earlier: list[Skill]) -> dict | None:
    """Robbee's harder rewrite of the passed stage 1 (current is its roadmap_challenge row), drawing on the new,
    more advanced skills and the earlier ones. It keeps stage 1's goal and interests. None if the model gets it wrong
    twice."""
    nodes = {n.skill_id: n for n in [*earlier, *new]}
    payload = {
        "role": role_title,
        "learner_stage": STAGES.get(stage, STAGES["fresh"]),
        "stage1": {
            "title": current["title"],
            "description": current["description"],
            "goal": f"SDG {current['sdg']}: {SDG_NAMES[current['sdg']]}",
            "tech_stack": current["tech_stack"],
            "rubric": current["rubric"],
            "judge_summary": current.get("summary") or "",
            "score": current.get("score"),
        },
        "new_skills": [_skill(n) for n in new],
        "earlier_skills": [_skill(n) for n in earlier if n.skill_id not in {s.skill_id for s in new}],
    }
    messages = [{"role": "system", "content": STAGE2_PROMPT}, {"role": "user", "content": json.dumps(payload)}]
    got = _ask_for(messages, lambda raw: sanitize(raw, 2, nodes, set(nodes), [current["sdg"]], set(current["interest_ids"])))
    if not got:
        return None
    return {**got, "sdg": current["sdg"], "interest_ids": current["interest_ids"],
            "twist": got["twist"] or "The client changed the brief. Build the bigger version."}
