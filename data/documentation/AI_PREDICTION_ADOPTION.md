# Claude Code Master Prompt: AI Progress, Occupational Adoption & Future Skills Forecasting Platform

## 1. Your role and mission

You are a senior machine-learning engineer, quantitative forecaster, data engineer, and applied labour-market researcher.

Build a reliable, evidence-based forecasting platform that estimates:

1. The probability that AI capability development will accelerate, remain broadly stable, or slow down.
2. How AI adoption may evolve across occupations, industries, and countries under different AI-progress scenarios.
3. Which occupational skills are likely to experience increasing, stable, decreasing, or emerging employer demand.
4. How these forecasts change when new structured data, job advertisements, model benchmarks, and external news become available.

The platform must be capable of updating its evidence and forecasts continuously as new information arrives.

The main objective is not to produce impressive-looking predictions. It is to produce **measurable, reproducible, appropriately calibrated forecasts that can be tested against future observations**.

### Non-negotiable principles

- Prevent any single dataset, especially the U.S. Census Bureau's Business Trends and Outlook Survey (BTOS), from unintentionally dominating unrelated predictions.
- Never confuse AI capability progress, occupational task exposure, actual AI adoption, hiring demand, and employment impact.
- Never claim an occupation-specific adoption rate is directly observed when it is only estimated indirectly.
- Never claim a model is accurate without an out-of-time evaluation.
- Never train and test using randomly mixed observations from the same time series.
- Never allow future information to leak into historical forecasting experiments.
- Never invent data, fabricate historical observations, or silently substitute synthetic data for real-world evidence.
- Never assume LightGBM, deep learning, Bayesian regression, or any other algorithm is inherently the best choice.
- Compare candidate models with simple baselines and select models using a predeclared, time-aware validation procedure.
- Keep source provenance, model versions, training cutoffs, prediction timestamps, assumptions, and uncertainty.
- Update the underlying dataset and generated forecasts as new data become available.
- Be transparent when evidence is insufficient to support a defensible prediction.

The system should prioritise scientific validity, maintainability, and an operationally functional end-to-end implementation over unnecessary architectural complexity.

---

## 2. Start by inspecting the existing repository

Before modifying anything:

1. Inspect the repository structure, source files, dependencies, configuration, database schema, existing models, ingestion jobs, APIs, and user interface.
2. Identify which parts already work and which components are missing.
3. Determine the existing technology stack, runtime environment, and available API credentials.
4. Review the current implementation for:
   - BTOS overdependence.
   - Incorrect merging of datasets with different measurement units.
   - Incorrect training and testing splits.
   - Temporal leakage.
   - Inadequate historical data retention.
   - Unsupported assumptions about occupation-level adoption.
   - Missing evaluation metrics.
   - Hard-coded forecasts.
   - Predictions that do not update after ingestion.
5. Preserve functional components and existing conventions where practical.
6. Produce a concise implementation plan, then proceed to implement it.

Do not stop after producing a research report, architecture diagram, recommendations, or placeholder functions. Build a functioning vertical slice from source ingestion through prediction, evaluation, and forecast presentation.

If the repository already has a frontend, integrate with it. If it has no presentation layer, implement a lightweight interface suitable for displaying forecasts and model-evaluation results without building an unnecessarily elaborate product.

Make reasonable assumptions and document them rather than blocking implementation on non-essential questions.

---

# PART A — DEFINE WHAT THE PLATFORM PREDICTS

## 3. Establish three independent forecasting domains

Implement three separate forecasting modules connected by a scenario engine.

### Model A: AI capability progress

Predict the future rate of progress in AI capabilities and estimate the probabilities of three regimes:

- Acceleration.
- Broadly stable progress.
- Slowdown.

The prediction target is the rate of capability improvement, not simply whether the newest model is better than the previous one.

### Model B: Occupational AI adoption

Estimate how AI adoption could evolve by country, industry, occupation, and forecast horizon.

Distinguish:

- Directly observed adoption rates.
- Forecasts of adoption at levels supported by historical survey data.
- Model-based occupational adoption estimates.
- Occupational AI exposure or adoption-propensity indices that are supported only by indirect evidence.

These must not be presented as interchangeable quantities.

### Model C: Future skill demand

Predict changes in employer demand for individual skills and skill combinations, particularly skills associated with AI, software development, automation, data engineering, AI infrastructure, AI governance, and other developing technological capabilities.

Distinguish:

- Absolute vacancy demand.
- The share of advertisements mentioning a skill.
- Relative growth in skill demand.
- Newly emerging skill terms.
- Broadening demand across occupations and industries.
- Disappearing or declining demand signals.

Each model needs its own target definition, candidate algorithms, evaluation procedure, baselines, and performance report.

Do not train one large universal model to predict all three targets.

---

## 4. Establish the unit of analysis and forecast horizons

Every forecast must specify its geography, target population, measurement unit, prediction horizon, and reference date.

Support a configurable combination of:

- Country.
- Industry or economic sector.
- Occupation.
- Skill.
- Company-size group, where relevant.
- Time period.
- Forecast horizon.
- AI-progress scenario.

Use configurable country and occupation taxonomies. Do not hard-code the United States as the target market merely because BTOS is available.

Where Malaysia is a target market, allow local occupational and industry classifications, such as MASCO, to be mapped to suitable international classifications. Keep the original classifications and the mapping version.

Recommended initial horizons:

| Forecast domain | Horizons |
|---|---|
| AI capability progress | 3 and 6 months |
| AI adoption | 6, 12 and 24 months |
| Skill demand | 3, 6 and 12 months |

Make horizons configurable. If historical data do not justify a particular horizon, show that limitation instead of extrapolating indefinitely.

All forecasts must carry an explicit `as_of_date`. A forecast made on one date must be distinguishable from a forecast regenerated after new data arrive.

---

# PART B — DATA COLLECTION AND SOURCE INDEPENDENCE

## 5. Implement a source registry

Create a central source registry that describes every supported data source.

For each source, maintain:

- Unique source identifier.
- Source name and documentation URL.
- Geographic and temporal coverage.
- Measurement unit.
- Supported forecast domain.
- Permitted use of the data.
- Data retrieval method.
- Authentication requirements.
- Update cadence.
- Last attempted retrieval.
- Last successful retrieval.
- Last observed source-data period.
- Data freshness status.
- Schema version.
- Known limitations and potential measurement breaks.

Make source adapters modular so another dataset can be added without rewriting the modelling pipeline.

Existing source adapters must include:

1. Census BTOS.
2. Adzuna API.
3. GDELT DOC 2.0 API.

Additional sources should be optional adapters, not mandatory dependencies that prevent the system from working when credentials or access are unavailable.

### 5.1 Census BTOS

Use official BTOS downloads and documentation.

BTOS can contribute business-level AI-use measurements at the geographic, industry, subsector, and firm-size levels supported by the available tables.

It must not be treated as a direct source of observed adoption rates for every occupation.

Implement the following safeguards:

- Record the exact survey question, questionnaire version, reference period, release period, and survey geography whenever available.
- Record whether the observation measures current AI use or expected future AI use.
- Keep current use and expected future use as distinct variables.
- Preserve survey estimates, denominators, uncertainty information, and suppression flags where published.
- Do not invent respondent counts from reported percentages.
- Account for survey sampling, weighting, uncertainty, and possible serial dependence.
- Check the documented AI-question wording revision introduced in November 2025.
- Represent the wording revision as a possible structural break.
- Test pre-revision and post-revision data separately.
- Where comparable historical observations cannot be established, exclude or separately model the incompatible portion rather than silently joining it into a continuous series.
- Do not carry U.S. survey estimates over to other countries without independent evidence and an explicitly documented transfer assumption.

BTOS must serve only the roles that its measurement design supports: principally a source of business-level adoption observations and a benchmark for compatible adoption forecasts.

**Do not use BTOS adoption percentages as a general-purpose feature or label for occupation-level adoption merely because occupation-level labels are missing.**

### 5.2 Adzuna API

Use the credentials already configured in the project, or define configuration variables for them.

Consult the current documentation:

- https://developer.adzuna.com/activedocs
- https://developer.adzuna.com/docs/historical
- https://api.intelligence.adzuna.com/api/doc/

Use the endpoints actually available to the configured account.

Potentially relevant information includes:

- Job advertisement records.
- Posting counts.
- Vacancy-demand trends.
- Hiring skills.
- Standardised job categories and occupations.
- Geographic and industry information.
- Salary trends, where useful.
- Historical data supplied by the applicable API plan.

Do not assume that the standard API provides a complete historical archive of every individual job advertisement. Distinguish between historical aggregate statistics and historical posting-level observations.

Before building a connector, verify the response schema, geographic coverage, API permissions, rate limits, and whether the subscription enables the required endpoint.

Requirements:

- Store raw responses before transformation.
- Capture retrieval timestamps and source dates.
- Retain stable external identifiers whenever available.
- Deduplicate postings.
- Detect reposted or repeatedly refreshed advertisements where feasible.
- Preserve posting volume and skill-demand share separately.
- Handle deleted vacancies, expired listings, and changing advertisement descriptions carefully.
- Avoid interpreting an increase in collected advertisements as real labour-market growth if the change is caused by API coverage, query settings, or geographic coverage.
- Build a historical snapshot archive where the API cannot provide the required historical detail.

A listing first collected on a given date must not be treated as though it was known to the model at an earlier date.

### 5.3 GDELT DOC 2.0

Use GDELT to collect external news signals related to AI capabilities, AI adoption, employment, skills, infrastructure, regulation, and potential deployment bottlenecks.

Documentation:

https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Create configurable, version-controlled query definitions rather than a single broad query containing only the word "AI".

Initial news categories should include:

1. AI model releases and technical breakthroughs.
2. Benchmark performance and reasoning capabilities.
3. AI agent reliability and task-completion capabilities.
4. Inference costs, hardware, computing capacity, and energy constraints.
5. Enterprise AI deployment and business integration.
6. AI investment and infrastructure expansion.
7. Regulatory changes, compliance requirements, and legal barriers.
8. AI security incidents, reliability failures, and restrictions on use.
9. Employer announcements related to skills and workforce changes.
10. Emerging technologies or capabilities that could materially change job requirements.

For each article or aggregated news observation, retain available fields such as publication time, retrieval time, URL, source domain, language, source country, query category, and classification result.

News features should include, as appropriate:

- Raw article counts.
- Deduplicated article counts.
- Relevant articles as a share of total monitored coverage.
- Distinct source count.
- Source concentration.
- Topic-specific volume trends.
- Tone or sentiment only where the interpretation is defensible.
- Lagged changes and unexpected spikes.

Do not interpret sentiment as technical progress.

Do not treat the standard GDELT volume timeline as a raw article count. Its standard volume output is normalised against total monitored global coverage. Preserve the measurement definition when storing and using that series.

Use separate raw-count and normalised-coverage features when the API supports them and when they answer different analytical questions.

Avoid duplicate articles, syndicated reporting, press-release echoes, and repeated coverage of the same event inflating a signal.

News is an explanatory or early-warning input. It is not automatically a ground-truth label for either AI progress or AI adoption.

### 5.4 Additional source adapters

Design the registry to support these optional additions:

- Epoch AI model and benchmark datasets.
- METR AI task-time-horizon measurements.
- Artificial Analysis model evaluations and cost metrics, subject to access and usage permissions.
- O*NET occupations, tasks, skills, and work activities.
- ILO occupational AI-exposure research.
- Eurostat enterprise AI-adoption statistics.
- OECD labour-market and AI-related employment datasets.
- Malaysia's ILMIA, DOSM, MASCO, and TalentCorp MyCOL datasets where access permits.
- Other official AI-adoption surveys or worker surveys that measure occupational AI use directly.

Priority should be given to usable sources with clear definitions, stable identifiers, defensible historical coverage, and suitable licensing.

A source must not be included merely because it is available.

### 5.5 Source weights must reflect evidence quality, not convenience

Do not assign BTOS, Adzuna, and GDELT arbitrary source weights such as 50%, 30%, and 20%.

Their measurements are fundamentally different. A survey estimate, a job-ad share, and news coverage do not automatically measure the same latent quantity.

Use a source only in a model whose target and measurement relationship it can reasonably inform.

Where multiple sources measure the same quantity, represent differences in sampling uncertainty, coverage, reliability, and measurement definitions explicitly where feasible.

For source-weighted estimates, document the statistical rationale for the weights.

Build a source-contribution report showing:

- Which sources provide direct labels.
- Which sources provide predictive features.
- Which sources provide contextual evidence only.
- How much test performance changes when each source is excluded.
- Whether conclusions are sensitive to the removal of any one source.

---

# PART C — DATA ENGINEERING AND HISTORICAL INTEGRITY

## 6. Use a layered data pipeline

Implement a reproducible data pipeline with the following logical layers.

### Layer 1: Raw data

Store source responses in their original form with metadata.

Retain historical versions instead of overwriting earlier responses.

### Layer 2: Normalised data

Standardise:

- Dates and time zones.
- Country identifiers.
- Industry identifiers.
- Occupation identifiers.
- Skill identifiers.
- Measurement units.
- Survey question versions.
- Source release identifiers.

Keep original identifiers for traceability.

Use explicit occupation and industry crosswalks rather than matching codes on similar-looking strings alone.

### Layer 3: Feature data

Generate clearly defined weekly or monthly features.

Monthly observations should be the primary analysis grain unless an individual target justifies another frequency.

Store the numerator and denominator for every derived proportion wherever possible.

Example fields:

`period`, `country`, `industry_code`, `occupation_code`, `skill_id`, `metric_name`, `numerator`, `denominator`, `value`, `uncertainty`, `source_id`, `source_published_at`, `fetched_at`, `valid_from`, `schema_version`.

These are illustrative fields, not a requirement to force incompatible data into one universal table. A suitable relational schema or set of fact tables is acceptable.

### Layer 4: Modelling datasets

Build separate modelling tables for:

- AI capability progress.
- AI adoption.
- Skill demand.

Every training dataset must identify:

- Its prediction target.
- Feature availability cutoff.
- Forecast horizon.
- Source lineage.
- Training eligibility.
- Missing-data treatment.
- Observation quality.

### Layer 5: Predictions and evaluations

Store every model run, evaluation, and forecast with its associated versions and timestamps.

At minimum, save:

- Model identifier and algorithm.
- Model version.
- Training cutoff.
- Data snapshot or data-vintage identifier.
- Target and horizon.
- Forecast value or probabilities.
- Prediction interval or credible interval when available.
- Evaluation fold and metrics.
- Selected features and relevant configuration.
- Failure or quality warnings.

Use reproducible data snapshots so a past forecast and the information available when it was made can be reconstructed.

## 7. Historical data and data-vintage preservation

This is essential.

External sources update, revise, delete, and backfill data. Using a source's current historical view to reconstruct past model inputs can create look-ahead bias when those observations or revisions were not available at the historical forecast date.

Implement point-in-time-aware data storage.

For historical backtesting:

- Use only records that would have been available by each forecast origin.
- Respect source publication and availability timestamps.
- Preserve revisions and distinguish the original release from a revised observation.
- Do not use an article published after the prediction cutoff.
- Do not use a job advertisement that only appeared later.
- Do not use benchmark results released after the forecast origin.
- Do not use future survey releases as historical features.
- Document any unavoidable limitations in reconstructing past data vintages.

If a source cannot provide historical vintages, mark that limitation and restrict the strength of the historical backtest claims.

## 8. Data quality and missing data

Implement validation for:

- Duplicate observations.
- Missing required fields.
- Unexpected time gaps.
- Invalid percentages or counts.
- Negative counts.
- Impossible numerator-denominator relationships.
- Unexplained changes in source coverage.
- Sudden changes in query configuration.
- Taxonomy-mapping failures.
- Unexpected measurement breaks.
- Excessive missingness.
- Stale data.
- API schema changes.

Never silently replace missing data with zero.

Distinguish:

- True zero.
- Missing observation.
- Suppressed observation.
- API failure.
- Data not collected.
- Not applicable.

Use imputation only when the assumption is appropriate for the target and the imputation is fitted using training data alone where required.

Display data-quality warnings alongside affected forecasts.

---

# PART D — MODEL A: AI CAPABILITY PROGRESS

## 9. Define an operational measure of AI progress

Do not equate general AI progress with one benchmark, article count, company valuation, or model release.

Build a capability-monitoring dataset from comparable historical measurements, including where possible:

- Performance on stable benchmark families.
- Task-completion reliability.
- Agentic task performance.
- Task difficulty or time-horizon measurements.
- Inference cost for comparable levels of performance.
- Other well-defined capability measurements.

Keep capability dimensions separate initially.

A model's benchmark score, task-time horizon, latency, and inference cost cannot be averaged blindly because they have different units and meanings.

Use documented transformations to create comparable measures where a composite capability index is justified.

Requirements:

- Track benchmark versions and changes in evaluation methodology.
- Detect changes in evaluation coverage.
- Prevent changes in dataset composition from appearing as real capability gains.
- Track cost-adjusted capability as a distinct measure.
- Keep a record of the models and observations contributing to each metric.
- Avoid retrospective normalisation using future observations during backtesting.

If a credible composite index cannot be constructed, forecast the component metrics separately and report separate regime probabilities.

## 10. Recommended primary algorithm: Bayesian local-linear-trend state-space model

Start with a Bayesian state-space or local-linear-trend model.

The reason for this choice is that AI progress observations may be sparse, irregular, noisy, and subject to changing rates of improvement. A state-space model can represent an uncertain underlying trend without requiring a large labelled training set.

A simple conceptual structure is:

- Observed capability measurement = latent capability level + measurement noise.
- Latent capability level changes according to an evolving slope.
- The slope can change gradually over time.
- The slope's change is uncertain and should not be interpreted as a real regime shift unless the evidence supports it.

Use a separate model per sufficiently distinct capability dimension, or a carefully justified multivariate model if it is supported by the available data.

Evaluate an appropriate implementation using PyMC or another well-supported probabilistic modelling framework. An equivalent statistical implementation is acceptable if its assumptions and uncertainty estimates are validated.

### 10.1 Define acceleration, stability, and slowdown correctly

Define the estimated rate of improvement as the latent trend slope.

Then define a practical tolerance for changes in the rate of improvement. The tolerance must account for measurement noise and should be configurable and documented.

Conceptually:

- **Acceleration:** the rate of improvement has increased beyond the tolerance.
- **Broadly stable progress:** the rate of improvement has not changed materially beyond the tolerance.
- **Slowdown:** the rate of improvement has decreased beyond the tolerance.

A slowdown does not mean capability is necessarily deteriorating.

Estimate posterior probabilities for these regimes from the distribution of the change in trend slope, rather than imposing an arbitrary fixed class label on each month.

For each forecast origin and horizon, produce:

- Probability of acceleration.
- Probability of broadly stable progress.
- Probability of slowdown.
- Predicted capability level.
- Predicted improvement rate.
- Credible intervals.
- Main metrics contributing to the forecast.
- Important assumptions and data-quality warnings.

The three probabilities must sum to 1 within numerical tolerance.

### 10.2 Candidate alternatives

Where sufficient observations exist, compare the primary model with:

- A simple linear-trend forecast.
- A local-level or exponential-smoothing model.
- A regularised trend model with predefined external signals.
- A change-point model only if sufficient historical observations exist to estimate changes defensibly.

Do not start with a complex regime-switching hidden Markov model merely because three regimes are desired. Its complexity may not be justified by the number of independent historical observations.

### 10.3 Incorporate GDELT as a possible leading signal

Use lagged, categorised news signals as candidate exogenous features.

Test them empirically.

For example, a rise in articles about inference-cost reduction might be associated with faster deployment, but it does not necessarily imply improved model reasoning. A reported breakthrough may not generalise to later independent evaluations.

Any news feature must:

- Be calculated using information available at the forecast origin.
- Be lagged by an explicitly documented interval.
- Be deduplicated and normalised where appropriate.
- Be evaluated through ablation tests.
- Be discarded when it does not improve reliable out-of-sample prediction or adds unstable noise.

A model that performs better without news must be allowed to exclude news.

---

# PART E — MODEL B: OCCUPATIONAL AI ADOPTION

## 11. Define adoption targets and evidence tiers

The adoption model must support distinct target types.

### Tier 1: Directly observed adoption

Use actual survey outcomes measuring AI use at the level represented by the survey.

Examples include business-level adoption by industry, firm-size group, or country, and worker-level adoption by occupation when an appropriate survey is available.

### Tier 2: Forecast adoption at an observed measurement level

Forecast survey-measured business or worker adoption using compatible historical observations.

For a survey that provides a rate with its standard error but not its respondent-level numerator and denominator, use an approach compatible with its published uncertainty. Do not invent binomial counts.

### Tier 3: Estimated occupational adoption

Where direct occupation-level adoption observations are unavailable, combine relevant features such as task exposure, business-sector adoption, occupational composition, hiring evidence, and the suitability of workflows for AI implementation.

However, do not label this estimate as a directly observed adoption rate.

The system must distinguish between a calibrated forecast of an actual adoption target and a model-based proxy for adoption propensity.

If available data cannot support reliable numeric occupational adoption rates, return an appropriately labelled index, qualitative scenario, or explicit insufficient-evidence status instead of false precision.

## 12. Recommended primary algorithm: Bayesian hierarchical adoption model

Use partial pooling to estimate group-level adoption outcomes.

A suitable starting point is a hierarchical logistic or binomial model for observed adoption. Use beta-binomial or an appropriate model for aggregated proportions when justified by the data.

Where data support the structure, represent groups using a hierarchy such as:

- Country.
- Industry.
- Occupation.
- Firm size.
- Time period.

Include only the grouping dimensions and interactions supported by the data. Do not add every possible random effect automatically.

The purpose of partial pooling is to share information across related groups while allowing meaningful differences. Groups with less information should ordinarily have more uncertainty.

Use time-varying effects or a dynamic trend component only when historical observations justify the additional complexity.

### 12.1 Important restrictions

- Do not treat repeated biweekly observations as statistically independent without addressing temporal dependence.
- Account for survey weights and measurement uncertainty where relevant.
- Do not assume every country has the same adoption baseline.
- Do not assume every industry responds equally to an improvement in AI capabilities.
- Do not infer employee-level adoption directly from business-level use.
- Do not use task exposure as a substitute for measured adoption.
- Do not use the presence of AI-related skills in job advertisements as proof that workers are using AI.
- Do not infer that a job is being replaced simply because AI could perform some of its tasks.

### 12.2 Adoption features

Candidate features may include:

- Lagged adoption observations.
- Recent adoption trend.
- Industry.
- Occupation.
- Country.
- Firm size.
- Task-exposure measures.
- Industry composition.
- AI-related skill-demand trends.
- Relevant and lagged capability metrics.
- Relevant regulation and implementation constraints.
- News signals associated with enterprise deployment.
- Measures of data, computing, infrastructure, and integration barriers when suitable data exist.

Every feature needs a defensible interpretation.

A source should not become a feature simply because it is available.

### 12.3 The BTOS-bias safeguard

Implement mandatory source-ablation experiments for adoption predictions:

1. All eligible sources.
2. Without BTOS-derived predictive features.
3. BTOS-compatible business-level benchmark alone.
4. Without news features.
5. Without job-ad-derived features.
6. Without capability-progress features.

BTOS is a label source for the business-adoption targets it actually measures. Do not allow its role as a target to be confused with its role as a predictor.

When a compatible business-adoption forecast is evaluated against BTOS observations, report the performance for that target separately from occupation-level predictions.

For occupation-level estimates, use independent occupational adoption observations as validation labels when possible. If these labels do not exist, report proxy validation and external consistency checks clearly, and do not claim occupational adoption accuracy has been established.

The system must not choose source combinations merely because one source produces a smoother-looking forecast.

### 12.4 Required output

For every adoption forecast, expose:

- Country.
- Industry.
- Occupation when supported.
- Forecast horizon.
- Target definition.
- Observed adoption level when available.
- Predicted adoption rate or separately labelled propensity estimate.
- Predictive interval or credible interval.
- Evidence tier.
- Data coverage and sample-quality status.
- Contributing features.
- Scenario assumptions.
- Backtest performance for the relevant target.
- Explanation of important limitations.

A result that has never been validated against an appropriate observed adoption target must be marked as unvalidated.

---

# PART F — MODEL C: FUTURE SKILL DEMAND

## 13. Define skill-demand targets rigorously

Use job advertisements to create a consistent historical skill-demand panel.

For each period, country, industry, occupation, and skill, calculate:

1. Number of unique eligible postings.
2. Number of unique postings mentioning the skill.
3. Share of postings mentioning the skill.
4. Change in absolute demand.
5. Change in demand share.
6. Number of distinct employers mentioning the skill, when available.
7. Distribution of the skill across occupations and industries.
8. Seniority and experience-level distribution, when available.
9. Share mentioning the skill as a requirement versus a preference when the text supports a reliable distinction.

For skill \(s\), occupation \(o\), industry \(i\), country \(c\), and period \(t\):

\[
D_{s,o,i,c,t}
=
\frac{\text{Unique eligible postings mentioning }s}
{\text{All eligible unique postings}}
\]

Store the numerator and denominator separately.

The ratio alone is insufficient for understanding changing demand because the total number of postings can rise or fall.

### 13.1 Normalise labour-market signals

Avoid relying exclusively on raw posting counts.

Changes in the number of advertisements can be caused by seasonality, changes in platform coverage, query settings, or genuine changes in labour demand.

Report at least:

- Raw count.
- Demand share.
- Relative change.
- Baseline-adjusted change.
- Data-coverage indicators.

Where useful, estimate seasonal patterns and compare changes against the relevant occupation's or industry's total posting volume.

### 13.2 Canonical skill taxonomy

Build a configurable skill taxonomy and synonym mapping system.

For example, related terminology may include:

- Large language models.
- LLMs.
- Large language model application development.

These should be mapped consistently when they genuinely describe the same skill, while retaining the original advertisement wording and the taxonomy version used.

Support:

- Normalisation of spelling and variants.
- Multiword skill extraction.
- Acronym handling.
- Skill taxonomy mapping.
- Job-title and occupation mapping.
- Versioned synonym lists.
- Skill co-occurrence analysis.
- Confidence scores for automated extraction.

Do not collapse terms with materially different meanings merely because they are semantically related.

If a language model is used to extract skills from text, cache the result, record the extraction model and prompt version, and make the process reproducible. Where possible, use deterministic taxonomy matching and rules for well-defined terms, with semantic matching as a supplementary method.

New skill terms should be reviewable and should not be added permanently to the taxonomy without provenance.

## 14. Recommended primary algorithm: regularised dynamic regression

Start with a parsimonious time-series forecasting approach.

Candidate models should include:

1. Seasonal-naive baseline where seasonality is supported.
2. Last-observation or simple-trend baseline.
3. Exponential smoothing or an appropriate state-space model.
4. Regularised dynamic regression using Ridge or ElasticNet.
5. SARIMAX where the series and its exogenous features justify it.
6. A pooled hierarchical regression when multiple related occupational skill series exist.
7. LightGBM as a challenger when there is enough genuine training information to justify nonlinear tree learning.

The target determines the likelihood and model family.

For example:

- If the target is a proportion based on a known numerator and denominator, consider a binomial or beta-binomial model.
- If the target is an overdispersed count of postings, consider negative binomial regression with a suitable exposure term.
- If the target is a continuous transformed series, a dynamic regression model may be appropriate.

Do not force all skill-demand targets into ordinary least-squares regression.

### 14.1 Why LightGBM is not the default

The fact that a dataset contains thousands of advertisements does not mean it contains thousands of independent monthly forecasting observations.

Many advertisements belong to the same time period, occupation, market, or employer. Their errors may be correlated.

A LightGBM model can be a valid candidate for a rich panel of occupation-skill-period observations, but its performance must be established empirically.

Before allowing it to become a production model:

- Compare it with strong statistical baselines.
- Evaluate it through rolling temporal validation.
- Keep the tree depth and number of leaves conservative.
- Use suitable minimum leaf sizes.
- Regularise model complexity.
- Tune on validation folds only.
- Prevent high-cardinality identifiers from creating memorisation.
- Check performance on later time periods.
- Measure whether it improves forecast accuracy enough to justify its complexity.

Use the official LightGBM guidance on limiting leaves and minimum data per leaf as a starting point for controlling overfitting:

https://github.com/lightgbm-org/LightGBM/blob/main/docs/Parameters-Tuning.rst

If LightGBM does not reliably outperform a simpler model, deploy the simpler model.

### 14.2 Do not start with deep learning

Do not introduce LSTMs, Transformers, neural forecasting architectures, or generative forecasting models merely because the project is about AI.

The relevant question is whether the available target history supports the model.

For a limited collection of monthly observations, a neural network can have a high effective complexity relative to the available temporal evidence.

Only introduce a deep-learning challenger when:

- There is enough genuinely informative training data.
- The target and loss function are appropriate.
- Validation demonstrates a repeatable benefit.
- The additional computational and operational cost is justified.

Synthetic augmentation must never be used to make the evaluation appear larger than the real dataset supports.

### 14.3 Emerging-skill detection

Implement a distinct emerging-skill detector in addition to the demand forecasting model.

An emerging skill may have evidence such as:

- Increasing demand share.
- Increasing absolute posting volume.
- Appearance across more employers.
- Appearance across more industries or occupations.
- Increasing requirement rather than preference status.
- Sustained demand across multiple periods.
- Relevant new technical developments.

Use minimum evidence thresholds and uncertainty measures to prevent small denominators from creating false growth signals.

Distinguish:

- A genuinely new term.
- A previously rare term gaining traction.
- An established skill gaining demand.
- A temporary news-driven spike.
- A skill whose demand appears to be declining.

Do not label a skill as emerging based solely on a single job advertisement, one news article, or a language model's qualitative judgement.

### 14.4 Required skill-demand outputs

For every forecast horizon, expose:

- Forecast demand share.
- Forecast posting volume when supported.
- Predicted change and uncertainty interval.
- Historical baseline.
- Recent observed trend.
- Occupations and industries driving the change.
- Number of distinct employers and relevant postings where available.
- Whether the skill is established, emerging, or declining, with evidence.
- Backtest performance.
- Data freshness and confidence warnings.
- Major relevant source articles, where available.

Do not treat skill demand as proof of future employment growth or declining employment.

---

# PART G — TRAINING, TESTING, AND MODEL SELECTION

## 15. Implement a rigorous temporal evaluation framework

This is mandatory.

The platform must not evaluate time-series forecasts using an ordinary random train/test split.

Random splits can allow observations from a future period to enter the training set while the model is evaluated on an earlier period. That does not simulate real forecasting.

Use chronological splits and rolling-origin backtesting.

Official scikit-learn guidance explains why time-series observations require specialised cross-validation rather than randomly shuffled folds:

https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split

### 15.1 Final holdout test set

Reserve the latest suitable historical period as a final holdout set.

A configurable starting strategy is to reserve roughly the latest 20% of available periods, subject to there being enough observations to evaluate the forecast horizons.

Do not hard-code this percentage as universally correct.

The actual holdout duration must account for:

- Total history length.
- Prediction horizon.
- Data frequency.
- Seasonality.
- Number of observations.
- Availability of meaningful benchmark periods.

The final holdout must remain untouched during model selection and hyperparameter tuning.

Do not repeatedly inspect its performance and modify the model until the result looks favourable.

### 15.2 Rolling-origin cross-validation

Implement expanding-window or rolling-window validation.

For each fold:

1. Train exclusively on observations available before the forecast origin.
2. Fit every learned preprocessing step using the training data only.
3. Produce forecasts for the future validation period at the required horizon.
4. Compare those forecasts with subsequently observed outcomes.
5. Advance the forecast origin.
6. Repeat across the available history.

For panel datasets, split by calendar time, not randomly by individual rows. Keep observations for the same future evaluation period together.

The evaluation should simulate the actual production forecasting process.

For each fold, ensure that:

- Vocabulary or feature selection has not used future observations.
- Scaling and imputation have been fitted on training observations only.
- Hyperparameters were chosen using validation data, not the final holdout.
- News and job-posting features existed by the historical cutoff.
- Outcome-derived features do not contain the target period itself.
- Forecast horizons do not accidentally overlap in a way that compromises interpretation.

### 15.3 Insufficient history

Do not force train/test evaluation when the available dataset cannot support it.

If there are too few independent periods to create a credible holdout and multiple validation folds:

- Run only the evaluations supported by the available history.
- Report the number of independent time periods.
- Explain which metrics are unreliable or unavailable.
- Return an explicit insufficient-history warning.
- Avoid declaring the selected model accurate.
- Recommend accumulating additional real observations or obtaining a legitimate historical source.

Use pooled panel data when it is statistically justified, but do not mistake repeated measurements from highly correlated groups for independent evidence.

For unseen-country or unseen-occupation generalisation, add a separate group-holdout evaluation where the data support it. This evaluates a different question from forecasting known groups into future periods.

## 16. Use appropriate evaluation metrics

### AI progress

Evaluate both numerical capability forecasts and regime probabilities.

Potential metrics:

- MAE and RMSE for continuous forecasts.
- Brier score and log loss for regime probabilities.
- Probability calibration.
- Credible-interval coverage.
- Comparison with simple trend or persistence baselines.

Avoid declaring a classifier successful based solely on accuracy.

### Adoption

Use:

- MAE for adoption rates.
- Appropriately weighted errors where measurement precision differs.
- Predictive interval or credible-interval coverage.
- Calibration for probabilistic outputs when applicable.
- Comparison with persistence and trend baselines.

Use metrics appropriate for small, bounded proportions. Avoid relying on MAPE when the target can be zero or close to zero.

Report business-adoption evaluation separately from worker- or occupation-adoption evaluation.

### Skill demand

Use metrics suitable for both share and count targets.

Potential metrics include:

- MAE.
- RMSE.
- WAPE.
- A zero-safe scaled metric such as MASE.
- Error in absolute percentage-point terms for skill-demand shares.
- Predictive interval coverage.

Do not select a metric simply because it makes a model look better.

### 16.1 Baseline comparison requirement

Every model must be compared with at least one relevant naive or statistical baseline.

Examples:

- Latest observation carried forward.
- Seasonal-naive forecast when appropriate.
- Linear trend.
- Simple exponential smoothing.

Report whether the selected candidate improves on those baselines in rolling-origin tests and in the final holdout.

If no candidate beats a baseline reliably, retain the baseline or label the model as not yet demonstrably better.

## 17. Use model selection rather than a hard-coded universal winner

Build a model registry containing candidate algorithms, fit status, data eligibility, configuration, prediction output, and evaluation metrics.

Select a model separately for each forecasting target and horizon.

The training pipeline should:

1. Check the target and available history.
2. Determine which candidate algorithms are eligible.
3. Fit the eligible candidates on training data.
4. Tune only within the permitted training and validation windows.
5. Evaluate through rolling-origin folds.
6. Select a candidate based on a predeclared performance criterion.
7. Compare the selected candidate with the baseline.
8. Evaluate the chosen model once on the locked final holdout.
9. Persist the performance report and the fitted model.
10. Record the selection rationale.

Do not use a single hard-coded rule such as "LightGBM if there are more than 1,000 rows". Sample size alone does not establish independent information, valid temporal coverage, or generalisation.

Do not select a model merely because it has the lowest training error.

Use a conservative complexity preference when candidates have similar performance.

### 17.1 Model-selection diagnostics

Provide diagnostics for:

- Training versus validation error.
- Performance by forecast horizon.
- Performance by geography and group where support permits.
- Residual behaviour.
- Calibration.
- Interval coverage.
- Missingness sensitivity.
- Data-source ablations.
- Performance across major measurement breaks.
- Sensitivity to the training window.
- The stability of model rankings across validation folds.

Store these results so users can see why a model was selected.

---

# PART H — PREVENTING BIAS AND DATA LEAKAGE

## 18. Mandatory source-ablation experiments

Implement a reproducible feature-ablation suite for each model.

At minimum, where applicable, compare:

1. All eligible features.
2. Structured data only.
3. Job-ad features excluded.
4. News features excluded.
5. AI-capability features excluded.
6. BTOS-derived features excluded.
7. Recent trend features excluded.

Not every ablation is appropriate for every target. For example, BTOS should not be treated as an optional predictor of an unrelated occupational target when it does not measure that target.

Record every experiment and its evaluation results.

The objective is to determine whether an input provides useful additional forecasting information, not to force all available sources into the model.

### 18.1 Distinguish four types of uncertainty

Where possible, report uncertainty arising from:

- Measurement uncertainty in the source data.
- Statistical model uncertainty.
- Future outcome variability.
- Scenario and assumption uncertainty.

A narrow interval should not be interpreted as reliable merely because a model did not represent the uncertainty of its underlying measurements.

### 18.2 Keep the targets independent

Implement tests or explicit validation checks to prevent these invalid substitutions:

- Task exposure being labelled as actual adoption.
- Business-level adoption being labelled as worker-level adoption.
- Job-posting growth being labelled as employment growth.
- News volume being labelled as capability improvement.
- AI skill demand being labelled as AI adoption.
- An emerging skill classification being treated as ground truth for a future demand forecast.

These are separate but related measurements.

---

# PART I — SCENARIO ENGINE

## 19. Connect the three models without erasing their differences

Build a scenario layer that combines Model A's AI-progress outlook with conditional forecasts from Models B and C.

At minimum, support:

### Fast-progress scenario

AI capabilities improve faster than the recent baseline, subject to the explicit assumptions of this scenario.

Simulate adoption and skill demand conditional on that assumption.

### Baseline scenario

AI capabilities and adoption develop around the modelled baseline trajectories.

### Slow-progress scenario

Capability improvements slow relative to the recent baseline, and adoption and skill demand are recalculated under the specified constraints.

Do not simply multiply all predictions by arbitrary percentages to create different scenarios.

Scenario adjustments must be based on explicit, configurable assumptions or fitted relationships that can be tested against historical evidence.

### 19.1 Conditional forecasts versus average forecasts

For each scenario, store and present the conditional forecast.

When Model A provides credible probabilities for its progress regimes, you may also calculate probability-weighted estimates of downstream outcomes.

Conceptually:

\[
E[Y_{t+h}] =
\sum_{k=1}^{K}
P(S_k\mid\mathcal{D}_t)
E[Y_{t+h}\mid S_k,\mathcal{D}_t]
\]

Here, \(S_k\) represents one of the defined scenarios and \(\mathcal{D}_t\) represents information available at the forecast origin.

This calculation is appropriate only when the scenario probabilities, conditional forecasts, and their assumptions are valid and aligned.

If the conditional effects of AI progress on adoption have not been estimated credibly, label the results as assumption-based scenario simulations rather than empirically calibrated forecasts.

### 19.2 Scenario outputs

For each selected occupation, industry, and skill, show:

- Recent observed state.
- Baseline forecast.
- Fast-progress forecast.
- Slow-progress forecast.
- Expected forecast where the probability weighting is justified.
- Uncertainty intervals.
- The assumptions producing differences between scenarios.
- Supporting historical evidence.
- Relevant emerging risks and opportunities.

Keep scenario outputs distinguishable from direct predictions and measured historical observations.

---

# PART J — ALWAYS-UP-TO-DATE DATA PIPELINE

## 20. Automate external data ingestion

Implement incremental ingestion so that new source data can be retrieved without manually running the entire collection process.

Provide modular commands equivalent to:

- `ingest --source all`
- `ingest --source adzuna`
- `ingest --source gdelt`
- `ingest --source btos`
- `build-features`
- `train`
- `evaluate`
- `forecast`
- `run-pipeline`

Adapt command names to the repository's existing conventions.

Support:

- Incremental updates.
- Configurable lookback windows.
- Backfills.
- Manual reruns.
- Dry runs.
- Per-source retries.
- Exponential backoff.
- Rate-limit handling.
- Timeouts.
- Logging and monitoring.
- Idempotent ingestion.
- Schema-change detection.
- Safe recovery after partial failure.

A failed request must not overwrite valid historical data with empty results.

If a source is unavailable, the pipeline should record the failure, preserve the last successful data, and continue with independent sources where doing so is safe.

### 20.1 Refresh cadence

Use source-appropriate schedules.

A sensible configurable starting point is:

- GDELT news signals: daily or several times per week.
- Adzuna listings and supported market aggregates: daily or weekly, subject to quota and relevance.
- BTOS: retrieve updates when new official data products are released, using the available publication schedule rather than repeatedly downloading unchanged data.
- Model benchmark and capability datasets: check weekly or monthly, depending on the actual source update frequency.
- Occupational taxonomies and exposure datasets: check periodically and refresh when new versions become available.

These are initial operational settings, not claims that every source updates at those intervals.

Avoid unnecessary polling and comply with API limits, source terms, and licence requirements.

### 20.2 Automated refresh and training

Use the scheduling mechanism appropriate to the existing repository and deployment environment.

Where GitHub Actions fits the project, provide a scheduled workflow and a manual workflow dispatch. Where the repository already has a scheduler, use it rather than adding a competing system.

The automated process should:

1. Collect new data.
2. Validate incoming data.
3. Save a new data snapshot.
4. Rebuild affected features.
5. Check whether enough new valid observations exist to justify retraining.
6. Retrain and evaluate eligible candidates when appropriate.
7. Compare new models against the currently deployed models.
8. Promote a new model only when it meets the predeclared evaluation requirements.
9. Generate the latest forecasts.
10. Save reports and data-freshness status.

Do not promote a newly trained model solely because it is the most recent model.

If the new candidate does not satisfy the acceptance criteria, retain the last acceptable model and report why promotion failed.

Distinguish the time of the latest data update from the time of the last successful model retraining.

### 20.3 Forecast freshness

The user should always be able to see whether a forecast reflects recent data.

Show:

- Forecast generated at.
- Training data cutoff.
- Latest observation date for each relevant source.
- Latest successful ingestion time.
- Source staleness warnings.
- Model version.
- Model training cutoff.
- Whether the latest refresh passed model evaluation.

When new data cannot be retrieved, do not pretend the existing forecast is fully up to date.

Keep the last valid forecast accessible, but label it as stale where necessary.

### 20.4 Secrets and operational security

Use environment variables for API credentials.

Provide an `.env.example` with placeholder names and no real keys.

Never commit or log API secrets.

Keep source adapters independently testable without live API access.

Respect rate limits, API licensing, source terms, and data-retention restrictions.

---

# PART K — RECOMMENDED TECHNICAL IMPLEMENTATION

## 21. Build a modular and maintainable architecture

Follow the repository's existing architecture wherever appropriate.

If the repository has no established design, consider a modular Python implementation using:

- Python 3.12 or another compatible supported version.
- Pandas or Polars for data transformations.
- DuckDB and Parquet for an initial analytical store.
- Pydantic for configuration and validation.
- scikit-learn for preprocessing, metrics, baselines, and candidate ML models.
- statsmodels for appropriate classical forecasting models.
- PyMC for Bayesian hierarchical and state-space models where needed.
- pytest for automated testing.

These are suggested defaults, not a reason to rewrite an existing working stack.

Avoid introducing heavy infrastructure without a demonstrated need.

Keep the system organised into modules similar to:

- `config/`
- `connectors/`
- `ingestion/`
- `data_quality/`
- `normalisation/`
- `taxonomy/`
- `features/`
- `models/`
- `evaluation/`
- `scenarios/`
- `forecasting/`
- `storage/`
- `api/`
- `dashboard/`
- `tests/`

Use suitable boundaries for data ingestion, modelling, evaluation, and presentation.

Do not place source collection, model fitting, data transformation, and dashboard logic in one giant script.

## 22. Core programmatic interfaces

Implement clean interfaces for source ingestion, feature construction, training, evaluation, and forecasts.

Conceptually, the platform should support operations equivalent to:

```python
pipeline.ingest_sources()
pipeline.validate_sources()
pipeline.build_features()

progress_model = train_progress_model()
adoption_model = train_adoption_model()
skills_model = train_skills_model()

evaluation_report = evaluate_models()
forecast_bundle = generate_forecasts()
scenario_bundle = run_scenarios()
```

Adapt the exact API to the repository.

The interfaces should return structured results with metadata, rather than writing untraceable predictions directly into console output.

Provide suitable exception handling and explicit statuses when an operation fails or data is insufficient.

## 23. Forecast and evaluation storage

Create a suitable schema for recording:

- Source registry.
- Ingestion jobs.
- Raw source records or references.
- Normalised observations.
- Skill taxonomy and mappings.
- Occupation and industry mappings.
- Feature datasets and data vintages.
- Model configurations.
- Training runs.
- Model versions.
- Evaluation folds.
- Evaluation metrics.
- Forecast outputs.
- Scenario assumptions.
- Source health and freshness.
- Errors and warnings.

Use stable identifiers and appropriate uniqueness constraints.

Prevent a rerun from accidentally duplicating an observation or silently destroying the provenance of a previous forecast.

---

# PART L — DASHBOARD AND PRESENTATION REQUIREMENTS

## 24. Display forecasts and the evidence behind them

Integrate with the existing frontend where possible.

The initial interface should expose the following sections.

### 24.1 AI capability outlook

Show:

- Probability of acceleration, broadly stable progress, and slowdown.
- Historical capability measurements.
- Forecast trajectory and uncertainty.
- Individual capability dimensions.
- Recent relevant news evidence.
- Benchmark freshness.
- Model evaluation status.

### 24.2 Occupational adoption

Allow users to filter by country, industry, occupation, and horizon.

Show:

- Observed adoption where available.
- Forecast adoption.
- Adoption-propensity estimates separately.
- Evidence tier.
- Credible or prediction interval.
- Exposure and adoption as distinct measures.
- Scenario comparison.
- Data coverage.
- Evaluation status.

### 24.3 Future skill demand

Allow filtering by country, occupation, industry, skill, and horizon.

Show:

- Fast-growing skills.
- Skills losing relative demand.
- Emerging skill candidates.
- Forecast demand share.
- Forecast volume where available.
- Current versus forecast demand.
- Relevant occupations and industries.
- Supporting job-ad and news evidence.
- Confidence and freshness status.

### 24.4 Model evaluation

Show:

- Training period.
- Final holdout period.
- Rolling-origin evaluation periods.
- Baseline results.
- Candidate-model comparisons.
- Selected model and selection rationale.
- Metrics by horizon.
- Data-source ablation results.
- Calibration and interval coverage.
- Model promotion or rejection status.

### 24.5 Source health

Show:

- Last successful ingestion.
- Latest observed period.
- Stale or failed sources.
- Number of usable observations.
- Missingness.
- Schema changes.
- Known measurement breaks.

Use explicit labels for historical observations, forecasts, proxies, and unvalidated estimates. Do not display every number with the same visual treatment as though its evidential status were identical.

---

# PART M — TESTING AND ACCEPTANCE CRITERIA

## 25. Mandatory automated tests

Add unit, integration, and regression tests.

At minimum, test the following.

### Data ingestion

- Source adapters parse documented response structures.
- Credentials are not required for offline unit tests.
- API failures do not destroy existing valid data.
- Duplicate records are handled correctly.
- Incremental ingestion is idempotent.
- Unexpected schemas are detected.
- Dates and timestamps are handled consistently.

### Data leakage

- No training feature uses information that became available after its forecast origin.
- Train and test periods do not overlap improperly.
- Preprocessing is fitted only on training data.
- Future advertisements do not enter historical predictions.
- News publication time is respected.
- Hyperparameter tuning does not use the locked final holdout.
- Time-based folds are generated by period rather than randomly shuffling panel rows.

### Adoption modelling

- BTOS is not used as a directly observed occupational-adoption label without a compatible target.
- Question wording changes are represented and tested appropriately.
- Occupation-level proxy results are labelled correctly.
- Unsupported survey denominators are not fabricated.
- Uncertainty is propagated where the selected approach supports it.

### Skill-demand modelling

- Numerators and denominators are retained.
- Skills are normalised consistently.
- Low-volume skills are flagged.
- Count and share forecasts remain distinct.
- Emerging-skill detection can distinguish a genuine trend from a single spike.

### Model evaluation

- Every candidate has baseline comparisons.
- Holdout data remain separate from tuning.
- Metrics are calculated against the correct target and horizon.
- Unavailable evaluation is reported as unavailable rather than zero error.
- A selected model must not be promoted just because it achieved a low training error.
- Source ablations can be reproduced.

### Forecast generation

- Regime probabilities sum to one.
- Prediction intervals have valid bounds where the chosen target requires them.
- Predictions contain timestamps and model versions.
- Missing data lead to appropriate warnings.
- Stale data do not silently produce an "up to date" status.
- A rejected model does not overwrite the last acceptable model.

Use fixed random seeds where appropriate and keep tests deterministic.

## 26. Definition of a successful implementation

The implementation is complete only when the following workflow works end to end:

1. The system can retrieve data from configured sources.
2. Source records are saved with provenance.
3. Data validation identifies invalid or missing observations.
4. Normalisation and feature engineering produce reproducible datasets.
5. The three modelling modules construct their own valid targets and features.
6. Candidate algorithms can be trained using historical training data.
7. A genuine temporal validation process evaluates candidate models.
8. A final holdout evaluation is performed without tuning on the holdout.
9. Baselines, candidate models, and source ablations are compared.
10. Unsupported predictions are marked as insufficiently evidenced.
11. The selected models produce forecasts with uncertainty and explicit timestamps.
12. Fast, baseline, and slow progress scenarios produce the appropriate downstream outputs.
13. New source data trigger the relevant update and evaluation process.
14. The system retains the last acceptable model when a new model fails its acceptance criteria.
15. The interface or CLI exposes forecast results, data freshness, and evaluation results.
16. Tests pass using real structural contracts or legitimate fixtures, without requiring live external APIs.
17. Documentation explains how to configure, run, evaluate, and maintain the platform.

Do not invent live results merely to make the dashboard appear populated. If the API credentials or internet access are unavailable, implement the source adapter, validate it offline with clearly identified test fixtures, and state what could not be verified.

---

# PART N — DOCUMENTATION AND DELIVERABLES

## 27. Required documentation

Produce and maintain:

### README

Explain:

- What the platform predicts.
- Its data sources.
- How to configure API credentials.
- How to ingest data.
- How to train and evaluate models.
- How to generate forecasts.
- How to schedule updates.
- How to run tests.
- Important limitations.

### Architecture documentation

Describe the data pipeline, model boundaries, data storage, model registry, scheduling, and scenario engine.

### Data dictionary

Explain every important field, metric, target, unit, and source.

### Modelling methodology

Document:

- Why each algorithm was selected.
- Which alternatives were tested.
- Target definitions.
- Feature engineering.
- Training and testing procedures.
- Metrics.
- Backtest results.
- Known limitations.
- Source-ablation results.

### Model cards

For every deployed model, document:

- Intended target and use.
- Geographic scope.
- Forecast horizons.
- Training data.
- Model version.
- Evaluation results.
- Supported claims.
- Uncertainty and known failure modes.
- Data requirements.
- Promotion status.

### Operations guide

Explain the scheduled jobs, source health monitoring, retraining criteria, secrets, recovery procedures, and how stale data are communicated.

---

# PART O — IMPLEMENTATION ORDER

## 28. Build the smallest reliable end-to-end system first

Use the following sequence.

### Phase 1: Audit and data contracts

Inspect the repository, create the implementation plan, define the source registry, and establish target and feature schemas.

### Phase 2: Historical data and ingestion

Build the Adzuna and GDELT collectors, ingest the available BTOS data, preserve source snapshots, and validate data quality.

Implement at least one working path from ingestion to a normalised historical dataset.

### Phase 3: Skill-demand forecasting

Implement skill extraction, aggregation, baselines, regularised dynamic regression, rolling-origin evaluation, and the first forecast outputs.

This is a suitable initial vertical slice because job advertisements provide relatively direct evidence of the demand signal being forecast.

### Phase 4: AI capability-progress modelling

Add benchmark ingestion, trend construction, Bayesian state-space estimation, regime probabilities, uncertainty, and historical forecast evaluation.

### Phase 5: Occupational adoption

Add the survey-based hierarchical model and occupational exposure features. Ensure that the output type reflects the available evidence.

Implement source-ablation diagnostics to prevent BTOS from being misapplied to unsupported targets.

### Phase 6: Scenario engine

Connect the models through explicit conditional forecasts and assumptions, while retaining the separate identity and uncertainty of each target.

### Phase 7: Automated refresh and evaluation

Implement scheduled ingestion, data-vintage retention, model retraining, validation, promotion rules, and freshness reporting.

### Phase 8: User interface and final validation

Complete the forecast views, model-evaluation reports, source-health views, tests, setup instructions, and acceptance checks.

Prioritise a working core pipeline over polishing optional features.

If time is constrained, reduce the number of candidate models or initial countries rather than sacrificing valid evaluation, historical provenance, or source separation.

---

# FINAL INSTRUCTIONS

Begin by inspecting the repository.

Then implement the platform incrementally, running the relevant tests and verifying each major stage.

At the end, provide a concise completion report covering:

1. What was implemented.
2. Which source adapters work and which still require credentials or access.
3. Which models were implemented.
4. How training, temporal validation, and final holdout testing work.
5. Which metrics and baseline comparisons are available.
6. Whether BTOS source-bias safeguards and source-ablation tests are implemented.
7. How automatic ingestion, retraining, and forecast refresh are triggered.
8. How to run the complete system.
9. Test results.
10. Remaining limitations and the most important next steps.

Clearly distinguish completed functionality from planned or unverified functionality.

Do not claim that a model performs accurately unless supported by real evaluation results on data that were not used for model selection.

**The final priority is a reliable end-to-end forecasting system whose predictions can be independently evaluated, whose data stay current, and whose uncertainty and evidence limitations are visible to the user.**