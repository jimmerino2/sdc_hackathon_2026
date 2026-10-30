# Claude Code Task: Benchmark LLM Forecasting via OpenRouter

## Objective

Implement a working LLM-based forecasting benchmark to evaluate whether a pretrained LLM, given my existing historical data, can predict skill demand and AI capability acceleration more accurately than my current forecasting models.

My application already contains two forecasting systems:

1. Skills demand forecasting for IT/software occupations.
2. AI acceleration forecasting using the existing AI capability/time-horizon dataset and forecasting logic.

Both currently perform worse than expected despite testing multiple statistical forecasting methods.

I want to test an LLM as an alternative forecasting approach using OpenRouter. I do not want to replace my existing forecasting systems before an empirical comparison establishes whether the LLM is better.

**The main goal is to build a cost-controlled, leakage-safe, reproducible benchmark that compares LLM predictions against the existing models on identical historical forecast targets.**

This is an experiment, not an assumption that LLMs are inherently better at forecasting.

## 1. Inspect the repository first

Inspect the existing codebase and identify:

- The data sources and loaders used by skills demand forecasting.
- The data sources and loaders used by AI acceleration forecasting.
- The exact definition of each forecast target.
- Existing forecast horizons, including any different horizon settings between the two systems.
- The historical forecast-origin and train/validation/test split logic.
- The current forecast results and baseline evaluation metrics.
- The existing prediction units and evaluation metrics.
- The application architecture, routing, frontend conventions and backend API structure.

Understand the existing implementation before creating new files or modifying functionality.

Reuse existing read-only data loaders and baseline results whenever possible. Do not duplicate expensive data preparation or retrain existing models unnecessarily.

Do not change the current production forecasting algorithms, their outputs or unrelated application features.

Implement this as a new, isolated LLM Forecast Benchmark page or module within the existing application, following the repository's current architecture. If an independent evaluation script is the quickest way to verify the backend first, implement that as well.

Prioritize a working end-to-end vertical slice over unnecessary abstractions.

## 2. OpenRouter integration

Use OpenRouter's OpenAI-compatible Chat Completions API:

`https://openrouter.ai/api/v1/chat/completions`

Keep model selection configurable through environment variables.

Example configuration:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=qwen/qwen3.5-9b
OPENROUTER_COMPARE_MODEL=openai/gpt-6-luna
OPENROUTER_MAX_SPEND_USD=2.00
OPENROUTER_BATCH_SIZE=10
OPENROUTER_MAX_OUTPUT_TOKENS=2048
```

Adjust these variables and their implementation to fit the project's existing configuration conventions.

Requirements:

- Never hard-code the API key.
- Never expose the API key to frontend code.
- Never commit a real key to version control.
- Add appropriate entries to `.gitignore` and `.env.example`.
- Use configurable model IDs so models can be replaced without code changes.
- Support structured JSON output when the selected model supports it.
- Validate and parse responses instead of trusting arbitrary model-generated text.
- Set a low temperature where supported.
- Impose output-token limits, request timeouts and bounded retries.
- Handle provider failures, malformed responses, rate limits and partial batches.
- Capture token usage and estimated or reported request costs.
- Do not send web-search or external research tools to the forecasting model.
- Do not assume that a model name guarantees a particular price or capability; inspect the current model information where feasible.

The benchmark should work with paid OpenRouter models and support a configurable model selection. Do not make it dependent on a particular free model remaining available.

Use the current listed pricing to estimate costs, and prefer actual reported usage costs where available.

## 3. Experiment A: Zero-shot LLM forecasting

Use a pretrained LLM to forecast the next target using the historical observations available at the forecast origin.

The LLM must receive a structured input describing:

- Benchmark type.
- Forecast-origin date.
- Forecast horizon.
- Target variable and units.
- Valid target range.
- Historical observations available before the forecast origin.
- Relevant historical counts, denominators, timestamps and explanatory variables that would genuinely have been available at that time.
- Any other existing input features that are part of the current forecasting pipeline and are available at the forecast origin.

Preserve the existing forecasting target definitions and units. Do not silently change what the model is being asked to predict.

### Skills demand forecasting

Use the actual time-series representation employed by the current skills forecasting implementation.

Include relevant historical skill-share values and advertisement counts where available. Preserve the existing definition of the target share and its denominator.

Do not treat missing months as zero-demand observations.

Do not introduce external package statistics, news, internet searches or other new signals in the primary experiment. The purpose of this experiment is to test whether the LLM can forecast better using information comparable to the existing model.

### AI acceleration forecasting

Inspect the existing AI acceleration model to determine exactly what it predicts.

Preserve its existing target definition, forecast horizons, measurement units and historical data preparation. If the application evaluates different horizons, evaluate each horizon separately.

For example, if the existing model forecasts AI capability time horizons at three, six and twelve months, retain those definitions rather than inventing an alternative target.

Do not assume that AI time-horizon growth is linear or that the next period's growth rate equals the historical average.

### Required output

The LLM should return machine-readable numerical predictions with a stable identifier for every requested forecast.

For example:

```json
{
  "predictions": [
    {
      "series_id": "series_001",
      "forecast_value": 0.075
    }
  ]
}
```

This is an illustrative schema; adapt the output units and fields to the actual target.

The model should return the required numerical values, not a long explanation for each observation.

Allow the application to validate numerical bounds and units, reject invalid outputs and record missing predictions as failures rather than silently replacing them with fabricated values.

Do not automatically accept self-reported confidence as calibrated statistical uncertainty.

## 4. Experiment B: Few-shot forecasting using my historical data

Implement a second experimental mode that supplies historical forecasting examples within the LLM's prompt.

This is important because I want to investigate whether the data I already collected can improve an LLM's performance.

This is in-context learning, not fine-tuning. Do not attempt to update the LLM's model weights through OpenRouter.

For every forecast origin:

1. Find historical examples whose forecast targets had already been observed before that origin.
2. Construct each example using only information that was available at its original forecast origin.
3. Include the corresponding historical target that became known afterwards, provided that target was already available at the current forecast origin.
4. Select examples from eligible earlier data, using a configurable deterministic sampling or similarity-based selection method.
5. Include a small number of representative examples in the prompt.
6. Ask the LLM to forecast the new series using those examples and its own observed history.
7. Ensure that no future target, validation outcome or test result enters the current prompt.

Use the same forecast horizon and target definition for the examples and the current forecast wherever possible.

Use examples from older observations and other eligible series where useful, without assuming that all skills or AI-model capability series share identical dynamics.

Keep the number of examples small and configurable to control token usage.

Compare the few-shot approach with zero-shot forecasting. Do not assume that including more examples necessarily improves accuracy.

## 5. Prevent historical information leakage

This is a mandatory requirement.

A model trained on public information may already know historical technology trends or AI capability results that occurred after an old forecast origin. Therefore, using the real identity of a skill or AI model could inadvertently expose historical outcomes through the pretrained model's knowledge.

Implement two clearly distinguished evaluation modes.

### Primary: Leakage-controlled numerical benchmark

For the primary benchmark:

- Replace skill names and AI-model names with anonymous stable identifiers.
- Supply only historical observations and features available at each forecast origin.
- Disable internet access and external retrieval.
- Do not provide the validation or test targets to the LLM.
- Do not include information derived from later observations.
- Use only historical few-shot examples that would have been available at that origin.
- Keep future outcomes entirely outside the prediction request and its context.

The model must forecast from numerical and historical evidence rather than its knowledge of the named technology or AI model.

### Optional: Name-aware exploratory benchmark

If useful, implement an optional experiment that includes real skill or AI-model names.

Clearly label this mode as exploratory because the pretrained model could have prior knowledge of historical outcomes or events.

Do not present its results as equivalent to the leakage-controlled benchmark.

Do not mix its results with the primary benchmark when selecting the winning forecasting method.

## 6. Use a fair chronological evaluation

Compare the LLM with the existing forecasting methods on identical forecast origins and realized targets.

Use the same evaluation periods, target definitions and eligible series wherever possible.

Start with a small, representative pilot:

- Up to 100 eligible skill series and up to four forecast origins per series.
- Up to 100 eligible AI acceleration series and up to four forecast origins per series, if that many exist.
- Use all eligible historical series when the relevant AI acceleration dataset is smaller.
- Use a fixed sampling seed for reproducibility.
- Select the sample without using future outcomes to decide which series should be included.
- Keep the sample, origins and target dates fixed across model comparisons.

This results in approximately 800 forecast cases across both benchmark types when the sample sizes permit. Run the initial pilot first, then expand the benchmark only when the results and remaining budget justify doing so.

The pilot should evaluate:

1. Existing model.
2. Zero-shot LLM using the primary, anonymous numerical inputs.
3. Few-shot LLM using the same primary inputs plus eligible historical examples.
4. Optionally, a second LLM on the same sample.

Run only the comparisons needed to establish a useful baseline. Do not make millions of API requests in the initial implementation.

### Existing benchmark results

Reuse existing backtest predictions and metrics if they are available and comparable.

If some baseline predictions must be regenerated, do so using the existing implementation and correct historical cutoffs.

Do not artificially improve the baseline by changing its evaluation definitions.

### Forecasting metrics

For skills demand, retain the existing measures where applicable and report at least:

- Mean absolute error in percentage points.
- Mean signed error.
- Direction accuracy on materially rising and falling skills.
- Error on stable skills.
- Rising-skill and falling-skill forecast bias.
- Results by advertisement-volume and skill-share groups.

Use the existing target-specific evaluation metrics for AI acceleration. Also report an appropriate absolute error, signed bias and any existing scale-specific metric that the project relies upon.

If the AI acceleration target is log-transformed or otherwise transformed, calculate the original-scale metrics correctly in addition to any transformed-scale metrics.

Report:

- Number of evaluated forecast cases.
- Number of successful LLM predictions.
- Invalid-output and request-failure rates.
- Metrics by forecast origin and horizon.
- Comparison against the existing model.

Do not claim improvement simply because the LLM produces more dynamic forecasts or generates a plausible explanation.

## 7. Cost controls and API usage

Credit usage must be bounded, visible and controllable.

The default spend limit should be USD 2.00 for the initial benchmark. Make it configurable.

Before each request:

1. Estimate its maximum or conservative expected cost using the selected model's current listed token prices and the configured output limit.
2. Check whether the remaining budget is sufficient.
3. Skip additional requests if the budget would be exceeded.
4. Record the reason for stopping and the number of forecasts not completed.

Batch compatible forecast cases into requests rather than making one API request per individual prediction. Preserve independent series identifiers so each result can be evaluated against its own target.

Record at least:

- Model identifier.
- Input and output token counts.
- Number of forecast cases in the request.
- Request status and retries.
- Reported cost, when available, and a calculated estimate otherwise.
- Accumulated benchmark expenditure.
- Remaining budget and completion status.

Use the model's current advertised prices or pricing metadata where available, rather than assuming that prices will never change.

Set conservative output-token limits. Avoid generating long reasoning traces and explanations for individual predictions.

Do not retry indefinitely or continue forecasting when the spend limit has been reached.

If feasible, make the pilot resumable so an interrupted run can continue without repeating successful paid requests.

## 8. Keep the benchmark isolated and reproducible

Do not replace the current production forecasting methods.

The new benchmark should read from existing data sources without changing their contents or altering the results used by the existing application.

Store benchmark results separately, with enough metadata to reproduce the comparison.

Record:

- Evaluation sample and forecast-origin identifiers.
- Model and configuration versions.
- Forecast horizon and target definitions.
- Prompt mode and relevant prompt-template version.
- Input and output token usage.
- Numerical predictions.
- Corresponding actual targets, attached during evaluation rather than sent to the LLM before forecasting.
- Error metrics and run status.

Reuse the application's current database or persistence mechanism if appropriate. Do not introduce a new database solely for this experiment if local files or an existing storage layer are sufficient.

Make the evaluation runnable from a CLI or script as well as accessible through the new benchmark interface where the existing architecture permits.

If the API key is missing, provide a working dry-run or mock mode that verifies data preparation, response validation, cost estimation and evaluation without making paid requests.

## 9. Benchmark interface

Create a functional interface that lets me:

- Select Skills Demand or AI Acceleration.
- Select the available forecast horizons.
- Choose the LLM and prompting method.
- Choose the pilot size and number of forecast origins.
- Set a maximum spend limit.
- Run a benchmark and see progress.
- View existing-model and LLM predictions side by side.
- Compare numerical metrics and directional performance.
- Inspect failed, skipped or invalid forecasts.
- View measured token usage and estimated or reported cost.

Keep the UI within the project's existing design conventions.

Prioritize the core benchmark and result comparison. Do not overbuild a model-management dashboard or unrelated visualizations.

## 10. Tests and acceptance criteria

Add tests covering:

- Historical data cutoff enforcement.
- Prevention of future-target leakage.
- Anonymous series identifiers in the primary benchmark.
- Correct few-shot example eligibility.
- Correct target units and forecast horizons.
- Valid JSON response parsing.
- Missing or invalid numerical outputs.
- Cost-limit enforcement.
- Request retries and partial batch failures.
- Reproducible sampling.
- Correct metric computation.
- Separation between existing production predictions and benchmark outputs.
- Accurate token and cost logging, including unavailable usage metadata.

Use mocked API responses for tests that should not incur real usage.

Before the first live benchmark, print a cost estimate and require an explicit user-initiated run through the project's existing workflow. Never launch a large historical evaluation automatically.

## 11. Execution order

**Phase 1:** Audit the existing code and identify the exact targets, data loaders, horizons and baseline metrics.

**Phase 2:** Build the OpenRouter integration, configuration and structured-response handling.

**Phase 3:** Implement zero-shot numerical forecasting and leakage-safe few-shot forecasting.

**Phase 4:** Build the fixed-sample historical benchmark and the metrics comparison.

**Phase 5:** Integrate the isolated benchmark interface and spend controls.

**Phase 6:** Run unit tests, execute a dry run, inspect the cost estimate and prepare the initial pilot for an explicit live run.

Do not stop after providing pseudocode or a technical proposal. Implement the working system and run all feasible tests.

## 12. Final report

Report:

1. The existing target definitions and data paths discovered.
2. Files created or changed.
3. OpenRouter configuration and selected model IDs.
4. Whether the primary experiment is leakage-controlled.
5. The final evaluation sample, origins and horizons.
6. Comparison metrics for existing, zero-shot and few-shot models.
7. Token usage, actual or estimated expenditure and any failed requests.
8. Whether the LLM improved forecast accuracy, directional performance or neither.
9. Any differences between the anonymous and name-aware experiments.
10. Remaining limitations and the recommended next step.

**Definition of success:** A working, cost-limited OpenRouter benchmark that compares LLM forecasting with the two existing forecasting systems using identical historical targets, leakage-safe evaluation and reproducible metrics, without replacing either production model or claiming unsupported accuracy improvements.