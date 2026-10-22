# pipeline/

Builds every table in `data/processed/` and checks them. Column meanings are in `data/documentation/STRUCTURE.md`, sources in `data/documentation/SOURCES.md`.

## Run

```bash
pip install -r pipeline/requirements.txt
python pipeline/refresh.py            # pull the latest Indeed data and rebuild everything
python pipeline/refresh.py --no-pull  # rebuild offline from data/raw
python pipeline/refresh.py --geo GB   # switch the proxy country (crosswalk is validated for US and GB)
```

`refresh.py` runs, in order: signals, crosswalk, O\*NET, AI exposure, model table, Malaysia vacancies (DOSM), AI adoption (RPS), business AI use (BTOS), then cross-table checks, then rewrites `manifest.json`. It exits with an error if a check fails or one of the three download steps (DOSM, RPS, BTOS) fails; a failed download leaves the old table in place. If `data/raw/onet/` is missing, the O\*NET step is skipped and the crosswalk is written with its job codes unverified (a warning is printed). If `data/raw/economic_index/` is missing, the AI exposure step is skipped and the old tables stay in place.

## Inputs (`data/raw/`, gitignored)

| Source | How it gets there |
|---|---|
| Indeed job postings and AI tracker (`jpt_repo/`, `ait_repo/`) | `refresh.py` clones or pulls them from GitHub |
| DOSM Job Market Insights (`dosm_jmi/jmi_q2_2026.xlsx`) | `build_jmi.py` downloads it if missing |
| Real-Time Population Survey (`rps/fred/*.csv`, `rps/occupation_index.xlsx`) | `build_ai_adoption.py` downloads them if missing. Delete `data/raw/rps/` to fetch a new quarter |
| Census BTOS (`btos/Sector.xlsx`, `National.xlsx`, `AI Core Questions.xlsx`) | `build_btos_ai.py` downloads them if missing. Delete `data/raw/btos/` to fetch the latest fortnight |
| Adzuna responses (`adzuna/<date>/*.json`) | `collect_adzuna.py` caches each day's calls here |
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
| `ai_adoption.csv`, `ai_adoption_jobs.csv` | `build_ai_adoption.py` | AI adoption per SOC major group and quarter, and per job |
| `btos_ai.csv` | `build_btos_ai.py` from `btos_sector_soc_map.csv` (map) | business AI use per sector and fortnight, two question wordings kept apart |
| `news_articles.csv` | `collect_news.py` from `news_sources.csv` (trusted domains) | AI-adoption headlines, appended weekly |
| `adzuna_ai_share.csv`, `skill_demand.csv` | `collect_adzuna.py` from `adzuna_category_map.csv` | weekly AI share of live ads per category, and skill ad counts per job |
| `manifest.json` | `refresh.py` | row counts and as-of dates, for the app's "last updated" badge |

## Editing the job list

Edit `crosswalk_source.csv` (one row per job × sector; split weights when a job spans sectors). If you add or remove a job, also edit `jmi_group_map_source.csv` (job → Malaysian occupation group), then rerun `refresh.py`. The checks fail loudly on unknown sectors, weights that do not sum to 1, codes not in O\*NET, and job lists that differ between tables.

## Updating a source

- **Indeed:** nothing to do, `refresh.py` pulls.
- **Economic Index:** put the new release's two files in `data/raw/economic_index/` (the latest by name is used) and rerun.
- **AI adoption scenarios:** see the schedule in `data/documentation/AI_ADOPTION_PLAN.md`. Weekly: `collect_news.py`, `collect_adzuna.py`, then `python src/backend/ml/ai_signal_score.py`. Quarterly (new FRED quarter): delete `data/raw/rps/`, rerun `refresh.py`, then `python src/backend/ml/ai_adoption_mc.py`.
- **DOSM JMI:** each release has a new download id. Update `SRC`, `DOWNLOAD_URL`, `SOURCE`, `SOURCE_URL` and `AS_OF` at the top of `build_jmi.py`, then rerun.

## Note on technology skills

Software skills (Python, Excel, ...) have no O\*NET Element ID, so they use `skill_id = "tech:<slug>"`. C, C# and C++ share the slug `tech:c` (see `STRUCTURE.md`).
