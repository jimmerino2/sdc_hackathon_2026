from app.roadmap import esco


def fake(results):
    """A search that answers from a table of text -> [titles], and remembers what it was asked."""
    asked = []

    def search(text):
        asked.append(text)
        return [{"uri": f"u/{t}", "title": t} for t in results.get(text, [])]

    return search, asked


def test_what_is_searched_for_is_the_name_without_software_then_its_last_word():
    assert esco.variants("Structured query language SQL") == ["Structured query language SQL", "SQL"]
    assert esco.variants("Amazon Web Services AWS software") == ["Amazon Web Services AWS", "AWS"]
    assert esco.variants("Python") == ["Python"] and esco.variants("software") == []


def test_only_a_result_that_is_exactly_the_skill_counts(monkeypatch):
    search, _ = fake({"React": ["react to emergency situations in a live performance environment"], "Python": ["Python (computer programming)"]})
    monkeypatch.setattr(esco, "_search", search)
    assert esco.find("React") is None  # a fuzzy match is not the skill
    assert esco.find("Python") == {"uri": "u/Python (computer programming)", "title": "Python (computer programming)"}


def test_the_last_word_is_tried_when_the_full_name_finds_nothing(monkeypatch):
    search, asked = fake({"Structured query language SQL": ["use query languages"], "SQL": ["SQL"]})
    monkeypatch.setattr(esco, "_search", search)
    assert esco.find("Structured query language SQL")["title"] == "SQL" and asked == ["Structured query language SQL", "SQL"]


def test_an_esco_that_cannot_be_reached_is_just_not_found(monkeypatch):
    def down(text):
        raise OSError("no network")

    monkeypatch.setattr(esco, "_search", down)
    assert esco.find("Python") is None


def test_the_page_link_carries_the_skills_uri():
    assert esco.page("http://data.europa.eu/esco/skill/abc") == "https://esco.ec.europa.eu/en/classification/skill?uri=http://data.europa.eu/esco/skill/abc"
