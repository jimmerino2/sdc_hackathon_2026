# Claude Code Prompt: Improve AI Capability Forecasting and Acceleration Prediction

## 1. Project Objective

Improve the existing AI capability forecasting application so it can produce more accurate, well-calibrated forecasts of METR's AI time horizon and better estimates of AI acceleration probability.

This is a hackathon project. Prioritise a functioning end-to-end forecasting system, defensible statistical methods, transparent uncertainty and useful visualisations. Do not overengineer the application.

**The main objective is not to make the predictions look more confident. It is to improve their performance on genuinely unseen historical outcomes.**

Preserve the existing primary measurement:

> The METR 50% task-completion time horizon: the task duration at which an AI model has an estimated 50% probability of successful completion.

Continue predicting the observed METR frontier at:
- 3 months
- 6 months
- 12 months

The application must also report probabilities for three pace categories:
- Faster than the historical growth pace.
- Approximately the same growth pace.
- Slower than the historical growth pace.

In addition, introduce a secondary forecast of the underlying smoothed capability-growth trend. This secondary output must be clearly distinguished from the primary observed-frontier forecast.

## 2. Inspect the Existing Application Before Modifying It

Begin by inspecting the entire relevant forecasting implementation.

Identify:
- The current dataset and its source.
- How historical METR frontier values are constructed.
- The existing naive, drift, damped drift, pooled mean, local trend/Kalman filter, ridge regression and LightGBM implementations.
- How the 3-, 6- and 12-month forecasts are generated.
- How the pace probabilities and Brier scores are calculated.
- How historical backtesting works.
- How the forecasting page and charts receive their data.

Reuse the existing stack, visual design and components where possible.

Implement changes directly in the existing application. Do not create an independent prototype, unnecessarily rewrite unrelated functionality or introduce a mandatory database integration.

The forecasting engine must run locally with a reproducible dataset and configuration.

## 3. Dataset Strategy: Real Measurements Plus Carefully Validated External Signals

Do not immediately replace METR with another dataset.

Use METR as the ground-truth measurement for the primary forecast, then investigate whether additional historical information and external indicators can improve predictive accuracy.

### A. METR primary dataset

Start with the official sources:

- Time Horizon research and published results: https://metr.org/time-horizons/
- Public analysis repository: https://github.com/METR/eval-analysis-public

Inspect the repository to locate the relevant task-level records, model-level measurements and benchmark-version information.

Do not assume the latest published data file contains a complete historical record. Verify its actual schema, coverage and update date.

Where possible, retain:
- Model identity and release date.
- Evaluation date and publication or availability date.
- Reported time horizon and measurement uncertainty.
- Benchmark version.
- Task duration and success observations.
- Data provenance.

Use the latest official data that is actually accessible. If a source cannot be fetched, support importing its downloaded files locally rather than silently substituting fabricated data.

### B. Historical benchmark-version bridge

The current and older METR benchmark versions must not be treated as identical measurement systems.

If overlapping model measurements are available:

1. Match corresponding models across versions.
2. Estimate the relationship between their log₂ time horizons.
3. Quantify the uncertainty in that relationship.
4. Use the older series as a supplementary historical prior or calibrated proxy.
5. Keep the original measurements and bridged estimates distinguishable.

If there are too few overlap observations for a reliable calibration, use the old series only as a weak prior or exclude it from quantitative forecasting.

Never artificially extend the current benchmark's history by copying old values into it.

### C. External datasets

Investigate the following sources as candidates for supplementary predictors:

1. Epoch AI model data: https://epoch.ai/data/ai-models
2. Epoch AI benchmark data: https://epoch.ai/benchmarks
3. LiveBench: https://livebench.ai/

Verify which data is publicly accessible, what its historical coverage is and whether it can be downloaded or queried reliably.

Do not integrate every available dataset by default. Examine each source and retain only fields that could plausibly contain information about future METR outcomes.

Candidate explanatory variables include:

- The frequency of frontier-model releases.
- Time between successive model releases.
- Changes in coding or agentic benchmark performance.
- Improvements in relevant benchmark scores over the preceding 1–3 months.
- The size of improvements achieved by newly released models.
- Training-compute indicators, where reliable historical measurements exist.
- Other evidence of increasing software-task capability.

These are candidate predictors, not assumptions that must be included.

**An external variable should enter the final model only if it adds measurable predictive value beyond the METR-only baseline.**

Do not assume benchmark scores are directly interchangeable with METR time horizons.

If the available external dataset is too short, poorly aligned or inconsistently measured, document the limitation and leave it out rather than forcing it into the model.

## 4. Prevent Data Leakage and Artificially Inflated Accuracy

This is a critical requirement.

Construct historical forecasts using only information that would actually have been available at each forecast origin.

When predicting from an earlier date:
- Do not use a model's future benchmark results.
- Do not use future publication dates.
- Do not use revised measurements unless the revisions were available at that origin.
- Do not use future data to calibrate the old/new benchmark bridge.
- Do not tune features, probability thresholds or model weights using the final test period.

If historical publication snapshots are unavailable, clearly identify the affected tests as approximate rather than claiming fully point-in-time validation.

Calculate the observed frontier from eligible measurements available by each date.

Distinguish between:
- A month with no new frontier record.
- A month with no new measurement available.
- A new measurement of an existing model.
- A new record-producing model release.
- A benchmark or measurement-method change.

Do not interpret an absence of observations as proof that progress stopped.

## 5. Represent Capability in Doubling Units

Use the transformation:

`y = log2(time_horizon_hours)`

Fit trend models using this scale and convert forecasts back into hours for display.

A one-unit increase represents a doubling of the measured time horizon.

Update existing baselines to work on the transformed scale where appropriate:
- Naive.
- Drift.
- Damped drift.
- Pooled mean.
- Local trend/Kalman filter.
- Ridge regression.
- LightGBM.

Keep simple baselines available for comparisons. Do not retain a complex model in the final ensemble solely because it already exists in the codebase.

## 6. Build a Two-Stage, Jump-Aware Forecasting Engine

The observed METR frontier moves in discrete jumps, often separated by periods without a new measured record.

Replace the assumption of smooth monthly progress with an explicit model of frontier jumps.

### Stage A: Probability of a new record

Estimate the probability that the observed frontier will increase during each forecast period.

Start with a simple constant baseline hazard or another appropriately regularised model. Do not assume that a new frontier jump becomes more likely merely because there has not been one for several months.

Use external indicators only when rolling-origin backtests show that they improve this probability estimate.

Account for the difference between:
- A model being released.
- A model being evaluated.
- A model becoming a measured frontier record.

When the evidence cannot distinguish predictable release timing from random timing, preserve that uncertainty.

### Stage B: Magnitude of the frontier jump

Conditional on a new record occurring, estimate the distribution of its improvement in log₂ horizon.

Use observed historical frontier improvements while accounting for:
- Measurement uncertainty.
- Benchmark-version differences.
- The limited number of large jumps.
- The selection bias of observing only models that were evaluated.
- The possibility of unusually large future improvements.

Use shrinkage or conservative priors when data is limited. Avoid fitting a complicated jump-size distribution to a handful of observations.

### Combine both stages

Simulate future frontier trajectories using both components.

Possible outcomes must include:
- No new record.
- A small improvement.
- A large improvement.

Generate at least several thousand Monte Carlo trajectories when computationally practical.

The simulation must also incorporate uncertainty in the current measured frontier and underlying growth rate.

The resulting distribution should determine the central forecast, predictive intervals and raw-frontier pace probabilities.

Do not make the model assume that a jump is due simply because time has passed.

## 7. Add a Secondary Smoothed-Trend Acceleration Forecast

The primary observed-frontier forecast must retain the original measurement and meaning.

Introduce a secondary model that estimates underlying capability growth after separating short-term frontier jumps from gradual trend changes.

This secondary output must use the same underlying METR time-horizon measurement, rather than substituting unrelated benchmark scores as the target.

Possible implementations include:
- A robust local-linear-trend state-space model.
- A Bayesian local trend with a gradually changing slope.
- A jump-aware state-space model in which the latent trend and observed frontier changes are modelled separately.

Start with the simplest implementation that performs well in backtesting.

The smoothed trend should not simply be a rolling average that has been selected because it makes the chart look smoother. Its parameters must be selected using training data and validated on unseen periods.

Provide two explicitly differentiated outputs:

**Primary: Observed frontier**
- Predicts the actual METR frontier in 3, 6 and 12 months.
- Retains the original meaning of the metric.
- Includes the probability of no new frontier record.
- Provides forecast uncertainty.

**Secondary: Underlying acceleration**
- Estimates the latent smoothed growth trend.
- Estimates whether that trend is accelerating, remaining approximately stable or decelerating.
- Includes its own uncertainty.
- Is explicitly labelled as a model-estimated underlying trend, not a direct observation of the frontier.

Do not redefine the original forecast to use the smoothed trend exclusively.

Evaluate both outputs independently. If the secondary output does not demonstrate predictive skill, report that finding honestly.

## 8. Generate Pace Probabilities Consistently

For the primary observed-frontier forecast, derive probabilities from simulated forecast trajectories rather than producing a separate classifier.

For a forecast horizon of `h` months, calculate:

`future_pace = (12 / h) * (future_log2_horizon - current_log2_horizon)`

Compare that future rate with the historical rate using consistent units.

Represent uncertainty in both the future rate and the historical rate. Do not treat the historical rate as perfectly known if it is derived from a noisy or bridged frontier series.

Use a configurable, documented tolerance for the approximately-same category. Start with a reasonable default, but do not optimise the threshold against final test outcomes.

Calculate:
- Probability of faster growth.
- Probability of approximately the same growth.
- Probability of slower growth.

Ensure all three probabilities sum to 100%, allowing for display rounding.

Generate distinct probabilities at 3, 6 and 12 months.

For the secondary smoothed-trend output, use the same category definitions as far as the underlying estimand permits, while clearly identifying that its pace probabilities concern the latent trend rather than whether a raw frontier jump arrives.

Do not blend raw-frontier and smoothed-trend probabilities into a single unexplained number.

Include a separate estimate of the probability that no new frontier record will appear within each forecast period.

The probabilities must come from the fitted model and simulated trajectories, not manually assigned or hardcoded values.

## 9. Backtesting and Model Selection

Implement a reproducible rolling-origin backtesting pipeline.

For every eligible historical forecast origin:

1. Construct the training data using only information available at that origin.
2. Fit each candidate model.
3. Generate the 3-, 6- and 12-month predictive distributions.
4. Derive the pace probabilities.
5. Compare forecasts with actual subsequent observations.
6. Record point-forecast errors, interval performance and probability scores.

Evaluate each forecast horizon separately.

### Forecast accuracy

Report:
- Mean absolute error in log₂ units.
- Median absolute error where useful.
- Multiplicative error in predicted hours.
- Predictive interval coverage.
- Predictive interval width or weighted interval score.

### Probability accuracy

Report:
- Multiclass Brier score.
- Log loss.
- Calibration diagnostics.
- Frequency of each realised class.
- Forecast sample size.
- Performance against a uniform one-third baseline.
- Performance against a training-data-only base-rate baseline.

Use a conventional multiclass Brier-score definition consistently and document it. If the score's scale differs from the existing application, make the definition explicit rather than comparing incompatible values.

### Test dependence

The historical forecasts overlap in time, so neighbouring test cases are not independent.

Where sufficient data exists:
- Add a non-overlapping forecast-origin evaluation.
- Use block-bootstrap or another dependence-aware uncertainty assessment.
- Keep a final time-based holdout separate from model development and tuning.

If there are too few observations to produce a meaningful independent test set, document that limitation instead of manufacturing extra test cases.

### Choose models based on evidence

Prefer models that improve performance consistently across eligible historical origins and forecast horizons.

Do not assume that an ensemble, a more complex Bayesian model or additional external predictors must outperform a simpler baseline.

If a supplementary signal does not improve out-of-sample results, exclude it.

If the evidence is inconclusive, keep the simpler model and make the uncertainty visible.

## 10. Probability Calibration and Confidence

The primary goal is to produce probabilities that are useful and statistically defensible.

If sufficient data exists, test probability calibration on held-out rolling-origin forecasts.

Where calibration is justified, apply a simple method such as regularised temperature scaling or another suitable multiclass calibration method. Fit the calibrator using training-period forecasts only.

Do not fit a calibration model on a tiny number of outcomes simply to make the probability bar appear more decisive.

When evidence is insufficient:
- Retain a transparent probability estimate from the predictive distribution.
- Consider conservative shrinkage towards an appropriate training-only base rate.
- Mark the confidence assessment as experimental.
- Report whether the model has demonstrated skill against the baselines.

Never force the three categories to appear equally likely or assign an artificial winner.

## 11. UI and Visualisation

Preserve the existing forecasting page and visual design.

Improve the existing visualisations to distinguish the different questions the model answers.

### Primary observed-frontier panel

Display:
- Current measured METR frontier.
- Forecasts at 3, 6 and 12 months.
- Historical observations.
- Central forecasts.
- 80% predictive intervals where supported by the model.
- Probability of no new record.
- Faster/same/slower probabilities for each horizon.

### Secondary underlying-trend panel

Display:
- The observed frontier.
- The model-estimated smoothed trend.
- The inferred growth rate.
- Whether the growth trend is accelerating, stable or decelerating.
- Uncertainty around the trend and its future direction.

Clearly distinguish observed data, bridged historical estimates and future predictions.

Do not portray the smoothed line as the actual observed frontier.

### Diagnostics panel

Add a compact expandable methodology and validation panel containing:
- Data sources and latest data dates.
- Benchmark versions.
- Any cross-version calibration used.
- Selected forecasting models.
- The historical backtest sample size.
- Backtesting results against baselines.
- Whether external signals improved prediction.
- Whether probability calibration has been validated.
- Relevant uncertainty and known limitations.

Keep the core charts readable. Do not overwhelm the main page with technical diagnostics.

## 12. Engineering Requirements

- Reuse the existing application stack and project conventions.
- Keep the forecasting engine separate from UI components.
- Implement reusable functions for data ingestion, frontier construction, benchmark bridging, jump modelling, trend smoothing, simulation, backtesting and pace-probability calculation.
- Keep the system runnable locally without Supabase.
- Cache downloaded data where appropriate and make simulations reproducible.
- Handle missing data, inaccessible sources, invalid measurements and insufficient history.
- Avoid unnecessary dependencies.
- Preserve unrelated application functionality.
- Add tests for benchmark-version handling, point-in-time data leakage, jump simulation, trend estimates, interval construction, pace probabilities and backtesting.

Do not merely produce a plan, mock results or placeholder implementations. Implement the working pipeline and run the available tests.

## 13. Definition of Done

The implementation is complete when:

1. The application can load the real METR dataset or clearly explain what local data is needed.
2. The observed frontier is constructed correctly.
3. Historical backtests respect information available at each forecast origin as far as the source data permits.
4. The primary forecast produces 3-, 6- and 12-month predictions with uncertainty.
5. The jump model represents both the occurrence and magnitude of frontier improvements.
6. The secondary smoothed-trend forecast works and is clearly distinguished from the observed-frontier forecast.
7. The pace probabilities are derived from simulated trajectories and documented definitions.
8. The probability of no new record is displayed separately.
9. External variables are retained only when their contribution has been tested.
10. The backtest compares the resulting model against simple baselines.
11. The forecasting page works locally without a database requirement.
12. Unverified accuracy improvements are not claimed.

## 14. Final Implementation Report

After completing the implementation, provide:
- The files changed and the main architectural changes.
- The official datasets successfully accessed and the date coverage of each.
- The external variables tested and which ones were retained.
- How the benchmark bridge, jump model and smoothed-trend model work.
- Backtesting results for the 3-, 6- and 12-month horizons.
- Brier scores and other probability metrics compared with baselines.
- Whether the non-overlapping evaluation supports the reported improvements.
- Any remaining data limitations or incomplete acceptance criteria.

Prioritise a working and honestly evaluated forecasting system. Do not invent observations, fabricate test outcomes or overstate the reliability of acceleration probabilities.