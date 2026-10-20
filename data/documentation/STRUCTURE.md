# Data Structure

All tables live in `data/processed/` and are rebuilt with `python pipeline/refresh.py` (see `pipeline/README.md` for inputs and options).

## Sources

| Source                   | Dataset                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| Indeed Postings          | Indeed Job Postings Index — https://github.com/hiring-lab/job_postings_tracker                          |
| Indeed AI Tracker        | Indeed AI Tracker — https://github.com/hiring-lab/ai-tracker                                            |
| Anthropic Economic Index | Anthropic Economic Index (release 2026-06-26) — https://huggingface.co/datasets/Anthropic/EconomicIndex |
| O\*NET                   | O\*NET 31.0 Database — https://www.onetcenter.org/database.html                                         |
| DOSM JMI                 | DOSM Job Market Insights, Q2 2026 — https://www.dosm.gov.my/portal-main/release-content/big-data-analytics-job-market-insights-q22026 |
| Ours                     | Computed in our pipeline, or hand-written by the team                                                   |

## What each table is for

| Table                  | Function                                                                                                                    |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `signals.csv`          | **The raw trend history:** how job ads and AI mentions moved, month by month                                                |
| `model_table_US.csv`   | **The forecasting worksheet:** the same trends rearranged so a model can learn "given the past, what happens in 12 months?" |
| `crosswalk.csv`        | **The translator:** turns a sector's trend into a job's trend (Indeed speaks sectors, users speak jobs)                     |
| `onet_roles.csv`       | **The job list:** the 46 jobs the app knows about, with a description and how much preparation each needs                   |
| `onet_role_skills.csv` | **The job requirements:** for each job, which skills matter, how much, and at what level                                    |
| `ai_exposure.csv`      | **The AI meter:** how much AI is already used for each job's work                                                           |
| `my_vacancies.csv`     | **The Malaysia context:** online job vacancies in Malaysia by occupation group and industry (display only, not a model input) |
| `onet_to_my_group.csv` | **The Malaysia translator:** which Malaysian occupation group each of the 46 jobs belongs to                                |

---

## 1. `signals.csv`

One row per **series × country × sector × month**. 23,118 rows. Built by `pipeline/build_signals.py`.

| Column               | Source                              | Type      | Derived from                                                                                                                                                                                                         |
| -------------------- | ----------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `series`             | Ours                                | text      | Label we assign: `job_postings_index` for Indeed Postings rows, `ai_postings_share` for Indeed AI Tracker rows                                                                                                       |
| `geo`                | Indeed Postings + Indeed AI Tracker | text      | Country code (`jobcountry` in both Indeed files). 6 countries for postings (US, GB, AU, CA, DE, FR), 9 for AI share                                                                                                  |
| `sector`             | Indeed Postings                     | text      | Indeed `display_name` (e.g. "Data & Analytics"). Blank for national totals and for all Indeed AI Tracker rows (AI share is country-level only)                                                                       |
| `month`              | Ours                                | `YYYY-MM` | Daily `date` grouped into calendar months                                                                                                                                                                            |
| `value`              | Indeed Postings + Indeed AI Tracker | number    | Monthly **mean** of the daily value. Indeed Postings `indeed_job_postings_index` (1 Feb 2020 = 100, seasonally adjusted, "total postings" only); Indeed AI Tracker `AI_share_postings` (% of postings mentioning AI) |
| `source`             | Ours                                | text      | Dataset name and licence, written by us                                                                                                                                                                              |
| `source_url`         | Ours                                | url       | Link to the source repo                                                                                                                                                                                              |
| `as_of_date`         | Indeed Postings + Indeed AI Tracker | date      | Latest daily `date` in the source file (postings 2026-10-09, AI share 2026-09-30)                                                                                                                                    |
| `is_partial`         | Ours                                | bool      | `True` if the month has fewer days of data than calendar days (the current month)                                                                                                                                    |
| `is_carried_forward` | Ours                                | bool      | `True` if the AI share was copied from the previous month because Indeed hasn't published it yet                                                                                                                     |

---

## 2. `model_table_US.csv`

One row per **sector × month** for the US. 3,760 rows (47 sectors, 2020-02 to 2026-09). Built by `pipeline/build_model_table.py` from `signals.csv`. Partial months are removed.

Note: US was chosen primarily to fit with our other sources, as the Indeed dataset is primarily for the US market.

| Column                   | Source                   | Type      | Derived from                                                                                                              |
| ------------------------ | ------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------- |
| `sector`                 | Indeed Postings          | text      | Indeed sector name                                                                                                        |
| `month`                  | Ours                     | `YYYY-MM` | From `signals.csv`                                                                                                        |
| `index`                  | Indeed Postings          | number    | Sector postings index this month                                                                                          |
| `index_lag1`             | Indeed Postings + Ours   | number    | `index` 1 month earlier (same sector)                                                                                     |
| `index_lag3`             | Indeed Postings + Ours   | number    | `index` 3 months earlier                                                                                                  |
| `index_lag12`            | Indeed Postings + Ours   | number    | `index` 12 months earlier                                                                                                 |
| `index_yoy`              | Indeed Postings + Ours   | number    | Year-on-year change: `index / index_lag12 − 1`                                                                            |
| `national_lag1`          | Indeed Postings + Ours   | number    | US national postings index, **last** month (1-month publication lag)                                                      |
| `ai_share_lag1`          | Indeed AI Tracker + Ours | number    | US % of postings mentioning AI, **last** month                                                                            |
| `ai_chg3_lag1`           | Indeed AI Tracker + Ours | number    | Change in AI share over 3 months, ending last month (computed on the full series from 2019, before joining)               |
| `ai_chg12_lag1`          | Indeed AI Tracker + Ours | number    | Change in AI share over 12 months, ending last month                                                                      |
| `ai_carried_forward`     | Ours                     | bool      | `True` if `ai_share_lag1` was carried forward. Currently always `False`: carry-forward only happens in the partial current month, which this table drops                                                                             |
| `period`                 | Ours                     | text      | `pandemic` (before 2022-01) or `post`, so the model can filter or flag the rebound years                                  |
| `target_index_12m_ahead` | Indeed Postings + Ours   | number    | `index` for the same sector **12 months later**: what the model learns to predict. Blank where the future isn't known yet |

---

## 3. `crosswalk.csv`

One row per **job × sector**. 51 rows (46 jobs; a few jobs span two sectors). Hand-written in `pipeline/crosswalk_source.csv`, validated by `pipeline/build_crosswalk.py`.

| Column          | Source          | Type | Derived from                                                                     |
| --------------- | --------------- | ---- | -------------------------------------------------------------------------------- |
| `onet_code`     | O\*NET          | text | O*NET-SOC code, chosen by us and checked to exist in O*NET `occupation_data.csv` |
| `title`         | O\*NET          | text | Official O\*NET `Title` (replaces whatever we typed)                             |
| `indeed_sector` | Indeed Postings | text | Indeed sector name, chosen by us and checked to exist in the US data             |
| `weight`        | Ours            | 0–1  | How much of the job belongs to that sector, set by us. Sums to 1 per job         |
| `rationale`     | Ours            | text | One-line reason for the mapping, written by us                                   |

---

## 4. `onet_roles.csv`

One row per **job**. 46 rows. Built by `pipeline/build_onet.py`.

| Column        | Source | Type | Derived from                                                                      |
| ------------- | ------ | ---- | --------------------------------------------------------------------------------- |
| `onet_code`   | O\*NET | text | `O*NET-SOC Code` in `occupation_data.csv` (filtered to the jobs in the crosswalk) |
| `title`       | O\*NET | text | `Title` in `occupation_data.csv`                                                  |
| `job_zone`    | O\*NET | 1–5  | `Job Zone` in `job_zones.csv` (1 = little preparation, 5 = extensive)             |
| `description` | O\*NET | text | `Description` in `occupation_data.csv`                                            |

---

## 5. `onet_role_skills.csv`

One row per **job × skill**. 4,548 rows (22 to 219 per job, about 99 on average). Built by `pipeline/build_onet.py`.

| Column       | Source        | Type | Derived from                                                                                                                                                                                |
| ------------ | ------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `onet_code`  | O\*NET        | text | `O*NET-SOC Code`                                                                                                                                                                            |
| `skill_id`   | O\*NET + Ours | text | Skills and knowledge: O*NET `Element ID` (e.g. `2.C.4.a`). Software: `tech:` + slug of `Workplace Example` (e.g. `tech:tensorflow`), made by us because O*NET gives software no per-item ID |
| `skill_name` | O\*NET        | text | `Element Name`, or `Workplace Example` for software                                                                                                                                         |
| `skill_type` | Ours          | text | Which O\*NET file it came from: `skill` (`essential_skills.csv` + `transferable_skills.csv`), `knowledge` (`knowledge.csv`), `tech` (`software_skills.csv`)                                 |
| `importance` | O\*NET + Ours | 1–5  | Skills and knowledge: O*NET `Data Value` where `Scale ID = IM`. Software: set by us from O*NET flags (4.0 In Demand, 3.5 Hot Technology, 2.5 neither). The 2.5 tier is currently unused: every job has at least one Hot or In Demand item                                       |
| `level`      | O\*NET        | 0–7  | O*NET `Data Value` where `Scale ID = LV`. Blank for software (O*NET has no level for it)                                                                                                    |

Filters we apply:

- Software is limited to "Hot" or "In Demand" items; jobs with none would keep up to 10 (no job needs this fallback today, so software rows per job range from 1 to 151).
- Software names are slugged into `skill_id`, so C, C# and C++ all become `tech:c` and only one survives per job (9 job-skill pairs affected). The build keeps the alphabetically first name so reruns are identical. Splitting the IDs would change the contract; not done yet.
- O\*NET's low-precision ("Recommend Suppress") estimates are kept, so core skills always have a level.

---

## 6. `ai_exposure.csv`

One row per **job**. 46 rows. Built by `pipeline/build_ai_exposure.py`.

| Column               | Source                            | Type | Derived from                                                                                                                                                                                                               |
| -------------------- | --------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `onet_code`          | O\*NET + Anthropic Economic Index | text | O\*NET-SOC code; matches the Economic Index `node_external_id` (category `soc_occupation`)                                                                                                                                 |
| `title`              | O\*NET                            | text | O\*NET title                                                                                                                                                                                                               |
| `exposure`           | Anthropic Economic Index + Ours   | 0–1  | Each occupation's share of Claude conversations (`pct`) × share that is work use (`use_case_work_pct`), averaged over Apr–May 2026 and over Claude.ai + API. Then **percentile-ranked by us** against all 746 occupations. A job with no observed usage at all (currently Wind Turbine Service Technicians) gets 0 by fallback, not a rank |
| `automation_share`   | Anthropic Economic Index + Ours   | 0–1  | `collaboration_bucket_automation_pct` ÷ 100, averaged over both sources weighted by work usage. Blank if no usage                                                                                                          |
| `augmentation_share` | Anthropic Economic Index + Ours   | 0–1  | `1 − automation_share`                                                                                                                                                                                                     |
| `source`             | Ours                              | text | Release name and method, written by us                                                                                                                                                                                     |
| `as_of_date`         | Anthropic Economic Index          | date | Economic Index release date (2026-06-26)                                                                                                                                                                                   |

---

## 7. `my_vacancies.csv`

One row per **frequency × period × group type × group**. 3,969 rows. Built by `pipeline/build_jmi.py` from `data/raw/dosm_jmi/jmi_q2_2026.xlsx`. **Display only: do not use as a model feature or target** (see caveats).

| Column       | Source   | Type | Derived from                                                                                                     |
| ------------ | -------- | ---- | ---------------------------------------------------------------------------------------------------------------- |
| `freq`       | DOSM JMI | text | `month` (2019-07 to 2026-06), `quarter` (2019-Q3 to 2026-Q2) or `year` (2020 to 2026)                            |
| `period`     | DOSM JMI | text | `YYYY-MM`, `YYYY-Qn` or `YYYY`, from the column headers of the DOSM workbook                                    |
| `group_type` | Ours     | text | `occupation` (Table 2, major occupation group) or `industry` (Table 1, economic activity)                        |
| `group`      | DOSM JMI | text | Group name; `Total` is DOSM's "Jumlah" row                                                                       |
| `vacancies`  | DOSM JMI | int  | Number of job offerings advertised online (scraped from Malaysian recruitment websites). DOSM's "-" is stored as 0 |
| `is_partial` | Ours     | bool | `True` for the year 2026 (only January to June published)                                                        |
| `source`, `source_url`, `as_of_date` | Ours | text | Release name, release page, release date (2026-08-18)                                                |

Caveats:

- **Counts, not an index.** Not seasonally adjusted, no base year.
- **Coverage jumps, not just demand.** The quarterly total about doubles in 2021-Q3 (90,502 to 192,480) and again in 2025-Q3 (281,736 to 588,148). DOSM warns the data does not represent all vacancies, so these look like changes in the websites covered. Compare within a few quarters, never across these breaks.
- **Coarse groups.** 9 occupation groups (no state split in this file), 21 industry groups.
- **Elementary Occupations is 0 until 2025**, and one early quarter (2019-Q3) has 25,568 in `Unclassified`: the classification changed, so group shares before 2025 are not comparable.
- Group rows sum exactly to `Total`, and months sum exactly to quarters.

---

## 8. `onet_to_my_group.csv`

One row per **job**. 46 rows. Hand-written in `pipeline/jmi_group_map_source.csv`, validated by `pipeline/build_jmi.py` (must cover exactly the jobs in `onet_roles.csv` and use group names that exist in `my_vacancies.csv`).

| Column                | Source | Type | Derived from                                                                                                           |
| --------------------- | ------ | ---- | ---------------------------------------------------------------------------------------------------------------------- |
| `onet_code`           | O\*NET | text | Same as `onet_roles.csv`                                                                                               |
| `title`               | O\*NET | text | Same as `onet_roles.csv`                                                                                               |
| `my_occupation_group` | Ours   | text | The `occupation` group in `my_vacancies.csv` we judged closest (approximate: O\*NET-SOC to ISCO-style groups by hand) |
| `rationale`           | Ours   | text | Short reason for the mapping                                                                                           |

Join: `onet_to_my_group.my_occupation_group` = `my_vacancies.group` where `group_type = 'occupation'`. Several jobs share one group (21 map to Professionals), so this is context for the group, not a per-job number.

---

## Supporting files

| File                     | Source                          | What it is                                                                                                                                |
| ------------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `ai_exposure_detail.csv` | Anthropic Economic Index + Ours | All 746 occupations with the raw Economic Index metrics per source, `usage_share`, and a `low_sample` flag (automation split unreliable) |
| `manifest.json`          | Ours                            | As-of date of each source and row count of each table; feeds the app's "last updated" badge                                               |
