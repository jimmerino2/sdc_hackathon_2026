"""Load the HRD Corp-claimable courses that teach one of the app's skills into Supabase (migrations/0026_hrd_programmes.sql).

    python pipeline/load_hrd_programmes.py --dry-run     # show which courses match which skills, write nothing
    python pipeline/load_hrd_programmes.py               # upsert the matching courses
    python pipeline/load_hrd_programmes.py --tech-only   # only courses for tools, programming and cyber security

Reads the CSV of the public HRD Corp BizMatch course list (data/hrdcorp/, see its README.txt) and keeps a course only if
its name matches the rule of at least one skill in SKILL_RULES below. A course stays in the table with every skill it
matches (`skills`, O*NET skill names as in onet_role_skills). The rules are deliberately narrow: a course is kept when its
title names the skill, and not for a loose topic fit.

Needs the SERVICE ROLE key. SUPABASE_URL and SUPABASE_SERVICE_KEY are read from the shell, else from src/backend/.env.
Rows are upserted on course_id, so re-running is safe; courses that stop matching are not deleted.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "hrdcorp"
BACKEND_ENV = ROOT / "src" / "backend" / ".env"
BATCH = 200

# skill name (as in onet_role_skills) -> regex on the course name. Case-insensitive.
SKILL_RULES: dict[str, str] = {
    # tools
    "Python": r"\bpython\b",
    "Microsoft Power BI": r"power\s?bi\b",
    "Microsoft Excel": r"microsoft excel|\bms excel\b|\bexcel (essentials|formulas?|dashboards?|spreadsheets?|advanced|basics?|pivot)|\b(advanced|basic|intermediate) excel\b",
    "Amazon Web Services AWS software": r"\baws\b|amazon web services",
    "Microsoft Azure software": r"\bazure\b",
    "Google Cloud": r"google cloud|\bgcp\b",
    "Tableau": r"\btableau\b",
    "Structured query language SQL": r"\bsql\b",
    "Microsoft Power Automate": r"power automate",
    "Microsoft Power Platform software": r"power platform|power apps",
    "Microsoft Word": r"\bms word\b|microsoft word",
    "Microsoft PowerPoint": r"powerpoint",
    "Microsoft Project": r"microsoft project|\bms project\b",
    "Microsoft Office software": r"microsoft office|\bms office\b|office 365|microsoft 365",
    "Google Workspace software": r"google workspace|g suite",
    "Google Analytics": r"google analytics",
    "Canva": r"\bcanva\b",
    "TikTok": r"tik ?tok",
    "Facebook": r"facebook",
    "Figma": r"\bfigma\b",
    "Adobe Photoshop": r"photoshop",
    "Adobe Illustrator": r"illustrator",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"kubernetes",
    "Linux": r"\blinux\b",
    "Git": r"\bgit\b|github",
    "JavaScript": r"javascript",
    "Java": r"\bjava\b",
    "React": r"\breact\b",
    "TensorFlow": r"tensorflow",
    "SAP software": r"\bsap\b",
    "Salesforce software": r"salesforce",
    "Intuit QuickBooks": r"quickbooks",
    "Autodesk AutoCAD": r"autocad",
    "Autodesk Revit": r"\brevit\b",
    "Trimble SketchUp Pro": r"sketchup",
    "WordPress": r"wordpress",
    # abilities
    "Time Management": r"time management",
    "Critical Thinking": r"critical thinking|analytical thinking|logical thinking",
    "Complex Problem Solving": r"problem[- ]solving",
    "Negotiation": r"negotiat",
    "Persuasion": r"persua|influenc",
    "Speaking": r"public speaking|presentation|presenting|communicat",
    "Active Listening": r"listening",
    "Writing": r"\bwriting\b",
    "Instructing": r"train the trainer|\bttt\b|coaching|mentoring|\bcoach\b",
    "Programming": r"(?<!linguistic )\bprogramming\b|\bcoding\b",
    "Systems Analysis": r"systems? analysis",
    # knowledge
    "Personnel and Human Resources": r"human resource|\bhr\b|recruitment|talent acquisition",
    "Sales and Marketing": r"\bsales\b|marketing",
    "Economics and Accounting": r"(?<!ghg )accounting|financial literacy|\bfinance\b|financial management",
    "Public Safety and Security": r"cyber",
    "Education and Training": r"instructional design|train the trainer|talent development|learning (and|&) development",
    "Management of Personnel Resources": r"leadership|\bleaders?\b|leading|supervis|people management|managing people|team management|for managers|new managers|performance management",
    "Social Perceptiveness": r"emotional intelligence|empath|interpersonal|\bdisc\b|teiq",
    "Coordination": r"collaborat|teamwork|team synergy|building teams|high-performing teams|conflict",
    "Judgment and Decision Making": r"decision[- ]mak",
    "Service Orientation": r"customer",
    "Customer and Personal Service": r"customer",
    "Management of Financial Resources": r"budget",
    "Management of Material Resources": r"inventory|supply chain|logistics|procurement",
    "Quality Control Analysis": r"(?<!service )(?<!environmental )quality|\bqc\b|zero defects|six sigma",
    "Operations Analysis": r"\blean\b|process improvement|process innovation|value stream|\b5s\b|continuous improvement|kaizen",
    "Psychology": r"psycholog|mental health|stress|(?<!cyber )resilien|well-?being|burnout|mindful",
    "Therapy and Counseling": r"counsel",
    "Law and Government": r"\blaw\b|legal|employment act|pdpa|(?<!environmental )compliance|industrial relations|statutory",
    "English Language": r"english",
    "Administrative": r"secretar|office administration|office management",
    "Administration and Management": r"strategic|business management|project management|general management|\bmba\b|business administration",
}


# Skills that are people, business or knowledge areas rather than tools or technical skills; --tech-only leaves them out.
SOFT_SKILLS = {
    "Time Management", "Critical Thinking", "Complex Problem Solving", "Negotiation", "Persuasion", "Speaking", "Active Listening",
    "Writing", "Instructing", "Systems Analysis", "Personnel and Human Resources", "Sales and Marketing", "Economics and Accounting",
    "Education and Training", "Management of Personnel Resources", "Social Perceptiveness", "Coordination", "Judgment and Decision Making",
    "Service Orientation", "Customer and Personal Service", "Management of Financial Resources", "Management of Material Resources",
    "Quality Control Analysis", "Operations Analysis", "Psychology", "Therapy and Counseling", "Law and Government", "English Language",
    "Administrative", "Administration and Management",
}


def match(course: str, tech_only: bool = False) -> list[str]:
    # "(for everyone other than HR)" says who a session is for, not what it teaches
    title = re.sub(r"\((?:for|FOR)[^)]*\)", " ", course)
    return [skill for skill, rx in SKILL_RULES.items() if re.search(rx, title, re.I) and not (tech_only and skill in SOFT_SKILLS)]


def latest_csv() -> Path:
    files = sorted(DATA.glob("bizmatch_courses_*.csv"))
    if not files:
        raise SystemExit(f"no bizmatch_courses_*.csv in {DATA}")
    return files[-1]


def read_rows(tech_only: bool = False) -> list[dict]:
    rows = []
    with open(latest_csv(), encoding="utf-8", newline="") as f:
        for raw in csv.DictReader(f):
            skills = match(raw["course_name"], tech_only)
            if not skills:
                continue
            rows.append({
                "course_id": int(raw["course_id"]),
                "mycoid": raw["mycoid"],
                "training_provider": raw["training_provider"],
                "scheme": raw["scheme"],
                "certification": raw["certification"] or None,
                "course_name": raw["course_name"],
                "fee_rm": float(raw["fee_rm"]),
                "discount_pct": float(raw["discount_pct"]),
                "fee_after_discount_rm": float(raw["fee_after_discount_rm"]),
                "skills": skills,
                "fetched": raw["fetched"],
                "source_url": raw["source_url"],
            })
    return rows


def env_value(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    if BACKEND_ENV.exists():
        for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"\'') or None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="show the matches, write nothing")
    ap.add_argument("--tech-only", action="store_true", help="only courses for tools, programming and cyber security")
    args = ap.parse_args()

    rows = read_rows(args.tech_only)
    by_skill: dict[str, list[dict]] = {}
    for r in rows:
        for s in r["skills"]:
            by_skill.setdefault(s, []).append(r)
    print(f"{len(rows)} courses match at least one of {len(by_skill)} skills (rules for {len(SKILL_RULES)} skills)\n")
    for skill in sorted(by_skill, key=lambda s: -len(by_skill[s])):
        print(f"{skill} ({len(by_skill[skill])})")
        for r in by_skill[skill]:
            print(f"    RM{r['fee_after_discount_rm']:>9,.2f}  {r['course_name'][:78]}  [{r['training_provider'][:30]}]")
    if args.dry_run:
        return 0

    url, key = env_value("SUPABASE_URL"), env_value("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in src/backend/.env or your shell.", file=sys.stderr)
        return 1
    from supabase import create_client  # imported late so --dry-run needs no dependency

    client = create_client(url, key)
    for i in range(0, len(rows), BATCH):
        client.table("hrd_programmes").upsert(rows[i:i + BATCH], on_conflict="course_id").execute()
    print(f"\nhrd_programmes: {len(rows)} courses upserted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
