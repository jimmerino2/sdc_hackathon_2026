from collections.abc import Callable, Iterator

from openai import OpenAI

from app.config import get_settings


def chat(prompt: str) -> str:
    settings = get_settings()
    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )
    res = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def complete(prompt: str, *, system: str | None = None, model: str | None = None, max_tokens: int = 1000, thinking: bool = True) -> str:
    """One chat call with an optional system message and model override; temperature 0, 60 s timeout.

    thinking=False turns the model's hidden reasoning off (Grafilab's chat-template switch), for short answers
    that should come back in a few seconds.
    """
    settings = get_settings()
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key, timeout=60)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(
        model=model or settings.openrouter_model, messages=messages, max_tokens=max_tokens, temperature=0,
        extra_body=None if thinking else {"chat_template_kwargs": {"enable_thinking": False}},
    )
    return res.choices[0].message.content or ""


def complete_stream(prompt: str, *, system: str | None = None, model: str | None = None, max_tokens: int = 1000, thinking: bool = True,
                    on_reasoning: Callable[[int], None] | None = None) -> Iterator[str]:
    """Like complete(), but yields the answer in pieces as the model writes it.

    on_reasoning(total_chars) is called as the model's hidden reasoning comes in, which is most of the wait when thinking is on.
    """
    settings = get_settings()
    client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key, timeout=60)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(
        model=model or settings.openrouter_model, messages=messages, max_tokens=max_tokens, temperature=0, stream=True,
        extra_body=None if thinking else {"chat_template_kwargs": {"enable_thinking": False}},
    )
    reasoned = 0
    for chunk in res:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if reasoning and on_reasoning:
            reasoned += len(reasoning)
            on_reasoning(reasoned)
        if delta.content:
            yield delta.content
