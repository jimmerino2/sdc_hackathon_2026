import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.forecast import service as forecast
from app.interests.schemas import Interest
from app.interests.sdg import SDG_NAMES
from app.interests.service import sdg_focus as focus_of
from app.jobs import scoring
from app.occupational import service as occupational
from app.jobs.schemas import ContextRole, Engine, JobMatch, MatchBreakdown, MatchParts, RecommendRequest, RecommendResponse, ScenarioOutlook, SdgReason, SkillFit
from app.supabase import get_client

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
TOP_JOBS = 10
DEFAULT_ICON = "briefcase"
KEY_TOOLS = 6  # a role's key skills: this many tools ...
KEY_ABILITIES = 4  # ... plus this many abilities (O*NET skill_type "skill", e.g. Programming, Critical Thinking)
# Only tech roles are matched for now.
TECH_ROLES = {
    "15-1211.00",  # Computer Systems Analysts
    "15-1212.00",  # Information Security Analysts
    "15-1232.00",  # Computer User Support Specialists
    "15-1252.00",  # Software Developers
    "15-1255.00",  # Web and Digital Interface Designers
    "15-2031.00",  # Operations Research Analysts
    "15-2051.00",  # Data Scientists
    "15-2051.01",  # Business Intelligence Analysts
}
# Non-tech roles shown for contrast on the demand-vs-AI chart, so its "at risk" and "stable" corners aren't empty.
CONTEXT_ROLES = [
    "43-3031.00",  # Bookkeeping, Accounting, and Auditing Clerks
    "43-4051.00",  # Customer Service Representatives
    "43-9021.00",  # Data Entry Keyers
    "29-1141.00",  # Registered Nurses
]
# Close equivalents, so a key skill counts as owned when the candidate has a near match.
# Each family: having any one counts for all the others.
FAMILIES = [
    {"Structured query language SQL", "PostgreSQL", "MySQL", "Microsoft SQL Server", "Transact-SQL", "Oracle PL/SQL"},
    {"Git", "GitHub", "GitLab"},
    {"Linux", "UNIX"},
    {"Amazon Web Services AWS software", "Amazon Elastic Compute Cloud EC2", "Microsoft Azure software"},
]
# One way: having the key counts for each skill in its list (React implies JavaScript, not the reverse).
IMPLIES = {
    **{lang: ["Programming"] for lang in [
        "Python", "Oracle Java", "JavaScript", "TypeScript", "C", "C++", "Go", "R", "Ruby", "PHP", "Scala", "Swift", "Perl",
    ]},
    **{fw: ["JavaScript", "Programming"] for fw in ["React", "Node.js", "Google Angular", "Vue.js", "TypeScript"]},
    **{lib: ["Python", "Programming"] for lib in ["pandas", "NumPy", "Django", "TensorFlow", "PyTorch"]},
    "Spring Framework": ["Oracle Java", "Programming"],
}
HORIZON = 12
SCENARIOS = [("Rapid AI", "AI accelerates"), ("Baseline", "AI holds steady"), ("Slow", "AI slows down")]
HEADLINE = "Rapid AI"  # the scenario behind JobMatch.match_percent and the order of the roles
NOTE = ("Match combines your skills (33%), the role's outlook under the chosen AI future (33%), your interests (24%) and your "
        "career stage (10%). It helps you compare roles and doesn't predict your chances of being hired. Posting change is the sector trend carried over to the role (US data stands in for Malaysia) "
        "and is indicative, not a precise prediction.")


@lru_cache
def _roles() -> list[dict]:
    """Every tech role with its tools and abilities (most important first), read once.

    O*NET rates nearly every tool 4.0 or 3.5, so ties are broken by how many tech roles list the tool:
    widely used tools (Python, SQL, Git) come before niche ones.
    """
    roles = pd.read_csv(DATA_DIR / "onet_roles.csv")
    roles = roles[roles["onet_code"].isin(TECH_ROLES)]
    skills = pd.read_csv(DATA_DIR / "onet_role_skills.csv").dropna(subset=["skill_name", "importance"])
    skills = skills[skills["onet_code"].isin(TECH_ROLES)].drop_duplicates(["onet_code", "skill_name"])
    spread = skills.groupby("skill_name")["onet_code"].nunique()
    out = []
    for code, title in zip(roles["onet_code"], roles["title"]):
        mine = skills[skills["onet_code"] == code].assign(spread=lambda d: d["skill_name"].map(spread))
        ranked = mine.sort_values(["importance", "spread", "skill_name"], ascending=[False, False, True])
        out.append({
            "onet_code": code, "title": title,
            "tools": list(zip(*[ranked[ranked["skill_type"] == "tech"][c] for c in ("skill_name", "importance")])),
            "abilities": list(zip(*[ranked[ranked["skill_type"] == "skill"][c] for c in ("skill_name", "importance")])),
            "knowledge": list(zip(*[ranked[ranked["skill_type"] == "knowledge"][c] for c in ("skill_name", "importance")])),
        })
    return out


def _expand(scores: dict[str, float]) -> dict[str, float]:
    """The learner's proficiency per skill (lower case) plus every close equivalent they imply, at the best proficiency among them."""
    out = dict(scores)
    for family in FAMILIES:
        best = max((out.get(n.lower(), 0.0) for n in family), default=0.0)
        if best:
            for n in family:
                out[n.lower()] = max(out.get(n.lower(), 0.0), best)
    for name, implied in IMPLIES.items():
        have = scores.get(name.lower(), 0.0)
        for n in implied:
            out[n.lower()] = max(out.get(n.lower(), 0.0), have)
    return out


TREND_WEIGHT = 2.0  # a key skill whose demand is forecast to rise counts this many times its O*NET importance
AI_SKILL_WEIGHT = 8.0  # an AI skill (one Jobee wrote for a role) counts double O*NET's top tool weight (4.0), the same boost a rising skill gets (TREND_WEIGHT), when it is added to the role's key skills: it is the first step of its section, so it is meant to matter
DEMAND_COUNTRY, DEMAND_HORIZON = "US", 6  # the occupational pipeline's biggest sample and middle horizon
# O*NET role -> the occupational pipeline's occupation with forecasts for it. The other roles have none, so no skill is boosted there.
OCCUPATIONS = {"15-1252.00": "software_engineer", "15-2051.00": "data_scientist", "15-2051.01": "data_analyst"}
# O*NET names the pipeline's registry spells differently.
REGISTRY_NAMES = {
    "structured query language sql": "sql", "oracle java": "java", "amazon web services aws software": "aws",
    "microsoft azure software": "azure", "hypertext markup language html": "html", "cascading style sheets css": "css",
}


@lru_cache
def _demand() -> dict[str, list[dict]]:
    """Forecast rows by registry skill name and alias (lower case), biggest sample first. Empty if the pipeline output is missing."""
    try:
        f = occupational.table("latest/forecast.csv.gz")
        f = f[(f["country"] == DEMAND_COUNTRY) & (f["h"] == DEMAND_HORIZON)].sort_values("ads_12m", ascending=False)
        rows = occupational.records(f)
        aliases = {e["skill_id"]: [e["name"], *e.get("aliases_seen", [])] for e in occupational.doc("taxonomy/skill_registry.json")["skills"]}
    except Exception as e:  # context only: the matching works without it
        print(f"Skill demand unavailable ({type(e).__name__})")
        return {}
    out: dict[str, list[dict]] = {}
    for r in rows:
        for name in aliases.get(r["skill_id"], [r["skill_name"]]):
            out.setdefault(name.lower(), []).append(r)
    return out


@lru_cache
def is_rising(onet_code: str, skill_name: str) -> bool:
    """Whether the Occupations page forecasts rising demand for this skill in this role's occupation (evidence above low)."""
    occupation = OCCUPATIONS.get(onet_code)
    if occupation is None:
        return False
    rows = [r for r in _demand().get(REGISTRY_NAMES.get(skill_name.lower(), skill_name.lower()), []) if r["occupation"] == occupation and r["evidence"] != "low"]
    return bool(rows) and rows[0]["direction"] == "rising"


def _with_key_skills(role: dict, have: set[str]) -> dict:
    """The role with its key skills picked: the top tools and abilities.

    Among equally rated tools, ones the candidate already has come first, so a role isn't judged on an
    arbitrary pick of tools when O*NET rates dozens of them the same.
    """
    tools, families = [], set()
    for name, weight in sorted(role["tools"], key=lambda t: (-t[1], t[0].lower() not in have)):
        family = next((i for i, f in enumerate(FAMILIES) if name in f), None)
        if family is not None and family in families:
            continue  # one tool per family: Git and GitHub shouldn't take two slots
        if family is not None:
            families.add(family)
        tools.append((name, weight))
        if len(tools) == KEY_TOOLS:
            break
    picked = tools + role["abilities"][:KEY_ABILITIES]
    # Trend momentum: a skill forecast to be in rising demand for this role counts double, so learning it moves the match more.
    trending = {n for n, _ in picked if is_rising(role["onet_code"], n)}
    return {**role, "key_skills": [n for n, _ in picked], "trending": trending,
            "weights": {n: w * (TREND_WEIGHT if n in trending else 1.0) for n, w in picked}}


_icons: dict[str, str] = {}


def _role_icons() -> dict[str, str]:
    """Each role's icon from onet_roles.icon (migration 0006). Cached once read; empty (so the default is used) until then."""
    if not _icons:
        try:
            _icons.update({r["onet_code"]: r["icon"] for r in get_client().table("onet_roles").select("onet_code, icon").execute().data})
        except Exception as e:
            print(f"Role icons unavailable ({type(e).__name__}); using the default")
    return _icons


_sdgs: dict[str, list[dict]] = {}


def _role_sdgs() -> dict[str, list[dict]]:
    """Each role's SDGs from onet_roles.sdg (migration 0014), biggest first, with the goal's name. Cached once read;
    empty (so roles are matched on skills alone and show no SDG reasons) until the column exists."""
    if not _sdgs:
        try:
            for r in get_client().table("onet_roles").select("onet_code, sdg").execute().data:
                goals = sorted(r.get("sdg") or [], key=lambda g: -g["value"])
                if goals:
                    _sdgs[r["onet_code"]] = [{"sdg": g["sdg"], "name": SDG_NAMES[g["sdg"]], "value": g["value"]} for g in goals]
        except Exception as e:
            print(f"Role SDGs unavailable ({type(e).__name__}); matching on skills only")
    return _sdgs


def _sdg_reasons(role: dict, interests: list[Interest]) -> list[SdgReason]:
    """The SDGs the role serves, each with the learner's interests that point at the same goal (strongest first).

    Built from the data, so it only ever names interests the learner picked and goals the role has. A goal no
    interest points at comes from the role itself, which the page shows by the role's title.
    """
    out = []
    for g in role.get("sdg", []):
        weight = lambda i: next((w.value for w in i.sdg if w.sdg == g["sdg"]), 0.0)  # noqa: E731
        mine = sorted((i for i in interests if weight(i) > 0), key=lambda i: -weight(i))
        out.append(SdgReason(sdg=g["sdg"], name=g["name"], value=g["value"], interests=[i.interest for i in mine]))
    return out


def _description(role: dict, owned: list[str], missing: list[str]) -> str:
    """A short sentence built from the actual overlap, so it never claims a skill the candidate lacks."""
    def names(xs):
        xs = xs[:3]
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
    if owned and missing:
        return f"Your {names(owned)} carry over; {names(missing[:2])} would be new."
    if owned:
        return f"Your {names(owned)} carry straight over."
    return f"Most of the key skills for this role would be new to you, starting with {names(missing[:2])}."


def _outlook(code: str, horizon: int) -> tuple[list[ScenarioOutlook], dict]:
    """The forecast under each scenario, and the job's AI exposure fields."""
    out, exposure = [], {}
    for scenario, tab in SCENARIOS:
        jobs = forecast.list_jobs(code, None, scenario, horizon)
        if not jobs:
            continue
        exposure = {"ai_exposure": jobs[0].ai_exposure, "automation_share": jobs[0].automation_share}
        o = jobs[0].outlook[0]
        out.append(ScenarioOutlook(scenario=scenario, tab=tab, change_pct=o.change_pct, range_low_pct=o.range.low,
                                   range_high_pct=o.range.high, trend=o.trend, forecast_for=o.forecast_for))
    return out, exposure


def _context(horizon: int) -> list[ContextRole]:
    out = []
    for code in CONTEXT_ROLES:
        outlook, exposure = _outlook(code, horizon)
        title = next((r["title"] for r in _all_titles() if r["onet_code"] == code), code)
        out.append(ContextRole(onet_code=code, title=title, outlook=outlook, **exposure))
    return out


@lru_cache
def _all_titles() -> list[dict]:
    return pd.read_csv(DATA_DIR / "onet_roles.csv")[["onet_code", "title"]].to_dict("records")


def graded(skills: list) -> dict[str, float]:
    """The learner's own skills: name in lower case -> proficiency step, the best one if a skill is listed twice."""
    out: dict[str, float] = {}
    for s in skills:
        out[s.name.lower()] = max(out.get(s.name.lower(), 0.0), scoring.proficiency(s.score))
    return out


def outlooks(horizon: int) -> dict[str, tuple[list[ScenarioOutlook], dict]]:
    """Every matched role's forecasts, read once so a comparison can score the roles many times."""
    return {code: _outlook(code, horizon) for code in TECH_ROLES}


def _skill_fit(role: dict, own: dict[str, float], proficiency: dict[str, float]) -> list[SkillFit]:
    """How each key skill counted, and through which of the learner's skills if not directly."""
    total = sum(role["weights"].values()) or 1.0

    def via(name: str) -> str | None:
        key = name.lower()
        if own.get(key) or not proficiency.get(key):
            return None
        linked = [*(n for f in FAMILIES if name in f for n in f if n != name), *(n for n, implied in IMPLIES.items() if name in implied)]
        return next((n for n in linked if own.get(n.lower(), 0.0) == proficiency[key]), None)

    return [SkillFit(name=n, importance_share=round(role["weights"][n] / total, 4), proficiency=proficiency.get(n.lower(), 0.0), via=via(n), trending=n in role["trending"])
            for n in role["key_skills"]]


def score_roles(own: dict[str, float], stage: str, picked: list[Interest], forecasts: dict[str, tuple[list[ScenarioOutlook], dict]],
                extra_skills: dict[str, dict[str, float]] | None = None) -> list[dict]:
    """The one role-matching calculation: every tech role scored for these skills, best first. The cards, the saved
    sets and the What-If simulator all come through here, so they can't disagree.

    extra_skills (O*NET code -> skill name -> weight) adds skills to a role's key skills on top of its ten, so a comparison can ask
    what the match would be if those skills counted too. Nothing the learner sees today passes it."""
    proficiency = _expand(own)
    have = {n for n, v in proficiency.items() if v > 0}
    edu = scoring.education(stage)
    sdgs = _role_sdgs()
    roles = [{**_with_key_skills(r, have), "sdg": sdgs.get(r["onet_code"], [])} for r in _roles()]
    for role in roles:
        add = (extra_skills or {}).get(role["onet_code"])
        if add:
            role["key_skills"] = [*role["key_skills"], *(n for n in add if n not in role["key_skills"])]
            role["weights"] = {**role["weights"], **{n: w for n, w in add.items() if n not in role["weights"]}}
    raw = {r["onet_code"]: scoring.interest_raw(picked, r["sdg"]) for r in roles}
    top_raw = max(raw.values(), default=0.0)
    scored = []
    for role in roles:
        skills = scoring.skills_fit(role["weights"], proficiency)
        interest = (raw[role["onet_code"]] / top_raw if top_raw else 0.0) if picked else None
        outlook, exposure = forecasts[role["onet_code"]]
        outlook = [o.model_copy(update={"match_percent": b["match_percent"], "breakdown": MatchBreakdown(**b)})
                   for o in outlook for b in [scoring.breakdown(edu, skills, scoring.outlook_score(o.change_pct), interest)]]
        headline = next((o.match_percent for o in outlook if o.scenario == HEADLINE), None)
        if headline is None:  # no forecast for this role: a flat outlook (1x)
            headline = round(100 * scoring.combine(edu, skills, scoring.outlook_score(0), interest))
        scored.append({"headline": headline, "skills": skills, "interest": interest, "role": role, "outlook": outlook, "exposure": exposure,
                       "owned": [n for n in role["key_skills"] if n.lower() in have], "missing": [n for n in role["key_skills"] if n.lower() not in have],
                       "fit": _skill_fit(role, own, proficiency), "edu": edu})
    scored.sort(key=lambda t: (-t["headline"], -t["skills"]))
    for scenario, _ in SCENARIOS:
        match = lambda t: next((o.match_percent for o in t["outlook"] if o.scenario == scenario), t["headline"])  # noqa: E731
        for place, t in enumerate(sorted(scored, key=lambda t: -match(t)), start=1):  # stable: ties keep the headline order
            t["outlook"] = [o.model_copy(update={"rank": place}) if o.scenario == scenario else o for o in t["outlook"]]
    return scored


def recommend(req: RecommendRequest, profile_id: str, stage: str = "under", horizon: int = HORIZON, interests: list[Interest] | None = None) -> RecommendResponse:
    """Score every tech role for the candidate by formula (see scoring.py) and return the best TOP_JOBS, each with its
    skills overlap, SDG links and the forecast and match under each AI scenario."""
    picked = interests or []
    start = time.perf_counter()
    own = graded([*req.skills, *req.top_skills])
    scored = score_roles(own, stage, picked, outlooks(horizon))
    icons = _role_icons()
    jobs = []
    for rank, t in enumerate(scored[:TOP_JOBS], start=1):
        role, owned, missing, interest = t["role"], t["owned"], t["missing"], t["interest"]
        jobs.append(JobMatch(
            rank=rank, onet_code=role["onet_code"], title=role["title"], icon=icons.get(role["onet_code"], DEFAULT_ICON), match_percent=t["headline"],
            match_parts=MatchParts(education=round(t["edu"], 4), interests=None if interest is None else round(interest, 4), skills=round(t["skills"], 4)),
            skills_owned=len(owned), skills_total=len(role["key_skills"]), skills_you_have=owned,
            skills_to_learn=missing, description=_description(role, owned, missing),
            outlook=t["outlook"], sdg_reasons=_sdg_reasons(role, picked), skill_fit=t["fit"], **t["exposure"],
        ))
    seconds = round(time.perf_counter() - start, 2)
    return RecommendResponse(profile_id=profile_id, jobs=jobs, context=_context(horizon), horizon_months=horizon, sdg_focus=focus_of(picked), note=NOTE,
                             generated_at=datetime.now(timezone.utc).isoformat(), stage=stage,
                             engine=Engine(source="formula", model="arithmetic", jobs_considered=len(scored), seconds=seconds))


def with_breakdowns(saved: RecommendResponse) -> RecommendResponse:
    """Fill in what a set saved before the breakdown existed lacks, from the parts it kept. Saved scores are never
    changed: a scenario whose breakdown doesn't come to its saved match (an older formula) is left without one."""
    for job in saved.jobs:
        parts = job.match_parts
        for o in job.outlook:
            if parts and o.breakdown is None:
                b = scoring.breakdown(parts.education, parts.skills, scoring.outlook_score(o.change_pct), parts.interests)
                if b["match_percent"] == o.match_percent:
                    o.breakdown = MatchBreakdown(**b)
    for scenario, _ in SCENARIOS:
        match = lambda j: next((o.match_percent for o in j.outlook if o.scenario == scenario), None) or j.match_percent  # noqa: E731
        for place, job in enumerate(sorted(saved.jobs, key=lambda j: (-match(j), j.rank)), start=1):
            for o in job.outlook:
                if o.scenario == scenario:
                    o.rank = place
    saved.note = NOTE
    return saved
