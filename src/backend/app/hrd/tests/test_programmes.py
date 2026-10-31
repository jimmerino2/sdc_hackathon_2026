"""HRD Corp programmes for a skill, with a fake table so nothing touches the database."""
from fastapi.testclient import TestClient

from app.deps import get_supabase
from app.hrd import service
from app.main import app

client = TestClient(app)


def row(cid, name, fee, provider="Provider A", pct=0.0):
    return {"course_id": cid, "training_provider": provider, "course_name": name, "scheme": "HRD Corp Claimable Course",
            "certification": "Attendance/Completion", "fee_rm": fee, "discount_pct": pct, "fee_after_discount_rm": fee * (1 - pct / 100),
            "fetched": "2026-10-31", "source_url": "https://example.test/courses?page=1", "skills": ["Critical Thinking"]}


class FakeDb:
    """db.table(...).select(...).contains(column, values).execute().data, remembering what it was asked."""

    def __init__(self, rows=None, fail=False):
        self.rows, self.fail, self.asked = rows or [], fail, None

    def table(self, name):
        self.asked = {"table": name}
        return self

    def select(self, columns):
        return self

    def contains(self, column, values):
        self.asked.update(column=column, values=values)
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("no such table")
        return type("R", (), {"data": self.rows})()


def test_enrolable_courses_come_before_in_house_ones_then_cheaper_first():
    db = FakeDb([
        row(1, "(In-House Training) Critical Thinking", 4000),
        row(2, "Critical Thinking - Analytical Skills", 6400, "B"),
        row(3, "Critical Thinking", 3000, "C"),
    ])
    out = service.programmes_for(db, "Critical Thinking")
    assert [p.course_id for p in out] == [3, 2, 1]
    assert [p.in_house for p in out] == [False, False, True]
    assert db.asked == {"table": "hrd_programmes", "column": "skills", "values": ["Critical Thinking"]}


def test_the_same_course_listed_twice_counts_once_and_the_limit_applies():
    db = FakeDb([row(1, "Same", 100), row(2, "Same", 100), row(3, "Other", 200), row(4, "Third", 300)])
    out = service.programmes_for(db, "Critical Thinking", limit=2)
    assert [p.course_id for p in out] == [1, 3]


def test_the_link_carries_the_sort_the_list_was_read_in():
    plain = row(1, "A", 100)
    plain["source_url"] = "https://bizmatch.test/courses?page=7"
    sorted_already = row(2, "B", 200)
    sorted_already["source_url"] = "https://bizmatch.test/courses?status=&page=9&sortOrder=asc&sortCol=name"
    out = {p.course_id: p.source_url for p in service.programmes_for(FakeDb([plain, sorted_already]), "Critical Thinking")}
    assert out[1] == "https://bizmatch.test/courses?page=7&sortOrder=asc&sortCol=name"
    assert out[2] == "https://bizmatch.test/courses?status=&page=9&sortOrder=asc&sortCol=name"
    assert service._list_url("https://bizmatch.test/courses") == "https://bizmatch.test/courses?sortOrder=asc&sortCol=name"


def test_a_table_that_cannot_be_read_gives_none():
    assert service.programmes_for(FakeDb(fail=True), "Critical Thinking") == []


def test_endpoint_returns_the_courses_and_rejects_a_missing_skill():
    app.dependency_overrides[get_supabase] = lambda: FakeDb([row(7, "Critical Thinking", 1000, pct=50)])
    try:
        res = client.get("/hrd/programmes", params={"skill": "Critical Thinking"})
        assert res.status_code == 200
        body = res.json()
        assert body[0]["course_id"] == 7 and body[0]["fee_after_discount_rm"] == 500 and body[0]["in_house"] is False
        assert client.get("/hrd/programmes").status_code == 422
        assert client.get("/hrd/programmes", params={"skill": "x", "limit": 99}).status_code == 422
    finally:
        app.dependency_overrides.clear()
