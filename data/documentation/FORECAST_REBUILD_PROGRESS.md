# Forecast rebuild: progress log

Branch: `feat/ai-prediction`. The old branch `feat/ai-adoption-mc` is reference only and must stay unchanged.
Do not merge into `main` until the acceptance tests in `src/backend/forecasting/tests/` pass.
Spec: `data/documentation/AI_PREDICTION_ADOPTION.md`. Python: `src/backend/venv/Scripts/python.exe`.

Update this file after every step so a cut-off session can resume.

## Plan

| # | Step | Status |
|---|------|--------|
| 1 | Audit repo and old branch, reuse/discard assessment (`FORECAST_REBUILD.md`) | done (assessment written in step 9) |
| 2 | Point-in-time vintage store from Indeed git history (`forecasting/vintages.py`) | done |
| 3 | Source registry + data contracts for the three domains (`forecasting/registry.py`, `contracts.py`) | done |
| 4 | Skill-demand features with as-of cutoffs (`forecasting/features.py`) | done |
| 5 | Chronological splits, rolling-origin CV, locked holdout (`forecasting/evaluation.py`) | done |
| 6 | Baselines + ridge + LightGBM challenger, selection, conformal ranges (`forecasting/models.py`) | done |
| 7 | Source ablations, timestamped forecast, model registry with promotion rule (`forecasting/run.py`) | done |
| 8 | Tests: leakage, splits, contracts, BTOS guard, promotion (`forecasting/tests/`) | done (38 tests) |
| 9 | Docs: `FORECAST_REBUILD.md`, `STRUCTURE.md`, `SOURCES.md`, READMEs | done |

## Decisions so far

- First vertical slice = **skill demand**: monthly share of job postings mentioning AI terms, per country
  (Indeed AI Tracker). It is the only skill-demand series with multi-year history; Adzuna snapshots are
  only weeks old. BTOS is not an input to this model (it measures business AI use, a different target).
- Point-in-time data: every commit of `hiring-lab/ai-tracker` and `hiring-lab/job_postings_tracker` that
  changed a data file is treated as a published vintage (commit date = availability date).

## Log

- 2026-10-24: audit done; progress file created.
- 2026-10-24: vintages.py builds `data/processed/forecasting/{ai_share,postings}_vintages.csv` (35 AI vintages
  2024-04..2026-10, 76 postings vintages 2021-02..2026-10). Raw clones: `data/raw/vintages/{ait_full,jpt_full}`
  (partial clones; rebuild with `python -m forecasting.vintages` from `src/backend`). Findings: schemas changed 4x
  (day-first dates in early files; % change instead of index before mid-2021); AI-share revisions mean 0.39 pp,
  max 1.58 pp; publication lag 1 month (max 2).
- 2026-10-24: registry.py, contracts.py, features.py, models.py, evaluation.py, run.py written; first full run
  `python -m forecasting.run --skip-ingest` (~2 min) -> output/runs/<run_id>/, model_registry.json,
  latest_forecast.csv. 65 origins (27 real, 38 reconstructed), holdout from 2025-02 (18 origins).
  Holdout MASE vs naive: h1 drift 0.80, h3 pooled_mean 0.66, h6 naive chosen (selection) but drift better on holdout.
  NEXT: tests (step 8), then docs (step 9).
- 2026-10-24: tests written, 38 pass (`python -m pytest forecasting/tests` from src/backend). NEXT: docs (step 9).
- 2026-10-24: docs done: FORECAST_REBUILD.md (audit, reuse/discard, design, results, model card, ops),
  STRUCTURE.md §9, SOURCES.md vintage notes, data/README.md, src/backend/forecasting/README.md.
  First vertical slice complete. NEXT (not started): port Adzuna collector so snapshots accumulate; better h=6
  candidate (local linear trend); business adoption (BTOS by wording) and occupation adoption (RPS) models;
  serve latest_forecast.csv through /forecast. Do not merge to main until the merge gate in FORECAST_REBUILD.md §11.

## Phase 2 (started 2026-10-24): adoption targets

User: Adzuna stays on the free tier -> context only, never a model input. Next: business adoption (BTOS) and
occupation adoption (RPS), on a generic engine shared with skill demand.

| # | Step | Status |
|---|------|--------|
| 10 | Generic engine: TargetSpec, per-target output dirs (`output/<target>/`) | done |
| 11 | BTOS ingestion with publication dates, wording segments, SE, `.` vs `S` codes (`forecasting/btos.py`) | done |
| 12 | RPS ingestion with fetch-time snapshots, optional FRED_API_KEY vintages (`forecasting/rps.py`) | done |
| 13 | Business- and occupation-adoption targets, run, tests | done |
| 14 | Docs update (FORECAST_REBUILD.md, STRUCTURE.md) | done |

Facts: BTOS Q7/Q24 old wording 202319-202520 (54 fortnights), not asked 202521-202523 ("."), new wording
202524-202621 (24 fortnights; 10.0% -> 17.3% jump). Dates sheet has Publication Date per smpdt (also future
schedule rows: drop those after today). RPS: 9 quarters 2024Q3-2026Q3 per SOC group; no FRED key, so no
historical vintages (FRED csv ignores vintage_date).
- 2026-10-24: engine generalised (forecasting/targets/, TargetSpec); skill-demand results reproduced exactly
  (26,040 identical predictions). btos.py + targets/business_adoption.py, rps.py + targets/occupation_adoption.py.
  `python -m forecasting.run --skip-ingest` runs all three (~3 min); outputs in output/<target>/. "validated" now
  needs holdout MASE <= 0.95 (an RPS 0.03% "gain" had been labelled validated). 50 tests pass.
  Results: BTOS h6 naive (baseline), h13 ridge validated (MASE 0.89); RPS h1 pooled_mean not_demonstrably_better,
  h2 not promoted (insufficient history). NEXT: step 14 docs.
- 2026-10-24: step 14 docs done: FORECAST_REBUILD.md (status, reuse table, §8a BTOS, §8b RPS, validated margin,
  running, limitations), STRUCTURE.md §10 BTOS, §11 RPS, per-target forecast outputs; SOURCES.md §6 BTOS, §7 RPS,
  Adzuna not used; data/README.md; forecasting/README.md. Fixed SOC "00" -> 0 in latest_forecast. 50 tests pass.
  NEXT (not started): AI capability target (benchmark source, e.g. Epoch AI / METR); local-linear-trend candidate
  for long horizons; serve latest_forecast.csv via /forecast + UI; merge gate (fresh-clone test + second run).

## Phase 3 (started 2026-10-24): AI capability target

Source: Epoch AI benchmark_data.zip (CC-BY): epoch_capabilities_index/eci_scores.csv (270 models, ECI + CI +
release date) and metr_time_horizons_external.csv (105 rows, METR version column). ECI is refitted jointly, so
past scores change: point-in-time comes from Wayback Machine captures of https://epoch.ai/data/benchmark_data.zip
(32 captures 2025-03..2026-10; CDX: web.archive.org/cdx/search/cdx?url=epoch.ai/data/benchmark_data.zip).
METR's own repo (METR/eval-analysis-public) only has raw runs + 24 commits: not used.

| # | Step | Status |
|---|------|--------|
| 15 | `forecasting/capability.py`: monthly Wayback vintages + current download, extract ECI and METR per vintage | done |
| 16 | Engine: per-target value transform (logit / identity / log2), metric names without `_pp` | done |
| 17 | Local-linear-trend (Kalman) candidate; regime probabilities + Brier score vs climatology | done |
| 18 | targets/capability_eci.py (+ METR horizon if vintages allow), run, tests | done |
| 19 | Docs | todo |
- 2026-10-24: capability.py (17 monthly Epoch captures via Wayback, gzip-encoded ones decompressed, Last-Modified
  kept as availability); ECI only in 3 vintages (from 2026-09) -> stored, not modelled. targets/capability_metr.py:
  frontier METR 50% time horizon per suite version (v1.0 active 2025-06..2026-02, v1.1 from 2026-03), log2 scale,
  errors in doublings, 3-month measurement-lag cut. Engine: per-target Scale, metrics renamed (no _pp), forecast
  columns forecast/low/high/value_unit (old logs converted), local_trend (Kalman LLT) candidate for every target,
  regime probabilities + Brier, holdout_mase_vs_drift. FIRST_RECONSTRUCTED moved 2024-01 -> 2023-01 after first run
  (too few selection origins) - disclose in docs. 59 tests pass. NEXT: rerun all targets, then step 19 docs.
