# Dataset for the LightGBM Algorithm and Monte Carlo Simulations

Four external datasets, one per question the app has to answer, plus one Malaysian context source (5). Last checked: 20 Oct 2026.

| #   | Dataset                   | Question it answers                        | Used for in the app                                         |
| --- | ------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| 1   | Indeed Job Postings Index | Which jobs are growing or shrinking?       | Demand forecast (Screen 3), X-axis of quadrant (Screen 4)   |
| 2   | Indeed AI Tracker         | How fast is AI spreading overall?          | AI-trend signal layer; Slow / Baseline / Rapid AI scenarios |
| 3   | Anthropic Economic Index  | How much is AI touching each specific job? | Y-axis of quadrant (Screen 4)                               |
| 4   | O\*NET 31.0 Database      | What skills does each job need?            | Skills gap and reskilling roadmap (Screens 4–5)             |
| 5   | DOSM Job Market Insights  | How many jobs are advertised in Malaysia?  | Malaysia context panel (display only, not a model input)    |

---

## 1. Indeed Job Postings Index

- **URL:** https://github.com/hiring-lab/job_postings_tracker
- **Publisher:** Indeed Hiring Lab
- **License:** CC-BY-4.0 (cite "Indeed Hiring Lab")
- **What it contains:** daily volume of job ads, seasonally adjusted, as an index where 1 Feb 2020 = 100. Broken down by occupational sector (e.g. Nursing, Data & Analytics, Software Development).
- **Coverage:** Feb 2020 – Oct 2026. Sector-level data for US (47 sectors), GB (49), AU, CA, DE and FR. **No Malaysia or Singapore.**
- **Update frequency:** weekly
- **As of:** 2026-10-09
- **Files used:** `<country>/job_postings_by_sector_<country>.csv`, `<country>/aggregate_job_postings_<country>.csv`
- **Why this one:** real, free, dated and refreshed weekly, which meets the brief's "updatable, dated source".
- **Vintages (forecast rebuild):** `<country>/aggregate_job_postings_<country>.csv` is read at the last commit of each month from Feb 2021. Before mid-2021 the files held % change since 1 Feb 2020, not an index. See `FORECAST_REBUILD.md`.

## 2. Indeed AI Tracker

- **URL:** https://github.com/hiring-lab/ai-tracker
- **Publisher:** Indeed Hiring Lab
- **License:** CC-BY-4.0 (cite "Indeed Hiring Lab")
- **What it contains:** daily percentage of all job ads that mention AI or GenAI.
- **Coverage:** Jan 2019 – Sep 2026; 9 countries (AU, CA, DE, FR, GB, IE, IT, NL, US). Country level only.
- **Update frequency:** monthly
- **As of:** 2026-09-30
- **Files used:** `AI_posting.csv`
- **Why this one:** a dated, regularly updated measure of AI adoption in the labour market. This is the brief's "AI-trend signal layer".
- **Vintages (forecast rebuild):** the repo's git history is used as a record of what was published when: each commit to `AI_posting.csv` (and its earlier names) is one vintage. There are 35 vintages from 29 Apr 2024. History is revised between vintages (mean 0.39 pp), so backtests must not read today's file. It measures **mentions in ads** (skill demand), not AI adoption. See `FORECAST_REBUILD.md`.
- **Also in the repo, not used yet:** `GenAI_posting.csv` (share mentioning GenAI terms, 12 vintages).

## 3. Anthropic Economic Index

- **URL:** https://huggingface.co/datasets/Anthropic/EconomicIndex
- **Publisher:** Anthropic
- **License:** CC-BY (confirm the version on the dataset card)
- **What it contains:** how real Claude usage maps to occupations and tasks. For each occupation:
  - its share of all conversations
  - the share that is work use
  - the split between automation (AI does the task) and augmentation (AI helps a person do it)
- **Coverage:** 746 occupations (O\*NET-SOC codes); global; months starting April and May 2026.
- **Release used:** 2026-06-26
- **Files used:** `aei_claude_ai_2026-06-26.csv` (Claude.ai), `aei_1p_api_2026-06-26.csv` (API)
- **Why this one:** gives a _different_ AI exposure score per job, based on observed real-world usage. It uses the same job codes as O\*NET, so it joins directly.
- **How we use it:** exposure (0–1) = how much real _work_ is done with Claude for that occupation, ranked against all occupations.

## 4. O\*NET 31.0 Database

- **URL:** https://www.onetcenter.org/database.html
- **Publisher:** U.S. Department of Labor, Employment and Training Administration (USDOL/ETA)
- **License:** CC-BY-4.0 (credit "O\*NET 31.0 Database, USDOL/ETA")
- **What it contains:** for ~900 occupations:
  - title and description
  - Job Zone (1–5, how much preparation the job needs)
  - required skills and knowledge, each rated for importance (1–5) and level (0–7)
  - software and technology used, with "Hot" and "In Demand" flags
- **Coverage:** US occupations; we use 46 of them.
- **Files used (CSV):** `occupation_data.csv`, `job_zones.csv`, `essential_skills.csv`, `transferable_skills.csv`, `knowledge.csv`, `software_skills.csv`
- **Why this one:** the standard, free, detailed job-skills database. We compare the user's resume against it to find the skills gap and order the roadmap.

---

## 5. DOSM Job Market Insights (Malaysia)

- **URL:** https://www.dosm.gov.my/portal-main/release-content/big-data-analytics-job-market-insights-q22026
- **Publisher:** Department of Statistics Malaysia (DOSM)
- **License:** not stated on the release page (confirm before redistributing)
- **What it contains:** number of job vacancies advertised online on Malaysian recruitment websites, by major occupation group (9) and economic activity (21 industries).
- **Coverage:** Malaysia (national, no state split in this file); monthly Jul 2019 – Jun 2026, quarterly Q3 2019 – Q2 2026, annual 2020 – 2026.
- **Update frequency:** quarterly (next release 17 Nov 2026)
- **As of:** 2026-08-18 (Q2 2026 release)
- **File used:** the release's "Data" workbook, saved as `data/raw/dosm_jmi/jmi_q2_2026.xlsx` (download id 20742; `build_jmi.py` fetches it if missing)
- **Why this one:** the only official source of Malaysian demand found. Counts are not comparable across time (coverage jumps in 2021-Q3 and 2025-Q3) and there are only 9 occupation groups, so we show it as context and never train on it.
- **Limits:** DOSM states it does not represent all vacancies in Malaysia.

## 6. Census Business Trends and Outlook Survey (BTOS) — forecast rebuild only

- **URL:** https://www.census.gov/hfp/btos/data_downloads
- **Publisher:** U.S. Census Bureau
- **License:** public domain (U.S. government work)
- **What it contains:** fortnightly survey of US businesses. Two AI questions are used:
  - Q7: used AI in the last two weeks;
  - Q24: expects to within six months.

  Both come with standard errors, nationally and for 19 NAICS sectors.
- **Coverage:** two question wordings, which must not be joined:
  - old: Sep 2023 – Oct 2025 (54 fortnights);
  - new: Nov 2025 onwards (24 fortnights so far).

  Three fortnights in between were not asked. The level jumps from 10.0% to 17.3% at the change.
- **Update frequency:** fortnightly, with a published schedule
- **As of:** fortnight 202621 (reference period ending 4 Oct 2026), published 22 Oct 2026
- **Files used:** `Sector.xlsx`, `National.xlsx`, `AI Core Questions.xlsx`
- **Used for:** the **business-adoption** target only (`btos_ai_use_rate`, see `FORECAST_REBUILD.md` §8a). It measures firms, so the forecast contracts refuse it as an occupation-adoption label and as a skill-demand input.

## 7. Real-Time Population Survey: Generative AI adoption (via FRED) — forecast rebuild only

- **URL:** https://sites.google.com/view/covid-rps/data (series `RPSGENAIUSAGESHAREOCC1`–`22` and `RPSGENAIUSAGESHAREWORK` on FRED)
- **Publisher:** Bick, Blandin & Deming; distributed by the Federal Reserve Bank of St. Louis (FRED)
- **What it contains:** quarterly % of employed US adults (18–64) who use generative AI for their job, for 22 SOC major groups and all workers.
- **Coverage:** 2024-Q3 – 2026-Q3 (9 quarters)
- **Update frequency:** quarterly
- **As of:** 2026-Q3, on FRED by 22 Oct 2026
- **Used for:** the **occupation-adoption** target only (`worker_genai_use_rate`, see `FORECAST_REBUILD.md` §8b). It is the only direct, worker-level evidence on occupational AI use.
- **Point in time:** ALFRED vintages via `FRED_API_KEY` (in `src/backend/.env`). FRED first published the series on 18 Jun 2026 and revised it on 16 Oct 2026. Earlier backtest origins are reconstructed.

## 8. Epoch AI benchmark data (METR time horizons, Epoch Capabilities Index) — forecast rebuild only

- **URL:** https://epoch.ai/benchmarks (download `https://epoch.ai/data/benchmark_data.zip`)
- **Publisher:** Epoch AI. The time horizons are measured by METR (https://metr.org).
- **License:** CC-BY-4.0 (cite "Epoch AI, 'Capabilities & benchmarking'")
- **What it contains:** benchmark results for AI models. Two parts are used:
  - `metr_time_horizons_external.csv`: the length of tasks (in human minutes) a model completes with 50% reliability, with CIs, release dates and METR suite version;
  - `epoch_capabilities_index/eci_scores.csv`: a composite index fitted over about 60 benchmarks.
- **Coverage:**
  - METR: about 50 models, released 2019–2026;
  - ECI: about 270 models.
- **Vintages:** 17 Wayback Machine captures from Mar 2025, one per month. METR appears from Jun 2025, ECI only from Sep 2026.
- **As of:** 23 Oct 2026 (Last-Modified)
- **Used for:** the **AI-capability** target (`frontier_time_horizon`, see `FORECAST_REBUILD.md` §8c), METR only.
- **Not used:** ECI is refitted with every update and has too few vintages to backtest without retrospective normalisation. It is stored for later.

## Not used in models

- **Adzuna job-ads API:** the account is on the free tier (25 calls a day), so stored snapshots will never reach a history long enough to train or backtest on. It is context only (decision of 24 Oct 2026).

---

## Plus two files we built

### The Malaysia map

- **File:** `pipeline/jmi_group_map_source.csv`: links each of our 46 jobs to one of DOSM's 9 occupation groups (approximate, hand-judged).

### The crosswalk

- **File:** `pipeline/crosswalk_source.csv` (in our repo)
- **What it does:** links each of our 46 jobs (O\*NET codes) to one or more Indeed sectors, with weights. For example, Data Scientists → Data & Analytics.
- **Why:** Indeed tracks sectors, but users and O\*NET think in jobs. This is the bridge that gives each job a demand trend.

---

## Evaluated and not used

| Dataset | Why not |
| ------- | ------- |
| Techsalerator "Job Posting Data in Malaysia" ([Kaggle](https://www.kaggle.com/datasets/techsalerator/job-posting-data-in-malaysia), checked 20 Oct 2026) | Not Malaysian data: 9,919 postings, only 123 (~1%) in Malaysia, the rest global. Covers Mar–Sep 2024 (six months) from just 8 employers (Bosch and ZF are ~89%). Many duplicates, salary mostly empty and garbled. Too short and skewed to be a demand index or to feed the forecast. At most usable for skill-phrase mining or example postings. |
