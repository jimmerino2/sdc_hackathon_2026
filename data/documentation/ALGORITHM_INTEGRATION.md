# Algorithm Integration

> **Temporary handoff note.** Once the algorithm owner has read the data in and the checklist at the bottom is done, **delete this file entirely**. Anything lasting belongs in `STRUCTURE.md` (the tables) or `SOURCES.md` (the sources), so move it there first.

For whoever builds the LightGBM model and the Monte Carlo scenarios. This note covers the **data side only**: what is ready, how it joins, and what to watch for. How to model it (features, target, validation, scenario design) is your call. Column meanings are in `STRUCTURE.md`.

## What the data layer gives you

Everything is rebuilt from source with `python pipeline/refresh.py` (see `pipeline/README.md`). Tables are in `data/processed/`. Every table was checked for matching job lists and duplicate keys when it was built.

| Table | Rows | Use it for |
| ----- | ---- | ---------- |
| `model_table_US.csv` | 3,760 | The forecasting worksheet: one row per US sector and month, with lags and a 12-month-ahead target |
| `signals.csv` | 23,118 | Raw monthly history for 6 countries (postings) and 9 countries (AI share), if you want features the model table doesn't have |
| `crosswalk.csv` | 51 | Turns a sector forecast into a job forecast (job → sector with weights) |
| `ai_exposure.csv` | 46 | How much AI is already used for each job (0–1) |
| `onet_roles.csv`, `onet_role_skills.csv` | 46 / 4,548 | Job list and skills; not needed by the model |
| `my_vacancies.csv`, `onet_to_my_group.csv` | 3,969 / 46 | Malaysia context. **Not a model input** (see below) |

## How the tables join

```
model_table_US.sector
        │  = crosswalk.indeed_sector
        ▼
crosswalk.onet_code  ──►  ai_exposure.onet_code   (AI exposure per job)
        │             ──►  onet_roles.onet_code    (job name, job zone)
        └─ weight (sums to 1 per job)              (a job can span two sectors)
```

To get a job-level forecast: take each sector's forecast and weight it by `crosswalk.weight`, summed per `onet_code`.

## What is in `model_table_US.csv`

- 47 sectors, months 2020-02 to 2026-09. Partial months were already removed, so the latest row is 2026-09.
- The target `target_index_12m_ahead` is the sector index 12 months later. It is blank for the latest 12 months per sector (564 rows blank, so 3,196 usable). The last month with a known target is 2025-09.
- Features are already lagged to avoid leakage: `index_lag1/3/12`, `index_yoy`, `national_lag1`, `ai_share_lag1`, `ai_chg3_lag1`, `ai_chg12_lag1`. The AI and national values use last month's data on purpose (1-month publication lag). Do not re-join `signals.csv` without keeping that lag.
- `period` is `pandemic` (before 2022-01) or `post`. Use it to filter or as a flag.
- The first 12 months of each sector have no `index_lag12` or `index_yoy` (blank), and the first month has no `index_lag1`. Handle the blanks, or start from 2021-02.

## Things to know before you model

1. **The AI features are national, not per sector.** `ai_share_lag1` and its changes are the same for every sector in a given month. Sector differences come only from the sector's own history.
2. **AI exposure is not in the model table.** It sits in `ai_exposure.csv`, per job. If scenarios should hit exposed jobs harder, that link has to be defined by you, and stated as an assumption if it isn't learned from data.
3. **The AI share moved a lot only recently.** Check how much your model actually responds to it before relying on Slow / Baseline / Rapid scenarios to look different.
4. **`ai_carried_forward` is always `False`** in the model table, so it carries no information.
5. **Only 36 of 47 sectors map to a job.** These 11 sectors have no job in `crosswalk.csv`: Architecture, Aviation, Cleaning & Sanitation, Dental, Hospitality & Tourism, Management, Mechanical Engineering, Medical Technician, Physicians & Surgeons, Sales, Social Science. You can still train on them, but no job forecast comes from them.
6. **The US stands in for Malaysia.** `manifest.json` has `is_proxy_geo: true`. Say so wherever forecasts are shown.
7. **Do not train on `my_vacancies.csv`.** It is a raw count (not an index), and the total jumps about 2x in 2021-Q3 and 2025-Q3 because DOSM's website coverage changed. It is for display only.
8. **Jobs with weak AI data.** Wind Turbine Service Technicians has `exposure = 0` as a fallback (no observed usage). Security Guards and Electricians sit at the tied floor (0.117), and all three have blank `automation_share`. `ai_exposure.csv` also flags noisy shares via `ai_exposure_detail.low_sample`.
9. **Small sample.** 3,196 usable rows come from 47 series, and rows within a sector overlap heavily, so the information is much less than the row count suggests.

## What we need back from you

The app reads your **results**, not the model. Agree this with the app/data owner:

1. **The output table.** `SUPABASE_INTEGRATION.md` proposes a `forecast_output` table (sector, scenario, horizon, predicted index, low/high range, as-of date). This is a proposal only; change it to match what the model actually produces.
2. **Scenario names.** `SOURCES.md` calls them Slow / Baseline / Rapid AI. Confirm.
3. **Job-level numbers or sector-level?** Either you apply the crosswalk weights, or the data side does it. Decide who.
4. **A reproducible run.** Record the data as-of dates (from `manifest.json`), the settings and the random seed with each output, so a result can be tied to the data behind it.
5. **Any new feature you need** from the data layer. Tell the data owner; new columns belong in `build_model_table.py`.

## Refreshing

`python pipeline/refresh.py` rebuilds all tables from the latest sources and rewrites `manifest.json`. Indeed updates weekly (postings) and monthly (AI share). After a refresh, retrain or at least recheck; the latest month and the last known target month will move forward.

## Checklist

1. Read `model_table_US.csv` and confirm the columns match what your code expects.
2. Decide the target and validation approach (not covered here).
3. Agree the output table with the app/data owner, and update `SUPABASE_INTEGRATION.md` and `STRUCTURE.md` to match.
4. Run a refresh and check your code still works on the new data.
5. Move anything still useful into `STRUCTURE.md`, then **delete this file**.
