# Claude Code Task: Build an Independent Occupational Forecasting Page — Local Prototype First

## 1. Objective

Implement an entirely new page in my existing AI forecasting application called **Occupational Forecasting**.

My current application already contains industry-level forecasting functionality, including AI capability progress, skill demand, and business and worker AI adoption forecasts.

I want to preserve that existing implementation and create a new, independent forecasting product area focused on individual occupations.

**This task is an independent page and forecasting pipeline implementation, not a modification or replacement of my existing forecasting system.**

For this phase, focus on making the new page and forecasting pipeline work end to end locally.

Do not integrate Supabase yet. I want to verify the data pipeline, forecasting logic, emerging-skill detection, and prediction accuracy before introducing database integration.

Do not merely build a dashboard with illustrative charts. Implement a working prototype that can ingest available data, prepare occupational datasets, train and evaluate models, generate forecasts, and display the resulting outputs.

## 2. Inspect the existing project first

Before making changes:

1. Inspect the application framework, routing, frontend components, backend architecture, data connectors, and existing forecasting implementation.
2. Identify the safest way to introduce an independent page without changing existing pages or their behavior.
3. Identify which existing infrastructure can safely be reused, such as navigation components, chart libraries, API clients, and general utilities.
4. Identify existing forecasting logic, data transformations, and trained models that should not be reused without independent validation.
5. Implement the new page within the existing application, following its established conventions where appropriate.

Do not restart the entire application, replace the current architecture unnecessarily, or rewrite unrelated components.

If a shared component needs to change, preserve backward compatibility and verify that existing pages continue working.

## 3. Independent architecture

The new Occupational Forecasting page must have its own:

- Route and page components.
- Occupational data preparation pipeline.
- Job-title-to-occupation classification.
- Skill extraction and normalization.
- Emerging-skill detection.
- Occupational feature engineering.
- Model training and prediction workflows.
- Chronological validation and backtesting.
- Forecast-generation logic.
- Model evaluation results.
- Local forecast outputs and model artifacts.

Do not depend on existing industry-level predictions as inputs to the new occupational models by default.

Do not reuse their derived features, target variables, model artifacts, or predictions as ground truth.

Existing raw source data or generic API connectors may be reused only after verifying that they are suitable for occupational analysis and do not embed assumptions specific to the old models.

Keep the new pipeline independent even if it shares infrastructure with the current application.

## 4. Local development and data storage

For this phase, do not integrate Supabase.

Specifically:

- Do not create Supabase tables, migrations, database functions, or policies.
- Do not add Supabase queries or writes for the new forecasting domain.
- Do not change existing Supabase configuration or remove existing Supabase integrations used by other parts of the application.
- Do not require new Supabase credentials for the new page to work.
- Do not store new occupational forecasts in existing database tables.

Use a dedicated local data directory, following the conventions of the current project where practical. For example:

`data/occupational_forecasting/`

Keep the new domain's raw-data snapshots, normalized datasets, taxonomy files, trained model artifacts, evaluation results, and forecast outputs separate from the existing industry's derived data.

Use appropriate local file formats, such as CSV or Parquet for tabular datasets and JSON for metadata, configuration, and model-run records. Choose formats compatible with the project's current stack.

Create clean interfaces between data access and forecasting logic so that a future implementation can replace local storage with Supabase without rewriting the entire forecasting pipeline.

Do not implement a premature abstraction framework or duplicate storage systems unnecessarily.

### Data integrity

Distinguish clearly between:

- Real data obtained from external sources.
- Previously collected historical data.
- Synthetic data used for tests.
- Clearly labelled demo fixtures.
- Actual model forecasts.

Never present synthetic or demo data as real observations.

If a data provider is unavailable, its credentials are missing, or its historical coverage is insufficient, display that limitation and allow supported parts of the application to continue working.

Persist the last successful dataset and model artifacts where possible, rather than silently overwriting good results with failed or empty updates.

## 5. Primary feature: occupation-specific skill demand forecasting

The main purpose of this page is to forecast how employer demand for individual skills changes within specific occupations and countries.

I do not want the system to focus only on the share of job advertisements mentioning AI.

I want to understand what skills employers actually require, including traditional technical skills, professional skills, and emerging technologies.

### Occupational hierarchy

Organize the analysis around:

Country → Job sector → Occupation → Skill

Start with the software and technology sector, including these occupations:

- Software Engineer
- AI / Machine Learning Engineer
- Data Scientist
- Data Analyst

Design the taxonomy and processing pipeline so additional occupations and sectors can be added later.

Country must remain an analysis dimension and filter. Do not aggregate every country's job advertisements into a single global demand estimate.

### Skill-demand measurements

For each country, occupation, and skill, calculate its historical and current demand using deduplicated, eligible job advertisements.

A primary metric should be:

Skill-demand share = number of eligible job advertisements classified into the selected occupation that mention the skill ÷ total eligible job advertisements classified into that occupation.

Define the denominator precisely and apply it consistently.

Also retain absolute advertisement counts, where possible, because a change in the percentage can occur even when the total number of job advertisements declines.

Show:

- Historical demand.
- Latest observed demand.
- Forecast demand at configurable future horizons.
- Historical and forecast trends.
- Growing and declining skills.
- Advertisement counts and evidence coverage.
- Model uncertainty and evaluation results.

Do not use one aggregate AI-keyword metric as a substitute for individual skill-demand analysis.

### Track ordinary skills, not only AI skills

The system must be capable of tracking ordinary technical and professional skills, such as Java, Python, Rust, SQL, auditing, cloud infrastructure, and other skills actually mentioned in advertisements.

These examples must not become a fixed, hardcoded list of the only skills the system can detect.

Use O*NET or other appropriate occupational and skill taxonomies as initial references. However, the system should not be limited to the skills already represented in those taxonomies.

## 6. Emerging-skill discovery

One of the most important requirements is to discover skills that are emerging in job advertisements before they are adequately represented in existing taxonomies.

Implement a reproducible pipeline that:

1. Extracts candidate skills and technologies from job-advertisement text.
2. Normalizes aliases, spelling variations, abbreviations, and equivalent terms.
3. Matches recognized skills to existing taxonomy entries where appropriate.
4. Preserves plausible new skill candidates when no suitable taxonomy entry exists.
5. Associates candidates with countries, job sectors, and occupations.
6. Tracks when candidates first appear and how their mentions evolve over time.
7. Measures recent demand, historical demand, and changes in demand.
8. Distinguishes genuine new concepts from alternate wording, noisy text, and isolated mentions.
9. Records evidence, source provenance, and candidate confidence.

Maintain a versioned skill registry with statuses such as:

- Known.
- Newly detected.
- Under review.
- Merged into an existing skill.
- Deprecated.

A newly detected phrase must not automatically be declared a new skill.

Use sufficient sample sizes, minimum evidence requirements, and transparent ranking criteria. When the evidence is weak, mark the candidate as uncertain rather than producing a confident emerging-skill claim.

Use language models or other semantic methods only where they add demonstrable value. Ground their outputs in actual job-ad evidence and validate extracted skills against the source text.

The output should allow me to answer:

**Which skills appear to be gaining importance in this particular occupation and country, including skills not yet well covered by O*NET?**

## 7. Job-advertisement ingestion and data quality

Inspect existing connectors, including the Adzuna API if it is already configured and suitable.

Reuse general API infrastructure where it is safe, but independently implement occupational-specific normalization and feature engineering.

Preserve useful fields such as:

- Source and source identifier.
- Retrieval timestamp.
- Posting date, where available.
- Country and location.
- Original job title.
- Employer, where available.
- Job description and requirements.
- Occupation classification.
- Extracted skills.
- Duplicate-matching information.

Handle duplicate advertisements, missing descriptions, inconsistent job titles, and source coverage limitations.

Distinguish posting dates from collection dates. Do not assume that the API provides complete historical job-advertisement data unless this is verified.

Respect provider rate limits, licensing, retention rules, and access restrictions.

Do not manufacture historical data when a provider only returns current results.

If a source does not supply reliable historical observations, design an incremental collection process that saves dated snapshots locally so future forecasting evaluations can use genuinely observed history.

## 8. Second feature: AI adoption by occupation

The page should also investigate occupational-level AI adoption, grouped by job sector.

Start with the same four software and technology occupations, and design the data model so additional occupations can be supported later.

Keep the following targets separate.

### A. Worker AI usage

Estimate the share of workers within an occupation who actually use AI on the job.

Where possible, use credible occupation-level surveys or other directly observed data.

### B. Employer deployment by occupational function

Investigate whether employers are deploying AI in the work performed by particular occupations.

Do not assume that an employer using AI somewhere in its business means that all of its employees, or every occupation, uses AI.

### Evidence and measurement constraints

The two measures above are not interchangeable.

Job advertisements can describe requested AI skills or indicate changing employer requirements, but they cannot directly establish the proportion of current workers who use AI.

Investigate the availability of suitable sources and preserve each source's population, definition, observation period, geography, and sample size where available.

If direct occupational measurements are unavailable, a transparent proxy-based estimate may be explored using appropriate evidence such as occupational task composition, AI task-exposure measures, surveys, or other validated indicators.

However:

- Clearly distinguish measured observations from model estimates.
- Never label task exposure as an observed adoption rate.
- Never convert a proxy into an adoption percentage without an empirically justified method.
- Show uncertainty and evidence coverage.
- Do not fabricate precise forecasts when the evidence is insufficient.

A smaller number of defensible estimates is preferable to a comprehensive dashboard filled with unsupported percentages.

## 9. Model design and validation

Treat predictive accuracy as a first-class requirement.

Do not simply select a sophisticated model and assume it is better than a baseline.

### Skill-demand forecasting

Start with appropriate baselines, such as persistence or simple trend forecasts, depending on the data available.

Then evaluate suitable models for the actual target and data volume. These may include regularized regression, dynamic regression, or appropriate count/proportion models.

Select models based on out-of-sample performance, stability, and interpretability rather than complexity alone.

Account for sparse observations, changing advertisement volume, country differences, occupation classification errors, and skills with intermittent demand.

### Adoption forecasting

Select a model suitable for the actual evidence and target definition.

Ensure predicted proportions remain within their valid bounds, calibrate estimates where feasible, and communicate uncertainty.

Do not fit an apparently precise occupational adoption model when the available evidence cannot identify the target reliably.

### Required evaluation safeguards

- Use chronological training, validation, and test periods.
- Use rolling-origin backtesting where appropriate.
- Prevent future information from entering historical features or training.
- Track when each observation became available, not just its event date.
- Establish baselines before introducing complex models.
- Use metrics appropriate to each target.
- Compare models against baselines and report the results.
- Keep an untouched final evaluation period where sufficient history is available.
- Store model versions, target definitions, data versions, and evaluation results locally.
- Represent uncertainty rather than displaying forecasts as certain outcomes.

For skill demand, evaluate both point forecasts and, where feasible, prediction intervals.

For occupational adoption, evaluate against independently observed occupational adoption evidence whenever possible.

Do not use existing industry-level predictions as the ground truth for the new models.

## 10. Relationship to existing industry forecasts

The existing industry-level forecasting system must remain unchanged.

Initially, the occupational models should operate independently of the existing industry forecasts.

Industry-level predictions may eventually be useful for diagnostic comparisons or a future hierarchical model, but they must not be treated as truth simply because they already exist.

Do not force occupational forecasts to agree with industry forecasts during this prototype phase.

If you implement an optional comparison, keep it read-only and clearly separate from model training and predictions. Compare only compatible definitions, time periods, populations, and geographies.

Any future approach that combines industry and occupational information must be justified through independent historical backtesting.

## 11. Occupational Forecasting page design

Create a dedicated page and navigation entry within the existing application.

Keep its user interface logically independent from the existing forecasting pages.

### Global filters

Provide controls for:

- Country.
- Job sector.
- Occupation.
- Historical date range.
- Forecast horizon.
- Latest available observation date.

Only display filters and options supported by the actual data.

### Skill-demand dashboard

Display:

- Historical demand versus forecast demand.
- Skills with increasing or decreasing demand.
- Individual skill trends.
- Advertisement counts and demand shares.
- Forecast uncertainty.
- Source coverage and latest data date.

Allow users to select a skill and inspect its historical evidence and forecast.

### Emerging-skills dashboard

Include a table showing:

- Candidate skill.
- Country and occupation.
- First observed date.
- Recent and historical mention counts.
- Current demand share.
- Growth indicators.
- Number of supporting advertisements.
- Taxonomy status.
- Evidence confidence.

Ensure low-volume, noisy candidates do not automatically dominate the rankings because of extreme percentage growth.

### Occupational AI-adoption dashboard

Keep worker AI usage separate from employer deployment by occupational function.

Clearly distinguish observed measurements from proxy-based estimates, and display source details, observation periods, evidence coverage, and uncertainty.

If there is insufficient evidence for an occupation, display that limitation rather than a fabricated result.

### Transparency

Make the model version, dataset version, latest observation date, forecast date, evaluation metrics, and important assumptions accessible from the page.

The purpose is to investigate real changes in job requirements and occupational adoption, not merely to display predicted numbers without supporting evidence.

## 12. Implementation order

Implement the project in this order:

1. Inspect the existing application and identify the safest route for the new page.
2. Add the page and navigation entry without disrupting existing pages.
3. Establish isolated local storage and data-access interfaces for the new forecasting domain.
4. Implement job-advertisement ingestion and data normalization.
5. Implement occupational classification and skill extraction.
6. Build the skill-demand calculation and baseline forecasting pipeline.
7. Build chronological backtesting and save evaluation reports.
8. Implement emerging-skill discovery and its evidence-quality controls.
9. Implement the occupational adoption evidence model and supported estimates.
10. Connect the page to the actual pipeline outputs.
11. Add automated tests and verify the complete local workflow.
12. Run regression checks on the existing application.

Prioritize a working end-to-end vertical slice for software and technology occupations before expanding coverage.

Do not attempt to implement every advanced feature before the first pipeline works.

If API access or sufficient historical data is unavailable, make the limitation explicit, complete the supported functionality, and keep demo data clearly labelled.

## 13. Acceptance criteria

The implementation is complete when:

- The new Occupational Forecasting page is accessible independently.
- Existing forecasting pages continue working as before.
- The new forecasting pipeline does not depend on existing industry prediction outputs.
- No Supabase integration is required for the new page.
- The new domain can ingest and process available data using local storage.
- Skill demand is measured per occupation, country, and individual skill.
- The system tracks ordinary skills and can discover plausible candidates beyond the initial taxonomy.
- Forecasts can be generated from the actual prepared datasets.
- Chronological backtesting and baseline comparisons are available.
- Occupational adoption measurements are separated from estimates and proxy indicators.
- Evidence volume, data freshness, model versions, and relevant uncertainty are visible.
- Automated tests cover the new pipeline and page functionality.
- No fabricated observations or unsupported claims of predictive accuracy are presented.
- Existing data, routes, models, and integrations have not been unintentionally modified.

## 14. Final implementation report

After implementing the page, provide a concise report covering:

1. The new route and page components.
2. New modules and files created.
3. Local data and model-artifact storage.
4. Sources that actually work and the historical coverage available.
5. The skill-demand and emerging-skill workflows.
6. Occupational adoption data availability and any estimates supported.
7. Models used, baselines, and actual backtesting results.
8. Tests performed and known limitations.
9. Confirmation that existing forecasting functionality remains intact and no Supabase integration was added to the new domain.

**Final priority: make the occupational forecasting workflow work independently and demonstrate its predictive performance locally. Supabase integration is explicitly out of scope for this phase.**