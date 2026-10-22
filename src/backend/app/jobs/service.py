import time
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.forecast import service as forecast
from app.jobs import fit
from app.jobs.schemas import ContextRole, Engine, JobMatch, RecommendRequest, RecommendResponse, ScenarioOutlook
from app.supabase import get_client

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
TOP_JOBS = 10
DEFAULT_ICON = "briefcase"
SHORTLIST = 20  # roles the engine scores: the best on skill overlap out of all of them
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
NOTE = ("Match is how well your skills fit the role today. Posting change is the sector trend carried over to the role "
        "(US data stands in for Malaysia) and is indicative, not a precise prediction.")


class RecommendError(Exception):
    """The fit step failed; carries a message to show the caller."""


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
        })
    return out


def _expand(have: set[str]) -> set[str]:
    """The candidate's skills (lower case) plus every close equivalent they imply."""
    out = set(have)
    for family in FAMILIES:
        if any(n.lower() in have for n in family):
            out |= {n.lower() for n in family}
    for name, implied in IMPLIES.items():
        if name.lower() in have:
            out |= {n.lower() for n in implied}
    return out


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
    return {**role, "key_skills": [n for n, _ in picked], "weights": dict(picked)}


_icons: dict[str, str] = {}


def _role_icons() -> dict[str, str]:
    """Each role's icon from onet_roles.icon (migration 0006). Cached once read; empty (so the default is used) until then."""
    if not _icons:
        try:
            _icons.update({r["onet_code"]: r["icon"] for r in get_client().table("onet_roles").select("onet_code, icon").execute().data})
        except Exception as e:
            print(f"Role icons unavailable ({type(e).__name__}); using the default")
    return _icons


def _overlap(role: dict, have: set[str]) -> float:
    """Share of the role's key-skill importance the candidate already covers, 0-1."""
    total = sum(role["weights"].values())
    return sum(w for n, w in role["weights"].items() if n.lower() in have) / total


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


def recommend(req: RecommendRequest, profile_id: str, source: str = "auto", horizon: int = HORIZON) -> RecommendResponse:
    """Pick the TOP_JOBS roles that fit the candidate best and attach each one's skills overlap and forecast."""
    settings = get_settings()
    skills = {s.name.lower(): s for s in [*req.skills, *req.top_skills]}
    ranked = sorted(skills.values(), key=lambda s: -s.score)
    top = [s.model_dump() for s in req.top_skills]
    profile = fit.profile_text(top, [s.model_dump() for s in ranked])
    have = _expand(set(skills))

    roles = [_with_key_skills(r, have) for r in _roles()]
    shortlist = sorted(roles, key=lambda r: -_overlap(r, have))[:SHORTLIST]
    start = time.perf_counter()
    engine, model, scores = None, None, None
    if source in ("auto", "openjev") and settings.openjev_url:
        try:
            scores, engine, model = fit.openjev_fit(profile, shortlist), "openjev", "openjev"
        except Exception as e:  # server down, bad token, timeout, unexpected reply
            if source == "openjev":
                raise RecommendError(f"OpenJev failed: {type(e).__name__}.") from e
            print(f"OpenJev failed ({type(e).__name__}: {e}); falling back to the LLM")
    elif source == "openjev":
        raise RecommendError("OPENJEV_URL is not set, so OpenJev can't be used.")
    if scores is None:
        try:
            scores, engine, model = fit.llm_fit(profile, shortlist), "llm", settings.resume_model or settings.openrouter_model
        except ValueError as e:
            raise RecommendError("The model's answer could not be read as JSON. Try again.") from e
        except Exception as e:
            raise RecommendError(f"The job matching step failed: {type(e).__name__}.") from e
    seconds = round(time.perf_counter() - start, 2)

    best = sorted(zip(shortlist, scores), key=lambda rs: (-rs[1], -_overlap(rs[0], have)))[:TOP_JOBS]
    icons = _role_icons()
    jobs = []
    for rank, (role, score) in enumerate(best, start=1):
        owned = [n for n in role["key_skills"] if n.lower() in have]
        missing = [n for n in role["key_skills"] if n.lower() not in have]
        outlook, exposure = _outlook(role["onet_code"], horizon)
        jobs.append(JobMatch(
            rank=rank, onet_code=role["onet_code"], title=role["title"], icon=icons.get(role["onet_code"], DEFAULT_ICON), match_percent=round(score * 100),
            skills_owned=len(owned), skills_total=len(role["key_skills"]), skills_you_have=owned,
            skills_to_learn=missing, description=_description(role, owned, missing),
            outlook=outlook, **exposure,
        ))
    return RecommendResponse(profile_id=profile_id, jobs=jobs, context=_context(horizon), horizon_months=horizon, note=NOTE,
                             engine=Engine(source=engine, model=model, jobs_considered=len(shortlist), seconds=seconds))
