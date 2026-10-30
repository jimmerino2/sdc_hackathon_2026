# llm_bench

An experiment: can an LLM, called through OpenRouter, forecast better than the two existing forecasting systems? It is scored on the same past forecasts those systems were tested on. Nothing here changes a served forecast. It reads the existing outputs and writes only to `data/llm_bench/`.

| Benchmark | Existing system | Target | Cases | Existing model |
| --- | --- | --- | --- | --- |
| Skills demand | `occupational/` | Share of a cell's eligible HN ads naming the skill, pooled over the 3 months ending at origin + h | Test period of the occupational backtest, rebuilt in memory (its scores equal `latest/evaluation.json`) | The method served per horizon (h3 `mean12`, h6 `mean12`, h12 `shrink`) |
| AI acceleration | `forecasting/` `frontier_time_horizon` | Frontier METR 50% time horizon (minutes) at last complete month + h, per METR suite | Holdout origins of the served capability run, using that origin's snapshot | Capability-engine `ensemble` |

## Run

From `src/backend`, using the backend venv. The page is `/benchmark` ("LLM benchmark" in the sidebar).

```
python -m llm_bench.run models                                    # free JSON-capable models, configured model prices
python -m llm_bench.run plan  --benchmark skills                  # sample + cost estimate; sends nothing
python -m llm_bench.run start --benchmark skills --dry-run        # whole pipeline, mock replies, no key
python -m llm_bench.run start --benchmark skills --max-requests 2 --yes        # free model, smoke test
python -m llm_bench.run start --benchmark skills --yes                         # free model, full pilot
python -m llm_bench.run start --benchmark skills --model qwen/qwen3.5-9b --yes # inexpensive paid comparison
python -m llm_bench.run resume <run_id> --yes
python -m pytest llm_bench/tests                                  # offline; OpenRouter is mocked
```

**Gateway.** `OPENROUTER_BENCH_BASE_URL` selects the gateway.

- **Grafilab** (`https://llm.grafilab.ai/v1`): it reuses the app's `OPENROUTER_API_KEY`.
  - Thinking is switched off (`enable_thinking: false`). With thinking on, Grafilab ignores `max_tokens`. A reply over the cap stops the run.
  - Prices come from OpenRouter's public listing for the same model, ×1.5 (`OPENROUTER_BENCH_PRICE_MARGIN`).
  - The reported cost is `grafilab_cost` in MYR, converted at `OPENROUTER_BENCH_MYR_PER_USD` (4.0, a low rate that over-counts USD).
  - Grafilab has no free models.
  - `python -m llm_bench.run models` lists the models with their reference prices.
- **openrouter.ai**: it needs `OPENROUTER_BENCH_API_KEY`.

The settings are the `OPENROUTER_BENCH_*` variables in `.env.example`. The key is an openrouter.ai key, separate from the app's Grafilab `OPENROUTER_API_KEY`, and it is never written to a run folder.

## Design

- **Modes.**
  - `zero` and `few` are primary. They are anonymous: series ids, month offsets, and no skill, country, occupation, model or benchmark names.
  - `zero_named` and `few_named` are exploratory. They show real names and dates, so the LLM may recall what happened. They are reported apart and never decide a winner.
- **Leakage controls:**
  - Inputs hold months at or before the origin only.
  - A batch shares one origin.
  - Few-shot examples are earlier forecasts whose target window had ended by the origin. For capability, their outcome is read from the case's own snapshot, not from later vintages.
  - Truth sits in a separate table and is joined only during evaluation.
  - No tools, plugins or web search are sent, and `:online` models are refused.
- **Sample.** Seeded and fixed per definition (`data/llm_bench/samples/<id>/`), so every model sees identical cases. The skills default is 100 series × 4 evenly spaced test origins at h = 3. Capability uses every holdout case (36).
- **Cost.**
  - Before each request, the maximum cost (estimated prompt tokens + `max_output_tokens`, at listed prices) must fit the remaining budget, and each retry must fit too.
  - After each request, the reported `usage.cost` is used. Otherwise cost is estimated from token counts, or, with no usage data, the maximum is assumed.
  - The run stops on the budget, a rate limit, a key or credit error, or 3 consecutive failures. It can be resumed without repeating answered requests.
- **Validation.** Replies must be JSON (a strict schema where the model supports one). A value that is missing, non-numeric, duplicated or out of range is recorded as such and never filled in.
- **Metrics.**
  - Skills use the occupational definitions: pp error, bias, direction on material moves (2 pp from the 12-month share), stable error, rising and falling bias, and groups by volume and level.
  - Capability uses log2 error (doublings), the typical factor, minutes and MASE against naive.
  - The LLM, existing model and naive are always scored on the same cases. A paired bootstrap shows whether the gap is beyond noise.

## Limits

- The pilot is small, and many cases share an origin, so the bootstrap interval is optimistic.
- Free models are rate-limited (about 20 requests a minute; a daily cap of about 50 without credit). A full free pilot may take two days of resumes, or larger batches (`--batch-size 20`).
- Anonymous capability numbers can still look familiar to a model trained on METR results.
- Skills `mean12` forecasts equal the 12-month share, so its direction accuracy is 0 by construction (as in `evaluation.json`).
