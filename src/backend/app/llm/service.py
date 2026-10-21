from openai import OpenAI

from app.config import get_settings


def chat(prompt: str) -> str:
    settings = get_settings()
    client = OpenAI(
        base_url="https://llm.grafilab.ai/v1",
        api_key=settings.openrouter_api_key,
    )
    res = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def complete(prompt: str, *, system: str | None = None, model: str | None = None, max_tokens: int = 1000) -> str:
    """One chat call with an optional system message and model override; temperature 0, 60 s timeout."""
    settings = get_settings()
    client = OpenAI(base_url="https://llm.grafilab.ai/v1", api_key=settings.openrouter_api_key, timeout=60)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(
        model=model or settings.openrouter_model, messages=messages, max_tokens=max_tokens, temperature=0
    )
    return res.choices[0].message.content or ""
