from app.forecast import service


def test_sources_name_publisher_and_dates_come_from_the_data():
    by_id = {s.id: s for s in service.sources()}
    postings = by_id["indeed_postings"]
    assert postings.name == "Indeed Job Postings Index" and postings.publisher == "Indeed Hiring Lab"
    assert postings.as_of and len(postings.as_of) == 10
    assert postings.latest_month == str(service._table().iloc[0]["origin_month"])
    assert by_id["indeed_ai_tracker"].url.startswith("https://")


def test_sources_follow_a_refreshed_manifest(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"signals_as_of": {"job_postings_index": "2030-01-02", "ai_postings_share": "2030-01-01"}}')
    monkeypatch.setattr(service, "MANIFEST", manifest)
    by_id = {s.id: s for s in service.sources()}
    assert by_id["indeed_postings"].as_of == "2030-01-02"
    assert by_id["indeed_ai_tracker"].as_of == "2030-01-01"


def test_job_history_ends_at_today_with_zero_change():
    job = service.list_jobs("11-2021.00", None, "Baseline", 12)[0]
    assert job.history[-1].month == job.forecast_from and job.history[-1].change_pct == 0
    assert len(job.history) == service.HISTORY_MONTHS + 1
    assert [h.month for h in job.history] == sorted(h.month for h in job.history)
