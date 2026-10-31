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
