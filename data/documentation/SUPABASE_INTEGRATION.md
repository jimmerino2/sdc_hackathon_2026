# Supabase Integration: forecast_output

> **Temporary handoff note.** Once `forecast_output` is in Supabase and the checklist at the bottom is done, **delete this file entirely**. Anything lasting belongs in `STRUCTURE.md` or `SOURCES.md`, so move it there first.

The reference tables (roles, skills, exposure, crosswalk, Malaysia vacancies) are already set up. Schema, loader and setup steps are in `migrations/README.md`. This note covers what is left: **getting the model's results into Supabase** as a new `forecast_output` table. For the model side (inputs, joins, things to watch) see `ALGORITHM_INTEGRATION.md`.

## Principle

The model runs offline. The app shows its **results**, not the model and not the training rows. Training data (`signals.csv`, `model_table_US.csv`) stays as files and is not loaded.

## Proposed table: `forecast_output`

**This is a proposal, not an agreement.** The algorithm owner decides what the model produces. Change the table to match, then record the final version in `STRUCTURE.md`.

| Column       | Type | Notes                                         |
| ------------ | ---- | --------------------------------------------- |
| `sector`     | text | Indeed sector name, joins to `crosswalk.indeed_sector` |
| `scenario`   | text | Slow / Baseline / Rapid AI (see `SOURCES.md`) |
| `horizon_m`  | int  | Months ahead (12 for the current model)       |
| `index_pred` | real | Predicted postings index                      |
| `index_low`, `index_high` | real | Range from the Monte Carlo runs  |
| `as_of_date` | date | Date of the data the model was trained on     |

Open questions to settle with the algorithm owner:

- **Sector-level or job-level rows?** Either the model output is per sector and the app applies `crosswalk.weight` (summed per `onet_code`), or the data side does it and loads per-job rows. Decide who does it.
- **Scenario names.** Confirm Slow / Baseline / Rapid AI.
- **Reproducibility.** Store the data as-of dates (from `manifest.json`), the settings and the random seed with each output, so a result can be tied to the data behind it. This may mean extra columns or a small `data_sources` table.
- **Sectors with no job.** 11 of the 47 sectors have no job in `crosswalk.csv`, so they can be forecast but never shown per job.

## Rules when loading

1. **Keep `as_of_date`.** The app's "last updated" badge reads it.
2. **Primary key.** Probably (`sector`, `scenario`, `horizon_m`); confirm once the columns are final.
3. **Blank means null.** Load blanks as `NULL`, and make the app handle them.
4. **Access.** Enable Row Level Security with a read-only policy for the anon key, as the other tables do. Do not give the anon key write access.
5. **Say the US stands in for Malaysia.** `manifest.json` has `is_proxy_geo: true`, and the UI should say so wherever forecasts are shown.

## Next steps for the PIC

1. Agree the final `forecast_output` columns with the algorithm owner (the questions above).
2. Add the table as `migrations/0002_forecast_output.sql`, with RLS and the read-only policy.
3. Add a `forecast_output` entry to `TABLES` in `pipeline/load_supabase.py`, and load the model's output file.
4. Record the final columns in `STRUCTURE.md`.
5. Check the "last updated" badge reads `as_of_date`.
6. Update `ALGORITHM_INTEGRATION.md` to match, or delete it once the algorithm owner is done.
7. Move anything still useful into `STRUCTURE.md` or `SOURCES.md`, then **delete this file**.
