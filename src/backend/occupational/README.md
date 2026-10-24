# occupational

Occupational forecasting: skill demand, emerging skills and AI adoption per **country × occupation**, starting with four software and technology occupations (Software Engineer, AI/ML Engineer, Data Scientist, Data Analyst).

It is independent of `forecasting/` (the industry and country-level targets on the AI outlook tab). It shares no features, targets, models or predictions with it, and uses no Supabase. Everything it reads and writes is under `data/occupational_forecasting/` (see that folder's README).

## Run

From `src/backend`, using the backend venv:

```
python -m occupational.run                # fetch new data (HN threads, O*NET, survey files), then build everything
python -m occupational.run --no-pull      # local raw cache only
python -m occupational.run --adzuna       # also take today's Adzuna snapshot (16 calls of the shared 20 a day)
python -m pytest occupational/tests       # offline tests on synthetic data, no credentials needed
```

- **First run:** about 12 minutes. It downloads around 500 MB (HN 38 MB, Stack Overflow survey files 460 MB, O*NET 8 MB) into `raw/`, which is gitignored.
- **Later runs:** about 6 minutes. Known-skill matches are cached per ad, and finished months are never fetched again.
- **Schedule:** run weekly. Add `--adzuna` once a week so the dated Adzuna snapshots build up.

A run that fails, or produces no forecast, is logged to `runs/run_log.jsonl` and leaves `latest/` unchanged. An empty table never overwrites a non-empty one.

## Sources

| Source | Used for | History |
| --- | --- | --- |
| HN "Ask HN: Who is hiring?" (hn.algolia.com) | Skill-demand series and emerging-skill discovery | Monthly since 2014-01: 152 threads, 85k posts |
| Adzuna API (free tier) | Dated live-ad snapshots, shown as a cross-check only | From 2026-10-23 onward. The API has no past ads, so nothing is back-filled |
| PyPI downloads (ClickPy, a public mirror of the PyPI BigQuery logs) and npm download counts | Package-adoption evidence for the emerging-signals view (`signals.py`), never an input to the job-ad baseline | PyPI from 2016-01, npm from 2015-12; monthly, one query (PyPI) and about 8 calls per package (npm) |
| Stack Overflow Developer Survey microdata | Worker AI usage per occupation and country (measured) | 2023, 2024, 2025 |
| O\*NET 31.0 software skills | Whether a skill is covered by O\*NET | Reference only |
| RPS (`data/processed/forecasting/rps_observations.csv`) | Context: SOC group 15 worker GenAI use | Raw observations, not the industry models' predictions |
| Anthropic Economic Index (`data/processed/ai_exposure.csv`) | Task exposure, labelled exposure | Reference only |

## Pipeline

| Module | Role |
| --- | --- |
| `store.py` | All file access: paths, atomic writes, last-good protection. The one module to replace for a database |
| `taxonomy.py` | Occupations, countries and skill vocabulary (`taxonomy/*.json`, `curated_skills.csv`), text cleaning, spelling keys, O\*NET coverage |
| `sources/` | `hn.py`, `adzuna.py`, `so_survey.py`, `onet.py`: fetch to `raw/` and return raw rows plus a health record |
| `normalize.py` | One row per ad: occupation(s), country(ies), duplicates, eligibility, known skills (cached) |
| `emerging.py` | Candidate terms from ad text, evidence windows, versioned skill registry, withheld-term back-check |
| `demand.py` | Panel: eligible ads (denominator) and ads naming each skill, per month × country × occupation |
| `models.py` | Methods: persistence, 12-month mean, shrink, trend, pooled ridge, blend, and the tuned ewma (recent level), dtrend (shrunk damped trend) and adaptive (recent level plus tested trend); the shared direction label |
| `backtest.py` | Parameter tuning on training targets, rolling-origin backtest, train / validation / test split by target month, multi-metric selection, gate, intervals, published forecast |
| `sources/packages.py` | Monthly package downloads for the indicators in `taxonomy/skill_signals.json`, cached in `raw/packages/` (tracked copy: `datasets/package_downloads.csv`) |
| `signals.py` | Skill-emergence engine: adoption and related-skill evidence, a control (own-series) and a hybrid correction to the baseline, a rise radar, their backtests, and the published evidence table |
| `adoption.py` | Worker usage (measured), employer-side proxy and task exposure, kept separate |
| `run.py` | CLI: ingest → build → evaluate → promote |

## Definitions

- **Eligible ad:** not a duplicate (same author in the same thread, the same opening text in the same month, or the same Adzuna id), and has a description (≥ 150 characters for HN; ≥ 60 for an Adzuna snippet).
- **Skill-demand share** for (month, country, occupation, skill) = ads naming the skill ÷ eligible ads classified into that occupation and country. Counts are kept next to every share.
- **Scope:** occupations in the `software_technology` sector of `occupations.json` (all four today).
- **Forecast target:** the share pooled over the 3 months ending at origin + h (ads naming the skill ÷ eligible ads, summed over those months), for h = 3, 6 and 12 months. Months with no ads in a cell are missing and carry no weight; a month with ads but no mention is an observed zero.
- **Split:** by target month.
  - The last 12 complete months are the test period. It is untouched until scoring.
  - The 12 months before them are validation, which chooses the method per horizon.
  - Everything earlier is training. Its last 48 months of targets tune the parameters of ewma, dtrend and adaptive (grid search on the selection score).
- **Direction:** forecast minus the last 3 months' share at the origin (the baseline), in share points. Rising or falling at ±1 pp or more, otherwise flat (about stable). The backtest and the published forecast use the same function (`models.direction`). A realised move is *material* at a threshold (1 or 2 pp) and *significant* when it is also beyond sampling noise (z ≥ 1.96).
- **Selection:** a composite score against persistence on validation: overall MAE (0.35), MAE on significant 2 pp moves (0.25), direction on those moves (0.2), bias on rising and falling skills (0.1), worst origin quarter (0.1). A method must be no worse than persistence overall and within 5% of the most accurate method's MAE. A simpler method is kept unless the best beats it in at least 80% of 200 paired bootstrap resamples of series. `evaluation.json` also records the winner under other weightings.
- **Gate:** if the chosen method's test error is worse than persistence's, persistence is served (`baseline_retained`).
- **Emerging signals:** package adoption (downloads relative to a skill-neutral reference basket, 3-month sums, ≥ 30k downloads in both windows compared) and related-skill demand (pooled over every IT cell, the skill itself excluded). A hybrid correction is published as `adjusted_forecast` only if it beats both the baseline and an own-series control on validation (series bootstrap, 80%) and is no worse on test; rise alerts only if they beat own-series alerts on average precision the same way. Otherwise the page shows the evidence and a scenario labelled as such.
- **Intervals:** the 10th to 90th percentile of past errors, grouped by forecast level and evidence. They are checked on the test period, overall, on significant moves and by evidence band.

## API

The backend serves these from `app/occupational/`. They are read-only and pick up new runs without a restart.

- `GET /occupational/meta`
- `GET /occupational/skills?country=&occupation=&h=[&origin=]`
- `GET /occupational/skills/{skill_id}?country=&occupation=`
- `GET /occupational/emerging?country=&occupation=`
- `GET /occupational/adoption?occupation=`
- `GET /occupational/signals?country=&occupation=`: the baseline next to its emerging-skill evidence, whether an adjusted forecast or rise alerts passed validation, and each indicator's source, freshness and quality
- `GET /occupational/evaluation`

The frontend page is `src/frontend/src/views/OccupationsView.vue`, route `/occupations` ("Occupations" in the sidebar). `?tab=emerging|adoption|method` opens a section directly.

## Adding an occupation or sector

1. Add an entry to `data/occupational_forecasting/taxonomy/occupations.json`. It needs title patterns, O\*NET codes, an Adzuna search term and Stack Overflow survey dev types.
2. Rerun the pipeline.

Countries are added the same way, in `geo.json`. Skills can be added to `curated_skills.csv`, or are discovered from ad text and proposed in the registry.
