# Supabase Integration

> **Temporary handoff note.** Once the data is in the app (or you've decided to bundle it) and the checklist at the bottom is done, **delete this file entirely**. Anything lasting belongs in `STRUCTURE.md` or `SOURCES.md`, so move it there first.

Plan for moving our data into Supabase once the app is built. Column meanings are in `STRUCTURE.md`; sources in `SOURCES.md`.

Status: **planned, nothing built yet.** The screen roles below come from `SOURCES.md`; check them against the actual app before you build.

## Principle

Put in Supabase only what the **app reads at runtime**. Training data stays as files. Small enough to bundle? Then Supabase is optional (see the last section).

## What goes where

### Load into Supabase

| Table                      | Rows  | Why the app needs it                                      |
| -------------------------- | ----- | --------------------------------------------------------- |
| `onet_roles`               | 46    | Role list and descriptions                                |
| `onet_role_skills`         | 4,548 | Skills gap and reskilling roadmap (Screens 4–5)           |
| `ai_exposure`              | 46    | Y-axis of the quadrant (Screen 4)                         |
| `crosswalk`                | 51    | Turns a role into its sector's demand trend               |
| `my_vacancies`             | 3,969 | Malaysia context panel (**display only**)                 |
| `onet_to_my_group`         | 46    | Maps a role to a Malaysian occupation group               |
| `forecast_output` (**new**) | tbd  | Demand forecast shown on Screen 3                         |

Optional: `ai_exposure_detail` (746 rows), only if the app shows occupations beyond our 46.

### Keep as files (do not load)

| File                 | Why                                                                                    |
| -------------------- | -------------------------------------------------------------------------------------- |
| `signals.csv`        | Raw trend history. Training input only (23,118 rows)                                   |
| `model_table_US.csv` | Forecasting worksheet. Training input only (3,760 rows)                                |
| `manifest.json`      | Read it at build time, or copy its as-of dates into a small `data_sources` table      |

## The new `forecast_output` table

The model runs offline. The app should show its **results**, not re-run it or read the training rows. This table does not exist yet. **The columns below are a proposal, not an agreement.** The algorithm owner decides what the model produces (see `ALGORITHM_INTEGRATION.md`); change this table to match, then record the final version in `STRUCTURE.md`. Proposed shape:

| Column       | Type | Notes                                         |
| ------------ | ---- | --------------------------------------------- |
| `sector`     | text | Indeed sector name, joins to `crosswalk.indeed_sector` |
| `scenario`   | text | Slow / Baseline / Rapid AI (see `SOURCES.md`) |
| `horizon_m`  | int  | Months ahead (12 for the current model)       |
| `index_pred` | real | Predicted postings index                      |
| `index_low`, `index_high` | real | Range from the Monte Carlo runs  |
| `as_of_date` | date | Date of the data the model was trained on     |

## Rules when loading

1. **Keep the provenance columns.** `source`, `source_url`, `as_of_date` (and `is_partial` on `my_vacancies`) go into Supabase unchanged. The app's "last updated" badge needs them.
2. **Primary keys / joins.**
   - `onet_roles`, `ai_exposure`, `onet_to_my_group`: `onet_code`.
   - `onet_role_skills`: (`onet_code`, `skill_id`). There are no duplicates today.
   - `crosswalk`: (`onet_code`, `indeed_sector`). Weights sum to 1 per job.
   - `my_vacancies`: (`freq`, `period`, `group_type`, `group`).
3. **Blank means null.** `ai_exposure.automation_share` and `augmentation_share` are blank for 3 jobs (Wind Turbine Service Technicians, Security Guards, Electricians). `onet_role_skills.level` is blank for all software rows. Load blanks as `NULL` and make the app handle them.
4. **Types.** Dates as `date`, flags as `boolean`, `onet_code` as `text` (it has a dot and leading zeros, e.g. `11-2021.00`).
5. **Access.** All of these are public reference data. Enable Row Level Security with a read-only policy for the anon key. Do not give the anon key write access.

## Known data issues the app must handle

Full detail in `STRUCTURE.md`. The ones that affect the app:

- **`my_vacancies` is display-only.** It is a raw count, not an index, and the total jumps about 2x in 2021-Q3 and again in 2025-Q3 because DOSM's website coverage changed. Never use it in a calculation or a chart that compares across those quarters.
- **Elementary Occupations is 0 before 2025** in `my_vacancies`, so the Freight Laborers role has no early history.
- **Wind Turbine Service Technicians (`49-9081.00`)** has `exposure = 0.000` because it is missing from the Anthropic Economic Index data (a fallback, not a real rank). It is also absent from `ai_exposure_detail`. Show it as "no data" rather than "no AI exposure".
- **Security Guards and Electricians** both have `exposure = 0.117`, the tied floor for occupations with no observed usage.
- **The US stands in for Malaysia** in the forecast (`is_proxy_geo: true` in `manifest.json`). The UI should say so.
- **`my_vacancies` 2026 is partial** (January to June).

## Refreshing

- Rebuild the CSVs, then replace the Supabase rows. Do not hand-edit rows in Supabase.
- Run `python pipeline/refresh.py`. It rebuilds every table, runs cross-table checks, and rewrites `manifest.json`. Inputs and options are in `pipeline/README.md`.
- DOSM publishes JMI quarterly (next release 17 Nov 2026). Update `SRC`, `DOWNLOAD_URL`, `SOURCE_URL` and `AS_OF` at the top of `pipeline/build_jmi.py` (the new release has a new download id), delete the old workbook in `data/raw/dosm_jmi/`, and re-run `refresh.py`. The workbook layout can change between releases, so spot-check the output.
- Indeed postings are refreshed weekly and the Indeed AI Tracker monthly (see `SOURCES.md`).

## Do you need Supabase at all?

Not strictly. The tables are small (the largest is 4,548 rows), so the app can bundle them as CSV or JSON.

- **Use Supabase** if you want data to update without a redeploy, or the app needs to save anything (a resume, a user's results).
- **Skip it** if the app is read-only and the demo data is fixed. Bundle the tables and keep the same provenance columns.

## Next steps for the PIC

1. Confirm which screens read which tables.
2. Decide Supabase vs bundled files.
3. Define `forecast_output` from what the model actually produces, then add it to `STRUCTURE.md`.
4. Create the tables, load the CSVs, and set the read-only policy.
5. Check the "last updated" badge reads `as_of_date`.
6. Confirm the DOSM licence (not stated on the release page) before the demo.
7. Move anything still useful into `STRUCTURE.md` or `SOURCES.md`, then **delete this file**.
