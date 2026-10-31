"""POST /forecast/sync and pipeline/sync_trends.py: the switch, one run at a time, and failing without touching the data."""
import json
import subprocess
import sys
import threading
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.forecast import sync
from app.main import app

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "pipeline"))
import sync_trends  # noqa: E402

client = TestClient(app)
SUMMARY = {"pulled": True, "pull_problem": None, "manual_edits": 0,
           "before": {"as_of": "2026-10-09", "forecast_from": "2026-08"}, "after": {"as_of": "2026-10-23", "forecast_from": "2026-09"}}


def _signals() -> pd.DataFrame:
    row = {"series": "job_postings_index", "geo": "US", "sector": "Marketing", "value": 100.0, "as_of_date": "2026-10-23"}
    return pd.DataFrame([{**row, "month": m} for m in ("2026-05", "2026-06", "2026-07")])


def _finished(monkeypatch, returncode=0, stdout=json.dumps(SUMMARY), stderr=""):
    monkeypatch.setattr(sync.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout, stderr))


def test_off_unless_allowed(monkeypatch):
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", False)
    monkeypatch.setattr(sync, "run", lambda: pytest.fail("the script must not run"))
    assert client.post("/forecast/sync").status_code == 403


def test_returns_the_summary_and_rereads_the_files(monkeypatch):
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", True)
    _finished(monkeypatch)
    cleared = []
    monkeypatch.setattr(sync.service, "clear_caches", lambda: cleared.append("tables"))
    monkeypatch.setattr(sync.retrain, "clear", lambda: cleared.append("retrains"))
    res = client.post("/forecast/sync")
    assert res.status_code == 200 and res.json()["after"]["as_of"] == "2026-10-23"
    assert sorted(cleared) == ["retrains", "tables"]


def test_a_failed_run_says_so_and_keeps_what_is_cached(monkeypatch):
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", True)
    _finished(monkeypatch, returncode=1, stdout="", stderr="signals.csv: Marketing 2026-06 (US) is there twice.")
    monkeypatch.setattr(sync.service, "clear_caches", lambda: pytest.fail("nothing changed, so nothing to re-read"))
    res = client.post("/forecast/sync")
    assert res.status_code == 502 and "current data was kept" in res.json()["detail"]


def test_one_run_at_a_time(monkeypatch):
    monkeypatch.setattr(get_settings(), "forecast_refresh_enabled", True)
    release, started = threading.Event(), threading.Event()

    def slow(*a, **k):
        started.set()
        release.wait(5)
        return subprocess.CompletedProcess(a, 0, json.dumps(SUMMARY), "")

    monkeypatch.setattr(sync.subprocess, "run", slow)
    monkeypatch.setattr(sync.service, "clear_caches", lambda: None)
    monkeypatch.setattr(sync.retrain, "clear", lambda: None)
    first = threading.Thread(target=lambda: client.post("/forecast/sync"))
    first.start()
    started.wait(5)
    assert client.post("/forecast/sync").status_code == 409
    release.set()
    first.join()


def test_a_changed_figure_counts_as_a_hand_edit(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_trends, "SNAPSHOT", tmp_path / "last.csv")
    _signals().to_csv(tmp_path / "last.csv", index=False)
    edited = _signals()
    assert sync_trends.hand_edits(edited) == 0
    edited.loc[1, "value"] = 45.0
    assert sync_trends.hand_edits(edited) == 1


def test_no_copy_to_compare_means_no_hand_edits(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_trends, "SNAPSHOT", tmp_path / "missing.csv")
    assert sync_trends.hand_edits(_signals()) == 0


def test_a_second_row_for_a_month_stops_the_run(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_trends, "SNAPSHOT", tmp_path / "missing.csv")
    df = _signals()
    with pytest.raises(SystemExit, match="twice"):
        sync_trends.hand_edits(pd.concat([df, df.tail(1)]))


def _ai_tables(monkeypatch, tmp_path):
    for name in ("a.csv", "b.csv"):
        (tmp_path / name).write_text("x\n1\n")
    monkeypatch.setattr(sync_trends, "AI_TABLES", tmp_path)
    monkeypatch.setattr(sync_trends, "AI_STATE", tmp_path / "state.json")
    monkeypatch.setattr(sync_trends, "RAW", tmp_path)
    monkeypatch.setattr(sync_trends, "AI_TARGETS", {"one": ("One", ["a.csv"]), "two": ("Two", ["b.csv"])})


def _forecast_ran(monkeypatch, ran, status="updated"):
    monkeypatch.setattr(sync_trends, "reforecast", lambda t: (ran.append(t), {"target": t, "name": t, "status": status})[1])


def test_only_a_changed_table_is_forecast_again(monkeypatch, tmp_path):
    _ai_tables(monkeypatch, tmp_path)
    ran = []
    _forecast_ran(monkeypatch, ran)
    assert len(sync_trends.reforecast_changed()) == 2
    ran.clear()
    assert sync_trends.reforecast_changed() == [] and ran == []
    (tmp_path / "b.csv").write_text("x\n2\n")
    sync_trends.reforecast_changed()
    assert ran == ["two"]


def test_a_failed_forecast_is_tried_again_next_time(monkeypatch, tmp_path):
    _ai_tables(monkeypatch, tmp_path)
    ran = []
    _forecast_ran(monkeypatch, ran, status="failed")
    sync_trends.reforecast_changed()
    ran.clear()
    sync_trends.reforecast_changed()
    assert sorted(ran) == ["one", "two"]


def test_a_stale_source_is_reported(monkeypatch):
    monkeypatch.setattr(sync_trends.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "h=1: not promoted: target source is stale", ""))
    assert sync_trends.reforecast("worker_genai_use_rate")["status"] == "stale"


def test_rewind_drops_later_months_and_their_dates():
    kept = sync_trends.rewind(_signals(), "2026-06")
    assert kept["month"].tolist() == ["2026-05", "2026-06"]
    assert kept["as_of_date"].max() == "2026-06-30"


def test_training_reads_the_signals_in_the_folder_it_was_given(monkeypatch, tmp_path):
    """Sync trains on its work folder. Reading the default signals.csv instead would put a new date on old numbers."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ml"))
    import train_lgbm

    pd.DataFrame({"sector": ["only here"]}).to_csv(tmp_path / "signals.csv", index=False)

    class Stop(Exception):
        pass

    def stop(args, data_dir, signals=None, **k):
        assert signals is not None and signals["sector"].tolist() == ["only here"]
        raise Stop

    monkeypatch.setattr(train_lgbm, "train_all", stop)
    monkeypatch.setattr(sys, "argv", ["train_lgbm.py", "--data", str(tmp_path / "model_table_US.csv")])
    with pytest.raises(Stop):
        train_lgbm.main()


def test_a_failed_pull_uses_the_last_copy(monkeypatch, tmp_path):
    for name in sync_trends.refresh.REPOS:
        (tmp_path / name / ".git").mkdir(parents=True)
    monkeypatch.setattr(sync_trends, "RAW", tmp_path)

    def down(timeout=None):
        raise subprocess.TimeoutExpired("git", timeout)

    monkeypatch.setattr(sync_trends.refresh, "pull", down)
    assert "last copy" in sync_trends.pulled()


def test_a_failed_pull_with_no_copy_stops(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_trends, "RAW", tmp_path)
    monkeypatch.setattr(sync_trends.refresh, "pull", lambda timeout=None: (_ for _ in ()).throw(OSError("no git")))
    with pytest.raises(OSError):
        sync_trends.pulled()
