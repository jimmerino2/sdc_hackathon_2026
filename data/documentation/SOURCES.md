# Dataset for the LightGBM Algorithm and Monte Carlo Simulations

Four external datasets, one per question the app has to answer, plus one Malaysian context source (5) and four sources for the AI adoption scenarios (6-9, added 22 Oct 2026; see `AI_ADOPTION_PLAN.md`). Last checked: 22 Oct 2026.

| #   | Dataset                   | Question it answers                        | Used for in the app                                         |
| --- | ------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| 1   | Indeed Job Postings Index | Which jobs are growing or shrinking?       | Demand forecast (Screen 3), X-axis of quadrant (Screen 4)   |
| 2   | Indeed AI Tracker         | How fast is AI spreading overall?          | AI-trend signal layer; Slow / Baseline / Rapid AI scenarios |
| 3   | Anthropic Economic Index  | How much is AI touching each specific job? | Y-axis of quadrant (Screen 4)                               |
| 4   | O\*NET 31.0 Database      | What skills does each job need?            | Skills gap and reskilling roadmap (Screens 4–5)             |
| 5   | DOSM Job Market Insights  | How many jobs are advertised in Malaysia?  | Malaysia context panel (display only, not a model input)    |
| 6   | Real-Time Population Survey | How many workers use AI at work, per occupation group? | Starting point of the AI adoption Monte Carlo        |
| 7   | Census BTOS               | How many businesses use AI, per sector, every two weeks? | Structured part of the weekly scenario score       |
| 8   | Adzuna API                | How many live job ads mention AI, or each skill? | Structured part of the score; skill demand per job  |
| 9   | GDELT DOC 2.0 API         | What does recent news say about AI adoption? | News part of the weekly scenario score (capped)          |

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

---

## 6. Real-Time Population Survey: Generative AI Adoption Tracker

- **URL:** quarterly series on FRED (`RPSGENAIUSAGESHAREOCC1` to `OCC22`, `RPSGENAIUSAGESHAREWORK`, e.g. https://fred.stlouisfed.org/series/RPSGENAIUSAGESHAREWORK); occupation adoption index at https://sites.google.com/view/covid-rps/data
- **Publisher:** Alexander Bick, Adam Blandin, David Deming; series hosted by the Federal Reserve Bank of St. Louis
- **License:** FRED marks the series "Copyrighted: Citation Required". Cite "Bick, A., Blandin, A. and Deming, D., The Rapid Adoption of Generative AI, Management Science (2026), retrieved from FRED". The index workbook states no licence; cite the same paper.
- **What it contains:** share of employed US adults aged 18-64 who answer yes to "Do you use Generative AI for your job?". FRED: one quarterly series per 2018 SOC major group (22) plus all workers. Index: the same rate pooled over four waves (Aug 2025 - May 2026) by SOC major, minor and broad occupation, with respondent counts.
- **Coverage:** United States; Q3 2024 - Q3 2026 (9 quarters). Respondents per group and quarter range from about 25 (Legal) to about 740 (Management).
- **Update frequency:** quarterly
- **As of:** 2026-07 (latest quarter)
- **Files used:** the 23 FRED CSVs and the index workbook, downloaded by `build_ai_adoption.py` into `data/raw/rps/`
- **Why this one:** the only open source found that tracks AI adoption per occupation over time, from real workers.

## 7. Census Business Trends and Outlook Survey (BTOS): AI use

- **URL:** https://www.census.gov/hfp/btos/data_downloads (`Sector.xlsx`, `National.xlsx`, `AI Core Questions.xlsx`)
- **Publisher:** U.S. Census Bureau
- **License:** U.S. federal government data (public domain); cite "U.S. Census Bureau, Business Trends and Outlook Survey"
- **What it contains:** share of US businesses that used AI in the last two weeks (question 7) and expect to in the next six months (question 24), with standard errors, by NAICS sector and nationally.
- **Coverage:** United States, 19 sectors plus multi-unit companies; every two weeks from Sep 2023, with a gap for the Oct-Nov 2025 shutdown.
- **Watch out:** the question changed in Nov 2025 from AI "in producing goods or services" to AI "in any of its business functions" (Census now writes "Super Intelligence or SI (formerly referred to as Artificial Intelligence or AI)"). The level jumps from about 9% to 17% at the change, so `btos_ai.csv` keeps the two wordings apart and changes are never compared across them.
- **Update frequency:** every two weeks
- **As of:** 2026-10-04 (reference period end)
- **Why this one:** the most frequent official AI adoption measure, by industry.

## 8. Adzuna API

- **URL:** https://developer.adzuna.com
- **Publisher:** Adzuna
- **License:** API terms of service; free key. Keys live in `src/backend/.env` (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`), never in git.
- **What it contains:** live job ads per country, searchable by keyword and category; we only read the total `count` of matching ads.
- **Coverage:** the countries Adzuna runs (we use us only by default, to stay within the free tier). **No Malaysia site.**
- **Update frequency:** live; `collect_adzuna.py` takes a weekly snapshot, so history starts from the first run.
- **Why this one:** the only ad source with keyword counts by category, for AI mentions and for skill demand.

## 9. GDELT DOC 2.0 API

- **URL:** https://api.gdeltproject.org/api/v2/doc/doc
- **Publisher:** The GDELT Project
- **License:** free and open, with attribution; one request every 5 seconds.
- **What it contains:** metadata of news articles worldwide (URL, title, domain, source country, date) matching a query; no article text.
- **Coverage:** global, with a `sourcecountry:malaysia` filter for Malaysian outlets.
- **How we use it:** `collect_news.py` keeps only articles from the trusted domains in `pipeline/news_sources.csv` (tiered), and `ml/ai_signal_score.py` has one LLM read each headline once.
- **Not used:** Google News RSS (its terms allow personal, non-commercial use only).

---

## Plus two files we built

### The Malaysia map

- **File:** `pipeline/jmi_group_map_source.csv`: links each of our 46 jobs to one of DOSM's 9 occupation groups (approximate, hand-judged).

### The crosswalk

- **File:** `pipeline/crosswalk_source.csv` (in our repo)
- **What it does:** links each of our 46 jobs (O\*NET codes) to one or more Indeed sectors, with weights. For example, Data Scientists → Data & Analytics.
- **Why:** Indeed tracks sectors, but users and O\*NET think in jobs. This is the bridge that gives each job a demand trend.

---

## Kept for later (not wired in)

| Dataset | Why kept, and the condition for using it |
| ------- | ---------------------------------------- |
| Job-SDF ([arXiv 2406.11920](https://arxiv.org/abs/2406.11920), checked 22 Oct 2026) | Monthly skill-demand series from 10.35 million job ads, 2,300+ skills, China 2021-2023: the only open dataset found built for skill-demand forecasting. Needs a mapping to O\*NET. If used, keep it separate from the job-postings forecast (`train_lgbm.py`). |

## Evaluated and not used

| Dataset | Why not |
| ------- | ------- |
| GitHub Innovation Graph ([github/innovationgraph](https://github.com/github/innovationgraph), CC0, checked 22 Oct 2026) | Considered as a Malaysian AI signal. Malaysia has only 2-8 topics per quarter (the "ai" topic first appears in 2026 Q1), and the share of developers on Jupyter Notebook stays flat (about 0.25%), so it carries no adoption trend. |
| Techsalerator "Job Posting Data in Malaysia" ([Kaggle](https://www.kaggle.com/datasets/techsalerator/job-posting-data-in-malaysia), checked 20 Oct 2026) | Not Malaysian data: 9,919 postings, only 123 (~1%) in Malaysia, the rest global. Covers Mar–Sep 2024 (six months) from just 8 employers (Bosch and ZF are ~89%). Many duplicates, salary mostly empty and garbled. Too short and skewed to be a demand index or to feed the forecast. At most usable for skill-phrase mining or example postings. |
