from supabase import Client

from app.hrd.schemas import Programme

COLUMNS = "course_id,training_provider,course_name,scheme,certification,fee_rm,discount_pct,fee_after_discount_rm,fetched,source_url"


LIST_SORT = "sortOrder=asc&sortCol=name"


def _list_url(url: str) -> str:
    """The BizMatch page a course was read from. The pages were read sorted by name, so the link must carry that sort or
    it opens a page with other courses on it. Rows loaded before the sort was stored get it added here."""
    return url if "sortCol=" in url else f"{url}{'&' if '?' in url else '?'}{LIST_SORT}"


def _is_in_house(course_name: str) -> bool:
    return "in-house" in course_name.lower()


def programmes_for(db: Client, skill: str, limit: int = 5) -> list[Programme]:
    """The HRD Corp-claimable courses that teach a skill (an O*NET skill name), best first.

    Courses a person can enrol in come before in-house workshops, then the cheaper ones first. The same course listed
    twice by a provider counts once. A table that can't be read (not created yet, no network) gives an empty list,
    since the page works without these courses.
    """
    try:
        rows = db.table("hrd_programmes").select(COLUMNS).contains("skills", [skill]).execute().data
    except Exception as e:
        print(f"could not read hrd_programmes ({type(e).__name__}); showing none")
        return []
    seen: set[tuple[str, str]] = set()
    out: list[Programme] = []
    for r in sorted(rows, key=lambda r: (_is_in_house(r["course_name"]), r["fee_after_discount_rm"], r["course_name"])):
        key = (r["training_provider"], r["course_name"])
        if key in seen:
            continue
        seen.add(key)
        out.append(Programme(**{**r, "in_house": _is_in_house(r["course_name"]), "fetched": str(r["fetched"]), "source_url": _list_url(r["source_url"])}))
    return out[:limit]
