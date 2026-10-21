import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
TOP_N = 5  # top skills returned

# Words that start many tool names; dropped when building keywords so "Microsoft Excel" is found by "excel".
VENDORS = {
    "microsoft", "adobe", "apache", "amazon", "atlassian", "google", "oracle", "ibm", "intuit", "red", "hat",
    "autodesk", "apple", "sap", "the", "thomson", "reuters", "trimble", "dassault", "systemes", "bentley", "cisco",
    "mozilla", "esri", "henry", "schein", "epic", "kronos", "mitre", "orion", "grafana", "labs", "tenable",
}
# Extra spellings people use on resumes, keyed by the lower-case skill name.
EXTRA_ALIASES = {
    "javascript": ["js"], "typescript": ["ts"], "postgresql": ["postgres"], "kubernetes": ["k8s"],
    "node.js": ["node"], "scikit-learn": ["sklearn"], "microsoft power bi": ["powerbi"],
    "microsoft excel": ["spreadsheet", "spreadsheets"], "google sheets": ["spreadsheet", "spreadsheets"],
    "amazon web services aws software": ["aws"], "microsoft azure software": ["azure"],
    "the mathworks matlab": ["matlab"], "ibm spss statistics": ["spss"], "tableau": ["tableau"],
    "oracle java": ["java"], "unix shell": ["shell"], "restful api": ["rest api", "rest apis", "restful"],
    "geographic information system gis systems": ["gis"], "microsoft office software": ["office", "ms office"],
    "react": ["reactjs", "react.js"], "transact-sql": ["t-sql", "tsql"], "linux": ["ubuntu", "debian", "centos", "fedora"],
    "google looker analytics": ["looker", "looker studio"], "hypertext markup language html": ["html5"],
    "microsoft power bi": ["powerbi", "power-bi"], "microsoft visual basic for applications vba": ["vba"],
    "amazon elastic compute cloud ec2": ["ec2"], "amazon web services aws cloudformation": ["cloudformation"],
    "apache subversion svn": ["svn"], "microsoft sql server": ["mssql", "ms sql"], "oracle database": ["oracle db"],
    "google android": ["android"], "apple ios": ["ios"], "apple macos": ["macos", "mac os"],
}
# Words too generic to act as a keyword on their own when a tool name is split into words.
GENERIC = {
    "software", "framework", "server", "enterprise", "platform", "database", "language", "systems", "system",
    "services", "service", "web", "studio", "analytics", "cloud", "office", "project", "developer", "edition",
    "shell", "script", "markup", "hypertext", "style", "sheets", "cascading", "object", "notation", "management",
    "geographic", "information", "workforce", "marketing", "automation", "integration", "reporting", "basic",
    "applications", "application", "visual", "structured", "query", "extensible", "science", "compute", "elastic",
    "active", "directory", "foundation", "team", "tracking", "applicant", "productivity", "creative", "docs",
    "sheets", "workspace", "warehouse", "firewall", "gateway", "protocol", "border", "tools", "tool", "power",
}
ALWAYS_ASK_MAX_LEN = 2  # names like "C", "R" or "Go" can't be matched by keyword; always include


@lru_cache
def skill_table() -> list[tuple[str, str]]:
    """Every distinct (skill name, skill type) in the O*NET table: ~260 names; type is skill, knowledge or tech."""
    df = pd.read_csv(DATA_DIR / "onet_role_skills.csv").dropna(subset=["skill_name"]).drop_duplicates("skill_name")
    return sorted(zip(df["skill_name"], df["skill_type"]))


def skill_vocabulary() -> list[str]:
    """Every skill name both engines can report: all ~260 in the O*NET table."""
    return [name for name, _ in skill_table()]


def _aliases(name: str) -> set[str]:
    """Lower-case keywords that suggest a tool is on the resume.

    The name, the name without its vendor, its acronyms (SQL, EC2), a hyphen-free and a ".js"-free spelling,
    its distinctive single words ("Jenkins" for "Jenkins CI"), plus hand-written aliases.
    """
    low = name.lower()
    words = name.split()
    plain = [w for w in words if w.lower() != "software"]
    trimmed = list(plain)
    while trimmed and trimmed[0].lower() in VENDORS:
        trimmed.pop(0)
    out = {" ".join(plain).lower(), " ".join(trimmed).lower()}
    out |= {w.lower() for w in words if len(w) >= 2 and w.isupper() and w.isalnum()}  # SQL, AWS, EC2, SSIS ...
    for w in trimmed:  # distinctive single words
        wl = w.lower()
        if len(wl) >= 4 and wl not in GENERIC and wl not in VENDORS and wl.isalpha():
            out.add(wl)
    out |= set(EXTRA_ALIASES.get(low, []))
    for a in list(out):  # spelling variants
        out.add(a.replace("-", " "))
        out.add(a.replace("-", ""))
        out.add(a.replace(".", ""))
        if a.endswith(".js"):
            out |= {a[:-3], a[:-3] + "js"}
    return {a for a in out if len(a) >= 2}


@lru_cache
def _alias_patterns() -> list[tuple[str, re.Pattern | None]]:
    """For each tool: its name and one regex that matches any of its keywords (None = always include)."""
    patterns = []
    for name, kind in skill_table():
        if kind != "tech":
            continue
        if len(name) <= ALWAYS_ASK_MAX_LEN:
            patterns.append((name, None))
            continue
        alts = "|".join(re.escape(a) for a in sorted(_aliases(name), key=len, reverse=True))
        patterns.append((name, re.compile(rf"(?<![a-z0-9])(?:{alts})(?![a-z])")))
    return patterns


def candidate_skills(text: str) -> list[str]:
    """Skills worth considering: all general skills and knowledge areas, plus tools named in the text."""
    low = text.lower()
    general = [name for name, kind in skill_table() if kind != "tech"]
    tools = [name for name, pat in _alias_patterns() if pat is None or pat.search(low)]
    return sorted(general + tools)


def candidates_for(text: str) -> list[str]:
    """The skill list both engines are given for this resume: filtered by default, all ~260 if RESUME_PREFILTER=false."""
    return candidate_skills(text) if get_settings().resume_prefilter else skill_vocabulary()
