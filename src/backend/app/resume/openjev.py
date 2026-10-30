import httpx

from app.config import get_settings
from app.resume.vocab import candidates_for


def score_resume(text: str, vocab: list[str] | None = None) -> dict:
    """Ask the OpenJev server which candidate skills the resume shows, each with a probability.

    One request, one independent yes/no question per candidate skill about the same resume text. Skills
    whose probability is at or above the threshold count as present. Returns {"candidates", "skills"} with
    skills as [{"name", "score"}] sorted strongest first. Raises on any network, auth or response problem
    so the caller can report or fall back.
    """
    settings = get_settings()
    vocab = vocab if vocab is not None else candidates_for(text)
    questions = {
        f"skill_{i}": {"type": "noul", "instructions": f"Does this resume show the skill: {name}?"}
        for i, name in enumerate(vocab)
    }
    headers = {"Authorization": f"Bearer {settings.openjev_token}"} if settings.openjev_token else {}
    res = httpx.post(
        settings.openjev_url.rstrip("/") + "/v1/systemone",
        json={"model": "openjev", "state": text, "questions": questions},
        headers=headers,
        timeout=httpx.Timeout(60, connect=5),  # a stopped pod fails fast so the fallback starts at once
    )
    res.raise_for_status()
    answers = res.json()["answers"]

    scored = sorted(((float(answers[f"skill_{i}"]["noul"]), name) for i, name in enumerate(vocab)), reverse=True)
    skills = [{"name": name, "score": round(p, 3)} for p, name in scored if p >= settings.openjev_threshold]
    return {"candidates": len(vocab), "skills": skills}
