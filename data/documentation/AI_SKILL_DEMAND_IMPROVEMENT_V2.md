# Claude Code Task: Build a Hybrid Skill-Emergence Forecasting System

## Objective

Improve the existing IT/software skills demand forecasting system by addressing a fundamental limitation in the current data: major increases in hiring demand can occur even when the skill's own historical job-advertisement series contains little or no warning.

Do not try to solve this by increasing trend weights, forcing extrapolation, or making the existing model more reactive.

The latest validation investigation found:

- Approximately 60% of significant rises were noisy rebounds in small country × occupation cells with fewer than 60 advertisements per quarter.
- The more meaningful rises occurred in large cells, particularly US Software Engineer, but several skills had little historical indication of their subsequent growth.
- Quarter-on-quarter momentum was not predictive of the next six months in the tested data.
- A Kalman filter performed worse on rising skills.
- Reducing cross-country pooling did not materially improve rising-skill forecasts.
- Increasing the trend weight worsened overall and rising-skill errors.
- The current served implementation has been restored to the previously evaluated version, and its model-version hash matches the original served run.

The working hypothesis is that historical job-ad data alone is insufficient to anticipate certain emerging skills.

**Build a hybrid system that uses independent technology-adoption signals and related-skill evidence to improve early identification of emerging demand. Preserve the original job-demand forecast as a separate baseline, and do not claim improvements without out-of-sample evidence.**

This is a hackathon-focused implementation. Prioritize an end-to-end demonstrable feature over an elaborate production platform.

## 1. Inspect the existing implementation first

Inspect the repository and trace the entire skills forecasting pipeline.

Examine the existing equivalents of:

- `models.py`
- `backtest.py`
- Skill demand aggregation and preprocessing
- Skill normalization and taxonomy logic
- Forecast serving or API endpoints
- Existing forecast visualization and confidence outputs
- Configuration, caching and data-source integrations
- Relevant tests

Confirm the actual paths before editing; do not assume that the names above are exact or that all logic lives in those files.

Reproduce the original backtest results if the available data permits it.

Preserve the existing served model as the baseline. Do not make unrelated changes to the application or discard working forecasting functionality.

The project is currently scoped to IT/software occupations. Keep this scope and prioritize the largest reliable cells, especially those with enough historical job advertisements to support meaningful evaluation. Flag weaker cells as low evidence instead of aggressively fitting their noise.

## 2. Separate the system into three concepts

Implement or extend the following logical components.

### A. Job-demand baseline

The baseline predicts the existing skill-demand target using job advertisements alone.

Preserve its definition, forecast horizon and existing behavior unless a verified bug requires a correction.

It should expose:

- Recent observed skill share
- Six-month forecast share
- Forecast change relative to a clearly defined recent baseline
- Rising, falling or approximately stable direction
- Prediction uncertainty, where supported

Do not secretly replace the baseline with a hand-adjusted number to make a forecast appear more promising.

### B. Skill-emergence signal engine

Build an additional engine to estimate whether evidence outside a skill's own historical job-ad series indicates possible acceleration.

Investigate three classes of evidence:

1. **Technology ecosystem adoption:** Historical package-download growth for a known software package or framework associated with the skill.
2. **Related-skill demand:** Historical changes in job-ad demand for skills that are meaningfully related to the target skill or belong to the same technology family.
3. **Additional validated leading indicators:** Other publicly obtainable, temporally aligned indicators that provide useful information without requiring excessive implementation effort.

Use this as a new information source, not as an excuse to increase the existing trend weight.

For the hackathon, prioritize reliable integration of one or two useful external sources over integrating many weakly justified sources.

### C. Signal-adjusted outlook

Combine the baseline and the signal engine only if the relationship between the signals and future job demand can be learned or justified through historical evaluation.

The application should distinguish between:

- Baseline forecast: what the job-ad model predicts.
- Emerging-skill signal: the additional evidence suggesting acceleration or elevated attention.
- Signal-adjusted forecast: a numerically revised forecast only when the model has sufficient validation.
- Scenario outlook: a conditional illustration of how demand might evolve if an emerging trend continues, clearly labelled as a scenario rather than an established prediction.

Do not automatically increase the numerical job-demand forecast whenever an external signal rises.

If there is not enough historical evidence to calibrate the effect of an external signal, show the signal and a transparent scenario instead of inventing a statistically unsupported adjusted forecast.

## 3. Integrate external data pragmatically

### A. Python ecosystem

Investigate PyPI package-download statistics for the Python skills and frameworks represented in the existing taxonomy.

Potential examples of skill-to-package mappings include FastAPI and its relevant ecosystem packages. Other mappings should be derived from the project's actual skill inventory.

A useful starting point is:

- PyPI Stats API: https://pypistats.org/api/
- PyPI Stats data-source information: https://pypistats.org/about

Important constraints:

- The PyPI Stats API retains only 180 days of time-series data.
- If the historical validation period requires longer coverage, investigate the underlying public download dataset in Google BigQuery.
- Do not pretend that a short live-data window provides sufficient history for a year-long backtest.
- Cache retrieved observations and store their observation dates and source metadata.
- Handle missing packages, API failures and rate limits gracefully.
- Be aware that package downloads include automated usage, and download growth is not equivalent to hiring growth.

### B. JavaScript and TypeScript ecosystem

If relevant to the existing skills inventory, investigate the npm registry download API:

https://github.com/npm/registry/blob/main/docs/download-counts.md

Use date-scoped observations to derive package-adoption features. Check API limits and available history before relying on the source for historical backtesting.

Do not make npm integration a blocking requirement for the initial implementation if Python ecosystem evidence is sufficient for the project's existing target population.

### C. Skill-to-indicator mapping

Create a small, inspectable and configurable mapping from normalized skills to external indicators and related skills.

Examples of possible relationships include:

- FastAPI → Python backend development, API frameworks and its relevant Python package ecosystem.
- AI agents → agent frameworks, LLM applications, retrieval systems and orchestration-related skills.

Treat these as starting examples, not proof that any particular relationship is predictive.

Requirements:

- Use mappings justified by the existing skill taxonomy and technical relationships.
- Support aliases, alternative names and package identifiers.
- Keep the mapping in a configuration file or similarly easy-to-edit structure.
- Record which indicators support each emerging-skill signal.
- Avoid circular mappings where a skill's own target value is inadvertently used as a separate leading indicator.
- Never add a mapping simply because the future validation result revealed that two skills rose together.
- Do not hard-code AI agents, FastAPI or any specific skill to rise.

If an indicator has no historical data aligned with the model's backtest origins, it must not be used to claim historical predictive improvement.

## 4. Build useful features from the external signals

Start with a compact, interpretable feature set.

Possible features include:

- Recent package-download growth over a few available windows.
- Changes in related-skill demand over recent months or quarters.
- Acceleration relative to each indicator's own historical baseline.
- Indicator level and activity volume.
- Consistency of the change across multiple recent observations.
- Evidence quality and data coverage.
- Historical strength of the relationship between the indicator and subsequent job-ad demand.

Account for different scales and normal growth patterns across indicators. Prefer robust transformations, minimum evidence requirements and sensible outlier handling over raw percentage-growth comparisons.

A package growing from a handful of downloads to a slightly larger handful must not be treated as equivalent to substantial growth in a mature package.

Where possible, use log-growth, standardized changes or other appropriate features, while handling zeros and extremely small denominators safely.

Do not treat missing data as zero.

## 5. Use related-skill information without overfitting

The current investigation tested cross-country pooling and found little improvement for the major rising skills. Do not repeat that experiment as the main proposed solution.

Instead, investigate information transfer across related software skills.

For example, if a framework begins gaining demand and its related technologies accelerate, determine whether those changes historically contain useful information about future demand for the target skill.

Use the existing skill taxonomy or an explicit configurable relationship map.

A candidate model could pool historical evidence across IT/software skills, using regularized features to learn which shared signals help predict a future change in skill demand.

Potential implementations include:

- A regularized regression using lagged job-demand and external-indicator features.
- A pooled model across eligible IT/software skill series.
- An interpretable ensemble with the existing baseline.
- A model that predicts the probability of a materially positive or negative demand change separately from the numerical demand forecast.

Start simple and compare candidates. Do not introduce a large neural model or an unnecessarily complex feature pipeline.

The aim is to learn whether independent signals offer predictive value that is absent from the target skill's own time series.

## 6. Preserve a meaningful distinction between forecast and scenario

The dashboard should not become a mechanism for concealing poor forecast accuracy.

Implement a clear user-facing distinction.

### Baseline forecast

Show the original job-ad-based six-month forecast, its recent baseline and its predicted change.

### Emerging-skill evidence

Show the external and related-skill indicators that support a possible acceleration, including:

- Indicator name
- Latest available observation
- Historical comparison window
- Recent change
- Data-source reference
- Data freshness or observation date
- Evidence-quality indication

Where relevant, explain that adoption evidence is not the same as hiring demand.

### Signal-adjusted outlook

Show a revised numerical prediction only if the model has been calibrated and evaluated using historical data that could actually have been available at the corresponding forecast origins.

Otherwise, show a clearly labelled conditional scenario. For example, the user should be able to understand that stronger ecosystem adoption may support an emerging-skill outlook, without being told that the job-ad model has established that the target share will rise by a particular amount.

Do not fabricate confidence percentages or numerical uplift coefficients.

For the hackathon demo, make the scenario visually useful and interactive where that fits the current application, but do not make synthetic scenario inputs look like observed real-world data.

## 7. Validate whether external signals actually improve the forecast

This is a mandatory requirement.

### A. Maintain a fair baseline

Evaluate the existing job-demand model and new candidate models on identical, eligible historical forecast origins and target definitions.

Record the baseline's measured performance before changing it.

### B. Use chronological rolling-origin backtesting

At every historical forecast origin:

1. Use only job advertisements available at that date.
2. Use only external indicators whose observations were available by that date.
3. Construct related-skill features using only historically available information.
4. Fit all model parameters and calibrations using only allowable past data.
5. Predict the same six-month target as the baseline.
6. Compare the result with the subsequently observed target.
7. Repeat across multiple origins.

Reserve an untouched final time period when sufficient observations exist.

Prevent future-data leakage through preprocessing, skill mapping, model selection, parameter tuning and external-data retrieval.

Do not use current external adoption figures to reconstruct what the model supposedly knew in a previous year.

If temporal alignment cannot be established, use the affected signal for current context or a scenario only, not for a claimed historical forecasting improvement.

### C. Compare meaningful measures

At minimum, compare:

- Overall MAE in percentage points.
- Signed forecast bias.
- MAE on materially rising skills.
- MAE on materially declining skills.
- Direction accuracy for materially moving skills.
- Performance on approximately stable skills.
- Rising and falling performance in large, well-supported cells separately from small, noisy cells.
- Results by historical forecast origin.
- Sample sizes and the coverage of external indicators.

Include 1- and 2-percentage-point movement thresholds where appropriate for the existing target.

Measure both the baseline and signal-adjusted model against the same actual outcomes. Do not judge success from a visually appealing chart, one successful skill or a single forecast origin.

Evaluate whether the emerging-skill signal can identify subsequent rises with sufficient precision to be useful. Also measure its false-positive rate: an early-warning engine that flags everything is not useful.

If numerical forecast improvement cannot be established, keep the signal engine as an evidence-based emerging-skill radar and scenario tool. State this honestly in the final report.

## 8. Make the hackathon experience compelling without faking accuracy

Prioritize an end-to-end feature that makes the limitation of the original forecast understandable.

The experience should help users answer:

- Which IT/software skills are forecast to increase in demand?
- Which skills have emerging ecosystem signals even though historical job-demand evidence is still limited?
- What evidence supports each alert?
- Is that evidence strong, weak or contradictory?
- Is the numerical forecast statistically supported, or is the displayed outlook only a scenario?
- What could happen if the emerging trend continues?

Keep the implementation compatible with the existing application's conventions and avoid redesigning unrelated pages.

The feature should still work when an external source is unavailable. Clearly distinguish cached real observations, live observations, missing information and any explicitly labelled demo fixtures.

Do not use invented external statistics in the main forecasting path.

## 9. Implementation order

Complete the work in this order.

**Phase 1 — Baseline:** Inspect and reproduce the current served model and its evaluation.

**Phase 2 — Data and mapping:** Implement the smallest useful external signal integration and configurable skill-to-indicator mapping.

**Phase 3 — Features and model:** Add aligned time-series features and a regularized candidate that combines job-demand history with external and related-skill signals.

**Phase 4 — Evaluation:** Run leakage-safe rolling-origin backtests and compare the new candidate against the unchanged baseline.

**Phase 5 — Product integration:** Integrate the emerging-skill evidence and calibrated forecast or scenario into the actual application.

**Phase 6 — Verification:** Test missing data, stale observations, low-volume skills, API failures, temporal leakage, forecast compatibility and numerical outputs.

Do not stop after generating a design document or pseudocode. Implement the working changes in the repository.

Prioritize an operational, demonstrable version over optional integrations and abstractions. If a historical signal source or required dataset cannot be obtained, continue with the feasible portions and explain the exact limitation.

## 10. Final report

Provide a concise report containing:

1. The confirmed limitation of the existing forecast.
2. The external indicators integrated and their historical coverage.
3. The source and observation period of each signal.
4. The skill mappings added and how they were justified.
5. Files changed and how the feature is connected to the application.
6. The baseline-versus-hybrid backtest comparison, including sample sizes.
7. Whether the additional signals improve rising-skill detection and whether false positives increase.
8. Whether the numerical forecast is empirically improved or the feature remains a scenario-based early-warning system.
9. Tests executed and their outcomes.
10. Remaining limitations and a brief demonstration walkthrough.

Do not claim an improvement that is not supported by the measured backtest.

**Definition of success:** A working IT/software skill-emergence feature that combines job-demand history with genuinely additional evidence, provides useful explanations and conditional outlooks, and clearly distinguishes validated numerical forecasts from unvalidated scenarios.