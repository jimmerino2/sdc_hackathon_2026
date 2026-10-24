"""The one LLM call the Bonus Quests make, for writing them and for judging submissions."""
from openai import OpenAI

from app.config import get_settings
from app.roadmap.planner import _thinking_options

TIMEOUT = 180  # a judged repo is ~30k tokens of input; with reasoning on that can take a couple of minutes


def ask(messages: list[dict], max_tokens: int) -> str:
    """One chat completion at temperature 0, thinking as set by CHALLENGE_REASONING."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key, timeout=TIMEOUT)
    res = client.chat.completions.create(
        model=settings.openrouter_model, messages=messages, max_tokens=max_tokens, temperature=0,
        extra_body=_thinking_options(settings.challenge_reasoning, settings.openrouter_base_url),
    )
    return res.choices[0].message.content or ""
