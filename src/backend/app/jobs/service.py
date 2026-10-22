import time
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.forecast import service as forecast
from app.jobs import fit
from app.jobs.schemas import Engine, JobMatch, RecommendRequest, RecommendResponse, ScenarioOutlook

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
TOP_JOBS = 3
SHORTLIST = 20  # roles the engine scores: the best on skill overlap out of all of them
KEY_SKILLS = 10  # a role's most important skills, used to judge overlap
HORIZON = 12
SCENARIOS = [("Rapid AI", "AI accelerates"), ("Baseline", "AI holds steady"), ("Slow", "AI slows down")]
NOTE = ("Match is how well your skills fit the role today. Posting change is the sector trend carried over to the role "
        "(US data stands in for Malaysia) and is indicative, not a precise prediction.")


class RecommendError(Exception):
    """The fit step failed; carries a message to show the caller."""


@lru_cache
def _roles() -> list[dict]:
    """Every role with its key skills (highest importance first), read once."""
    roles = pd.read_csv(DATA_DIR / "onet_roles.csv")
    skills = pd.read_csv(DATA_DIR / "onet_role_skills.csv").dropna(subset=["skill_name", "importance"])
    out = []
    for code, title in zip(roles["onet_code"], roles["title"]):
        top = (skills[skills["onet_code"] == code].drop_duplicates("skill_name")
               .sort_values("importance", ascending=False).head(KEY_SKILLS))
        if len(top):
            out.append({"onet_code": code, "title": title, "key_skills": top["skill_name"].tolist(),
                        "weights": dict(zip(top["skill_name"], top["importance"]))})
    return out


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


def _outlook(code: str, horizon: int) -> list[ScenarioOutlook]:
    out = []
    for scenario, tab in SCENARIOS:
        jobs = forecast.list_jobs(code, None, scenario, horizon)
        if not jobs:
            continue
        o = jobs[0].outlook[0]
        out.append(ScenarioOutlook(scenario=scenario, tab=tab, change_pct=o.change_pct, range_low_pct=o.range.low,
                                   range_high_pct=o.range.high, trend=o.trend, forecast_for=o.forecast_for))
    return out


def recommend(req: RecommendRequest, resume_id: str, source: str = "auto", horizon: int = HORIZON) -> RecommendResponse:
    """Pick the 3 roles that fit the candidate best and attach each one's skills overlap and forecast."""
    settings = get_settings()
    skills = {s.name.lower(): s for s in [*req.skills, *req.top_skills]}
    ranked = sorted(skills.values(), key=lambda s: -s.score)
    top = [s.model_dump() for s in req.top_skills]
    profile = fit.profile_text(top, [s.model_dump() for s in ranked])
    have = set(skills)

    shortlist = sorted(_roles(), key=lambda r: -_overlap(r, have))[:SHORTLIST]
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
    jobs = []
    for rank, (role, score) in enumerate(best, start=1):
        owned = [n for n in role["key_skills"] if n.lower() in have]
        missing = [n for n in role["key_skills"] if n.lower() not in have]
        jobs.append(JobMatch(
            rank=rank, onet_code=role["onet_code"], title=role["title"], match_percent=round(score * 100),
            skills_owned=len(owned), skills_total=len(role["key_skills"]), skills_you_have=owned,
            skills_to_learn=missing, description=_description(role, owned, missing),
            outlook=_outlook(role["onet_code"], horizon),
        ))
    return RecommendResponse(resume_id=resume_id, jobs=jobs, horizon_months=horizon, note=NOTE,
                             engine=Engine(source=engine, model=model, jobs_considered=len(shortlist), seconds=seconds))
