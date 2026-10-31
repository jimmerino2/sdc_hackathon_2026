"""Read the stated duration of each learning resource in migrations/0010_skill_sources.sql.

    python pipeline/fetch_durations.py            # fetch every link, write data/processed/skill_source_durations.csv
    python pipeline/fetch_durations.py --sql      # also write migrations/0024_skill_source_durations.sql from the CSV

Only a duration the page itself states is kept, and each row records which rule read it:

  youtube      the video's own length (watch?v= links; playlists have no single length)
  coursera     "N hours to complete" on a Coursera course page
  classcentral "N weeks, M hours a week" on a Class Central course page
  jsonld       timeRequired / duration on the page's own Course or LearningResource
  edx          "N hours to complete" on an edX course page (/learn/ subject pages list many courses, so they are skipped)

Anything else (sites that block scripts, pages that do not state a time) gets no row: the app then uses its
written formula for that skill and labels it an estimate. Nothing here guesses.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse as up
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_SQL = ROOT / "migrations" / "0010_skill_sources.sql"
OUT_CSV = ROOT / "data" / "processed" / "skill_source_durations.csv"
OUT_SQL = ROOT / "migrations" / "0024_skill_source_durations.sql"
MIN_MINUTES, MAX_MINUTES = 5, 6000  # a stated time outside this is a parsing mistake, not a duration
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobeeBot/1.0; +https://jobee-sdchack.replit.app)", "Accept-Language": "en"}

ROW = re.compile(r"\('((?:[^']|'')*)',\s*'(project|certificate|video|activity)',\s*(\d+),\s*'((?:[^']|'')*)',\s*'([^']*)'")
ISO = re.compile(r"^P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$")


def sources() -> list[dict]:
    """Every link in the sources migration: skill_name, source_type, rank, title, url."""
    text = SOURCES_SQL.read_text(encoding="utf-8")
    return [{"skill_name": a.replace("''", "'"), "source_type": b, "rank": int(c), "title": d.replace("''", "'"), "url": e}
            for a, b, c, d, e in ROW.findall(text)]


def iso_minutes(value: str) -> int | None:
    """'PT1H6M13S' -> 66 (rounded to the nearest minute)."""
    m = ISO.match(value.strip())
    if not m or not any(m.groups()):
        return None
    h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return round(h * 60 + mi + s / 60)


def fetch(url: str) -> str | None:
    for _ in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as f:
                return f.read(3_000_000).decode("utf-8", "ignore")
        except Exception:
            continue
    return None


def youtube(url: str, html: str) -> int | None:
    q = up.parse_qs(up.urlparse(url).query)
    if "v" not in q:  # a playlist or channel page
        return None
    m = re.search(r'"lengthSeconds":"(\d+)"', html) or re.search(r'itemprop="duration" content="([^"]+)"', html)
    if not m:
        return None
    return round(int(m.group(1)) / 60) if m.group(1).isdigit() else iso_minutes(m.group(1))


def hours_to_complete(html: str) -> int | None:
    m = re.search(r"(?i)(\d+(?:\.\d+)?)\s*hours?\s*to complete", html)
    return round(float(m.group(1)) * 60) if m else None


def classcentral(html: str) -> int | None:
    m = re.search(r"(?i)(\d+)\s*weeks?,\s*(\d+)\s*hours?\s*a\s*week", html)
    return int(m.group(1)) * int(m.group(2)) * 60 if m else None


def jsonld(html: str) -> int | None:
    """timeRequired / duration on the page's own top-level Course or LearningResource."""
    for block in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, flags=re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            kind = item.get("@type") if isinstance(item, dict) else None
            kinds = kind if isinstance(kind, list) else [kind]
            if any(k in ("Course", "LearningResource") for k in kinds):  # not VideoObject: that is often a promo clip
                for key in ("timeRequired", "duration", "totalTime"):
                    if isinstance(item.get(key), str) and (mins := iso_minutes(item[key])):
                        return mins
    return None


def read_duration(url: str, html: str) -> tuple[int, str] | None:
    host = up.urlparse(url).netloc.removeprefix("www.")
    path = up.urlparse(url).path
    found: tuple[int | None, str] = (None, "")
    if host in ("youtube.com", "youtu.be"):
        found = (youtube(url, html), "youtube")
    elif host == "coursera.org" and path.startswith("/learn/"):
        found = (hours_to_complete(html), "coursera")
    elif host == "edx.org" and path.startswith("/course/"):
        found = (hours_to_complete(html), "edx")
    elif host == "classcentral.com" and path.startswith("/course/"):
        found = (classcentral(html), "classcentral")
    if found[0] is None:
        found = (jsonld(html), "jsonld")
    minutes, rule = found
    return (minutes, rule) if minutes and MIN_MINUTES <= minutes <= MAX_MINUTES else None


def work(row: dict) -> dict | None:
    html = fetch(row["url"])
    got = read_duration(row["url"], html) if html else None
    if not got:
        return None
    return {"skill_name": row["skill_name"], "rank": row["rank"], "url": row["url"], "minutes": got[0], "rule": got[1],
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")}


def write_sql(rows: list[dict]) -> None:
    q = lambda s: "'" + s.replace("'", "''") + "'"  # noqa: E731
    lines = [
        "-- How long each learning resource says it takes, where the page states it (see pipeline/fetch_durations.py).",
        "-- A link with no value here has no stated time; the app then uses its written formula and labels it an estimate.",
        "alter table public.skill_sources add column if not exists duration_minutes integer check (duration_minutes between 5 and 6000);",
        "alter table public.skill_sources add column if not exists duration_rule text;",
        "alter table public.skill_sources add column if not exists duration_fetched date;",
        "",
    ]
    for r in sorted(rows, key=lambda r: (r["skill_name"], r["rank"])):
        lines.append(f"update public.skill_sources set duration_minutes = {r['minutes']}, duration_rule = {q(r['rule'])}, "
                     f"duration_fetched = '{r['fetched_at']}' where skill_name = {q(r['skill_name'])} and url = {q(r['url'])};")
    OUT_SQL.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", action="store_true", help="also write the migration from the CSV")
    ap.add_argument("--no-fetch", action="store_true", help="reuse the CSV instead of fetching")
    args = ap.parse_args()
    if not args.no_fetch:
        links = sources()
        with ThreadPoolExecutor(8) as pool:
            rows = [r for r in pool.map(work, links) if r]
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["skill_name", "rank", "url", "minutes", "rule", "fetched_at"])
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} of {len(links)} links state a duration -> {OUT_CSV}")
    if args.sql:
        write_sql(list(csv.DictReader(OUT_CSV.open(encoding="utf-8"))) if args.no_fetch else rows)
        print(f"wrote {OUT_SQL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
