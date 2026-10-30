"""OpenRouter chat completions with bounded cost: listed pricing, a spend budget checked before every request,
bounded retries, and the reported cost (usage.cost) preferred over the estimate.

Cost per request
  before   max_cost = estimated prompt tokens x prompt price + max_output_tokens x completion price + request price.
           Prompt tokens are estimated at 1.8 characters each (measured about 2 on these prompts). The request is
           sent only if spent + max_cost <= limit.
  after    usage.cost when the response reports it ("reported"); else usage tokens x listed prices ("estimated");
           with no usage at all, max_cost ("assumed_max"), so the budget never under-counts.
Never sent: tools, plugins or web search. A model id ending in ":online" (OpenRouter's web-search variant) is refused.

Grafilab gateway (base URL llm.grafilab.ai): the same chat API, with differences handled here
  prices    Grafilab lists none. Prices come from OpenRouter's public listing for the same model (matched on the id, or
            on the part after the "/"), times the price margin, for the before-request check only
            (price_source "openrouter_reference"). A model with no reference has no price and is refused.
  cost      usage.grafilab_cost, in MYR: converted at myr_per_usd (set low, so USD is over- rather than under-counted)
  thinking  turned off with chat_template_kwargs.enable_thinking=false. With thinking on, Grafilab returned far more
            tokens than max_tokens (249 for a 20-token cap), which would break the maximum-cost check; a reply over the
            cap is flagged (output_cap_exceeded) and stops the run.
  JSON      json_object mode (no schema support is advertised)
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field

import httpx

CHARS_PER_TOKEN = 1.8  # measured ~2.0 on these digit-heavy JSON prompts (Grafilab qwen3.7-flash); lower = safer
MODELS_TTL_S = 6 * 3600
OPENROUTER_URL = "https://openrouter.ai/api/v1"
GRAFILAB_SUPPORTED = ("response_format", "temperature", "seed")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    prompt: float  # USD per prompt token
    completion: float  # USD per completion token
    request: float  # USD per request
    supported: tuple[str, ...]
    context_length: int | None
    listed: bool  # False: no price known (not in the model list, or no reference price), so nothing is spent
    gateway: str = "openrouter"  # openrouter | grafilab
    price_source: str = "listed"  # listed | openrouter_reference | unknown

    @property
    def free(self) -> bool:
        return self.listed and self.prompt == 0 and self.completion == 0 and self.request == 0

    def public(self) -> dict:
        return {**asdict(self), "free": self.free}


def fetch_models(base_url: str, timeout: float = 30, transport: httpx.BaseTransport | None = None) -> list[dict]:
    """OpenRouter's public model list (no key needed): pricing and supported parameters."""
    with httpx.Client(timeout=timeout, transport=transport) as c:
        r = c.get(f"{base_url}/models")
        r.raise_for_status()
        return r.json()["data"]


_cache: dict[str, tuple[float, list[dict]]] = {}


def models(base_url: str, transport: httpx.BaseTransport | None = None) -> list[dict]:
    hit = _cache.get(base_url)
    if hit and time.time() - hit[0] < MODELS_TTL_S and transport is None:
        return hit[1]
    data = fetch_models(base_url, transport=transport)
    if transport is None:
        _cache[base_url] = (time.time(), data)
    return data


def gateway_of(base_url: str) -> str:
    return "grafilab" if "grafilab" in base_url else "openrouter"


def _reference(ref: list[dict], model_id: str) -> dict | None:
    by_id = {x["id"]: x for x in ref}
    if model_id in by_id:
        return by_id[model_id]
    tail = model_id.split("/", 1)[-1]
    hits = [x for x in ref if x["id"].split("/", 1)[-1] == tail and not x["id"].endswith(":free")]
    return hits[0] if len(hits) == 1 else None


def catalog(base_url: str, api_key: str = "", margin: float = 1.5, transport: httpx.BaseTransport | None = None) -> list[dict]:
    """Models in OpenRouter's listing format, plus "gateway" and "price_source". For Grafilab: its own model list
    (needs the key), priced from OpenRouter's public listing x margin; a model with no reference has no price."""
    if gateway_of(base_url) == "openrouter":
        return models(base_url, transport=transport)
    key = f"grafilab:{base_url}"
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < MODELS_TTL_S and transport is None:
        return hit[1]
    with httpx.Client(timeout=30, transport=transport) as c:
        r = c.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"})
        r.raise_for_status()
        own = r.json()["data"]
    ref = models(OPENROUTER_URL, transport=transport)
    out = []
    for m in own:
        if m.get("kind", "chat") != "chat":
            continue
        rm = _reference(ref, m["id"])
        e = {"id": m["id"], "context_length": m.get("context_length"), "supported_parameters": list(GRAFILAB_SUPPORTED),
             "gateway": "grafilab", "reference_id": rm["id"] if rm else None}
        if rm:
            pr = rm.get("pricing") or {}
            e["pricing"] = {k: str(float(pr.get(k) or 0) * margin) for k in ("prompt", "completion", "request")}
            e["price_source"] = "openrouter_reference"
        else:
            e["price_source"] = "unknown"
        out.append(e)
    if transport is None:
        _cache[key] = (time.time(), out)
    return out


def model_info(listing: list[dict], model_id: str) -> ModelInfo:
    if model_id.endswith(":online"):
        raise ConfigError(f"{model_id}: ':online' adds web search, which this benchmark must not use")
    m = next((x for x in listing if x.get("id") == model_id), None)
    if m is None or m.get("price_source") == "unknown":
        m = m or {}
        return ModelInfo(model_id, float("nan"), float("nan"), 0.0, tuple(m.get("supported_parameters") or ()),
                         m.get("context_length"), listed=False, gateway=m.get("gateway", "openrouter"),
                         price_source="unknown")
    p = m.get("pricing") or {}
    num = lambda k: float(p.get(k) or 0)
    return ModelInfo(model_id, num("prompt"), num("completion"), num("request"), tuple(m.get("supported_parameters") or ()),
                     m.get("context_length"), listed=True, gateway=m.get("gateway", "openrouter"),
                     price_source=m.get("price_source", "listed"))


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 20


def max_cost(info: ModelInfo, prompt_tokens: int, max_output_tokens: int) -> float:
    if not info.listed:
        raise ConfigError(f"{info.id}: no known price (not listed, or no OpenRouter reference); refusing to spend")
    return prompt_tokens * info.prompt + max_output_tokens * info.completion + info.request


class Budget:
    """Spend limit shared by parallel requests: each reserves its maximum cost before sending and settles with the
    actual cost after, so requests in flight can never jointly exceed the limit."""

    def __init__(self, limit_usd: float, spent_usd: float = 0.0):
        self.limit, self.spent, self.reserved = float(limit_usd), float(spent_usd), 0.0
        self._lock = threading.Lock()

    @property
    def remaining(self) -> float:
        return self.limit - self.spent

    def allows(self, cost: float) -> bool:
        return self.spent + self.reserved + cost <= self.limit + 1e-12

    def reserve(self, cost: float) -> bool:
        with self._lock:
            if not self.allows(cost):
                return False
            self.reserved += cost
            return True

    def settle(self, reserved: float, actual: float) -> None:
        with self._lock:
            self.reserved -= reserved
            self.spent += float(actual)

    def add(self, cost: float) -> None:
        self.settle(0.0, cost)


@dataclass
class Result:
    status: str  # ok | http_error | rate_limited | timeout | provider_error | refused_budget
    content: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float = 0.0
    cost_source: str = "none"  # reported | estimated | assumed_max | none
    max_cost_usd: float = 0.0
    retries: int = 0
    http_status: int | None = None
    error: str | None = None
    served_model: str | None = None
    provider: str | None = None
    latency_s: float = 0.0
    output_cap_exceeded: bool = False  # the reply had more tokens than max_tokens: the cost cap cannot be trusted
    params: dict = field(default_factory=dict)


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"predictions": {"type": "array", "items": {
        "type": "object",
        "properties": {"series_id": {"type": "string"}, "forecast_value": {"type": "number"}},
        "required": ["series_id", "forecast_value"], "additionalProperties": False}}},
    "required": ["predictions"], "additionalProperties": False}


def request_body(info: ModelInfo, messages: list[dict], max_output_tokens: int, reasoning: str, seed: int) -> dict:
    """Only parameters the model lists as supported; JSON output enforced where it can be."""
    if info.gateway == "grafilab":
        body = {"model": info.id, "messages": messages, "max_tokens": max_output_tokens, "temperature": 0, "seed": seed,
                "response_format": {"type": "json_object"}}
        if reasoning == "off":
            body["chat_template_kwargs"] = {"enable_thinking": False}
        return body
    sp = set(info.supported)
    body: dict = {"model": info.id, "messages": messages, "max_tokens": max_output_tokens, "usage": {"include": True}}
    if "temperature" in sp:
        body["temperature"] = 0
    if "seed" in sp:
        body["seed"] = seed
    if "structured_outputs" in sp:
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": {"name": "forecasts", "strict": True, "schema": RESPONSE_SCHEMA}}
    elif "response_format" in sp:
        body["response_format"] = {"type": "json_object"}
    if "reasoning" in sp and reasoning != "default":
        body["reasoning"] = {"enabled": False} if reasoning == "off" else {"effort": reasoning, "exclude": True}
    return body


class Client:
    """One OpenRouter model. `transport` replaces the network in tests (httpx.MockTransport)."""

    def __init__(self, base_url: str, api_key: str, info: ModelInfo, *, timeout_s: float, max_retries: int,
                 min_interval_s: float = 0.0, reasoning: str = "off", transport: httpx.BaseTransport | None = None,
                 sleep=time.sleep, myr_per_usd: float = 4.0):
        if not api_key:
            raise ConfigError("no API key for this gateway (OPENROUTER_BENCH_API_KEY)")
        self.info, self.max_retries, self.min_interval, self.reasoning = info, max_retries, min_interval_s, reasoning
        self.url = f"{base_url}/chat/completions"
        self.http = httpx.Client(timeout=timeout_s, transport=transport, headers={
            "Authorization": f"Bearer {api_key}", "X-Title": "sdc-hackathon-2026 LLM forecast benchmark"})
        self.sleep, self._last, self.myr_per_usd = sleep, 0.0, myr_per_usd
        self._turn = threading.Lock()

    def close(self) -> None:
        self.http.close()

    def _wait_turn(self) -> None:
        with self._turn:  # spaces request starts, also across threads
            gap = self.min_interval - (time.monotonic() - self._last)
            if gap > 0:
                self.sleep(gap)
            self._last = time.monotonic()

    def complete(self, messages: list[dict], max_output_tokens: int, budget: Budget, seed: int = 7) -> Result:
        prompt_text = "".join(m["content"] for m in messages)
        cap = max_cost(self.info, estimate_tokens(prompt_text), max_output_tokens)
        body = request_body(self.info, messages, max_output_tokens, self.reasoning, seed)
        params = {k: v for k, v in body.items() if k not in ("messages",)}
        if not budget.reserve(cap):
            return Result("refused_budget", max_cost_usd=cap, params=params,
                          error=f"max cost {cap:.6f} USD exceeds remaining budget {budget.remaining:.6f} USD")
        res = Result("http_error", max_cost_usd=cap, params=params)
        t0 = time.monotonic()
        for attempt in range(self.max_retries + 1):
            if attempt and not budget.allows(res.cost_usd):  # a retry must fit too (this attempt's cap is reserved)
                res.error = f"{res.error}; retry skipped: budget"
                break
            res.retries = attempt
            self._wait_turn()
            try:
                r = self.http.post(self.url, json=body)
            except httpx.TimeoutException as e:
                # the provider may still finish and bill the generation: count the maximum
                res.status, res.error = "timeout", f"timeout: {e}"
                self._add_cost(res, cap, "assumed_max")
                self._backoff(attempt, None)
                continue
            except httpx.HTTPError as e:
                res.status, res.error = "http_error", f"{type(e).__name__}: {e}"
                self._backoff(attempt, None)
                continue
            res.http_status = r.status_code
            if r.status_code == 429:
                res.status, res.error = "rate_limited", _err_text(r)
                self._backoff(attempt, r.headers.get("retry-after"))
                continue
            if r.status_code >= 500 or r.status_code == 408:
                res.status, res.error = "http_error", _err_text(r)
                self._backoff(attempt, r.headers.get("retry-after"))
                continue
            if r.status_code >= 400:  # bad request, auth, payment: retrying will not help
                res.status, res.error = "http_error", _err_text(r)
                break
            try:
                data = r.json()
            except ValueError:
                res.status, res.error = "provider_error", "response is not JSON"
                self._add_cost(res, cap, "assumed_max")
                self._backoff(attempt, None)
                continue
            self._account(res, data, cap)  # a failed generation can still be billed
            if data.get("error") or not data.get("choices"):
                res.status, res.error = "provider_error", json.dumps(data.get("error") or "no choices")[:500]
                self._backoff(attempt, None)
                continue
            msg = data["choices"][0].get("message") or {}
            res.status, res.content, res.error = "ok", msg.get("content") or "", None
            res.served_model, res.provider = data.get("model"), data.get("provider")
            res.output_cap_exceeded = (res.completion_tokens or 0) > max_output_tokens * 1.05 + 5
            break
        res.latency_s = round(time.monotonic() - t0, 2)
        budget.settle(cap, res.cost_usd)
        return res

    def _add_cost(self, res: Result, cost: float, source: str) -> None:
        res.cost_usd += float(cost)
        order = ("none", "reported", "estimated", "assumed_max")  # the least certain source of any attempt wins
        if order.index(source) > order.index(res.cost_source):
            res.cost_source = source

    def _account(self, res: Result, data: dict, cap: float) -> None:
        u = data.get("usage") or {}
        if u:
            res.prompt_tokens = (res.prompt_tokens or 0) + (u.get("prompt_tokens") or 0)
            res.completion_tokens = (res.completion_tokens or 0) + (u.get("completion_tokens") or 0)
        rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        if rt is not None:
            res.reasoning_tokens = (res.reasoning_tokens or 0) + rt
        if u.get("cost") is not None:
            self._add_cost(res, float(u["cost"]), "reported")
        elif u.get("grafilab_cost") is not None and str(u.get("grafilab_cost_currency") or "MYR").upper() in ("MYR", "USD"):
            rate = self.myr_per_usd if str(u.get("grafilab_cost_currency") or "MYR").upper() == "MYR" else 1.0
            self._add_cost(res, float(u["grafilab_cost"]) / rate, "reported")
        elif u.get("prompt_tokens") is not None:
            self._add_cost(res, u["prompt_tokens"] * self.info.prompt + (u.get("completion_tokens") or 0)
                           * self.info.completion + self.info.request, "estimated")
        elif data.get("choices") or data.get("error"):
            self._add_cost(res, cap, "assumed_max")

    def _backoff(self, attempt: int, retry_after: str | None) -> None:
        if attempt >= self.max_retries:
            return
        try:
            wait = min(float(retry_after), 60.0) if retry_after else 2.0 * 2 ** attempt
        except ValueError:
            wait = 2.0 * 2 ** attempt
        self.sleep(wait)


def _err_text(r: httpx.Response) -> str:
    try:
        e = r.json().get("error")
        return f"HTTP {r.status_code}: " + (e.get("message") if isinstance(e, dict) else str(e))[:500]
    except ValueError:
        return f"HTTP {r.status_code}: {r.text[:300]}"
