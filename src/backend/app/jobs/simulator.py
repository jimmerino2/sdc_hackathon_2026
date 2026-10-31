"""The Career What-If Simulator: the learner's matches now against the same profile with extra skills.

Nothing is scored here. Both sides go through service.score_roles, so the difference comes only from the matching
engine; this module compares the two results and words why they differ. Nothing is written anywhere.
"""
from functools import lru_cache

from app.interests.schemas import Interest
from app.jobs import scoring, service
from app.jobs.schemas import RoleComparison, ScenarioComparison, ScenarioSummary, SimulatedSkill, SimulateResponse, SkillChange, SkillDemand, SkillGain, SkillOption
from app.occupational import service as occupational
from app.resume.schemas import SkillScore

MIN_IMPORTANCE = 2.25  # a skill counts as linked to a role only above this O*NET importance (the roadmap uses the same cut-off); O*NET rates every subject area for every role, most of them near zero
LEARNED = 1.0  # every skill the learner adds counts the same: fully learned, with no Basic / Good / Strong choice
DEMAND_COUNTRY, DEMAND_HORIZON = "US", 6  # the occupational pipeline's biggest sample and middle horizon
# O*NET role -> the occupational pipeline's occupation with forecasts for it. The other roles have none.
OCCUPATIONS = {"15-1252.00": "software_engineer", "15-2051.00": "data_scientist", "15-2051.01": "data_analyst"}
# O*NET names the pipeline's registry spells differently.
REGISTRY_NAMES = {
    "structured query language sql": "sql", "oracle java": "java", "amazon web services aws software": "aws",
    "microsoft azure software": "azure", "hypertext markup language html": "html", "cascading style sheets css": "css",
}


class UnknownRole(ValueError):
    """A focus role that is not one of the matched roles."""


class UnknownSkill(ValueError):
    """A simulated skill that no matched role uses, so it could not change anything."""


@lru_cache
def _catalogue() -> dict[str, str]:
    """Every skill the matched roles list: lower case -> O*NET name."""
    return {n.lower(): n for r in service._roles() for n in _relevant(r)}


def _relevant(role: dict) -> list[str]:
    """A role's tools, abilities and knowledge areas that matter for it (importance above MIN_IMPORTANCE), by name."""
    return [n for n, importance in role["tools"] + role["abilities"] + role["knowledge"] if importance > MIN_IMPORTANCE]


def _linked(code: str) -> set[str]:
    """The skills O*NET links to one role, by name: the ones that matter for it, not every area O*NET rates."""
    return {n for r in service._roles() if r["onet_code"] == code for n in _relevant(r)}


def _names(xs: list[str]) -> str:
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _changes(before: dict, after: dict) -> tuple[list[SkillChange], list[str]]:
    """The key skills that count for more than before, and the ones a simulated skill pushed out of the key skills."""
    was = {f.name: f for f in before["fit"]}
    gained = [SkillChange(name=f.name, before=was[f.name].proficiency if f.name in was else 0.0, after=f.proficiency, via=f.via)
              for f in after["fit"] if f.proficiency > (was[f.name].proficiency if f.name in was else 0.0)]
    kept = {f.name for f in after["fit"]}
    return gained, [f.name for f in before["fit"] if f.name not in kept]


def _explain(title: str, change: int, gained: list[SkillChange], replaced: list[str], rank_before: int, rank_after: int) -> str:
    """Why the match moved. Every name and number comes from the two results being compared."""
    moved = "" if rank_before == rank_after else f" It moves from #{rank_before} to #{rank_after} among your roles."
    if not gained:
        return f"None of the skills you added is a key skill for {title}, so your match stays the same.{moved}"
    plain = [g.name for g in gained if not g.via]
    through = [f"{g.via} also counts for {g.name}" for g in gained if g.via]
    what = "; ".join(filter(None, [f"you’d cover {_names(plain)}" if plain else "", *through]))
    swap = f" O*NET rates {_names(replaced)} the same, so {'it drops' if len(replaced) == 1 else 'they drop'} out of the key skills counted." if replaced else ""
    if change > 0:
        return f"Your {title} match rises {change} point{'s' if change != 1 else ''} because {what}.{swap}{moved}"
    if change < 0:
        return f"Your {title} match falls {-change} point{'s' if change != -1 else ''}: {what}, but at a lower level than the skills it replaces.{swap}{moved}"
    return f"Your {title} skills score improves because {what}, but not by enough to move the rounded match.{swap}{moved}"


def _match(t: dict, scenario: str) -> tuple[int, int, object]:
    """(match, rank, breakdown) of a scored role under one scenario."""
    o = next((o for o in t["outlook"] if o.scenario == scenario), None)
    return (o.match_percent, o.rank, o.breakdown) if o else (t["headline"], 0, None)


def _coverage(scored: list[dict]) -> float:
    total = sum(len(t["role"]["key_skills"]) for t in scored)
    return round(sum(len(t["owned"]) for t in scored) / total, 4) if total else 0.0


def _demand() -> dict[str, list[dict]]:
    """Forecast rows by registry skill name and alias (lower case), biggest sample first. Empty if the pipeline output is missing."""
    try:
        f = occupational.table("latest/forecast.csv.gz")
        f = f[(f["country"] == DEMAND_COUNTRY) & (f["h"] == DEMAND_HORIZON)].sort_values("ads_12m", ascending=False)
        rows = occupational.records(f)
        aliases = {e["skill_id"]: [e["name"], *e.get("aliases_seen", [])] for e in occupational.doc("taxonomy/skill_registry.json")["skills"]}
    except Exception as e:  # context only: the simulator works without it
        print(f"Skill demand unavailable ({type(e).__name__})")
        return {}
    out: dict[str, list[dict]] = {}
    for r in rows:
        for name in aliases.get(r["skill_id"], [r["skill_name"]]):
            out.setdefault(name.lower(), []).append(r)
    return out


def _emerging() -> set[str]:
    """Skill names whose rise in job ads clears the pipeline's evidence minimum, with more than low confidence."""
    try:
        e = occupational.table("datasets/emerging.csv")
    except Exception as err:
        print(f"Emerging skills unavailable ({type(err).__name__})")
        return set()
    e = e[e["meets_evidence_minimum"].astype(bool) & (e["confidence"] != "low") & (e["growth_lb_pp"] > 0) & (e["country"] == DEMAND_COUNTRY)]
    return {n.lower() for n in e["name"]}


def _gain(baseline: list[dict], own: dict[str, float], name: str, trial: float, stage: str, picked: list[Interest], forecasts: dict, focus: str) -> list[SkillGain]:
    """This one skill added on its own, through the matching engine, against the baseline: the change for the focus role."""
    scored = {t["role"]["onet_code"]: t for t in service.score_roles({**own, name.lower(): trial}, stage, picked, forecasts)}
    role = next(t for t in baseline if t["role"]["onet_code"] == focus)
    out = []
    for scenario, _ in service.SCENARIOS:
        change = _match(scored[focus], scenario)[0] - _match(role, scenario)[0]
        out.append(SkillGain(scenario=scenario, average_change=float(change), best_change=change, best_role=role["role"]["title"]))
    return out


def _options(baseline: list[dict], own: dict[str, float], stage: str, picked: list[Interest], forecasts: dict, focus: str) -> list[SkillOption]:
    """The skills O*NET links to the focus role that the learner hasn't maxed out, best first. A linked skill outside the
    role's 10 key skills stays in the list with a gain of 0: that is the real answer for it, and the page says so."""
    expanded = service._expand(own)
    tied: dict[str, list[str]] = {}  # candidate -> roles where it is a key skill the learner is missing
    for t in baseline:
        for n in t["missing"]:
            tied.setdefault(n, []).append(t["role"]["title"])
    linked = _linked(focus)
    names = [n for n in sorted(_catalogue().values()) if n in linked and expanded.get(n.lower(), 0.0) < 1.0]
    listing = {n: sum(n in _relevant(r) for r in service._roles()) for n in names}
    demand, emerging = _demand(), _emerging()
    out = []
    for name in names:
        current = expanded.get(name.lower(), 0.0)
        trial = LEARNED
        gains = _gain(baseline, own, name, trial, stage, picked, forecasts, focus)
        key = REGISTRY_NAMES.get(name.lower(), name.lower())
        rows = [r for r in demand.get(key, []) if r["occupation"] in OCCUPATIONS.values()]
        d = next((r for r in rows if r["evidence"] != "low"), rows[0] if rows else None)
        out.append(SkillOption(
            name=name, current=current, trial=trial, roles_listing=listing[name], gap_roles=tied.get(name, []), gains=gains, emerging=key in emerging,
            demand=d and SkillDemand(occupation=d["occupation"], direction=d["direction"], last_share=d["last_share_3m"], forecast=d["forecast"],
                                     target_month=d["target_month"], evidence=d["evidence"]),
        ))
    out.sort(key=lambda o: -max(g.best_change for g in o.gains))
    return out


def simulate(profile_id: str, skills: list[SkillScore], stage: str, picked: list[Interest], tried: list[SimulatedSkill], horizon: int, focus_role: str | None = None) -> SimulateResponse:
    """The current profile against a copy with `tried` added. A skill the learner already has stays at the higher level."""
    catalogue = _catalogue()
    unknown = [s.name for s in tried if s.name.lower() not in catalogue]
    if unknown:
        raise UnknownSkill(", ".join(unknown))
    own = service.graded(skills)
    forecasts = service.outlooks(horizon)
    baseline = service.score_roles(own, stage, picked, forecasts)
    if focus_role is not None and focus_role not in {t["role"]["onet_code"] for t in baseline}:
        raise UnknownRole(focus_role)
    focus = focus_role or min(baseline, key=lambda t: _match(t, service.HEADLINE)[1])["role"]["onet_code"]
    simulated = service.score_roles(service.graded([*skills, *tried]), stage, picked, forecasts)
    before = {t["role"]["onet_code"]: t for t in baseline}
    icons = service._role_icons()

    roles = []
    for after in simulated:
        code, title = after["role"]["onet_code"], after["role"]["title"]
        was = before[code]
        gained, replaced = _changes(was, after)
        scenarios = []
        for scenario, tab in service.SCENARIOS:
            (p0, r0, b0), (p1, r1, b1) = _match(was, scenario), _match(after, scenario)
            scenarios.append(ScenarioComparison(scenario=scenario, tab=tab, current_percent=p0, simulated_percent=p1, change=p1 - p0, current_rank=r0, simulated_rank=r1,
                                                current=b0, simulated=b1, outlook=next((o for o in after["outlook"] if o.scenario == scenario), None),
                                                explanation=_explain(title, p1 - p0, gained, replaced, r0, r1)))
        roles.append(RoleComparison(onet_code=code, title=title, icon=icons.get(code, service.DEFAULT_ICON), skills_owned_before=len(was["owned"]), skills_owned_after=len(after["owned"]),
                                    skills_total=len(after["role"]["key_skills"]), skills_gained=gained, skills_replaced=replaced, skills_remaining=after["missing"], skill_fit=after["fit"],
                                    sdg_reasons=service._sdg_reasons(after["role"], picked), scenarios=scenarios))

    def top(scored: list[dict], scenario: str) -> dict:
        return min(scored, key=lambda t: _match(t, scenario)[1])

    summary = [ScenarioSummary(scenario=s, tab=tab, current_top=top(baseline, s)["role"]["title"], simulated_top=top(simulated, s)["role"]["title"],
                               current_top_percent=_match(top(baseline, s), s)[0], simulated_top_percent=_match(top(simulated, s), s)[0])
               for s, tab in service.SCENARIOS]
    return SimulateResponse(profile_id=profile_id, horizon_months=horizon, coverage_before=_coverage(baseline), coverage_after=_coverage(simulated),
                            summary=summary, roles=roles, focus_role=focus,
                            options=[] if tried else _options(baseline, own, stage, picked, forecasts, focus))
