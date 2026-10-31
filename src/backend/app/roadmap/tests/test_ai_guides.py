import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from app.roadmap import ai_skills, planner, service
from app.roadmap.planner import PlanNode, PlanSection
from app.roadmap.schemas import Source

PLAN = [PlanSection("Basics", [[PlanNode("a"), PlanNode("b", ["a"])], [PlanNode("c")]]), PlanSection("Ops", [[PlanNode("d")]])]
G1, G2 = ai_skills.BY_ID["ai:prompt-engineering"], ai_skills.BY_ID["ai:rag"]


def _guides():
    return {1: {"skill_id": G1.id, "title": G1.title, "description": "d"}, 2: {"skill_id": G2.id, "title": G2.title, "description": "d"}}


def _rows(plan, guides):
    return {r["skill_id"]: r for r in service.detail_rows(planner.with_guides(plan, guides), "r", "x")}


# ---------- the fixed list ----------

def test_the_list_has_thirteen_distinct_skills_with_short_titles_and_lines():
    cat = ai_skills.CATALOG
    assert len(cat) == 13 and len({s.id for s in cat}) == 13 and len({s.title.lower() for s in cat}) == 13
    assert all(len(s.title) <= 40 and len(s.description) <= planner.MAX_DESCRIPTION for s in cat)
    assert all(planner.is_guide(s.id) for s in cat) and not planner.is_guide("2.A.1.a") and not planner.is_guide("tech:python")


def test_each_skill_has_three_short_steps_and_two_youtube_videos():
    for s in ai_skills.CATALOG:
        assert len(s.steps) == 3 and all(0 < len(t) <= 90 for t in s.steps), s.id
        assert len(s.videos) == 2 and len({v.url for v in s.videos}) == 2, s.id
        for v in s.videos:
            u = urlparse(v.url)
            assert u.scheme == "https" and u.netloc == "www.youtube.com" and u.path == "/watch" and len(parse_qs(u.query)["v"][0]) == 11, v.url


def test_no_video_is_used_by_two_skills():
    urls = [v.url for s in ai_skills.CATALOG for v in s.videos]
    assert len(urls) == len(set(urls))


def test_a_roadmap_shows_an_ai_skill_with_its_fixed_steps_and_videos():
    g = service._guide(G1.id, G1.title, "Line written for the role.")
    assert g.description == "Line written for the role." and g.steps == list(G1.steps)
    assert [(s.source_type, s.title, s.url) for s in g.sources] == [("video", v.title, v.url) for v in G1.videos] and [s.rank for s in g.sources] == [1, 2]
    assert [Source(**s.model_dump()) for s in g.sources]
    assert service._guide(G1.id, G1.title, None).description == G1.description  # nothing stored: the skill's own line


def test_an_id_from_an_older_version_still_shows_with_what_is_stored():
    g = service._guide("ai:0123456789ab", "Old title", "Old line.")
    assert g.title == "Old title" and g.description == "Old line." and g.steps == [] and g.sources == []


# ---------- where they go in the plan ----------

def test_an_ai_skill_leads_the_first_unit_of_its_section_and_the_skills_wait_for_it():
    plan = planner.with_guides(PLAN, _guides())
    first = plan[0].units[0]
    assert first[0].skill_id == G1.id and first[0].previous_nodes == []
    assert all(n.previous_nodes[0] == G1.id and n.previous_nodes_required for n in first[1:])
    assert plan[0].units[1][0].previous_nodes == []  # later units open when the unit before is done, so they need no link
    assert plan[1].units[0][0].skill_id == G2.id


def test_nothing_in_a_section_is_open_until_its_ai_skill_is_done():
    rows = _rows(PLAN, _guides())
    assert rows[G1.id]["status"] == "available"
    assert rows["a"]["status"] == rows["b"]["status"] == rows["c"]["status"] == "locked"
    assert rows[G2.id]["status"] == "locked"  # the second section is not reached yet


def test_a_section_without_an_ai_skill_is_unchanged():
    assert planner.with_guides(PLAN, {2: _guides()[2]})[0] == PLAN[0]


def test_the_input_plan_is_not_changed():
    planner.with_guides(PLAN, _guides())
    assert [n.skill_id for n in PLAN[0].units[0]] == ["a", "b"] and PLAN[0].units[0][1].previous_nodes == ["a"]


def test_a_copied_plan_leaves_ai_skills_out():
    rows = [
        {"skill_id": G1.id, "section": 1, "unit": 1, "previous_nodes": [], "previous_nodes_required": True},
        {"skill_id": "a", "section": 1, "unit": 1, "previous_nodes": [G1.id], "previous_nodes_required": True},
    ]
    plan = service.plan_from_rows(rows)
    assert [n.skill_id for n in plan[0].units[0]] == ["a"] and plan[0].units[0][0].previous_nodes == []


# ---------- choosing them ----------

options_seen: dict = {}


def _model(monkeypatch, reply):
    sent = []
    options_seen.clear()
    monkeypatch.setattr(planner, "_complete", lambda messages, **options: sent.append(messages) or options_seen.update(options) or reply)
    monkeypatch.setattr(planner, "get_settings", lambda: SimpleNamespace(ai_model_mode="OPENROUTER", openrouter_api_key="k"))
    return sent


def pick(sections=3, existing=None):
    return planner.choose_guides("Data Scientists", "Develop and apply models.", sections, existing)


def test_the_model_picks_which_skills_and_in_what_order_and_writes_a_line_each(monkeypatch):
    _model(monkeypatch, '{"skills":[{"id":"ai:prompt-engineering","description":"Ask AI for the analysis you mean."},{"id":"ai:rag","description":"Ground answers in your data."}]}')
    got = pick(3)
    assert list(got) == [1, 2]  # two of three sections get one: it decides how many
    assert got[1] == {"skill_id": "ai:prompt-engineering", "title": "Prompt Engineering", "description": "Ask AI for the analysis you mean."}
    assert got[2]["skill_id"] == "ai:rag"


def test_the_model_sees_only_the_role_and_the_number_of_sections(monkeypatch):
    sent = _model(monkeypatch, '{"skills":[{"id":"ai:rag"}]}')
    pick(5)
    seen = json.loads(sent[0][1]["content"])
    assert set(seen) == {"role", "role_description", "sections", "catalog"} and seen["sections"] == 5 and seen["role"] == "Data Scientists"
    assert len(seen["catalog"]) == 13 and set(seen["catalog"][0]) == {"id", "title", "about"}


def test_it_is_asked_without_thinking_and_with_a_small_output(monkeypatch):
    _model(monkeypatch, '{"skills":[{"id":"ai:rag"}]}')
    pick()
    assert options_seen == {"reasoning": "off", "max_tokens": planner.GUIDE_MAX_TOKENS}


def test_unknown_ids_repeats_and_more_than_the_sections_are_dropped(monkeypatch):
    _model(monkeypatch, '{"skills":[{"id":"ai:made-up"},{"id":"ai:rag"},{"id":"ai:rag"},{"id":"ai:mcp"},{"id":"ai:agents-md"}]}')
    assert [g["skill_id"] for g in pick(2).values()] == ["ai:rag", "ai:mcp"]


def test_a_missing_or_long_line_falls_back_to_the_skills_own_or_is_cut(monkeypatch):
    _model(monkeypatch, '{"skills":[{"id":"ai:rag"},{"id":"ai:mcp","description":"' + "word " * 100 + '"}]}')
    got = pick(2)
    assert got[1]["description"] == ai_skills.BY_ID["ai:rag"].description and len(got[2]["description"]) <= planner.MAX_DESCRIPTION


def test_a_line_the_role_already_has_is_kept(monkeypatch):
    _model(monkeypatch, '{"skills":[{"id":"ai:rag","description":"New line."},{"id":"ai:mcp","description":"Fresh."}]}')
    got = pick(2, {"ai:rag": "Stored line."})
    assert got[1]["description"] == "Stored line." and got[2]["description"] == "Fresh."


def test_when_the_model_is_unusable_the_fixed_order_is_used_one_per_section(monkeypatch):
    sent = _model(monkeypatch, "not json")
    got = pick(4)
    assert [g["skill_id"] for g in got.values()] == [s.id for s in ai_skills.CATALOG[:4]]
    assert all(g["description"] == ai_skills.BY_ID[g["skill_id"]].description for g in got.values())
    assert len(sent) == 2  # one retry


def test_a_long_roadmap_never_gets_more_than_the_list_has(monkeypatch):
    _model(monkeypatch, "not json")
    assert len(pick(20)) == 13


def test_no_sections_no_skills(monkeypatch):
    sent = _model(monkeypatch, "not json")
    assert pick(0) == {} and not sent
