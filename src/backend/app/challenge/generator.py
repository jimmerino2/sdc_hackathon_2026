"""Writes a roadmap's Bonus Quests with an LLM: for each group of sections, a project built from their skills and
themed on one of the learner's SDGs through their interests, with a weighted rubric to judge it by."""
import json

from app.challenge.model import ask
from app.interests.schemas import Interest
from app.interests.sdg import SDG_NAMES
from app.roadmap.planner import _extract_json
from app.roadmap.schemas import Node

MAX_OUTPUT_TOKENS = 8000  # two challenges are ~1.5k tokens; the rest is headroom for reasoning
MIN_CRITERIA, MAX_CRITERIA = 3, 6
MAX_TITLE, MAX_DESCRIPTION, MAX_CRITERION, MAX_CRITERION_DESCRIPTION = 120, 1600, 80, 400
MAX_STACK = 4  # roadmap skills per challenge: small projects, not everything the sections taught
MAX_SUPPORTING, MAX_TOOL = 2, 40  # tools off the roadmap the project may need, e.g. PowerShell for a Windows-admin script

# profiles.stage, in words the model can pitch a project at
STAGES = {
    "under": "an undergraduate student, new to building projects",
    "fresh": "a fresh graduate building a first portfolio",
    "working": "a working adult switching careers, a beginner at coding",
}

SYSTEM_PROMPT = """You design optional portfolio projects ("Bonus Quests") for someone learning towards a tech role. They are a reward for finishing part of a learning roadmap and a reason to build something real instead of only ticking skills off.

You get the role, who the learner is (learner_stage), the learner's interests (each tied to UN Sustainable Development Goals), the learner's goals with how strongly their interests point at each, and a list of challenges_needed. Each needed challenge names the roadmap sections it covers, the skills of those sections, and earlier_skills learned before them.

For each needed challenge write ONE project:
1. Deliverable: ALWAYS a code repository, judged only from its files. Never a spreadsheet, a document, slides or a configured third-party product (a ServiceNow instance, an Excel workbook).
2. Stack: build it mainly from that challenge's skills. Choose a small, coherent stack a beginner could actually build, at most 4 of the skills: when skills are alternatives for the same job (the same group, e.g. React and Vue.js, or two databases), pick only one. Leave out generic abilities and anything that cannot show in code (browsers, chat apps). When the sections teach tools rather than languages (office suites, operating systems, directory or ticketing products), make a project that automates, extends or works with those tools (scripts, a small web tool, an import/export or reporting pipeline) and list them in the stack. Add an earlier skill only when the stack needs it (e.g. the language a framework runs on). If the project needs a language or framework that is not among the skills, name at most 2 in supporting_tools (common ones such as Python, PowerShell, HTML/CSS/JavaScript); otherwise leave it empty. Group the chosen skills into areas such as Frontend, Backend, Database, Data analysis, Machine learning, Automation, Security, Testing, Tooling.
3. Purpose: the project must tackle a concrete problem for one of the learner's goals (prefer goals with a higher share), seen through one or more of their interests. What the app itself does must serve that goal for real people (who it helps and how, said in the description); the learner gaining skills or a job does not count.
4. Scope: keep it SIMPLE. These are encouragement, not exams: a beginner at the learner's stage should finish it in a weekend, following tutorials where needed. One small app, script or notebook with one core job; no authentication, deployment, microservices, real-time features or machine learning unless the sections are about exactly that. The description is 2-3 plain-language sentences on what to build and why, then exactly 3 key features as lines starting with "- ".
5. Rubric: 4 criteria (5 at most), each judgeable from the repository's code and README alone, with integer weights adding up to 100. Always include one criterion on how well the project serves the chosen goal and one on how well it uses the stack. Each description says what earns a high score, in terms a beginner can meet: a working, readable project that does what the brief asks should score well.
6. Different challenges must be different projects, and a later one may build on the earlier one's stack.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{"challenges":[{"sections":[1,2],"title":"...","description":"Two or three sentences.\\n- feature one\\n- feature two\\n- feature three","sdg":3,"interest_ids":[5],"tech_stack":[{"area":"Frontend","skill_ids":["<id>"]}],"supporting_tools":[],"rubric":[{"criterion":"...","description":"...","weight":30}]}]}
Use only skill ids, sdg numbers and interest ids from the input. "sections" must match a needed challenge exactly."""


def _skill(n: Node) -> dict:
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


def sanitize(raw: dict, groups: list[list[int]], nodes: dict[str, Node], section_of: dict[str, int], allowed_sdgs: list[int], interest_ids: set[int]) -> list[dict]:
    """Keep only challenges that are safe to store: one per needed group, skills that sit in or before that group's
    sections, a goal the learner has, the learner's interests, and a rubric whose weights add up to 100.
    A challenge with no usable skills or too few criteria is dropped."""
    wanted = {tuple(g) for g in groups}
    out: dict[tuple, dict] = {}
    for c in raw.get("challenges") or []:
        if not isinstance(c, dict):
            continue
        try:
            sections = tuple(sorted(int(s) for s in c.get("sections") or []))
        except (TypeError, ValueError):
            continue
        if sections not in wanted or sections in out:
            continue
        title, description = _line(c.get("title"), MAX_TITLE), _block(c.get("description"), MAX_DESCRIPTION)
        if not title or not description:
            continue

        last = sections[-1]
        seen: set[str] = set()
        stack = []
        for area in c.get("tech_stack") or []:
            if not isinstance(area, dict):
                continue
            ids = []
            for s in area.get("skill_ids") or []:
                if len(seen) < MAX_STACK and isinstance(s, str) and s in nodes and s not in seen and section_of[s] <= last:
                    ids.append(s)
                    seen.add(s)
            if ids:
                stack.append({"area": _line(area.get("area"), 40) or "Stack", "skills": [nodes[s].skill_name for s in ids], "ids": ids})
        if not stack:
            continue
        # A supporting tool that is a roadmap skill after all (e.g. JavaScript from an earlier section) is kept as that skill.
        by_name = {n.skill_name.lower(): sid for sid, n in nodes.items() if section_of[sid] <= last}
        tools = [t for t in dict.fromkeys(_line(t, MAX_TOOL) for t in c.get("supporting_tools") or []) if t][:MAX_SUPPORTING]
        known = [by_name[t.lower()] for t in tools if t.lower() in by_name and by_name[t.lower()] not in seen]
        seen.update(known)
        tools = [nodes[sid].skill_name for sid in known] + [t for t in tools if t.lower() not in by_name]
        if tools:
            stack.append({"area": "Supporting", "skills": tools, "ids": known})

        rubric = [r for r in c.get("rubric") or [] if isinstance(r, dict) and _line(r.get("criterion"), MAX_CRITERION)][:MAX_CRITERIA]
        if len(rubric) < MIN_CRITERIA:
            continue
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

        out[sections] = {
            "sections": list(sections),
            "title": title,
            "description": description,
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
    return [out[tuple(g)] for g in groups if tuple(g) in out]


def write(role_title: str, role_description: str | None, stage: str, interests: list[Interest], goals: list[tuple[int, float]],
          groups: list[list[int]], by_section: dict[int, list[Node]]) -> list[dict]:
    """One challenge per group of sections (fewer if the model gets some wrong twice), pitched at the learner's stage
    (profiles.stage). goals is (sdg, share), biggest first; the challenge's goal is always one of them."""
    nodes = {n.skill_id: n for ns in by_section.values() for n in ns}
    section_of = {n.skill_id: s for s, ns in by_section.items() for n in ns}
    needed = [
        {
            "sections": g,
            "skills": [_skill(n) for s in g for n in by_section.get(s, [])],
            "earlier_skills": [_skill(n) for s in sorted(by_section) if s < g[0] for n in by_section[s]],
        }
        for g in groups
    ]
    payload = {
        "role": role_title,
        "role_description": role_description or "",
        "learner_stage": STAGES.get(stage, STAGES["fresh"]),
        "learner_interests": [{"id": i.id, "interest": i.interest, "description": i.description, "sdgs": [w.sdg for w in i.sdg]} for i in interests],
        "learner_goals": [{"sdg": g, "name": SDG_NAMES[g], "share": round(v, 2)} for g, v in goals],
        "challenges_needed": needed,
    }
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(payload)}]
    allowed = [g for g, _ in goals]
    interest_ids = {i.id for i in interests}

    best: list[dict] = []
    for _ in range(2):  # one retry when a challenge is missing or the reply is unusable
        reply = ask(messages, MAX_OUTPUT_TOKENS)
        try:
            got = sanitize(_extract_json(reply), groups, nodes, section_of, allowed, interest_ids)
            problem = None if len(got) == len(groups) else f"only {len(got)} of {len(groups)} challenges were usable"
        except (ValueError, AttributeError) as e:
            got, problem = [], str(e)
        if len(got) > len(best):
            best = got
        if not problem:
            break
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": f"That reply was not fully usable ({problem}). Reply again with only the JSON object, one challenge per needed challenge, in the required shape."},
        ]
    return best
