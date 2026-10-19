from openai import OpenAI

from app.config import get_settings


def chat(prompt: str) -> str:
    settings = get_settings()
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    res = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content
