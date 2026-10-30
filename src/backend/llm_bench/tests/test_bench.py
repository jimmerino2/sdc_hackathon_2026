"""LLM forecast benchmark: leakage, anonymity, few-shot eligibility, parsing, cost limits, retries, metrics, storage."""
import hashlib
import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from llm_bench.tests.fakes import Mock, echo_last, reply
from llm_bench import cases as K, metrics as MX, openrouter as OR, prompts as P, runner as R

REPO = Path(__file__).resolve().parents[4]


# ------------------------------------------------------------------ cutoffs and leakage


def test_skill_history_ends_at_origin(skills_built):
    p, _, _, cs = skills_built
    keys = p.series.apply(lambda s: f"{s['country']}|{s['occupation']}|{s['skill_id']}", axis=1)
    row_of = {k: i for i, k in enumerate(keys)}
    for c in cs.cases.to_dict("records"):
        row, t = row_of[c["series_key"]], c["origin_idx"]
        a, n = json.loads(c["input_anon"]), json.loads(c["input_named"])
        assert a["first_month"] + len(a["eligible_ads"]) - 1 == 0  # offsets run to the origin, never past it
        assert a["eligible_ads"][-1] == p.N[row, t] and n["first_month"] == str(p.months[t - len(n["eligible_ads"]) + 1])
        assert c["target_month"] == str(p.months[t + c["h"]])


def test_skill_inputs_ignore_months_after_origin(skills_built):
    """Overwriting every month after the origin changes nothing in the case's inputs."""
    p, _, _, cs = skills_built
    c = cs.cases.iloc[0]
    keys = p.series.apply(lambda s: f"{s['country']}|{s['occupation']}|{s['skill_id']}", axis=1)
    row, t = int(np.nonzero((keys == c["series_key"]).to_numpy())[0][0]), int(c["origin_idx"])
    before = K._skill_history(p, row, t, K.SKILL_MONTHS, False)
    K0, N0, f0 = p.K.copy(), p.N.copy(), p.f
    try:
        p.K[:, t + 1:] = 999
        p.N[:, t + 1:] = 1000
        from occupational import models as OM
        occs = sorted(p.series["occupation"].unique()); skills = sorted(p.series["skill_id"].unique())
        p.f = OM.features(p.K, p.N, p.series["skill_id"].map({s: i for i, s in enumerate(skills)}).to_numpy(),
                          p.series["occupation"].map({o: i for i, o in enumerate(occs)}).to_numpy(), len(occs))
        assert K._skill_history(p, row, t, K.SKILL_MONTHS, False) == before
    finally:
        p.K, p.N, p.f = K0, N0, f0


def test_truth_is_not_in_case_inputs(skills_built, cap_built):
    for cs in (skills_built[3], cap_built):
        assert not {"actual", "actual_k", "actual_n"} & set(cs.cases.columns)
        assert set(cs.truth["case_id"]) == set(cs.cases["case_id"])


def test_capability_inputs_end_at_snapshot(cap_built):
    for c in cap_built.cases.to_dict("records"):
        a = json.loads(c["input_anon"])
        assert max(x[0] for x in a["frontier_change_points"]) == 0
        assert all(m["released"] <= 0 for m in a["measured_items"])
        n = json.loads(c["input_named"])
        assert max(x[0] for x in n["frontier_change_points"]) == c["origin_last_period"]
        assert str(pd.Period(c["origin_last_period"], "M") + c["h"]) == c["target_month"]


# ------------------------------------------------------------------ anonymity


def _skill_names(reg):
    return [e["name"] for e in reg["skills"] if len(e["name"]) >= 5] + [e["skill_id"] for e in reg["skills"] if len(e["skill_id"]) >= 5]


def test_primary_prompts_are_anonymous(skills_built, cap_built):
    _, reg, _, cs = skills_built
    names = _skill_names(reg)
    for mode in P.PRIMARY:
        for b in P.batches(cs.cases, 10):
            text = "".join(m["content"] for m in P.messages("skills", mode, b))
            leaked = [x for x in names if x in text]
            assert not leaked, leaked[:5]
            for word in ("software_engineer", "data_scientist", "Hacker News", "2025-", "2026-"):
                assert word not in text
    for mode in P.PRIMARY:
        for b in P.batches(cap_built.cases, 10):
            text = "".join(m["content"] for m in P.messages("capability", mode, b))
            for word in ("METR", "gpt", "claude", "GPT", "Claude", "v1.1", "v1.0", "202", "minutes", "Epoch"):
                assert word not in text, word


def test_named_prompts_carry_names(skills_built, cap_built):
    b = P.batches(skills_built[3].cases, 10)[0]
    assert "skill" in json.loads(P.messages("skills", "zero_named", b)[1]["content"])["series"][0]
    text = P.messages("capability", "zero_named", P.batches(cap_built.cases, 10)[-1])[1]["content"]
    assert "METR" in text and "202" in text


def test_anon_ids_are_stable_and_uninformative():
    ids = [f"sk|US|software_engineer|skill{i}|2025-01|h3" for i in range(50)]
    a, b = K.anon_ids(ids, 1, "S"), K.anon_ids(list(reversed(ids)), 1, "S")
    assert a == b and len(set(a.values())) == 50
    assert [a[i] for i in sorted(ids)] != sorted(a.values())  # a permutation, not the sorted order


# ------------------------------------------------------------------ few-shot eligibility


def test_skill_examples_were_observed_before_origin(skills_built):
    _, _, _, cs = skills_built
    n = 0
    for c in cs.cases.to_dict("records"):
        for e in json.loads(c["example_ids"]):
            assert e["target_idx"] <= c["origin_idx"], (e, c["case_id"])
            n += 1
    assert n > 0


def test_capability_examples_use_this_origin_view(cap_built):
    n = 0
    for c in cap_built.cases.to_dict("records"):
        last = pd.Period(c["origin_last_period"], "M")
        for e in json.loads(c["example_ids"]):
            assert pd.Period(e["target_period"], "M") <= last
            assert pd.Timestamp(e["origin"]) < pd.Timestamp(c["origin"])
            assert pd.Timestamp(e["seen_at"]) == pd.Timestamp(c["origin"])  # outcome read from this case's snapshot
            n += 1
    assert n > 0


def test_batches_share_one_origin(skills_built, cap_built):
    for cs in (skills_built[3], cap_built):
        for b in P.batches(cs.cases, 7):
            assert b["batch_key"].nunique() == 1 and len(b) <= 7


# ------------------------------------------------------------------ units, horizons, sampling


def test_units_and_horizons(skills_built, cap_built):
    sk = skills_built[3].cases
    assert set(sk["h"]) == {3, 12}
    assert (sk["existing_method"] == sk["h"].map({3: "mean12", 12: "shrink"})).all()
    assert set(cap_built.cases["h"]) <= {3, 6, 12} and (cap_built.cases["existing_method"] == "ensemble").all()
    b = P.batches(sk, 3)[0]
    out = P.parse("skills", json.dumps({"predictions": [{"series_id": b["anon_id"].iloc[0], "forecast_value": 4.2}]}), b)
    assert next(o for o in out if o["status"] == "ok")["value"] == pytest.approx(0.042)  # percent -> share


def test_sampling_is_reproducible(skills_built):
    p, reg, bt, cs = skills_built
    again = K.skill_cases(horizons=(3, 12), n_series=12, n_origins=2, seed=7, few_shot_k=3, panel=(p, reg), bt=bt)
    other = K.skill_cases(horizons=(3, 12), n_series=12, n_origins=2, seed=8, few_shot_k=3, panel=(p, reg), bt=bt)
    assert list(again.cases["case_id"]) == list(cs.cases["case_id"])
    assert list(again.cases["anon_id"]) == list(cs.cases["anon_id"])
    assert set(other.cases["case_id"]) != set(cs.cases["case_id"])


def test_baseline_matches_the_backtest(skills_built):
    _, _, bt, cs = skills_built
    t = cs.truth.merge(cs.cases[["case_id", "f_persistence", "existing", "origin_idx", "h", "series_key"]], on="case_id")
    assert (t["actual"] == t["actual_k"] / t["actual_n"]).all()
    assert t["f_persistence"].notna().all() and t["existing"].notna().all()


# ------------------------------------------------------------------ parsing and validation


def _batch(ids, last=100.0):
    return pd.DataFrame({"anon_id": ids, "case_id": [f"c{i}" for i in ids], "last_value": last})


@pytest.mark.parametrize("content", [
    '{"predictions":[{"series_id":"S1","forecast_value":3.5}]}',
    '```json\n{"predictions":[{"series_id":"S1","forecast_value":3.5}]}\n```',
    'Sure! {"predictions":[{"series_id":"S1","forecast_value":"3.5"}]} done',
    '[{"series_id":"S1","forecast_value":3.5}]',
])
def test_parse_valid_json(content):
    out = P.parse("skills", content, _batch(["S1"]))
    assert out[0]["status"] == "ok" and out[0]["value"] == pytest.approx(0.035)


def test_parse_missing_and_invalid_values():
    b = _batch(["S1", "S2", "S3", "S4", "S5", "S6"])
    content = json.dumps({"predictions": [
        {"series_id": "S1", "forecast_value": 101}, {"series_id": "S2", "forecast_value": "n/a"},
        {"series_id": "S3", "forecast_value": True}, {"series_id": "S4", "forecast_value": 1},
        {"series_id": "S4", "forecast_value": 2}, {"series_id": "S5", "forecast_value": None},
        {"series_id": "ZZ", "forecast_value": 5}]})
    out = {o["case_id"]: o for o in P.parse("skills", content, b)}
    assert out["cS1"]["status"] == "invalid" and "outside" in out["cS1"]["reason"]
    assert out["cS2"]["status"] == "invalid" and out["cS3"]["status"] == "invalid"
    assert out["cS4"]["status"] == "invalid" and "more than once" in out["cS4"]["reason"]
    assert out["cS5"]["status"] == "invalid" and out["cS6"]["status"] == "missing"
    assert all(o["value"] is None for o in out.values())  # never filled in


def test_parse_unparseable_and_capability_range():
    out = P.parse("skills", "I think it will go up.", _batch(["S1"]))
    assert out[0]["status"] == "unparseable"
    cap = P.parse("capability", '{"predictions":[{"series_id":"A1","forecast_value":-5},{"series_id":"A2","forecast_value":250}]}',
                  _batch(["A1", "A2"]))
    assert [o["status"] for o in cap] == ["invalid", "ok"] and cap[1]["value"] == 250


# ------------------------------------------------------------------ client: cost, retries, logging


def _client(mock, model="test/paid", retries=2):
    info = OR.model_info(OR.fetch_models("https://or.test/api/v1", transport=mock.transport), model)
    return OR.Client("https://or.test/api/v1", "k", info, timeout_s=5, max_retries=retries, transport=mock.transport,
                     sleep=lambda s: None)


MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "x" * 3000}]


def test_budget_refuses_before_sending():
    mock = Mock([lambda b: reply(preds=[])])
    c = _client(mock)
    cap = OR.max_cost(c.info, OR.estimate_tokens("s" + "x" * 3000), 2048)
    res = c.complete(MSGS, 2048, OR.Budget(cap * 0.5))
    assert res.status == "refused_budget" and not mock.bodies


def test_retry_then_success_and_reported_cost():
    mock = Mock([lambda b: httpx.Response(503, json={"error": {"message": "busy"}}),
                 lambda b: reply(preds=[], usage={"prompt_tokens": 1000, "completion_tokens": 50, "cost": 0.0012})])
    budget = OR.Budget(1.0)
    res = _client(mock).complete(MSGS, 100, budget)
    assert res.status == "ok" and res.retries == 1 and res.cost_source == "reported"
    assert res.cost_usd == pytest.approx(0.0012) and budget.spent == pytest.approx(0.0012)
    body = mock.bodies[0]
    assert body["temperature"] == 0 and body["response_format"]["type"] == "json_schema"
    assert "tools" not in body and "plugins" not in body and body["reasoning"] == {"enabled": False}


def test_rate_limit_is_bounded():
    mock = Mock([lambda b: httpx.Response(429, json={"error": {"message": "free-models-per-day"}}, headers={"retry-after": "1"})])
    res = _client(mock, retries=2).complete(MSGS, 100, OR.Budget(1.0))
    assert res.status == "rate_limited" and len(mock.bodies) == 3 and res.cost_usd == 0


def test_cost_estimated_or_assumed_without_reported_cost():
    est = _client(Mock([lambda b: reply(preds=[], usage={"prompt_tokens": 1000, "completion_tokens": 100})])).complete(MSGS, 100, OR.Budget(1))
    assert est.cost_source == "estimated" and est.cost_usd == pytest.approx(1000 * 1e-6 + 100 * 2e-6)
    none = _client(Mock([lambda b: reply(preds=[])])).complete(MSGS, 100, OR.Budget(1))
    assert none.cost_source == "assumed_max" and none.cost_usd == pytest.approx(none.max_cost_usd)
    assert none.prompt_tokens is None


def test_free_model_uses_json_object_and_online_refused():
    mock = Mock([lambda b: reply(preds=[], usage={"prompt_tokens": 10, "completion_tokens": 5, "cost": 0})])
    c = _client(mock, model="test/free:free")
    assert c.info.free
    c.complete(MSGS, 100, OR.Budget(0.0))  # free: fits a zero budget
    assert mock.bodies[0]["response_format"] == {"type": "json_object"} and "reasoning" not in mock.bodies[0]
    with pytest.raises(OR.ConfigError):
        OR.model_info([], "test/paid:online")
    with pytest.raises(OR.ConfigError):
        OR.max_cost(OR.model_info([], "unlisted/model"), 10, 10)


# ------------------------------------------------------------------ runs: budget stop, partial batches, resume, isolation


def _cap_cfg(**kw):
    return R.RunConfig(benchmark="capability", horizons=[3], modes=["zero"], model="test/paid", batch_size=10, **kw)


def test_run_partial_batch_and_resume(bench_dir):
    def half(body):  # answers only the first series of each batch, with an invalid extra
        s = json.loads(body["messages"][-1]["content"])["series"]
        return reply(preds=[{"series_id": s[0]["series_id"], "forecast_value": s[0]["frontier_change_points"][-1][1]}],
                     usage={"prompt_tokens": 500, "completion_tokens": 20, "cost": 0.0001})
    mock = Mock([half])
    rid = R.create(_cap_cfg(max_requests=3), transport=mock.transport)
    st = R.execute(rid, transport=mock.transport, sleep=lambda s: None)
    assert st["state"] == "paused_request_limit" and len(mock.bodies) == 3
    cfgp = bench_dir / "runs" / rid / "config.json"
    c = json.loads(cfgp.read_text()); c["config"]["max_requests"] = 0; cfgp.write_text(json.dumps(c))
    st = R.execute(rid, transport=mock.transport, sleep=lambda s: None)
    keys = [json.loads(x)["key"] for x in (bench_dir / "runs" / rid / "requests.jsonl").read_text().splitlines()]
    assert st["state"] == "completed" and len(keys) == len(set(keys)) == R.load(rid)["plan"]["n_requests"]
    rep = json.loads((bench_dir / "runs" / rid / "report.json").read_text())
    stat = rep["modes"]["zero"]["statuses"]
    assert stat.get("ok", 0) > 0 and stat.get("ok", 0) + stat.get("missing", 0) == rep["modes"]["zero"]["n_cases"]
    assert rep["usage"]["cost_usd"] == pytest.approx(0.0001 * len(keys))
    assert rep["usage"]["cost_by_source"] == {"reported": pytest.approx(0.0001 * len(keys))}


def test_run_stops_at_budget(bench_dir):
    mock = Mock([echo_last])
    rid = R.create(_cap_cfg(max_spend_usd=0.004, max_output_tokens=1000), transport=mock.transport)
    st = R.execute(rid, transport=mock.transport, sleep=lambda s: None)
    assert st["state"] == "stopped_budget" and st["requests_not_completed"] > 0 and st["cases_not_completed"] > 0
    assert st["spent_usd"] <= 0.004
    preds = R.predictions(rid)
    assert (preds["status"] == "skipped_budget").any()


def test_auth_error_stops_run(bench_dir):
    mock = Mock([lambda b: httpx.Response(401, json={"error": {"message": "bad key"}})])
    rid = R.create(_cap_cfg(), transport=mock.transport)
    st = R.execute(rid, transport=mock.transport, sleep=lambda s: None)
    assert st["state"] == "auth_or_payment" and len(mock.bodies) == 1


def _tree_hash(*dirs):
    h = hashlib.sha256()
    for d in dirs:
        for p in sorted(Path(d).rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(d)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def test_benchmark_never_writes_production_outputs(bench_dir):
    prod = [REPO / "data" / "occupational_forecasting" / "latest", REPO / "src" / "backend" / "forecasting" / "output" / "frontier_time_horizon"]
    before = _tree_hash(*prod)
    mock = Mock([echo_last])
    rid = R.create(_cap_cfg(dry_run=True), transport=mock.transport)
    R.execute(rid)
    assert _tree_hash(*prod) == before
    assert (bench_dir / "runs" / rid / "report.json").exists()
    assert not mock.bodies  # dry run: nothing sent
    cfg = (bench_dir / "runs" / rid / "config.json").read_text()
    assert "test-key-not-real" not in cfg


# ------------------------------------------------------------------ metrics


def test_skill_metrics_by_hand():
    f = np.array([0.10, 0.05, 0.20]); a = np.array([0.13, 0.05, 0.15]); p12 = np.array([0.10, 0.04, 0.18])
    d = MX.skill_scores(f, a, p12, naive=np.array([0.10, 0.04, 0.18]))
    assert d["mae_pp"] == pytest.approx((3 + 0 + 5) / 3) and d["bias_pp"] == pytest.approx((-3 + 0 + 5) / 3)
    # material: case 0 (+3 pp, forecast flat -> wrong), case 2 (-3 pp, forecast +2 -> wrong); case 1 stable
    assert d["n_material"] == 2 and d["direction_acc"] == 0.0 and d["stable_mae_pp"] == pytest.approx(0)
    assert d["rising_bias_pp"] == pytest.approx(-3) and d["falling_bias_pp"] == pytest.approx(5)
    assert d["mae_ratio_vs_naive"] == pytest.approx((8 / 3) / ((3 + 1 + 3) / 3))


def test_capability_metrics_by_hand():
    d = MX.cap_scores(np.array([200.0, 50.0]), np.array([100.0, 100.0]), naive=np.array([100.0, 25.0]))
    assert d["mae_doublings"] == pytest.approx(1.0) and d["bias_doublings"] == pytest.approx(0.0)
    assert d["typical_factor"] == pytest.approx(2.0) and d["mae_minutes"] == pytest.approx(75)
    assert d["mase_vs_naive"] == pytest.approx(1.0 / 1.0)


def test_comparison_is_paired():
    df = pd.DataFrame({"h": 3, "origin": "o", "actual": [0.1, 0.2, 0.3], "existing": [0.1, 0.2, 0.9],
                       "naive": [0.1, 0.2, 0.3], "llm": [0.1, np.nan, 0.3], "p12_origin": [0.1, 0.2, 0.3],
                       "n3_origin": [10, 100, 300]})
    out = MX.compare("skills", df, "zero")
    assert out["n_valid"] == 2 and out["overall"]["existing"]["n"] == 2
    assert out["overall"]["existing"]["mae_pp"] == pytest.approx(30)


# ------------------------------------------------------------------ Grafilab gateway


GRAFILAB = "https://llm.grafilab.ai/v1"


def _grafilab_mock(script):
    mock = Mock(script)
    inner = mock.__call__

    def handler(request):
        if request.url.host == "llm.grafilab.ai" and request.url.path.endswith("/models"):
            assert request.headers["authorization"] == "Bearer g-key"
            return httpx.Response(200, json={"data": [{"id": "test/paid", "kind": "chat"}, {"id": "grafilab/paid", "kind": "chat"},
                                                      {"id": "x/no-ref", "kind": "chat"}, {"id": "img/gen", "kind": "image"}]})
        return inner(request)
    return mock, httpx.MockTransport(handler)


def test_grafilab_prices_from_openrouter_reference():
    _, tr = _grafilab_mock([lambda b: reply(preds=[])])
    cat = OR.catalog(GRAFILAB, "g-key", margin=1.5, transport=tr)
    assert {m["id"] for m in cat} == {"test/paid", "grafilab/paid", "x/no-ref"}  # image models dropped
    paid = OR.model_info(cat, "test/paid")
    assert paid.gateway == "grafilab" and paid.price_source == "openrouter_reference"
    assert paid.prompt == pytest.approx(1.5e-6) and paid.completion == pytest.approx(3e-6)
    assert OR.model_info(cat, "grafilab/paid").prompt == pytest.approx(1.5e-6)  # matched on the part after "/"
    assert not OR.model_info(cat, "x/no-ref").listed  # no reference: no price, so no spending


def test_grafilab_request_and_myr_cost():
    mock, tr = _grafilab_mock([lambda b: reply(preds=[], usage={"prompt_tokens": 20, "completion_tokens": 5,
                                                                 "grafilab_cost": 0.0004, "grafilab_cost_currency": "MYR"})])
    info = OR.model_info(OR.catalog(GRAFILAB, "g-key", transport=tr), "test/paid")
    c = OR.Client(GRAFILAB, "g-key", info, timeout_s=5, max_retries=0, transport=tr, sleep=lambda s: None, myr_per_usd=4.0)
    res = c.complete(MSGS, 100, OR.Budget(1.0))
    body = mock.bodies[0]
    assert body["chat_template_kwargs"] == {"enable_thinking": False} and body["response_format"] == {"type": "json_object"}
    assert "reasoning" not in body and "usage" not in body and "tools" not in body
    assert res.cost_source == "reported" and res.cost_usd == pytest.approx(0.0001)


def test_reply_over_output_cap_stops_run(bench_dir, monkeypatch):
    monkeypatch.setenv("OPENROUTER_BENCH_BASE_URL", GRAFILAB)
    monkeypatch.setenv("OPENROUTER_BENCH_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "g-key")  # Grafilab falls back to the app's key
    mock, tr = _grafilab_mock([lambda b: reply(preds=[], usage={"prompt_tokens": 20, "completion_tokens": 5000,
                                                                 "grafilab_cost": 0.001, "grafilab_cost_currency": "MYR"})])
    rid = R.create(_cap_cfg(max_output_tokens=100), transport=tr)
    st = R.execute(rid, transport=tr, sleep=lambda s: None)
    assert st["state"] == "output_cap_ignored" and len(mock.bodies) == 1


# ------------------------------------------------------------------ parallel requests


def test_budget_reservations_block_overspend():
    b = OR.Budget(1.0)
    assert b.reserve(0.6) and not b.reserve(0.6)  # the second would exceed the limit while the first is in flight
    b.settle(0.6, 0.1)
    assert b.spent == pytest.approx(0.1) and b.reserved == 0 and b.reserve(0.6)


def test_parallel_run_matches_sequential(bench_dir):
    seq, par = Mock([echo_last]), Mock([echo_last])
    r1 = R.create(_cap_cfg(), transport=seq.transport)
    R.execute(r1, transport=seq.transport, sleep=lambda s: None)
    r2 = R.create(_cap_cfg(concurrency=4), transport=par.transport)
    st = R.execute(r2, transport=par.transport, sleep=lambda s: None)
    assert st["state"] == "completed" and len(par.bodies) == len(seq.bodies)
    keys = [json.loads(x)["key"] for x in (bench_dir / "runs" / r2 / "requests.jsonl").read_text().splitlines()]
    assert len(keys) == len(set(keys))
    a, b = R.predictions(r1).sort_values(["case_id", "mode"]), R.predictions(r2).sort_values(["case_id", "mode"])
    assert list(a["value"]) == list(b["value"])


def test_parallel_run_stops_at_budget(bench_dir):
    mock = Mock([echo_last])
    rid = R.create(_cap_cfg(max_spend_usd=0.004, max_output_tokens=1000, concurrency=4), transport=mock.transport)
    st = R.execute(rid, transport=mock.transport, sleep=lambda s: None)
    assert st["state"] == "stopped_budget" and st["spent_usd"] <= 0.004
