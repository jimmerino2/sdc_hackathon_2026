from types import SimpleNamespace

from app.roadmap import planner, service
from app.roadmap.planner import PlanNode, PlanSection

NAMES = {"a": "Python", "b": "SQL", "c": "Git", "d": "Docker"}
PLAN = [PlanSection("Basics", [[PlanNode("a"), PlanNode("b", ["a"])], [PlanNode("c")]]), PlanSection("Ops", [[PlanNode("d")]])]
CODE = "15-1252.00"


def _guides(titles=("AI for basics", "AI for ops")):
    return {i: {"skill_id": planner.ai_skill_id(CODE, t), "title": t, "description": "d", "steps": []} for i, t in enumerate(titles, start=1)}


def _rows(plan, guides):
    return {r["skill_id"]: r for r in service.detail_rows(planner.with_guides(plan, guides), "r", "x")}


def test_an_ai_skill_leads_the_first_unit_of_its_section_and_the_skills_wait_for_it():
    g = _guides()
    plan = planner.with_guides(PLAN, g)
    first = plan[0].units[0]
    assert first[0].skill_id == g[1]["skill_id"] and first[0].previous_nodes == []
    assert all(n.previous_nodes[0] == g[1]["skill_id"] and n.previous_nodes_required for n in first[1:])
    assert plan[0].units[1][0].previous_nodes == []  # later units open when the unit before is done, so they need no link
    assert plan[1].units[0][0].skill_id == g[2]["skill_id"]


def test_nothing_in_a_section_is_open_until_its_ai_skill_is_done():
    g = _guides()
    rows = _rows(PLAN, g)
    assert rows[g[1]["skill_id"]]["status"] == "available"
    assert rows["a"]["status"] == rows["b"]["status"] == rows["c"]["status"] == "locked"
    assert rows[g[2]["skill_id"]]["status"] == "locked"  # the second section is not reached yet


def test_a_section_without_an_ai_skill_is_unchanged():
    assert planner.with_guides(PLAN, {2: _guides()[2]})[0] == PLAN[0]


def test_the_input_plan_is_not_changed():
    planner.with_guides(PLAN, _guides())
    assert [n.skill_id for n in PLAN[0].units[0]] == ["a", "b"] and PLAN[0].units[0][1].previous_nodes == ["a"]


def test_a_copied_plan_leaves_ai_skills_out():
    gid = planner.ai_skill_id(CODE, "AI for basics")
    rows = [
        {"skill_id": gid, "section": 1, "unit": 1, "previous_nodes": [], "previous_nodes_required": True},
        {"skill_id": "a", "section": 1, "unit": 1, "previous_nodes": [gid], "previous_nodes_required": True},
    ]
    plan = service.plan_from_rows(rows)
    assert [n.skill_id for n in plan[0].units[0]] == ["a"] and plan[0].units[0][0].previous_nodes == []


def test_the_same_title_for_the_same_role_is_the_same_skill():
    assert planner.ai_skill_id(CODE, "AI for Basics") == planner.ai_skill_id(CODE, "  ai   for basics ")
    assert planner.ai_skill_id(CODE, "AI for basics") != planner.ai_skill_id("15-2051.00", "AI for basics")
    assert planner.is_guide(planner.ai_skill_id(CODE, "x")) and not planner.is_guide("2.A.1.a") and not planner.is_guide("tech:python")


options_seen: dict = {}


def _model(monkeypatch, reply):
    sent = []
    options_seen.clear()
    monkeypatch.setattr(planner, "_complete", lambda messages, **options: sent.append(messages) or options_seen.update(options) or reply)
    monkeypatch.setattr(planner, "get_settings", lambda: SimpleNamespace(ai_model_mode="OPENROUTER", openrouter_api_key="k"))
    return sent


def write(plan=PLAN, existing=None):
    return planner.write_guides("Role", CODE, plan, NAMES, existing)


def test_the_model_writes_one_per_section_and_gets_the_skill_names(monkeypatch):
    sent = _model(monkeypatch, '{"guides":[{"section":1,"title":"AI for web basics","description":"Use AI to explain Python and SQL.","steps":["Ask it to explain loops.","","Check the docs."]},'
                               '{"section":2,"title":"AI for ops","description":"Use AI to learn Docker.","steps":[]},{"section":9,"title":"x","description":"y"}]}')
    got = write()
    assert set(got) == {1, 2}  # an unknown section is dropped
    assert got[1]["title"] == "AI for web basics" and got[1]["steps"] == ["Ask it to explain loops.", "Check the docs."]
    assert got[1]["skill_id"] == planner.ai_skill_id(CODE, "AI for web basics")
    assert "Python" in sent[0][1]["content"] and "Docker" in sent[0][1]["content"]


def test_a_section_the_model_skips_gets_the_fallback(monkeypatch):
    _model(monkeypatch, '{"guides":[{"section":1,"title":"AI for web basics","description":"Use AI to explain Python and SQL."}]}')
    got = write()
    assert got[1]["title"] == "AI for web basics" and got[2]["title"] == "AI for Ops" and "Docker" in got[2]["description"]


def test_when_the_model_is_unusable_every_section_still_gets_one_with_its_own_title(monkeypatch):
    sent = _model(monkeypatch, "not json")
    got = write()
    assert [g["title"] for g in got.values()] == ["AI for Basics", "AI for Ops"]
    assert len({g["skill_id"] for g in got.values()}) == 2
    assert len(sent) == 2  # one retry


def test_two_sections_never_share_a_skill(monkeypatch):
    _model(monkeypatch, '{"guides":[{"section":1,"title":"AI study","description":"a"},{"section":2,"title":"ai  STUDY","description":"b"}]}')
    got = write()
    assert got[1]["skill_id"] != got[2]["skill_id"] and got[2]["title"] == "ai STUDY 2"


def test_an_ai_skill_the_role_already_has_is_reused_not_rewritten(monkeypatch):
    sent = _model(monkeypatch, '{"guides":[{"section":1,"title":"AI for web basics","description":"Fresh text.","steps":["new"]},{"section":2,"title":"AI for ops","description":"x"}]}')
    old = {planner.norm_title("AI for web basics"): {"title": "AI for web basics", "description": "Stored text.", "steps": ["old"]}}
    got = write(existing=old)
    assert got[1]["description"] == "Stored text." and got[1]["steps"] == ["old"]
    assert got[1]["skill_id"] == planner.ai_skill_id(CODE, "AI for web basics")
    assert got[2]["description"] == "x"  # not stored before, so the model's own
    assert "AI for web basics" in sent[0][1]["content"]  # the model is told which titles exist


def test_a_section_with_no_known_skills_gets_none(monkeypatch):
    _model(monkeypatch, '{"guides":[]}')
    assert write([PlanSection("Empty", [[PlanNode("zzz")]])]) == {}


def test_at_most_the_stored_number_of_sections_get_one(monkeypatch):
    _model(monkeypatch, "not json")
    many = [PlanSection(f"S{i}", [[PlanNode("a")]]) for i in range(12)]
    assert set(write(many)) == set(range(1, planner.MAX_GUIDES + 1))


def test_details_are_kept_short():
    long = "word " * 100
    got = planner.sanitize_guides({"guides": [{"section": 1, "title": "t", "description": long, "steps": [long, "b", "c", "d", "e"]}]}, [1])[1]
    assert len(got["description"]) <= planner.MAX_DESCRIPTION
    assert len(got["steps"]) == planner.MAX_STEPS and all(len(s) <= planner.MAX_STEP for s in got["steps"])
    fb = planner.fallback_guide("Basics", ["Python", "SQL"])
    assert len(fb["description"]) <= planner.MAX_DESCRIPTION and len(fb["steps"]) <= planner.MAX_STEPS and all(len(s) <= planner.MAX_STEP for s in fb["steps"])


def test_the_model_is_asked_without_thinking_and_with_a_small_output(monkeypatch):
    _model(monkeypatch, "not json")
    write()
    assert options_seen == {"reasoning": "off", "max_tokens": planner.GUIDE_MAX_TOKENS}


HITS = {"Python": {"uri": "u/python", "title": "Python (computer programming)"}, "SQL": {"uri": "u/sql", "title": "SQL"},
        "Git": {"uri": "u/git", "title": "Git"}, "Docker": {"uri": "u/docker", "title": "Docker"}}


def sourced(guides, find=lambda n: HITS.get(n)):
    return planner.attach_sources(PLAN, guides, NAMES, find, lambda uri: f"https://esco.test/?uri={uri}")


def test_each_ai_skill_gets_its_own_esco_pages_then_a_taxonomy_reference():
    got = sourced(_guides())
    one, two = got[1]["sources"], got[2]["sources"]
    assert [s["title"] for s in one] == ["ESCO: Python (computer programming)", "ESCO: SQL", "ESCO skills services and API"]
    assert [s["title"] for s in two] == ["ESCO: Docker", "Lightcast skills taxonomy"]
    assert [s["rank"] for s in one] == [1, 2, 3] and all(s["source_type"] == "reference" for s in one)
    assert not {s["url"] for s in one} & {s["url"] for s in two}  # none shared


def test_an_esco_page_is_used_once_in_a_roadmap():
    same = {"uri": "u/x", "title": "X"}
    got = sourced(_guides(), lambda n: same)
    assert [s["title"] for s in got[1]["sources"]][0] == "ESCO: X"
    assert not any(s["title"] == "ESCO: X" for s in got[2]["sources"])


def test_when_esco_has_nothing_every_ai_skill_still_has_a_source():
    got = sourced(_guides(), lambda n: None)
    assert [len(g["sources"]) for g in got.values()] == [1, 1]
    assert got[1]["sources"][0]["url"] != got[2]["sources"][0]["url"]  # the three taxonomies are handed out in turn
    assert all(s["url"].startswith("https://") for g in got.values() for s in g["sources"])


def test_a_reused_ai_skill_keeps_the_sources_it_was_written_with():
    g = _guides()
    g[1]["sources"] = [{"source_type": "reference", "rank": 1, "title": "Old", "url": "https://old.test", "duration_minutes": None}]
    got = sourced(g)
    assert got[1]["sources"][0]["title"] == "Old" and len(got[1]["sources"]) == 1
    assert got[2]["sources"][0]["title"] == "ESCO: Docker"


def test_sources_fit_the_roadmaps_own_source_schema():
    from app.roadmap.schemas import Source

    for g in sourced(_guides()).values():
        assert [Source(**s) for s in g["sources"]]
