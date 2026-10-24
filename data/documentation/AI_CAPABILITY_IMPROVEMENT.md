# Claude Code Prompt — Improve AI Time-Horizon Forecasting and Acceleration Probabilities

## Objective

Improve the accuracy and reliability of my existing AI capability forecasting system for a hackathon prototype.

The system forecasts METR's 50% task-completion time horizon, which measures the human-expert task duration at which an AI agent is predicted to succeed 50% of the time.

**Preserve the existing measurement and forecast targets. Do not redefine what is being measured.**

The system must continue forecasting the METR frontier at:
- 3 months
- 6 months
- 12 months

It must also estimate the probability that AI time-horizon growth over each future period will be:
- Faster than the historical pace
- Approximately the same as the historical pace
- Slower than the historical pace

The main goal is to improve the actual forecasting methodology, not merely change the presentation of predictions.

This is a hackathon prototype. Prioritise a working end-to-end forecasting engine, defensible statistical methods and useful visual output over production-grade infrastructure.

## 1. Inspect the Existing Project First

Before changing code:

1. Inspect the current repository, forecasting page, data pipeline, existing models, visualisations, dependencies and tests.
2. Identify how the current forecast values and faster/same/slower probabilities are calculated.
3. Determine why the existing methods may be inaccurate.
4. Reuse existing architecture and UI components wherever possible.
5. Implement the improvements directly in the current project. Do not create a disconnected prototype or unnecessarily rewrite unrelated pages.

The currently implemented models include:

- Naive forecast
- Drift
- Damped drift
- Pooled mean
- Local trend using a Kalman filter
- Ridge regression
- LightGBM

Retain these as baselines where appropriate. They do not all need to remain in the final production forecast if backtesting shows that some add no predictive value.

Do not integrate Supabase or introduce a mandatory external backend for this task. The forecasting engine must work locally with a reproducible dataset and calculations.

## 2. Data Strategy: Use a Pragmatic, Measurement-Aware Workaround

The available historical data is too limited to support an unrestricted, high-dimensional forecasting model. Address this directly rather than pretending more observations exist.

### Primary data source

Use official METR data wherever possible:

- Time Horizon 1.1 current benchmark: https://metr.org/time-horizons/
- Public analysis repository: https://github.com/METR/eval-analysis-public
- Current benchmark data file: https://metr.org/assets/benchmark_results_1_1.yaml

Inspect the official data format and use the appropriate historical Time Horizon 1.0 data from the repository where accessible.

Do not assume that the current benchmark data file contains a complete history of monthly frontier observations. Inspect the actual contents.

If an official source cannot be fetched automatically, support importing a locally stored CSV or YAML file. Do not silently replace missing real data with fabricated observations.

### Use three distinct data layers

**Layer A — Observed data**

Store actual published METR model measurements with available metadata, including:
- Model name and release date
- Evaluation or measurement date, if available
- Publication or availability date, if available
- Time horizon in hours
- Benchmark version
- Reported uncertainty or confidence interval, if available
- Data source and provenance

Preserve the original data and its units.

**Layer B — Historical bridge and prior**

The older Time Horizon 1.0 series may provide useful historical information about the pace of capability growth.

Where models have measurements under both benchmark versions:

1. Match the overlapping models.
2. Compare their log₂ time horizons.
3. Estimate a robust calibration mapping between versions.
4. Quantify the uncertainty in that mapping.
5. Use the older series as an informative prior or historical proxy for the new series.

Do not concatenate Time Horizon 1.0 and 1.1 values as though they are directly comparable measurements. Clearly distinguish actual observations from bridged estimates.

If the overlap is too small to estimate a credible mapping, use the older series only as a weak prior and widen the resulting uncertainty.

**Layer C — Simulated trajectories**

Generate thousands of simulated future trajectories using the fitted probabilistic forecasting model.

These simulations may be used to:
- Estimate predictive intervals
- Estimate faster/same/slower probabilities
- Test sensitivity to modelling assumptions
- Evaluate possible future jump scenarios

Synthetic trajectories must never be presented as real historical measurements or used as independent evidence that the model is accurate.

### Reconstruct the frontier correctly

The forecasting target is the best measured 50% time horizon available at each forecast origin.

For each timestamp, calculate the maximum eligible time horizon among the measurements that were actually available by that date.

Respect publication-time availability wherever possible. A measurement published in the future must not appear in the training data of an earlier historical forecast.

If exact historical publication snapshots are unavailable, document that limitation and distinguish the resulting approximate backtest from a fully point-in-time backtest.

Distinguish these cases:
- No new frontier result was recorded.
- No new measurement was available.
- A previously measured model became available for the first time.
- A new benchmark version or modelling correction changed historical values.

Do not interpret missing measurements as proof that AI progress stopped.

## 3. Represent the Time Horizon in Doubling Units

Transform the time horizon before fitting trend models:

`y = log2(time_horizon_hours)`

Use this representation as the primary modelling scale.

A one-unit increase represents a doubling of the measured time horizon. Predictions and errors should therefore be compared in doubling units, rather than treating absolute errors in raw hours as equivalent at every scale.

Convert forecasts back to hours for display.

Ensure all models use a consistent time unit, timestamp convention and 50% time-horizon definition.

## 4. Implement a Jump-Aware Probabilistic Forecasting Model

The frontier is a staircase rather than a smooth monthly signal. It can remain unchanged for a while and then increase sharply when a stronger model is measured.

Create a forecasting engine that represents both:
- The gradual underlying growth trend.
- The probability, timing and magnitude of discrete frontier jumps.

Start with a simple model that can be estimated from limited observations. Do not introduce unnecessary model complexity.

### Component A — Conservative trend

Implement a damped-trend forecast in log₂ units.

Use it as a conservative baseline that avoids extrapolating a recent steep slope indefinitely.

### Component B — Local trend

Improve the current local-trend implementation or replace it with a robust state-space equivalent.

Track:
- Latent frontier level
- Current growth rate
- Uncertainty in the level and growth rate
- Gradual changes in the growth rate

Use robust error assumptions where appropriate so one unusually large observation does not dominate the entire forecast.

### Component C — Jump process

Implement a simple probabilistic model for frontier jumps.

It should estimate:
- The likelihood of a frontier jump over a given period.
- The distribution of jump sizes.
- The possibility of a zero-jump period.
- The possibility of a larger-than-usual jump.

Use shrinkage or conservative priors because the recent benchmark history is short.

Where useful, use actual model-level observations to help estimate jump-size distributions, but account for benchmark-version differences and the selection bias inherent in observing only evaluated models.

Do not assume monthly frontier increments are independent and identically distributed without testing that assumption.

### Component D — Ensemble

Combine the best distinct forecasting approaches instead of blindly selecting the method with the smallest error on a tiny historical sample.

Use rolling-origin backtesting to estimate model performance.

Apply weight regularisation or shrinkage so an apparently successful model does not receive extreme weight merely because it performed well on a few test cases.

Keep a simple baseline in the ensemble unless there is strong evidence that doing so is harmful.

LightGBM and ridge regression may remain comparison models, but do not let them dominate when the dataset is too small to support reliable estimation.

### Predictive simulations

Generate at least several thousand Monte Carlo forecast trajectories for the 3-, 6- and 12-month horizons.

Each trajectory should reflect:
- Uncertainty in the current frontier
- Uncertainty in the underlying growth rate
- Potential frontier jumps
- Residual variation
- Historical benchmark calibration uncertainty, if a bridge is used

Use a reproducible random seed where appropriate.

Calculate the central forecast and predictive intervals from these simulated trajectories. Use an 80% predictive interval when displaying the likely range, and explain what that interval represents.

Do not claim that an interval is calibrated unless historical validation supports that claim.

## 5. Calculate Pace Probabilities from the Forecast Distribution

This is a critical requirement.

Do not use an independent classifier or manually assigned probabilities to generate the faster/same/slower bar.

Derive the probabilities from the same simulated future trajectories used to generate the time-horizon forecasts.

### Historical pace

Define the historical pace in doublings per year.

When a reliable 12-month history is available for Time Horizon 1.1, use the change in log₂ frontier over the past 12 months.

When the new benchmark does not have sufficient comparable history, use the calibrated historical bridge only if it is defensible. Label the result as a bridged or prior-assisted baseline, rather than presenting it as a directly observed 12-month trend.

Carry uncertainty in the historical pace into the probability calculation.

Do not silently treat a short recent period as a full year of observations.

### Future pace

For each simulated trajectory and forecast horizon `h` months, calculate:

`future_pace = (12 / h) * (future_log2_horizon - current_log2_horizon)`

Compare the future pace against the historical pace using consistent units.

Define an explicit, configurable tolerance for “approximately the same pace”.

Use a sensible default, such as:

`delta = max(0.25 doublings/year, 20% of absolute historical pace)`

Make this a documented configuration setting, not a value selected to maximise the score on the final test set.

Classify each simulation as:
- Faster: future pace exceeds historical pace plus the tolerance.
- Same: future pace is within the tolerance.
- Slower: future pace is below historical pace minus the tolerance.

Calculate the percentage of simulated trajectories assigned to each category.

The three probabilities must sum to 100%, subject only to harmless display rounding.

Generate separate pace probabilities for 3, 6 and 12 months.

### Calibration and fallback

When sufficient data exists, evaluate and calibrate the probabilities using rolling-origin historical forecasts.

When the data is insufficient:
- Use conservative shrinkage towards an appropriate historical base rate.
- Make uncertainty and limitations visible.
- Mark the estimate as experimental or prior-assisted.
- Never force the probabilities to appear more certain than the evidence supports.

Do not assume that using Monte Carlo simulation automatically makes the probabilities accurate.

## 6. Rigorous Historical Backtesting

Implement a reproducible rolling-origin backtesting pipeline.

At each historical forecast origin:
1. Use only information available at that origin.
2. Fit or update each model.
3. Forecast 3, 6 and 12 months ahead.
4. Compare predictions with the corresponding later observations.
5. Record errors and probabilistic scores.
6. Move the forecast origin forward and repeat.

Respect the available data. Do not invent historical outcomes when a horizon cannot be evaluated.

Keep a final time-based holdout separate from model development and tuning wherever the dataset size permits. If the sample is too small for a meaningful holdout, state that limitation.

### Metrics

For horizon forecasts, report:
- Mean absolute error in log₂ units.
- Median absolute error where useful.
- Error in doublings and multiplicative error in hours.
- Predictive interval coverage.
- Predictive interval width or weighted interval score.

For faster/same/slower probabilities, report:
- Multiclass Brier score.
- Log loss, with appropriate safeguards against numerical extremes.
- Class frequencies and calibration diagnostics.
- Number of evaluated forecast cases.

Compare against naive and simple trend baselines.

A lower error on one tiny holdout is not sufficient evidence that a model is superior. Report the test sample size and avoid overstating differences.

If no approach beats the baselines consistently, prefer the simpler and more stable forecast.

Do not tune model weights, the pace tolerance or the forecast horizon using information from future test outcomes.

## 7. Benchmark Version and Measurement Uncertainty

Treat benchmark version and measurement uncertainty as first-class data fields.

Use confidence intervals or bootstrap samples when available. If the reported uncertainty is represented by samples, propagate those samples into the frontier and forecasts rather than merely adding arbitrary margins at the end.

For a bridged historical series, propagate uncertainty from the mapping between benchmark versions.

Avoid false precision when recent estimates are near the current benchmark's effective upper limit.

Do not extrapolate a high measured horizon as if the benchmark's precision were constant indefinitely. Use a transparent uncertainty adjustment when the task suite becomes saturated or weakly constrains a model's horizon.

Explain that the metric measures software-task completion capability under the benchmark's conditions, not AI intelligence or capability in every domain.

## 8. UI Requirements

Keep the existing visual design and page structure where possible. Focus UI changes on making the improved predictions understandable.

The existing page should continue to display:
- Current measured frontier.
- Forecasted frontier at 3, 6 and 12 months.
- Historical and forecast lines on the time-horizon chart.
- An 80% predictive range, where supported.
- Faster/same/slower probability bars for each forecast horizon.

Ensure historical observations, bridged estimates and future forecasts are visually distinguishable.

Add a compact methodology or diagnostics section showing:
- Data source and latest available data date.
- Benchmark version used.
- Whether a historical benchmark bridge was applied.
- Forecast method or ensemble used.
- Backtesting performance and sample size.
- Whether the pace probability has demonstrated skill over the baselines.
- Relevant uncertainty or data limitations.

Avoid cluttering the main chart. Keep the primary results prominent and place technical diagnostics in a secondary panel or expandable section.

Do not use green or high acceleration probabilities purely to make the result look impressive. Display probabilities produced by the actual calculation.

## 9. Engineering Requirements

- Follow the existing project stack and conventions.
- Keep the forecasting logic separate from presentation components.
- Create reusable functions for data preparation, frontier construction, model fitting, simulation, backtesting and pace classification.
- Keep data and configuration local and reproducible.
- Add reasonable error handling for missing values, malformed input, insufficient history and network failures.
- Do not add unnecessary dependencies if the existing stack can implement the required methods.
- Do not break other forecasting pages, navigation or existing functionality.
- Do not add fake sample observations to the official dataset.
- Add tests for data version handling, leakage prevention, forecast generation, prediction intervals, pace-probability calculation and missing-data behaviour.

## 10. Acceptance Criteria

Consider the task complete only when:

1. The project runs locally without a required external database.
2. The dataset loader works with the available real data and clearly identifies any missing input.
3. The monthly frontier is constructed correctly.
4. Historical forecasts use only information available at each forecast origin, to the extent allowed by the source data.
5. The model produces numeric forecasts and predictive intervals for 3, 6 and 12 months.
6. The jump-aware model and ensemble generate reproducible simulations.
7. The faster/same/slower probabilities are computed from those simulations and sum to 100%.
8. The probabilities and forecasts are compared with simple baselines using historical backtesting.
9. The UI clearly distinguishes observations, bridged estimates, predictions and uncertainty.
10. The application continues working if some optional model or data source is unavailable.

Do not stop at writing an architectural plan or placeholder functions. Implement and test the working forecasting pipeline.

If a sophisticated component cannot be justified by the available data, implement a simpler defensible alternative and explain why.

## Final Deliverable

After implementation, provide a concise summary of:
- What changed.
- Which dataset sources were actually used.
- How the historical benchmark bridge works, if implemented.
- Which forecasting methods are in the final ensemble and why.
- How the pace probabilities are calculated.
- Backtesting results compared with the baselines.
- Known limitations and any acceptance criteria that remain incomplete.

Prioritise an honest, working end-to-end forecast over unnecessary features or an impressive-looking result that cannot be supported by the data.