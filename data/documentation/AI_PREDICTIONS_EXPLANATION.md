
# Jobee — Career Intelligence & Explainability Improvements

You are working on **Jobee**, an existing career guidance platform built for SDC 2026, Domain 1, SDG 8 (Decent Work and Economic Growth).

Your task is to implement three interconnected improvements to the existing application:

1. Career What-If Simulator
2. Explainable Role Matching and Score Breakdowns
3. Forecast Transparency and Methodology

These features should work together to make Jobee more interactive, understandable, and trustworthy.

**IMPORTANT: This is an extension of an existing application, NOT a new project.** Inspect the existing codebase before implementing anything. Reuse existing components, APIs, calculations, data structures, forecasting artifacts, and design patterns wherever possible.

Do not rebuild existing features unnecessarily.

---

# 1. Understand the Existing Application First

Jobee's current architecture:

- Frontend: Vue 3, Vite, TypeScript
- Backend: Python, FastAPI
- Database and authentication: Supabase
- Forecasting: pandas, scikit-learn, LightGBM
- Resume processing: the LLM gateway (OPENROUTER_MODEL)
- Hosting: Replit Autoscale

The main application flow:

1. User completes onboarding.
2. User uploads a resume or manually selects skills.
3. User rates their proficiency in each skill.
4. Jobee recommends eight technology occupations using deterministic weighted scoring.
5. User explores roles under three AI futures:
   - AI accelerates
   - AI holds steady
   - AI slows down
6. The user selects a role and receives a skill-gap analysis.
7. An LLM generates a learning roadmap.
8. The user completes practical projects and submits GitHub repositories for AI grading.

There are also two market intelligence sections:

- **AI Outlook:** AI adoption and capability forecasts.
- **Occupations:** Skill-demand forecasts across four job types.

## Critical implementation instructions

Before writing code:

1. Inspect the existing frontend pages, routes, components, stores and API clients.
2. Locate the actual role-matching implementation and understand how its score is calculated.
3. Identify where the skill proficiency ratings and role requirements are stored.
4. Inspect the forecast artifacts, metadata, API responses and model-selection logic.
5. Understand how the three AI scenarios currently affect role matching and forecast visualisations.
6. Identify existing charting, dialog, drawer, tooltip and accordion components.
7. Identify the existing design system and preserve its visual language.

Use the actual implementation as the source of truth. The project brief describes the intended system, but some implementation details may have changed.

Do not invent new API endpoints or data fields without checking what already exists.

After inspection, produce a short implementation plan and proceed with the implementation. Do not stop at the plan or ask me to approve it.

---

# 2. Feature One: Career What-If Simulator

## Objective

Build an interactive simulator that allows users to explore how acquiring additional skills could change their career opportunities.

The central question should be:

**"What would happen to my career opportunities if I learned this skill?"**

This is one of Jobee's most important differentiating features.

Instead of simply telling users which skills they lack, Jobee should allow them to experiment with acquiring those skills and immediately see the potential impact on their career recommendations.

## 2.1 User experience

Integrate the simulator naturally into the existing role-matching or career exploration experience.

Do not create an entirely separate application or unnecessarily complicate navigation.

The user should be able to:

1. View their existing skill profile.
2. Browse skills they do not currently possess or have low proficiency in.
3. Select one or more skills to simulate acquiring.
4. Optionally select a proficiency level, using the existing proficiency scale.
5. Recalculate their role matches.
6. Compare their original profile against their simulated profile.
7. Switch between the three AI futures.
8. Identify which skills provide the greatest improvement in career opportunities.

The interface should feel interactive and exploratory rather than like another static analytics dashboard.

## 2.2 Simulation functionality

The simulator must use the existing deterministic role-matching engine.

Do NOT create a separate matching formula just for the simulator.

The calculation should work as follows:

**Baseline:**
- Current user skills.
- Current proficiency ratings.
- Current interests.
- Current career stage.
- Selected AI scenario.

**Simulated profile:**
- All existing user information remains unchanged.
- Add the selected simulated skills.
- Apply their simulated proficiency levels.
- Recalculate the role-matching scores using the same existing matching engine.

The simulator must calculate the results dynamically.

It must NOT:
- Arbitrarily increase matching percentages.
- Apply hardcoded bonuses for selected skills.
- Modify the original user profile during simulation.
- Call an LLM to calculate matching scores.
- Introduce a second independent scoring system.

Simulation results should be temporary and must not overwrite the user's actual skills or database records.

Only save changes if the user explicitly chooses an existing profile-update action.

## 2.3 Comparison interface

Display a comparison of the user's current and simulated career opportunities.

For example:

**Current profile vs Simulated profile**

| Metric | Current | Simulated |
|---|---|---|
| Skill coverage | Existing value | Recalculated value |
| Top recommended role | Existing role | Updated role |
| Match score | Existing score | Updated score |
| Role ranking | Existing ranking | Updated ranking |

Show the eight recommended occupations, where supported by the existing matching system.

For each occupation, show:

- Current match score.
- Simulated match score.
- Score difference.
- Current ranking.
- Simulated ranking.
- Skills gained or remaining gaps.

Make improvements and decreases visually distinguishable.

Also provide a clear explanation of WHY a particular role improved or declined.

For example:

"Your Software Developer match improved because you acquired FastAPI, which covers an additional required skill."

The explanation must be derived from the actual difference between the baseline and simulated match breakdowns. Do not generate fictional reasons.

## 2.4 Skill exploration

Provide a convenient way to select skills.

Prioritise:
- Missing skills from recommended occupations.
- Skills with high relevance across multiple occupations.
- Emerging skills already identified by Jobee's occupation forecasting pipeline.

Where possible, show:
- Skill name.
- Number of supported occupations requiring it.
- Relevant occupations.
- Forecasted demand direction.
- Current user proficiency.
- Simulated proficiency.

Allow users to select multiple skills.

Avoid displaying skills that already have the same or higher proficiency than the simulated target level.

## 2.5 AI future integration

The simulator must support all three existing AI futures:

- AI accelerates.
- AI holds steady.
- AI slows down.

Allow the user to switch scenarios without losing their simulated skill selections.

The simulator should demonstrate that the value of a particular skill may differ depending on how AI adoption and occupational demand develop.

Recalculate using existing scenario-specific outlook data.

Do not invent new scenario forecasts or treat the scenarios as probabilities.

## 2.6 Actionable outcome

Once the user is satisfied with their simulation, provide a logical next step:

**"Build these skills"**

This should connect to Jobee's existing learning roadmap functionality.

Ideally:
- Pass the selected target occupation.
- Pass the simulated skill gaps.
- Use the existing roadmap generation process.
- Prioritise the skills the user selected or still lacks.

Do not build a separate learning roadmap generator.

If the roadmap API cannot accept this information yet, extend it minimally while preserving backwards compatibility.

---

# 3. Feature Two: Explainable Role Matching and Score Breakdowns

## Objective

Currently, Jobee calculates several components of a role-matching score, but users mainly see the final match percentage.

This makes recommendations difficult to understand and potentially difficult to trust.

Expose the underlying calculation so users understand:

- Why a role was recommended.
- Which factors contributed to the result.
- What they are doing well.
- What they are missing.
- What they can improve.

## 3.1 Score breakdown

For each recommended occupation, display the individual matching components.

The intended components are:

| Component | Intended weight | What it measures |
|---|---:|---|
| Skills | 35% | Existing skills and proficiency compared with role requirements |
| Outlook | 35% | Role demand under the selected AI future |
| Interests | 25% | Alignment between user interests and the role's SDG associations |
| Education | 10% | User's career or education stage |

IMPORTANT: These intended weights sum to 105%, not 100%.

Inspect the actual implementation and verify the configured weights and score normalisation.

If they do not produce a valid weighted score, correct the calculation in a mathematically consistent way, preserve the intended relative weighting, document the change, and add tests.

Do not silently introduce inconsistent percentages into the UI.

## 3.2 Visual presentation

Add an expandable score breakdown to each role recommendation card and a more detailed breakdown on the individual occupation page.

Keep the main recommendation cards relatively compact.

Example:

**Software Developer — 78% Match**

| Component | Score | Weight |
|---|---:|---:|
| Skills | 82/100 | 35% |
| Outlook | 75/100 | 35% |
| Interests | 90/100 | 25% |
| Education | 60/100 | 10% |

The actual scores and weights must come from the existing scoring implementation.

Prefer visual progress bars or another intuitive representation rather than displaying only numbers.

Show weighted contributions where meaningful, ensuring that their totals reconcile with the actual matching formula.

## 3.3 Explain each component

When a user expands a component, provide a short explanation.

Examples:

**Skills**

"You already possess 7 of the 10 relevant skills for this occupation. Your strongest matches are Python and SQL. Your main gaps are FastAPI, Docker and Kubernetes."

**Outlook**

"Demand for this occupation is projected to increase under the AI accelerates scenario."

Show the actual underlying forecast metric and direction.

**Interests**

"This occupation aligns with your selected interests in innovation and sustainable infrastructure."

Make it clear that SDG alignment is based on Jobee's mapping methodology rather than an independently verified measurement of personal suitability.

**Education**

"This adjustment reflects your current career stage."

Check whether this component actually differentiates occupations. If its value is identical across all roles, explain that it is a shared profile adjustment rather than presenting it as a factor distinguishing one occupation from another.

## 3.4 Explain the match percentage

A matching score is a ranking and guidance mechanism.

It is NOT:
- A probability of getting hired.
- A probability of succeeding in an occupation.
- An objectively validated measure of career suitability.

Inspect whether the application applies a transformation to the raw score before displaying it.

If a nonlinear transformation or normalisation is applied, explain it appropriately.

Where practical, expose both:
- The final displayed match score.
- The underlying raw or normalised calculation.

Add a small tooltip or explanation:

"Your match score compares your existing skills, career outlook, interests and career stage against the requirements of each occupation. It helps prioritise career options, but does not predict your likelihood of getting hired."

Avoid overwhelming users with mathematical explanations unless they expand the breakdown.

## 3.5 Consistency with the simulator

The score breakdown must use exactly the same calculations as the Career What-If Simulator.

When a skill changes in the simulator:
- Update the skill component.
- Recalculate the final score.
- Update the weighted contributions.
- Update the role ranking if applicable.

There must never be two different sources of truth for role matching.

---

# 4. Feature Three: Forecast Transparency and Methodology

## Objective

Jobee's forecasting capabilities are an important part of its identity.

However, forecasts are difficult to trust when users cannot see where the data came from, what is being predicted, how accurate the model is, or what assumptions influence the results.

Improve the existing AI Outlook and Occupations sections by making the forecasting methodology transparent and accessible.

This should feel like a built-in explanation of Jobee's intelligence, not an academic paper or a separate analytics application.

## 4.1 Forecast information panel

Add an expandable "How this forecast works" or "Forecast information" panel to relevant charts.

Each forecast should expose the information that is actually available.

Include:

**A. Data provenance**
- Data source.
- Geographic coverage.
- Population or sample represented.
- Data collection period.
- Last updated date.
- Whether the dataset is complete or has coverage limitations.

**B. What is being measured**
- The exact metric being forecasted.
- Its unit.
- Its denominator, where applicable.
- Whether the metric measures absolute values, percentages, growth rates or mentions in job advertisements.

**C. Forecast configuration**
- Forecast horizon.
- Forecast frequency.
- Selected forecasting model.
- Whether the chart displays a model forecast or a simple baseline.
- Relevant model-selection information.

**D. Reliability**
- Backtesting approach.
- Historical evaluation period.
- Number of evaluation origins or cases.
- Available error metrics.
- Comparison against simple baselines.
- Whether the selected model outperformed the baseline.

**E. Limitations**
- Geographic limitations.
- Sample bias.
- Historical coverage limitations.
- Assumptions and proxy measurements.
- Important factors the model does not capture.

Do not invent any missing information.

If a metric, sample size, error range or validation result is unavailable, explicitly show "Not available" or omit that field.

Never fabricate accuracy percentages, confidence intervals, data sources or model performance.

## 4.2 AI Outlook transparency

The AI Outlook section includes multiple forecasting questions:

- AI mentions in job advertisements.
- Business AI adoption.
- Worker AI adoption.
- AI capability.

Treat these as separate forecasting series.

For each one, identify its actual data source, measurement definition, geographic scope, model and evaluation information.

The intended source families in the project brief include:
- Indeed.
- US Census Business Trends and Outlook Survey (BTOS).
- RPS survey data.
- METR data.

However, inspect the actual pipeline and deployed artifacts before displaying these sources.

Do not assume every source is used by every forecast.

### AI capability

For AI capability forecasts, explain what the measurement means.

Where METR time-horizon data is used, make clear that the metric represents task time horizons at a specified success level, not general AI intelligence.

Clearly distinguish:
- Historical observations.
- Forecasted values.
- Uncertainty ranges.
- Scenario assumptions.

Avoid implying that a model's time horizon directly translates into a universal automation percentage for occupations.

### AI scenarios

Preserve the three existing AI futures:

1. AI accelerates.
2. AI holds steady.
3. AI slows down.

Explain that these represent different assumptions about possible developments.

Unless probabilities are explicitly calculated and supported by the model, do not present them as three equally probable predictions.

Make the assumptions or adjustments behind each scenario inspectable where the existing pipeline exposes them.

## 4.3 Occupation and skill-demand transparency

The Occupations section predicts skill demand for four job types.

The intended skill-demand metric is:

"Share of sampled Hacker News job advertisements mentioning a particular skill."

Make this definition explicit wherever relevant.

Do not allow users to mistake it for:
- The percentage of all jobs requiring that skill.
- The percentage of all Malaysian vacancies requiring that skill.
- The absolute number of vacancies for that skill.

For each skill-demand forecast, expose:

- Skill name.
- Occupation or job type.
- Original data source.
- Observation period.
- Forecast horizon.
- Historical trend.
- Forecast direction.
- Available uncertainty range.
- Backtesting performance.
- Whether the selected model beat a simple baseline.

Show the actual sample size or advertisement counts if they are available.

Adzuna should be identified according to its actual role in the pipeline, including whether it is a cross-check rather than a training source.

### Emerging skills

For emerging-skill signals, explain:
- What qualifies a skill as emerging.
- Which data source identified the signal.
- Whether the skill has sufficient historical observations.
- Whether the signal is an observed increase or a forecasted increase.

Do not describe a skill as definitively emerging based on a weak or insufficient sample.

## 4.4 Forecast visualisation improvements

Improve the existing charts without unnecessarily redesigning them.

Users should be able to distinguish:

- Historical actual values.
- Forecasted values.
- Forecast ranges or error bands.
- Baseline projections, where relevant.

Use consistent visual distinctions throughout the AI Outlook and Occupations pages.

When available, show:
- Forecast issue date.
- Last historical observation.
- Forecast period.
- Forecast horizon.

Uncertainty ranges must be labelled according to how they were actually calculated.

For example:
- If based on backtesting errors, describe them as historical error bands.
- Only call them confidence or prediction intervals when the statistical methodology supports those descriptions.

If a model falls back to a simple baseline, make this visible rather than implying the sophisticated model was selected.

Example:

"Baseline selected: LightGBM did not outperform the year-on-year baseline during backtesting."

This is not necessarily a failure. Jobee should communicate that model selection is evidence-driven.

## 4.5 Malaysia versus US data transparency

Jobee is intended for the Malaysian market, but several historical forecasting datasets are US-based.

Do not hide this limitation.

Add an accessible geographical-coverage explanation.

Suggested messaging:

"Some of Jobee's labour-market forecasts use US historical data because the available Malaysian vacancy data does not provide sufficiently consistent historical coverage for the same forecasting methodology. These forecasts should therefore be interpreted as broader labour-market signals rather than direct predictions of Malaysian vacancy growth."

Where appropriate, distinguish:
- International forecasting signals.
- Malaysian occupational context.
- Malaysian validation or cross-check information.

If DOSM, TalentCorp/MyCOL or MASCO data is already integrated, expose the actual role each source plays.

If not, do not pretend that these sources are currently validating the model.

Do not force local data into the forecasting pipeline just to make the interface appear more localised.

## 4.6 Methodology documentation

Create or extend a centralised forecast metadata structure rather than hardcoding explanations independently inside every chart component.

Where possible, use existing model artifacts or metadata files.

If the existing data structure does not contain some information, extend it minimally.

The UI should read from a consistent metadata source.

A possible conceptual structure:

```json
{
  "forecast_id": "skill_demand_fastapi",
  "metric": "share_of_sampled_job_ads_mentioning_skill",
  "geography": "United States",
  "source": "Hacker News job advertisements",
  "observation_period": {
    "start": "actual_start_date",
    "end": "actual_end_date"
  },
  "forecast_horizon_months": 6,
  "selected_model": "actual_selected_model",
  "baseline_model": "actual_baseline_model",
  "model_selection_reason": "actual_reason",
  "validation": {
    "method": "actual_method",
    "evaluation_origins": null,
    "metrics": {},
    "outperformed_baseline": null
  },
  "limitations": [
    "Technology-heavy job advertisement sample"
  ]
}
```

This is only an illustrative schema. Adapt it to the existing application and actual metadata.

Do not populate placeholder values with invented factual claims.

Ensure old forecast artifacts and existing API consumers continue to work.

---

# 5. UI/UX and Design Requirements

All three features should look and feel like part of the existing Jobee application.

Preserve:
- Existing visual identity.
- Companion bee theme.
- Existing colour palette.
- Typography.
- Navigation.
- Card styles.
- Responsive behaviour.
- Existing interaction patterns.

Do not introduce an unrelated design system.

### General UX principles

1. Keep the main interface approachable for students and fresh graduates.
2. Put technical explanations behind expandable information panels.
3. Use concise explanations rather than dense academic text.
4. Prefer visual comparisons and meaningful charts.
5. Clearly distinguish actual data, simulations and forecasts.
6. Show the user what changed and why.
7. Avoid unnecessary dashboards or excessive statistics.

### Responsive behaviour

All three features must work on desktop, tablet and mobile.

In particular:
- Simulator comparison layouts should collapse cleanly on mobile.
- Charts should remain readable.
- Score breakdowns should not overflow.
- Methodology panels should be accessible without disrupting navigation.

---

# 6. Technical Requirements

## Architecture

Follow the existing architecture.

- Vue components should remain reusable.
- Keep business logic out of presentation components where the existing architecture supports separation.
- Use shared TypeScript types for API responses.
- Keep backend calculations in their authoritative service.
- Reuse existing FastAPI routes where possible.
- Add API changes only when genuinely necessary.
- Preserve existing authentication and Supabase behaviour.

## Calculation integrity

The role-matching formula must have one authoritative implementation.

The simulator, role cards and detailed score breakdowns must use consistent results.

Check:
- Weight normalisation.
- Score ranges.
- Missing user skills.
- Missing occupational skill requirements.
- Proficiency scales.
- Scenario switching.
- Score transformations.
- Ranking ties.

Do not silently change unrelated matching behaviour.

## Forecast integrity

The transparency layer must report what the forecasting pipeline actually does.

It must not:
- Retrain models unnecessarily.
- Introduce a new forecasting algorithm.
- Replace existing forecasts.
- Fabricate backtesting results.
- Invent confidence intervals.
- Present proxy data as Malaysian labour-market data.
- Describe a baseline fallback as a successful ML model.
- Mix incompatible metrics or denominators.

The objective is to make the existing forecasting process understandable, not to rewrite it.

## LLM usage

None of these three features should require an LLM for their core calculations.

The simulator and match breakdowns must be deterministic.

Forecast explanations should primarily use structured metadata and predefined descriptions.

Do not add unnecessary OpenRouter or other LLM calls.

Keep API usage and computational overhead low.

---

# 7. Testing and Acceptance Criteria

Do not consider the work complete simply because the UI renders.

Implement and test the actual functionality.

## Career What-If Simulator

- [ ] User can select skills to simulate acquiring.
- [ ] User can simulate different proficiency levels.
- [ ] Existing skills are not duplicated.
- [ ] All eight role recommendations can be recalculated where supported.
- [ ] Current and simulated results are comparable.
- [ ] Role score changes are produced by the real matching engine.
- [ ] Ranking changes are calculated correctly.
- [ ] All three AI scenarios work.
- [ ] Switching scenarios preserves selected simulated skills.
- [ ] Explanations correctly identify the causes of score changes.
- [ ] Reset restores the original profile simulation.
- [ ] Simulation does not overwrite the user's saved profile.
- [ ] Users can proceed to the existing learning roadmap flow.

## Explainable Role Matching

- [ ] Each recommended role exposes its score breakdown.
- [ ] Component weights are correct and mathematically consistent.
- [ ] Weighted contributions reconcile with the final score.
- [ ] Existing score transformations are documented.
- [ ] Users can understand why a role was recommended.
- [ ] Skill strengths and skill gaps are accurate.
- [ ] Education and interest components are explained honestly.
- [ ] No component is presented as a hiring probability.
- [ ] Simulator and role pages show consistent calculations.

## Forecast Transparency

- [ ] AI Outlook forecasts have accessible methodology information.
- [ ] Occupation skill-demand forecasts have accessible methodology information.
- [ ] Data sources are correctly attributed.
- [ ] Geographic coverage is visible.
- [ ] Forecast metrics and denominators are defined.
- [ ] Historical and forecasted values are distinguishable.
- [ ] Error bands are accurately labelled.
- [ ] Baseline selection is explained.
- [ ] Backtesting metrics are shown only when available.
- [ ] Scenario assumptions are documented where available.
- [ ] Missing metadata does not generate fabricated explanations.
- [ ] Existing forecast charts still work.
- [ ] Existing forecast artifacts remain compatible.

## General

- [ ] No regressions in existing onboarding.
- [ ] No regressions in resume upload.
- [ ] No regressions in role matching.
- [ ] No regressions in learning roadmaps.
- [ ] No regressions in project challenges or repository grading.
- [ ] No regressions in Hive or Social features.
- [ ] Frontend type checks pass.
- [ ] Backend tests pass.
- [ ] Mobile and desktop layouts work.
- [ ] No unnecessary new dependencies.

---

# 8. Implementation Priority

Implement in this order:

**Phase 1 — Explainable matching**
- Verify the existing matching formula.
- Expose score breakdowns.
- Ensure calculations are consistent.

**Phase 2 — Career What-If Simulator**
- Build the interactive skill selection interface.
- Integrate the existing matching engine.
- Implement baseline versus simulated comparisons.
- Connect the result to the existing roadmap flow.

**Phase 3 — Forecast transparency**
- Audit available forecast metadata.
- Build reusable forecast information components.
- Integrate the components into AI Outlook and Occupations.
- Improve chart labels and methodology explanations.

**Phase 4 — Integration and quality assurance**
- Run the relevant automated tests.
- Verify end-to-end user flows.
- Check responsive layouts.
- Fix regressions.

Do not sacrifice the functionality of the main career journey to over-polish secondary elements.

---

# 9. Final Deliverables

After implementation, provide:

1. Summary of features implemented.
2. List of frontend files created or modified.
3. List of backend files created or modified.
4. Any database or API changes.
5. How the simulator reuses the existing matching engine.
6. How score breakdowns are calculated.
7. Which forecast metadata is available and which information is still missing.
8. Tests executed and their results.
9. Known limitations or incomplete functionality.

Clearly distinguish fully implemented functionality from placeholders.

**Final product goal:**

Jobee should evolve from a career recommendation platform into an interactive career intelligence platform.

Users should be able to:

- Understand what the future labour market might look like.
- Understand why Jobee recommends particular occupations.
- Experiment with acquiring new skills.
- See how those skills change their career opportunities.
- Take the next step towards acquiring and demonstrating those skills.

The three features should reinforce one another to create one coherent experience.

**Build the actual working implementation. Do not merely provide a design proposal or a list of suggested changes.**