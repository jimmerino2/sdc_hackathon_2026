# Claude Code Task: Improve IT/Software Skills Demand Forecasting

## Objective

Improve the existing skills demand forecasting system because its current six-month forecasts perform poorly at identifying rising and falling skills.

The current implementation has already been backtested across approximately 1.6 million scored forecasts. The investigation identified these problems:

- `mean12` is selected in `models.py` because it achieves the lowest pooled average error, despite its 0% direction accuracy on the reported subset of materially moving series.
- The forecast is effectively a trailing average that cannot anticipate meaningful changes.
- The existing `trend` method can overreact to small counts because its log-odds slope is insufficiently shrunk according to uncertainty.
- `backtest.py` calculates direction accuracy but does not use it when selecting the winning model.
- The direction label compares the forecast against a trailing 12-month share, which makes `mean12` appear directionally flat by construction.
- Sparse series and stable skills dominate the aggregate evaluation, concealing poor performance on emerging or declining skills.

Your job is to fix the underlying forecasting and evaluation logic, not merely improve charts, rename models, or add explanatory labels.

**The primary goal is a functional, empirically validated six-month skill demand forecasting model that predicts meaningful rises and falls while remaining robust to noise.**

Do not assume that a more sophisticated method will automatically perform better. Implement reasonable candidates, compare them through proper backtesting, and serve the best-performing approach based on measured results.

## 1. Scope and constraints

### Scope

For this iteration, focus exclusively on IT/software occupations and their associated skills.

- Use the project's existing occupation classification and filtering logic to establish the in-scope IT/software population.
- Do not attempt to solve forecasting for every occupation or industry yet.
- Where appropriate, leverage evidence across multiple IT/software occupations to estimate shared model parameters, while preserving skill-specific signals.
- Do not claim that the approach generalizes to unrelated occupations.
- If some skills or IT/software roles still have insufficient observations, handle their uncertainty appropriately rather than fabricating confidence.

### Implementation constraints

1. Inspect the existing repository and understand the complete forecasting path before making changes.
2. Investigate `models.py`, `backtest.py` and every related module responsible for data preparation, feature construction, model selection, forecast serving, uncertainty intervals and direction labels.
3. Preserve the existing application architecture, unrelated forecasting functionality and API contracts wherever possible.
4. Do not rebuild the entire application or introduce unnecessary dependencies.
5. Prioritize a working end-to-end forecasting implementation over production-grade abstractions or additional features.
6. Do not introduce Supabase integration changes or unrelated database work.
7. Do not change the definition of the forecasting target silently. Determine whether the existing target is the share at month six or an aggregation over the next six months, document it, and preserve it unless there is a compelling, explicitly justified reason to change it.
8. Never use future observations in historical forecasts, feature engineering, model selection or uncertainty calibration.

## 2. Audit the current implementation

Before editing, trace the complete flow:

Raw job advertisement data
→ monthly skill-demand aggregation
→ historical feature construction
→ candidate model predictions
→ six-month forecasting
→ model selection
→ direction classification
→ uncertainty estimation
→ forecast API or UI.

Identify:

- The precise numerator and denominator used to calculate skill share.
- Whether the percentage represents a monthly share, a pooled share across advertisements, or another measure.
- How months with no advertisements, missing observations and zero skill mentions are represented.
- The exact six-month forecasting target and evaluation window.
- Whether historical observations are weighted by advertisement volume.
- How candidate models are trained and how their parameters are selected.
- Whether backtesting reproduces the data that would genuinely have been available at each forecast origin.
- How confidence intervals and direction labels are derived.

Do not assume that the diagnosis above captures every implementation issue. Verify it against the code.

Keep the existing backtest as a reproducible baseline before modifying the system. Record the current performance metrics, served model and relevant configuration.

## 3. Implement and compare forecasting candidates

Retain the current `mean12`, ridge, blend and trend implementations as appropriate for comparison. Add or improve candidates that address the actual weaknesses.

At minimum, investigate the following approaches.

### A. Recent-level baseline

Create a forecast based on the most recent three-month skill-share estimate.

Also evaluate an exponentially weighted recent-level estimate, so that more recent observations receive more influence than older observations.

If the target represents the share across pooled advertisements, compute an appropriate pooled estimate using the underlying counts. If the target instead represents an equal-weighted average of monthly shares, preserve that definition.

The purpose is to reduce stale predictions when the underlying market changes.

### B. Shrunk, damped trend forecast

Create an interpretable trend-aware model that estimates recent direction and magnitude before projecting forward.

Use a statistically appropriate approach for bounded proportions, such as a smoothed logit-share trend or another method justified by the existing data.

Requirements:

- Account for the number of relevant advertisements supporting each observation.
- Smooth small counts and zero observations appropriately before applying transformations such as logit.
- Estimate the recent trend using a window or weighting scheme chosen through rolling-origin validation.
- Explore signals such as differences between recent three-month and preceding three-month shares, as well as slopes over recent history.
- Shrink uncertain slopes toward zero.
- Apply trend damping or another validated correction to avoid linear extrapolation of a short-lived movement over six months.
- Reduce reliance on a trend when its direction or magnitude is inconsistent across recent observations.
- Prevent predictions from falling outside the valid share range.
- Distinguish genuine missing data from an observed month with zero skill mentions.
- Avoid treating an isolated spike as sufficient proof of a sustained trend.

Estimate trend shrinkage, window lengths and damping parameters using historical validation data. Do not select arbitrary constants merely because they make a sample forecast look better.

### C. Adaptive recent-level-plus-trend forecast

Evaluate a forecast that starts from a recent estimate of the skill's share and adds a reliability-adjusted trend projection.

Conceptually:

forecast = recent skill-share level + horizon × adjusted trend

The adjusted trend should depend on evidence strength, uncertainty and validated trend persistence.

This model should behave differently in different circumstances:

- **Strong, sustained increase:** respond to the increase, with appropriate damping.
- **Strong, sustained decline:** forecast a decline rather than remaining anchored to the historical average.
- **Single-month spike:** avoid extrapolating the spike aggressively.
- **Weak evidence:** favor a conservative recent-level estimate.
- **Emerging skill with limited history:** use available recent evidence, but reflect its uncertainty instead of automatically reverting to a long historical average.
- **Skill near 0% or 100%:** respect the bounds of the forecast target.

Compare the adaptive forecast against the existing ridge and blend methods, and retain the adaptive approach only if the evidence supports doing so.

### D. Seasonality and other alternatives

Evaluate seasonal-naive or other simple forecasting alternatives only when the existing data provides enough evidence of repeatable seasonality.

Do not assume yearly seasonality simply because the observations are monthly.

Do not add deep learning, complicated ensemble architectures or extensive external data integration unless simpler methods demonstrably fail and the additional complexity is justified.

## 4. Redesign the backtesting and model-selection criteria

This is a core requirement, not an optional reporting improvement.

A single pooled average error must no longer be sufficient to establish that a candidate is the best model.

### A. Use rolling-origin backtesting

Evaluate candidates at multiple historical forecast origins using the same forecast horizon as the production system.

At each origin:

1. Restrict all inputs to information available at that point.
2. Fit or calibrate the candidate using only allowable historical data.
3. Produce the actual six-month-ahead forecast.
4. Compare the prediction with the corresponding realized target.
5. Advance the origin and repeat.

Use chronological validation and a genuinely untouched final test period where sufficient history exists.

Do not tune parameters on the final test period. Check all preprocessing, smoothing and model-selection steps for leakage.

Use comparable origins and eligible series when comparing candidates.

### B. Report multiple complementary metrics

Report at least:

1. Overall mean absolute error in percentage points.
2. Mean signed error, to reveal systematic over- or under-forecasting.
3. MAE for materially rising skills.
4. MAE for materially declining skills.
5. Direction accuracy among materially moving skills.
6. Forecast bias for rising versus falling skills.
7. Performance on approximately stable skills.
8. Performance across skill-share levels and advertisement-volume bands.
9. Prediction-interval coverage, if uncertainty intervals are produced.
10. Performance by forecast origin, so a model is not declared successful because of one favorable period.

For direction accuracy, report the results for multiple predefined material-change thresholds, including 1 and 2 percentage points where supported by the target definition.

Report the number of observations in each evaluation group. Do not present direction accuracy without its sample size.

Use both series-level metrics and appropriately defined advertisement-volume-weighted metrics where useful. Explain what each metric measures and avoid allowing thousands of tiny, largely static series to conceal poor performance on moving skills.

Use unweighted or weighted aggregation consistently with the intended business objective; do not change weighting simply to make a candidate win.

### C. Correct direction evaluation

Correct the existing direction calculation in `backtest.py`.

The direction of a forecast must be calculated relative to a contemporaneous baseline available at the forecast origin, such as a reliable recent three-month skill-share estimate.

Compare that baseline with the forecast target to determine the predicted change.

For evaluation, compare the predicted change with the realized change measured from the same baseline to the actual target over the same horizon.

Classify predictions and outcomes consistently as rising, falling or approximately stable.

A correct direction label must not be generated merely because a forecast repeats its trailing average. Conversely, do not force every skill to rise or fall when its predicted movement is too small or uncertain to distinguish reliably from stability.

Keep the directional definitions identical between the backtest and production serving path.

### D. Redesign model selection

Retain the current overall MAE and other existing metrics, but introduce a transparent model-selection criterion that accounts for:

- Overall forecast accuracy.
- Error on materially moving skills.
- Direction accuracy on materially moving skills.
- Systematic bias on rising and falling skills.
- Stability of performance across historical forecast origins.

Use a documented composite score or another defensible selection rule. Make any weights configurable and explain their rationale. Evaluate whether the model ranking changes materially under reasonable changes to those weights.

Do not choose a complex model solely because its direction accuracy improves, if its forecast errors deteriorate substantially. Equally, do not let a nearly flat model win automatically because of a tiny improvement in pooled MAE while failing to detect meaningful movement.

A candidate should demonstrate acceptable overall accuracy and a credible improvement in the dimensions it is designed to fix.

If the evidence is inconclusive, prefer a conservative model and clearly report the limitation instead of claiming an improvement.

## 5. Improve trend reliability and uncertainty

Use the available advertisement counts and rolling-backtest errors to improve the treatment of uncertainty.

Where appropriate:

- Estimate or approximate sampling uncertainty in the skill share.
- Make trend estimates less aggressive when they rely on limited evidence.
- Assess whether recent movements persist across multiple observations.
- Calibrate prediction intervals using historical out-of-sample errors, ideally accounting for share level, horizon and evidence strength where sufficient data exists.
- Check interval coverage rather than assuming that historically pooled intervals are valid for all types of skills.
- Keep confidence in the direction separate from uncertainty in the forecasted share where the existing design supports that distinction.

Do not equate a large observed percentage change with strong evidence when it is based on very few advertisements.

Do not treat an entire month without available advertisement data as a zero-demand observation.

Avoid adding arbitrary confidence scores or unsupported certainty claims.

## 6. Keep the output compatible with the existing product

Integrate the selected model into the actual serving path rather than leaving it as an isolated backtest experiment.

Preserve existing API and UI contracts wherever possible. Reuse existing output fields when practical and introduce additional fields only when necessary.

The forecast output should allow the existing application to communicate:

- Current or recent observed skill share.
- Forecast share for the existing six-month target.
- Forecast change in percentage points relative to the recent baseline.
- Direction: rising, falling, or approximately stable.
- An uncertainty indication or prediction interval, if supported by the model and existing interface.

Where evidence is insufficient, represent uncertainty explicitly instead of presenting a flat forecast as a confident prediction.

Make sure the model selected by the backtest is the model actually used by the production forecast endpoint or relevant application component. Avoid discrepancies between backtest logic and serving logic.

Do not redesign unrelated application pages.

## 7. Add regression tests

Add or update tests for the forecasting and evaluation pipeline.

Include cases for:

- A sustained increase in skill share.
- A sustained decrease in skill share.
- A noisy one-month spike followed by reversion.
- A skill whose share remains approximately stable.
- A low-frequency skill with only a small number of matching advertisements.
- Months with zero advertisement volume versus months with zero skill mentions.
- A rapid change in total advertisement volume.
- Shares near their valid lower and upper bounds.
- Insufficient historical observations.
- Correct direction classification relative to the recent baseline.
- Consistent direction calculations between backtesting and production serving.
- Prevention of future-data leakage.
- Reproducible evaluation and model selection.

Tests should verify both forecast values and their direction classifications. Do not hard-code expected performance improvements without evidence.

## 8. Implementation workflow

Complete the work in this order:

**Phase 1 — Audit:** Trace the existing code and reproduce the reported baseline.

**Phase 2 — Forecasting:** Implement the recent-level and improved trend-aware candidates with appropriate smoothing, shrinkage and damping.

**Phase 3 — Evaluation:** Correct directional evaluation, implement rolling-origin comparisons and introduce the documented multi-metric selection criterion.

**Phase 4 — Integration:** Connect the chosen approach to the existing production forecasting path, preserving application compatibility.

**Phase 5 — Verification:** Run the relevant tests and backtests, investigate regressions, and verify that the deployed prediction path uses the evaluated model.

Do not stop after describing a proposed solution or writing pseudocode. Implement the working changes in the repository.

If a step is blocked by missing data or unavailable project dependencies, complete the other feasible steps and explain the specific limitation.

## 9. Final report

When finished, provide a concise but evidence-based report containing:

1. The root causes confirmed in the code.
2. The files changed and the purpose of each change.
3. The forecasting candidates implemented.
4. The backtesting methodology and historical periods used.
5. A comparison table of the original baseline and all relevant candidates, including MAE, signed bias, rising-skill MAE, falling-skill MAE and direction accuracy on materially moving skills.
6. Results at the 1- and 2-percentage-point movement thresholds, with sample sizes.
7. Whether the selected approach improves meaningful trend detection without an unacceptable deterioration in overall accuracy.
8. The final model-selection rule and the reason the winning candidate was selected.
9. The tests executed and their outcomes.
10. Remaining weaknesses, data limitations and any work that could not be completed.

Distinguish measured results from assumptions. Do not claim that the model has improved unless the backtest supports that claim.

**Definition of success:** The end-to-end forecast uses the evaluated model, remains compatible with the existing application, and demonstrates through leakage-safe historical evaluation that it provides a better balance between forecast-level accuracy and the ability to identify meaningful increases and decreases in IT/software skill demand.