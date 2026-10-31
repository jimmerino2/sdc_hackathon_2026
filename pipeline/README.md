# pipeline/

Builds every table in `data/processed/` and checks them. Column meanings are in `data/documentation/STRUCTURE.md`, sources in `data/documentation/SOURCES.md`.

## Run

```bash
pip install -r pipeline/requirements.txt
python pipeline/refresh.py            # pull the latest Indeed data and rebuild everything
python pipeline/refresh.py --no-pull  # rebuild offline from data/raw
python pipeline/refresh.py --geo GB   # switch the proxy country (crosswalk is validated for US and GB)
```

`refresh.py` runs, in order: signals, crosswalk, O\*NET, AI exposure, model table, Malaysia vacancies (DOSM), then cross-table checks, then rewrites `manifest.json`. It exits with an error if a check fails or the DOSM step fails. If `data/raw/onet/` is missing, the O\*NET step is skipped and the crosswalk is written with its job codes unverified (a warning is printed). If `data/raw/economic_index/` is missing, the AI exposure step is skipped and the old tables stay in place.

## Inputs (`data/raw/`, gitignored)

| Source | How it gets there |
|---|---|
| Indeed job postings and AI tracker (`jpt_repo/`, `ait_repo/`) | `refresh.py` clones or pulls them from GitHub |
| DOSM Job Market Insights (`dosm_jmi/jmi_q2_2026.xlsx`) | `build_jmi.py` downloads it if missing |
| O\*NET 31.0 text files (`onet/`) | **By hand.** Download `db_31_0_text.zip` from onetcenter.org (Database, text format) and unzip into `data/raw/onet/` |
| Anthropic Economic Index (`economic_index/aei_claude_ai_<release>.csv`, `aei_1p_api_<release>.csv`, about 300 MB) | **By hand.** Download both files from the `release_<date>/data/` folder of huggingface.co/datasets/Anthropic/EconomicIndex |

## Outputs (`data/processed/`)

| File | Built by | Notes |
|---|---|---|
| `signals.csv` | `build_signals.py` | series × geo × sector × month, with `source`, `as_of_date`, `is_partial`, `is_carried_forward` |
| `crosswalk.csv` | `build_crosswalk.py` from `crosswalk_source.csv` | job → Indeed sector, weights sum to 1, codes checked against O\*NET |
| `onet_roles.csv`, `onet_role_skills.csv` | `build_onet.py` | skills, knowledge and software for the jobs in the crosswalk |
| `ai_exposure.csv`, `ai_exposure_detail.csv` | `build_ai_exposure.py` | exposure is the percentile rank of observed work usage |
| `model_table_<geo>.csv` | `build_model_table.py` | leakage-safe monthly table (AI features computed before the join, 1-month publication lag, partial months dropped) |
| `my_vacancies.csv`, `onet_to_my_group.csv` | `build_jmi.py` from `jmi_group_map_source.csv` | Malaysia vacancies by occupation and industry. **Display only, not a model input** |
| `manifest.json` | `refresh.py` | row counts and as-of dates, for the app's "last updated" badge |

## Editing the job list

Edit `crosswalk_source.csv` (one row per job × sector; split weights when a job spans sectors). If you add or remove a job, also edit `jmi_group_map_source.csv` (job → Malaysian occupation group), then rerun `refresh.py`. The checks fail loudly on unknown sectors, weights that do not sum to 1, codes not in O\*NET, and job lists that differ between tables.

## Updating a source

- **Indeed:** nothing to do, `refresh.py` pulls.
- **Economic Index:** put the new release's two files in `data/raw/economic_index/` (the latest by name is used) and rerun.
- **DOSM JMI:** each release has a new download id. Update `SRC`, `DOWNLOAD_URL`, `SOURCE`, `SOURCE_URL` and `AS_OF` at the top of `build_jmi.py`, then rerun.

## Note on technology skills

Software skills (Python, Excel, ...) have no O\*NET Element ID, so they use `skill_id = "tech:<slug>"`. C, C# and C++ share the slug `tech:c` (see `STRUCTURE.md`).

## Syncing role forecasts from the app

The **Sync** button on the Roles page runs `sync_trends.py` through `POST /forecast/sync` when `FORECAST_REFRESH_ENABLED=true`. It pulls Indeed, rebuilds `signals.csv` and `model_table_US.csv`, retrains the role forecasts and rewrites `manifest.json`, in about 10 seconds. A failed run keeps the current data. If the pull fails, the last copy in `data/raw` is used.

After that, Sync forecasts worker adoption and business adoption again, side by side, if a table of theirs in `data/processed/forecasting` changed since the last run. That takes about 2.5 minutes. Nothing new is fetched for them, and a stale source or a failed run leaves the old forecast showing, which the page says. AI capability and skill trends are not part of it.

Run `refresh.py` or `sync_trends.py` once first, because Sync needs `data/raw` if the network fails.

To change one figure, edit its `value` in `data/processed/signals.csv` (keep one row per month) and press Sync. A change since the last sync is kept: nothing is pulled, the forecasts are retrained on it and the page says so. Press Sync again to pull and put the source's value back.

To rewind the data, run `python pipeline/sync_trends.py --no-pull --until 2026-06`. Pressing Sync brings it back up to date.

The rewind and the edits are not written to the Supabase table `forecast_signals`, which the quarter picker's retrain reads.
