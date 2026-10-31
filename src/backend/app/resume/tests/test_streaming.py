"""The resume endpoint's progress events, with the model replaced so nothing is called over the network."""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.resume import gateway, service
from app.resume.gateway import finished_skills

client = TestClient(app)
PDF = b"%PDF-1.4 fake"


def _events(res) -> list[dict]:
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def test_finished_skills_waits_for_a_whole_entry():
    answer = '{"skills": [{"name": "Python", "score": 0.9}, {"name": "SQ'
    found, end = finished_skills(answer)
    assert found == [("Python", 0.9)]
    more, _ = finished_skills(answer + 'L", "score": 0.7}]}', end)
    assert more == [("SQL", 0.7)]


def test_finished_skills_unescapes_names():
    found, _ = finished_skills(r'{"name": "Oracle \"Java\"", "score": 1}')
    assert found == [('Oracle "Java"', 1.0)]


def test_stream_reports_each_skill_then_the_result(monkeypatch):
    monkeypatch.setattr(service, "extract_pdf_text", lambda data: {"text": "Python", "page_count": 1, "pages_read": 1, "char_count": 6})
    monkeypatch.setattr(service, "candidates_for", lambda text: ["Python", "SQL"])

    def fake_score(text, vocab, on_skill=None, on_thinking=None):
        on_skill("Python", 0.9)
        on_skill("SQL", 0.6)
        return {"candidates": len(vocab), "skills": [{"name": "Python", "score": 0.9}, {"name": "SQL", "score": 0.6}]}

    monkeypatch.setattr(gateway, "score_resume", fake_score)
    res = client.post("/resume/stream", files={"file": ("cv.pdf", PDF, "application/pdf")})
    kinds = [e["type"] for e in _events(res)]
    assert kinds == ["read", "candidates", "engine", "skill", "skill", "result"]
    result = _events(res)[-1]
    assert [s["name"] for s in result["skills"]] == ["Python", "SQL"]
    assert result["engine"]["source"] == "llm"


def test_a_bad_file_is_rejected_before_streaming_starts():
    res = client.post("/resume/stream", files={"file": ("cv.pdf", b"not a pdf", "application/pdf")})
    assert res.status_code == 400


def test_stream_sends_the_expected_time_and_thins_out_reasoning_events(monkeypatch):
    monkeypatch.setattr(service, "extract_pdf_text", lambda data: {"text": "Python", "page_count": 1, "pages_read": 1, "char_count": 6})
    monkeypatch.setattr(service, "candidates_for", lambda text: ["Python"])
    monkeypatch.setattr(service.get_settings(), "resume_thinking", False)

    def fake_score(text, vocab, on_skill=None, on_thinking=None):
        for chars in (500, 1000, 1500):  # arrive within the same second: one event gets through
            on_thinking(chars)
        return {"candidates": 1, "skills": [{"name": "Python", "score": 0.9}]}

    monkeypatch.setattr(gateway, "score_resume", fake_score)
    events = _events(client.post("/resume/stream", files={"file": ("cv.pdf", PDF, "application/pdf")}))
    assert events[0]["expected_seconds"] == 8
    assert [e for e in events if e["type"] == "thinking"] == [{"type": "thinking", "words": 100}]


def test_the_result_names_the_model_from_the_settings(monkeypatch):
    monkeypatch.setattr(service, "candidates_for", lambda text: ["Python"])
    monkeypatch.setattr(service.get_settings(), "openrouter_model", "gemini/some-model")
    monkeypatch.setattr(gateway, "score_resume", lambda text, vocab, on_skill=None, on_thinking=None: {"candidates": 1, "skills": [{"name": "Python", "score": 0.9}]})
    result = service.extract_skills("Python")
    assert result["error"] is None
    assert result["engine"]["source"] == "llm" and result["engine"]["model"] == "gemini/some-model"
    assert result["top_skills"] == [{"name": "Python", "score": 0.9}]


def test_a_failing_model_gives_an_error_instead_of_raising(monkeypatch):
    monkeypatch.setattr(service, "candidates_for", lambda text: ["Python"])

    def boom(*a, **k):
        raise RuntimeError("gateway down")

    monkeypatch.setattr(gateway, "score_resume", boom)
    result = service.extract_skills("Python")
    assert result["skills"] is None and result["error"]
