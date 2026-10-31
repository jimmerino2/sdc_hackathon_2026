"""The SDG targets each role and skill serves.

Read from the Supabase tables onet_roles_sdg and onet_skills_sdg (migrations/0026_onet_sdg_targets.sql, filled by
pipeline/load_supabase.py). Where a table is missing or empty the same rows come from data/processed/*_sdg.csv, so the
role page shows them before the migration is applied.
"""
import csv
import re
from functools import lru_cache
from pathlib import Path

from app.interests.sdg import SDG_NAMES
from app.sdg.schemas import RoleGoal, RoleSdg, SdgGoal, SdgTarget, SkillSdg
from app.supabase import get_client

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
COLUMNS = "main_sdg, relevant_sdgs, targets"


def parse_row(raw: dict) -> dict:
    """A CSV row's text columns as the table has them: 'SDG 8: ...' -> 8, 'SDG 12 (...), SDG 9 (...)' -> [12, 9],
    '8.2 productivity ... · 12.8 awareness ...' -> [{code, sdg, text}, ...] (same as pipeline/load_supabase.sdg_row)."""
    targets = []
    for t in filter(None, (t.strip() for t in raw["targets"].split("·"))):
        m = re.match(r"(\d+)\.([0-9a-z]+) (.+)", t)
        if m:
            targets.append({"code": f"{m[1]}.{m[2]}", "sdg": int(m[1]), "text": m[3]})
    return {"main_sdg": int(re.match(r"SDG (\d+)", raw["main_sdg"])[1]),
            "relevant_sdgs": [int(n) for n in re.findall(r"SDG (\d+)", raw["relevant_sdgs"])], "targets": targets}


def _read(table: str, key: str, extra: str = "") -> dict[str, dict]:
    """Every row of one table by its key, from Supabase or else the CSV."""
    try:
        rows = get_client().table(table).select(f"{key}, {COLUMNS}{extra}").execute().data
        if rows:
            return {r[key]: r for r in rows}
    except Exception as e:  # table not created yet, no network...
        print(f"could not read {table} from Supabase ({type(e).__name__}); using {table}.csv")
    with open(DATA_DIR / f"{table}.csv", encoding="utf-8", newline="") as f:
        return {r["onet_id"]: {**r, key: r["onet_id"], **parse_row(r)} for r in csv.DictReader(f)}


@lru_cache
def _roles() -> dict[str, dict]:
    return _read("onet_roles_sdg", "onet_code")


@lru_cache
def _skills() -> dict[str, dict]:
    return _read("onet_skills_sdg", "skill_id", ", skill_name, skill_type")


@lru_cache
def _role_skill_ids() -> dict[str, list[str]]:
    """Each role's O*NET skill ids, in onet_role_skills.csv's order."""
    out: dict[str, list[str]] = {}
    with open(DATA_DIR / "onet_role_skills.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            ids = out.setdefault(r["onet_code"], [])
            if r["skill_id"] not in ids:
                ids.append(r["skill_id"])
    return out


@lru_cache
def _role_goals() -> dict[str, RoleGoal]:
    """Each role's measurable goal, from onet_roles_sustainable_goals.csv."""
    out: dict[str, RoleGoal] = {}
    with open(DATA_DIR / "onet_roles_sustainable_goals.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            m = re.match(r"SDG (\d+)", r["prosperity_sdg"])
            out[r["onet_role_id"]] = RoleGoal(sdg=int(m[1]) if m else None, text=r["goal"].strip())
    return out


def _goal(n: int) -> SdgGoal:
    return SdgGoal(sdg=n, name=SDG_NAMES[n])


def _parts(r: dict) -> dict:
    """main, relevant and targets, with the main goal's targets first (then in the order written)."""
    targets = sorted(r["targets"], key=lambda t: t["sdg"] != r["main_sdg"])
    return {"main": _goal(r["main_sdg"]), "relevant": [_goal(n) for n in r["relevant_sdgs"] if n != r["main_sdg"]],
            "targets": [SdgTarget(**t) for t in targets]}


def role_sdg(onet_code: str) -> RoleSdg | None:
    """The role's SDGs and targets and those of its skills; None if the role has none on record."""
    r = _roles().get(onet_code)
    if not r:
        return None
    skills = _skills()
    return RoleSdg(onet_code=onet_code, **_parts(r), goal=_role_goals().get(onet_code), skills=[
        SkillSdg(skill_id=i, skill_name=skills[i]["skill_name"], skill_type=skills[i]["skill_type"], **_parts(skills[i]))
        for i in _role_skill_ids().get(onet_code, []) if i in skills
    ])
