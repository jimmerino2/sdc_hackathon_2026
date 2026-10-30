"""A scripted OpenRouter for the tests (httpx.MockTransport): nothing leaves the machine."""
import json

import httpx

MODELS = [
    {"id": "test/free:free", "pricing": {"prompt": "0", "completion": "0"},
     "supported_parameters": ["response_format", "temperature", "seed"], "context_length": 100000},
    {"id": "test/paid", "pricing": {"prompt": "0.000001", "completion": "0.000002", "request": "0"},
     "supported_parameters": ["response_format", "structured_outputs", "temperature", "seed", "reasoning"],
     "context_length": 100000},
]


def reply(content: str | None = None, usage: dict | None = None, preds=None, status: int = 200, headers=None):
    if preds is not None:
        content = json.dumps({"predictions": preds})
    body = {"id": "x", "model": "test/paid", "choices": [{"message": {"role": "assistant", "content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return httpx.Response(status, json=body, headers=headers or {})


class Mock:
    """A scripted OpenRouter: /models from MODELS; chat replies from `script` (callables of the request body), the
    last one repeating. Records every chat request body."""

    def __init__(self, script):
        self.script, self.bodies = list(script), []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": MODELS})
        body = json.loads(request.content)
        self.bodies.append(body)
        fn = self.script[min(len(self.bodies) - 1, len(self.script) - 1)]
        return fn(body)

    @property
    def transport(self):
        return httpx.MockTransport(self)


def echo_last(body):
    """Answer every series in the prompt with a fixed in-range value."""
    payload = json.loads(body["messages"][-1]["content"])
    preds = [{"series_id": s["series_id"], "forecast_value": (s["frontier_change_points"][-1][1]
                                                              if "frontier_change_points" in s else 1.0)}
             for s in payload["series"]]
    return reply(preds=preds, usage={"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.0001})
