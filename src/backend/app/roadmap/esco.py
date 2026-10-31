"""Looks a skill up in ESCO, the European Commission's skills taxonomy, so an AI skill can link to the real ESCO page of a skill in
its section. The search is ESCO's public web service (https://esco.ec.europa.eu/en/use-esco/use-esco-services-api), which needs no key.

ESCO's search is fuzzy: "React" finds "react to emergency situations", and "Amazon Web Services AWS software" finds "software
components libraries". A wrong link is worse than none, so a result only counts when its title is exactly the skill asked for
(ignoring a bracket such as "Python (computer programming)"); anything else is treated as not found."""
import json
import re
import urllib.parse
import urllib.request

SEARCH = "https://ec.europa.eu/esco/api/search"
PAGE = "https://esco.ec.europa.eu/en/classification/skill?uri="
TIMEOUT = 3  # seconds: a slow or unreachable ESCO must not hold up a roadmap
RESULTS = 5  # results read per search


def _head(title: str) -> str:
    """A title without its bracket, lower case: "Python (computer programming)" -> "python"."""
    return re.sub(r"\s*\(.*?\)", "", title).strip().lower()


def variants(name: str) -> list[str]:
    """What to search for, best first: the name without the word "software" (O*NET adds it to products), then its last word, which is
    usually the thing itself ("Structured query language SQL" -> "SQL", "Oracle Java" -> "Java")."""
    words = re.sub(r"\bsoftware\b", "", name, flags=re.I).split()
    if not words:
        return []
    return list(dict.fromkeys([" ".join(words), words[-1]]))


def _search(text: str) -> list[dict]:
    """ESCO's best skills for a text, each with its "uri" and "title". Raises if ESCO can't be reached or answers oddly."""
    query = urllib.parse.urlencode({"language": "en", "type": "skill", "text": text, "limit": RESULTS, "full": "false"})
    with urllib.request.urlopen(urllib.request.Request(f"{SEARCH}?{query}", headers={"User-Agent": "Jobee"}), timeout=TIMEOUT) as res:
        return json.load(res).get("_embedded", {}).get("results", [])


def find(name: str) -> dict | None:
    """The ESCO skill with exactly this name, as {"uri", "title"}; None if there is none or ESCO can't be reached."""
    for text in variants(name):
        try:
            for hit in _search(text):
                if _head(hit["title"]) == text.lower():
                    return {"uri": hit["uri"], "title": hit["title"]}
        except Exception as e:  # no network, a slow answer or an unexpected one: the AI skill just has fewer sources
            print(f"ESCO lookup for {text!r} failed ({type(e).__name__})")
            return None
    return None


def page(uri: str) -> str:
    """The ESCO portal page of a skill."""
    return PAGE + urllib.parse.quote(uri, safe=":/")
