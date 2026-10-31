import httpx

from app.config import get_settings
from app.resume.vocab import candidates_for

CHECK_SECONDS = 3


def _headers() -> dict:
    token = get_settings().openjev_token
    return {"Authorization": f"Bearer {token}"} if token else {}


def is_available() -> bool:
    """True if the OpenJev server is up and its model is loaded, so a resume can go to it now.

    Asks the server's /ping, which answers 200 only once the model is ready; a stopped endpoint, a worker still
    loading the model (about 7 minutes cold), a bad token or a network problem all count as not available. Never
    raises, and gives up in a few seconds so the caller can use the LLM at once. A load-balancing endpoint may start
    a worker when it is pinged, so with workers scaled down this can wake one for a later resume.
    """
    settings = get_settings()
    if not settings.openjev_url:
        return False
    try:
        res = httpx.get(settings.openjev_url.rstrip("/") + "/ping", headers=_headers(), timeout=httpx.Timeout(CHECK_SECONDS, connect=CHECK_SECONDS))
    except httpx.HTTPError:
        return False
    return res.status_code == 200


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
    res = httpx.post(
        settings.openjev_url.rstrip("/") + "/v1/systemone",
        json={"model": "openjev", "state": text, "questions": questions},
        headers=_headers(),
        timeout=httpx.Timeout(60, connect=5),  # a stopped pod fails fast so the fallback starts at once
    )
    res.raise_for_status()
    answers = res.json()["answers"]

    scored = sorted(((float(answers[f"skill_{i}"]["noul"]), name) for i, name in enumerate(vocab)), reverse=True)
    skills = [{"name": name, "score": round(p, 3)} for p, name in scored if p >= settings.openjev_threshold]
    return {"candidates": len(vocab), "skills": skills}
