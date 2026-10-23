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
| 3 | Source registry + data contracts for the three domains (`forecasting/registry.py`, `contracts.py`) | todo |
| 4 | Skill-demand features with as-of cutoffs (`forecasting/features.py`) | todo |
| 5 | Chronological splits, rolling-origin CV, locked holdout (`forecasting/evaluation.py`) | todo |
| 6 | Baselines + ridge + LightGBM challenger, selection, conformal ranges (`forecasting/models.py`) | todo |
| 7 | Source ablations, timestamped forecast, model registry with promotion rule (`forecasting/run.py`) | todo |
| 8 | Tests: leakage, splits, contracts, BTOS guard, promotion (`forecasting/tests/`) | todo |
| 9 | Docs: `FORECAST_REBUILD.md`, `STRUCTURE.md`, `SOURCES.md`, READMEs | todo |

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
