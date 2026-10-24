"""Taxonomy, classification, country parsing, skill matching and normalisation rules."""
import pandas as pd
import pytest

from occupational import normalize, store, taxonomy as T


def test_occupation_titles(data_dir):
    assert T.occupations_in("Acme | Senior Backend Engineer | Remote (US)") == ["software_engineer"]
    assert T.occupations_in("Acme | Machine Learning Engineer | NYC") == ["ml_engineer"]
    assert set(T.occupations_in("Acme | Software Engineer & Data Scientist | SF")) == {"software_engineer", "data_scientist"}
    assert T.occupations_in("Acme | BI Analyst | London") == ["data_analyst"]
    assert T.occupations_in("Acme | Product Marketing Lead | SF") == []


def test_body_titles_only_count_in_singular(data_dir):
    # "work with our data scientists" in a software post is not a data-scientist job
    assert T.occupations_in("Acme | Backend Engineer | SF", "You will work with our data scientists.") == ["software_engineer"]
    assert "data_scientist" in T.occupations_in("Acme | SF", "We are hiring a Data Scientist to own experiments.")


def test_countries(data_dir):
    assert T.countries_in("Acme | Remote (US) | Full-time") == ["US"]
    assert set(T.countries_in("Acme | London or Berlin | ONSITE")) == {"GB", "DE"}
    assert T.countries_in("Acme | REMOTE | Full-time") == []
    assert T.countries_in("Acme | Austin, TX") == ["US"]


@pytest.mark.parametrize("text,yes,no", [
    ("Our stack: Java, Kotlin and Postgres", {"java", "kotlin", "postgres"}, {"javascript"}),
    ("Frontend in JavaScript and TypeScript", {"javascript", "typescript"}, {"java"}),
    ("Systems work in C++ and Rust", {"cpp", "rust"}, {"c", "csharp"}),
    ("Services in Go, Python", {"go", "python"}, set()),
    ("Let's go to market fast", set(), {"go"}),
    ("Analysis in R, SQL and Python", {"r_lang", "sql", "python"}, set()),
    ("Built with React Native", {"react_native"}, {"react"}),
    ("We use Cursor and Claude Code daily", {"ai_assisted_dev"}, set()),
])
def test_skill_matching(data_dir, text, yes, no):
    found = set(T.match_skills(text))
    assert yes <= found
    assert not (no & found)


def test_spelling_keys(data_dir):
    assert T.key("Next.js") == T.key("NextJS") == T.key("next js") == "nextjs"
    assert T.key("Agents") == "agent"
    assert T.literal_keys(r"postgres(ql)?") == {T.key("postgres"), "postgresql"}
    assert T.literal_keys(r"react(?![ -]native)(\.js|js)?") == {"react", "reactjs"}
    assert T.literal_keys(r"\bml\b") == {"ml"}
    assert T.literal_keys(r"CI(?=\s*[,/)]|\s+pipelines?)") == {"ci"}


def _raw(rows):
    base = {"source": "hn_whoishiring", "thread_id": "t1", "month": "2026-01", "retrieved_at": "2026-10-01",
            "employer": "Acme", "url": ""}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_dedupe_and_eligibility(data_dir):
    long = "Acme | Software Engineer | SF\n" + "Python and Postgres. " * 20
    raw = _raw([
        {"source_id": "1", "author": "a", "posted_at": "2026-01-02", "title_raw": long.split("\n")[0], "location_raw": long.split("\n")[0], "text": long},
        {"source_id": "2", "author": "a", "posted_at": "2026-01-03", "title_raw": long.split("\n")[0], "location_raw": long.split("\n")[0], "text": long + " again"},
        {"source_id": "3", "author": "b", "posted_at": "2026-01-04", "title_raw": "Beta | Software Engineer | SF", "location_raw": "Beta | SF", "text": "Beta | Software Engineer | SF\nshort"},
        {"source_id": "4", "author": "c", "posted_at": "2026-01-05", "title_raw": long.split("\n")[0], "location_raw": long.split("\n")[0], "text": long},
    ])
    d = normalize.normalize(raw).set_index("source_id")
    assert not d.loc["1", "is_duplicate"] and d.loc["1", "eligible"]
    assert d.loc["2", "is_duplicate"]                      # same author, same thread
    assert d.loc["4", "is_duplicate"]                      # same opening text, same month
    assert not d.loc["3", "eligible"] and d.loc["3", "ineligible_reason"] == "missing or short description"
    assert d.loc["1", "available_at"] == "2026-02-01"      # a month counts once it is over
    assert d.loc["1", "countries"] == "US" and d.loc["1", "occupations"] == "software_engineer"


def test_known_skill_cache_reuses_and_refreshes(data_dir):
    long = "Acme | Software Engineer | SF\n" + "We use Python and Postgres. " * 10
    ads = normalize.normalize(_raw([{"source_id": "1", "author": "a", "posted_at": "2026-01-02",
                                     "title_raw": long.split("\n")[0], "location_raw": long.split("\n")[0], "text": long}]))
    first = normalize.extract_known(ads)
    assert set(first["skill_id"]) >= {"python", "postgres"}
    assert store.exists(normalize.CACHE)
    second = normalize.extract_known(ads)
    assert sorted(second["skill_id"]) == sorted(first["skill_id"])


def test_store_keeps_last_good_table(data_dir):
    store.write_table("datasets/x.csv", pd.DataFrame({"a": [1]}))
    with pytest.raises(store.EmptyUpdate):
        store.write_table("datasets/x.csv", pd.DataFrame({"a": []}))
    assert len(store.read_table("datasets/x.csv")) == 1
