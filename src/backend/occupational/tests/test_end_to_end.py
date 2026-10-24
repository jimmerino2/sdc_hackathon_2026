"""The whole pipeline on SYNTHETIC ads in a temporary data dir, then the API on its outputs."""
from datetime import datetime, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from occupational import run, store
from occupational.sources import adzuna, hn

from .conftest import synthetic_hn_ads


@pytest.fixture
def built(data_dir, monkeypatch):
    monkeypatch.setattr(hn, "load_ads", lambda: synthetic_hn_ads())
    monkeypatch.setattr(adzuna, "load_ads", lambda: pd.DataFrame())
    health = {"hn_whoishiring": {"status": "synthetic_test"}}
    m = run.build(health, datetime(2025, 1, 15, tzinfo=timezone.utc), 0.0)
    return m


def test_pipeline_builds_and_promotes(built):
    m = built
    assert m["last_complete_month"] == "2024-12"
    for rel in ("latest/forecast.csv.gz", "latest/evaluation.json", "latest/backtest.csv.gz", "manifest.json",
                "datasets/demand_totals.csv", "datasets/emerging.csv", "taxonomy/skill_registry.json"):
        assert store.exists(rel), rel
    tot = store.read_table("datasets/demand_totals.csv")
    us = tot[(tot["country"] == "US") & (tot["occupation"] == "software_engineer")]
    assert (us["n_ads"] == 30).all()  # 3 of every 4 synthetic ads are software engineers in SF
    fc = store.read_table("latest/forecast.csv.gz")
    py = fc[(fc["skill_id"] == "python") & (fc["country"] == "US") & (fc["occupation"] == "software_engineer")]
    assert py["forecast"].between(0.3, 0.7).all()


def test_emerging_term_found_from_text(built):
    reg = store.read_json("taxonomy/skill_registry.json")
    z = [e for e in reg["skills"] if e["name"] == "Zorblang"]
    assert z and z[0]["status"] in ("newly_detected", "under_review") and z[0]["origin"] == "discovered"
    assert z[0]["evidence"] and "Zorblang" in z[0]["evidence"][0]["snippet"]


def test_failed_update_keeps_latest(built, monkeypatch):
    before = store.read_json("manifest.json")["run_id"]
    monkeypatch.setattr(hn, "load_ads", lambda: pd.DataFrame())
    with pytest.raises(RuntimeError):
        run.build({}, datetime(2025, 2, 15, tzinfo=timezone.utc), 0.0)
    assert store.read_json("manifest.json")["run_id"] == before
    assert store.exists("latest/forecast.csv.gz")


def test_api_serves_the_outputs(built):
    from app.main import app
    from app.occupational import service
    service._csv.cache_clear()
    service._json.cache_clear()
    c = TestClient(app)
    m = c.get("/occupational/meta").json()
    assert m["last_complete_month"] == "2024-12" and m["horizons"] == [3, 6, 12]
    s = c.get("/occupational/skills", params={"country": "US", "occupation": "software_engineer", "h": 6}).json()
    assert s["mode"] == "latest" and any(r["skill_id"] == "python" for r in s["rows"])
    d = c.get("/occupational/skills/python", params={"country": "US", "occupation": "software_engineer"}).json()
    assert len(d["history"]) == 72 and d["forecast"]
    assert c.get("/occupational/skills/nope", params={"country": "US", "occupation": "software_engineer"}).status_code == 404
    e = c.get("/occupational/emerging", params={"country": "US", "occupation": "software_engineer"}).json()
    assert e["rows"] and e["backcheck"]["skills"]
    a = c.get("/occupational/adoption", params={"occupation": "software_engineer"}).json()
    assert "not_found" in a and a["worker_usage"] == []  # no survey files in the test dir: shown as missing, not invented
    assert c.get("/occupational/evaluation").status_code == 200
    # emerging signals: no package data in the test dir, so adoption is missing (not zero) and nothing is validated
    g = c.get("/occupational/signals", params={"country": "US", "occupation": "software_engineer"}).json()
    assert g["status"] == "ok" and g["rows"]
    assert all(r["adoption_g6"] is None and r["adjusted_forecast"] is None for r in g["rows"])
    base = {r["skill_id"]: r["forecast"] for r in s["rows"]}
    assert all(abs(r["forecast"] - base[r["skill_id"]]) < 1e-12 for r in g["rows"])  # the baseline, unchanged
