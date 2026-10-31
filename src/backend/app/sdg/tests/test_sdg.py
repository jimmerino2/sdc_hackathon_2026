"""Role and skill SDG targets, read from the CSVs (the Supabase client is made to fail)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sdg import service

client = TestClient(app)


class NoDb:
    def table(self, name):
        raise ConnectionError("no database in tests")


@pytest.fixture(autouse=True)
def from_csv(monkeypatch):
    monkeypatch.setattr(service, "get_client", lambda: NoDb())
    for f in (service._roles, service._skills):
        f.cache_clear()
    yield
    for f in (service._roles, service._skills):
        f.cache_clear()


def test_parse_row():
    row = service.parse_row({"main_sdg": "SDG 9: Industry, Innovation, and Infrastructure",
                             "relevant_sdgs": "SDG 12 (Responsible Consumption and Production), SDG 13 (Climate Action)",
                             "targets": "9.1 resilient logistics · 12.b sustainable tourism · 13.1 low-carbon routes"})
    assert row == {"main_sdg": 9, "relevant_sdgs": [12, 13], "targets": [
        {"code": "9.1", "sdg": 9, "text": "resilient logistics"},
        {"code": "12.b", "sdg": 12, "text": "sustainable tourism"},
        {"code": "13.1", "sdg": 13, "text": "low-carbon routes"}]}


def test_role_with_its_skills():
    r = client.get("/sdg/roles/15-1255.00")  # Web and Digital Interface Designers
    assert r.status_code == 200
    body = r.json()
    assert body["main"]["sdg"] >= 1 and body["targets"]
    assert body["targets"][0]["sdg"] == body["main"]["sdg"]  # the main goal's targets come first
    assert body["main"]["sdg"] not in [g["sdg"] for g in body["relevant"]]
    assert body["skills"] and all(s["targets"] for s in body["skills"])


def test_unknown_role():
    assert client.get("/sdg/roles/00-0000.00").status_code == 404


def test_reevaluated_role_systems_analysts():
    r = client.get("/sdg/roles/15-1211.00")
    assert r.status_code == 200
    body = r.json()
    assert body["onet_code"] == "15-1211.00"
    assert body["main"]["sdg"] == 9
    assert sorted([g["sdg"] for g in body["relevant"]]) == [8, 17]
    assert len(body["targets"]) == 5
    target_codes = [t["code"] for t in body["targets"]]
    assert target_codes == ["9.1", "9.4", "9.c", "8.2", "17.8"]
    # Main SDG targets must precede relevant SDG targets
    assert [t["sdg"] for t in body["targets"][:3]] == [9, 9, 9]


def test_reevaluated_role_software_developers():
    r = client.get("/sdg/roles/15-1252.00")
    assert r.status_code == 200
    body = r.json()
    assert body["onet_code"] == "15-1252.00"
    assert body["main"]["sdg"] == 9
    # Confirm flawed SDGs 4 and 13 are no longer present
    relevant_ids = [g["sdg"] for g in body["relevant"]]
    assert 4 not in relevant_ids
    assert 13 not in relevant_ids
    assert sorted(relevant_ids) == [8, 17]
    assert len(body["targets"]) == 5
    target_codes = [t["code"] for t in body["targets"]]
    assert target_codes == ["9.5", "9.1", "9.4", "8.2", "17.8"]
    # Main SDG targets must precede relevant SDG targets
    assert [t["sdg"] for t in body["targets"][:3]] == [9, 9, 9]

