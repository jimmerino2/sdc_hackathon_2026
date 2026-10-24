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
| `models.py` | Methods: persistence, 12-month mean, shrink, damped trend, pooled ridge, blend |
| `backtest.py` | Rolling-origin backtest, train / validation / test split by target month, selection, gate, intervals, published forecast |
| `adoption.py` | Worker usage (measured), employer-side proxy and task exposure, kept separate |
| `run.py` | CLI: ingest → build → evaluate → promote |

## Definitions

- **Eligible ad:** not a duplicate (same author in the same thread, the same opening text in the same month, or the same Adzuna id), and has a description (≥ 150 characters for HN; ≥ 60 for an Adzuna snippet).
- **Skill-demand share** for (month, country, occupation, skill) = ads naming the skill ÷ eligible ads classified into that occupation and country. Counts are kept next to every share.
- **Forecast target:** the share pooled over the 3 months ending at origin + h, for h = 3, 6 and 12 months.
- **Split:** by target month.
  - The last 12 complete months are the test period. It is untouched until scoring.
  - The 12 months before them are validation, which chooses the method per horizon.
  - Everything earlier is training.
- **Gate:** if the chosen method's test error is worse than persistence's, persistence is served (`baseline_retained`).
- **Intervals:** the 10th to 90th percentile of past errors, grouped by forecast level and evidence. They are checked on the test period.

## API

The backend serves these from `app/occupational/`. They are read-only and pick up new runs without a restart.

- `GET /occupational/meta`
- `GET /occupational/skills?country=&occupation=&h=[&origin=]`
- `GET /occupational/skills/{skill_id}?country=&occupation=`
- `GET /occupational/emerging?country=&occupation=`
- `GET /occupational/adoption?occupation=`
- `GET /occupational/evaluation`

The frontend page is `src/frontend/src/views/OccupationsView.vue`, route `/occupations` ("Occupations" in the sidebar). `?tab=emerging|adoption|method` opens a section directly.

## Adding an occupation or sector

1. Add an entry to `data/occupational_forecasting/taxonomy/occupations.json`. It needs title patterns, O\*NET codes, an Adzuna search term and Stack Overflow survey dev types.
2. Rerun the pipeline.

Countries are added the same way, in `geo.json`. Skills can be added to `curated_skills.csv`, or are discovered from ad text and proposed in the registry.
