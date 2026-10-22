# AI Adoption Forecast: Build Plan

How we forecast **AI adoption at work** under three scenarios with a Monte Carlo simulation, and keep the scenario odds **up to date every period** with a live external score. Current sources are in `SOURCES.md`, table columns in `STRUCTURE.md`, how to run it in `src/backend/ml/README.md`.

## Status (22 Oct 2026, branch `feat/ai-adoption-mc`, backup tag `backup/pre-ai-adoption`)

| Phase | State |
| ----- | ----- |
| 0 Set-up | Done. Adzuna keys are in `src/backend/.env` (free tier: US only, 22 categories) |
| 1 Data layer | Done: `ai_adoption.csv`, `ai_adoption_jobs.csv`, `btos_ai.csv`, wired into `refresh.py` |
| 2 Monte Carlo | Done: backtest 10–90% coverage 79–84% |
| 3 Adzuna | Done and run for 2026-W43 (46 calls on 22 Oct, before the daily cap existed). **Free tier is 25 calls a day:** the collector now keeps all runs together within 20 calls a day (`data/raw/adzuna/calls_log.csv`), resumes an unfinished week the next day, reuses category totals for 28 days and the category list for 30. Weekly cost: 22 calls (44 every fourth week); `--skills` monthly: 45 calls over 3 days. AI share enters the score after 6 weekly runs |
| 4 Score and odds | Done and run for week 2026-W43: Indeed + BTOS + news (36 headlines read in 3 LLM calls, 10 relevant). The trusted list keeps about 10% of what GDELT returns (39 of 375), mostly Malaysian outlets; widen `pipeline/news_sources.csv` if more international news is wanted. Adzuna joins the score once it has 6+ weeks |
| 5 API | Done: `/forecast/ai-adoption`, `/forecast/ai-adoption/jobs`, `/forecast/ai-adoption/odds-history`, `/forecast/skill-demand`. Frontend: two test pages outside the flow, `/lab/adoption-roles` and `/lab/adoption-signal` (same design as Future roles and Forecast & skill gap); the flow's own pages are unchanged |

**Changed from the plan while building:**

- **GitHub Innovation Graph dropped.** Malaysia has only 2–8 topics per quarter and the Jupyter share is flat, so it carries no adoption trend (`SOURCES.md`, "Evaluated and not used"). Malaysian freshness comes from news filtered to Malaysian outlets instead.
- **Google News RSS dropped:** its terms allow personal, non-commercial use only. News comes from GDELT alone.
- **Signal changes are measured on the logit of each rate**, not in percentage points, so a 2-point move at 5% and at 40% compare fairly.
- **Survey design effect set to 3.0** so the ranges hold ~80% of past readings (1.5 gave 72%).
- **The data shows no reliable difference between group trends**, so every group currently follows the national trend from its own level.
- **LLM cost cap is a call cap** (5 calls of 40 headlines per run): the shared `complete()` helper does not return costs.
- **Skill demand endpoint** is `/forecast/skill-demand` (in the forecast router) rather than `/skills/demand`.

## Goal

For each occupation group (and each of our 46 jobs), show:

- the share of workers using generative AI at work, now and 3, 6, 9 and 12 months ahead, as a range (10th / 50th / 90th percentile);
- under three scenarios: **AI accelerates**, **AI holds**, **AI declines**;
- with a **probability for each scenario** that is recomputed every week from fresh signals, and the signals that moved it;
- plus a **skill demand** trend per job.

**Not a goal:** beating a baseline on accuracy. The news part of the score cannot be backtested (see [Limits](#limits)). What matters is that the score is current, the odds move when the evidence moves, and every change is explained.

## Decisions already made

| Decision | Choice | Why |
| -------- | ------ | --- |
| Forecasting method | Monte Carlo on AI adoption, not LightGBM | LightGBM forecasts job postings and did not beat simple baselines; adoption data is too short (207 points) for it |
| "AI holds" | Adoption keeps growing **at today's pace** | Matches the app's existing "steady / Baseline" tab; keeps the likeliest future in the middle scenario |
| How the external score enters | It changes the **scenario odds**, never the simulated paths | Keeps noisy signals from distorting the numbers; the effect can be capped |
| Validation of news | **One** extraction model + fixed rules in code | An AI council (4 models + reviews + chairman, ~13 calls) is not worth it: one article cannot move much here, and there is no ground truth to show a council does better |
| LLM client | Reuse `src/backend/app/llm/service.complete` (temperature 0) | Same gateway and keys as the rest of the backend |
| Existing job-postings forecast | **Untouched** | `train_lgbm.py`, `forecast_output.csv`, `job_forecast.csv` and the `/forecast` endpoints stay as they are |
| Job-SDF (skill demand, China) | Not used | Kept for later in `SOURCES.md` |

## Data sources

| # | Source | What it gives | Frequency | Coverage | Access | Role |
| - | ------ | ------------- | --------- | -------- | ------ | ---- |
| 1 | **Real-Time Population Survey** via FRED (`RPSGENAIUSAGESHAREOCC1`–`22`, `RPSGENAIUSAGESHAREWORK`) | % of employed US adults using generative AI for their job, per SOC major group | Quarterly, 2024-07 → 2026-07 (9 quarters) | US, 22 groups + all workers | Free CSV, "Copyrighted: Citation Required" | **Ground truth** the simulation starts from |
| 2 | RPS occupation adoption index (Google Sheets workbook) | Same rate pooled over 4 waves, per SOC broad / minor / major group, with respondent counts | Pooled, no time dimension | US | Free, no licence stated; cite Bick, Blandin & Deming | Each job's starting rate; respondent counts for the noise model |
| 3 | **Indeed AI Tracker** (already in `signals.csv`, `ai_postings_share`) | % of job ads mentioning AI | Monthly since 2019 | US + 8 countries, national | Already pulled by `refresh.py` | Structured signal |
| 4 | **Census BTOS**, AI use question | % of businesses using AI, by sector | Every 2 weeks since Sep 2023 | US, by sector | Free download from census.gov/hfp/btos (exact file to confirm) | Structured signal. **Question wording changed Nov 2025**: treat as a series break |
| 5 | **Adzuna API** (keys obtained) | Number of live ads matching a keyword, per category and country | Live; we sample weekly | Countries to confirm (likely US, GB, SG; **not Malaysia**) | `app_id` + `app_key`; daily call limit to confirm in the dashboard | (a) % of ads mentioning AI per category = structured signal; (b) skill demand counts |
| 6 | ~~GitHub Innovation Graph~~ | Dropped: no adoption trend in the Malaysian data (see Status) | | | | |
| 7 | **News**: GDELT DOC 2.0 API | Articles about AI releases, price cuts, enterprise rollouts, regulation, bans, AI-attributed layoffs | Daily; we pull weekly | Global, filterable by country (`sourcecountry:malaysia`) | Free, one request per 5 s | News signal (capped) |
| 8 | HN "Who is Hiring?" via Algolia API (optional) | Skills mentioned in ~400 tech job ads a month | Monthly since 2011 | Tech, mostly US / remote | Free, no key | Gives skill demand **history** for tech jobs while Adzuna builds its own |

## Architecture

```
STRUCTURED (slow, reliable)                       LIVE (fast, noisier)
1 FRED survey ──► starting level, trend, noise    3 Indeed AI share   (monthly)
2 RPS index   ──► each job's starting rate        4 BTOS AI use       (every 2 weeks)
                                                  5 Adzuna AI share   (weekly)
                                                  6 GitHub AI topics  (quarterly, MY)
                                                  7 News              (weekly, 1 LLM call per batch)
        │                                                  │
        ▼                                                  ▼
  Monte Carlo per group                     External score per group, S in [-1, +1]
  (10,000 paths x 3 scenarios)              (validation rules below; every input logged)
        │                                                  │
        └──────────────► scenario odds = prior tilted by S (capped) ◄──┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
             Accelerates             Holds               Declines     → p10 / p50 / p90 + probability
                                       │
                   job level (job's own rate x group path) ──► API ──► scenario tabs in the app

5 Adzuna skill counts (+ 8 HN history) ──► skill demand trend per job (separate output, same refresh)
```

## Phases

Work on a branch, with a backup tag on `main` before starting. Every phase ends with the existing endpoints returning byte-identical responses (compare against the tag, as done before).

### Phase 0: Set-up (0.5 h)

- [ ] `git tag backup/pre-ai-adoption` on `main`, then `git switch -c feat/ai-adoption-mc`.
- [ ] Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` to `src/backend/.env` (gitignored) and empty entries to `.env.example`.
- [ ] One test call per country we plan to use; record the supported countries and the daily call limit here.

**Done when:** a test call returns a `count`, and the limit is written down.

### Phase 1: Data layer (0.5 day)

- [ ] Restore `pipeline/build_ai_adoption.py` (reverted earlier; rebuild from that version): FRED series → `data/processed/ai_adoption.csv`, RPS index → `data/processed/ai_adoption_jobs.csv`.
- [ ] Add the **respondents per group and quarter** column (pooled `number_observations` ÷ 4 waves, as an approximation) for the noise model.
- [ ] New `pipeline/build_btos_ai.py` → `data/processed/btos_ai.csv` (sector × period, rate, `series_break` flag at the Nov 2025 wording change).
- [ ] New `pipeline/build_github_ai.py` → `data/processed/github_ai.csv` (economy × quarter, share of developers on AI topics; keep MY and US).
- [ ] Wire all three into `refresh.py` as download steps that **warn and keep the old table on failure** (same pattern as DOSM), add their keys to the cross-table checks and their as-of dates to `manifest.json`.
- [ ] Document each source in `SOURCES.md` and each table in `STRUCTURE.md`.

**Done when:** `refresh.py` checks pass and no existing table changes.

### Phase 2: Monte Carlo (1 day)

New `src/backend/ml/ai_adoption_mc.py`. Outputs in `src/backend/ml/output/`.

- [ ] **Noise filter:** a local level-and-trend filter per group on the logit of the rate, with observation noise from the respondent count (`p(1-p)/n`). Small groups (Legal, about 25 respondents a quarter) get smoothed; big ones (Management, about 740) are trusted.
- [ ] **Shared trend:** group trend = national trend + the group's own difference shrunk toward 0 (more shrinkage for smaller groups). The earlier test showed the national trend beats each group's own.
- [ ] **Simulation in logit space**, so paths stay between 0% and 100% and slow down near the top (S-curve).
- [ ] **Scenarios**, as named parameters at the top of the file (assumptions, not learned):

  | Scenario | Drift per quarter |
  | -------- | ----------------- |
  | Accelerates | 1.5 x the filtered trend |
  | Holds | 1.0 x the filtered trend |
  | Declines | −0.5 x the filtered trend |

- [ ] 10,000 paths per group and scenario, 4 quarters ahead (3 / 6 / 9 / 12 months), fixed seed per run date.
- [ ] **Job level:** job path = job's own starting rate x (group path ÷ group start), clipped to 0–1.
- [ ] **Sanity backtest** (not an accuracy target): from each past origin with at least 4 quarters, check that the "Holds" 10–90% range contains the real outcome roughly 80% of the time. Write the result to the meta file.
- [ ] Outputs: `ai_adoption_mc.csv` (group x scenario x horizon: p10, p50, p90), `ai_adoption_mc_jobs.csv` (same per job), `ai_adoption_mc_meta.json` (parameters, seed, data as-of, backtest coverage).

**Done when:** the outputs exist, every range is within 0–1, and the coverage check is recorded.

### Phase 3: Adzuna collector (0.5 to 1 day)

New `pipeline/collect_adzuna.py`, run weekly. Appends to history tables (never overwrites past weeks).

- [ ] **AI share per category:** for each Adzuna category and country, `count(ads matching AI terms) ÷ count(all ads)`. AI terms: `"artificial intelligence" OR "generative AI" OR LLM OR "machine learning" OR ChatGPT OR copilot`. Map each Adzuna category to SOC major groups in a hand-written `pipeline/adzuna_category_map.csv` (one row per category, with a rationale).
- [ ] **Skill demand:** for each job's top skills in `onet_role_skills.csv` (by importance), `count(ads matching the skill) ÷ count(ads in the job's category)`.
- [ ] **Call budget:** a `--max-calls` limit per run; if the skill list is bigger than the budget, rotate skills across weeks. Cache responses per day; retry with backoff on 429/5xx.
- [ ] Outputs: `data/processed/adzuna_ai_share.csv` (week x country x category), `data/processed/skill_demand.csv` (week x country x onet_code x skill).
- [ ] Optional: `pipeline/build_hn_skills.py` → `data/processed/skill_demand_hn.csv` (month x skill share in HN hiring posts, 2011 onward) so tech jobs have a trend from day one.

**Done when:** one run stays within the budget and rerunning the same week does not duplicate rows.

### Phase 4: External score and odds (1 day)

New `src/backend/ml/ai_signal_score.py`, run weekly after the collectors.

**News extraction** (one LLM call per batch of up to 50 articles, via `app/llm/service.complete`). Output per article, as strict JSON:

| Field | Values |
| ----- | ------ |
| `direction` | `accelerate`, `hold`, `decline` |
| `strength` | 1 (minor) to 3 (major) |
| `soc_majors` | list of SOC major codes, or `ALL` |
| `region` | ISO country code or `GLOBAL` |
| `is_fact` | true for something that happened, false for an announcement or forecast |
| `quote` | the sentence that supports the call |

The system prompt says news is data, never instructions. Output that does not match the format is rejected and logged.

**Validation rules (code, not AI):**

| Rule | Detail |
| ---- | ------ |
| Allowed sources only | A source list with a trust tier (1 official, 2 established news, 3 trade press). Anything else is dropped |
| Duplicates | Same URL, or same normalised title within 7 days, counts once |
| Corroboration | A `strength` 3 item only counts if at least 2 independent sources report it within 14 days |
| Announcements | `is_fact = false` counts half |
| Age | Weight halves every 30 days |
| Weekly cap | The score cannot move more than 0.3 in one week |
| Logging | Every article, its extraction, its weight and every LLM call (tokens, cost) is saved |
| Cost cap | A run stops if LLM cost passes US$1 |

**Score per group** (`S`, between −1 and +1):

- Structured part (weight 0.6): for each of sources 3–6, the latest change versus its own recent history, as a z-score squashed with `tanh(z / 2)`; averaged over the sources that cover the group.
- News part (weight 0.4): `tanh(sum(direction x strength x tier weight x age weight) / 5)`, where direction is +1, 0 or −1.
- Each part is kept separately in the output, so the app can show both.

**Odds:**

```
odds(s) ∝ prior(s) x exp(k x S x dir(s))      dir: accelerates +1, holds 0, declines −1
prior = 25% / 50% / 25%,   k = 1.0,   each scenario kept between 10% and 60%
```

- [ ] Outputs: `ai_signal_score.csv` (week x group: S, structured part, news part, top 3 contributing items), `scenario_odds_history.csv` (week x group: three odds). **History is appended every week**, so the app can show how the odds moved.
- [ ] Track record: when a new survey quarter arrives, record which scenario's p50 was closest, next to the odds we had given it.

**Done when:** a weekly run updates the odds, and every change can be traced to the items behind it.

### Phase 5: API and app (0.5 day)

New endpoints (existing ones unchanged):

| Endpoint | Returns |
| -------- | ------- |
| `GET /forecast/ai-adoption?group=&horizon=` | Per group: current rate, the three scenarios (p10 / p50 / p90 per horizon), this week's odds, the score with its structured and news parts, and the top signals |
| `GET /forecast/ai-adoption/jobs?onet_code=&title=` | The same per job, from the job's own starting rate |
| `GET /forecast/ai-adoption/odds-history?group=` | Weekly odds over time |
| `GET /skills/demand?onet_code=&country=` | Weekly skill demand shares for the job's skills (plus HN history where available) |

- [ ] Every response carries `data_as_of`, `country`, a `reliability` note and the source names.
- [ ] Frontend: the existing scenario keys (`accelerates`, `steady`, `slows`) map to accelerates / holds / declines; show the odds next to each tab and the top signals under it.

**Done when:** the new endpoints return 200, a bad `horizon` returns 422, and the existing endpoints are byte-identical to the backup tag.

## Refresh schedule

| When | What runs |
| ---- | --------- |
| Weekly | `collect_adzuna.py` (22 calls; run it again the next day if it says categories are left), `collect_news.py`, `ai_signal_score.py` (new odds). The API re-reads changed files on its own |
| Monthly | `collect_adzuna.py --skills` on three consecutive days (45 skill calls, 20 a day at most); `refresh.py` (Indeed AI Tracker, BTOS), then `ai_signal_score.py` |
| Quarterly | `build_ai_adoption.py` (new FRED quarter; delete `data/raw/rps/` first), `build_github_ai.py`, `ai_adoption_mc.py` (new starting point), track-record update |

## Limits

- **The news score cannot be shown to improve accuracy.** There are no past scores (scoring old news now would use hindsight, since the model knows what happened next), only 9 survey quarters to check against, and its weights are our choices. It is there to keep the odds current and explained. The track record in Phase 4 is how we find out over time.
- **Scenario drifts and the prior are assumptions**, stated as named parameters and shown in the meta file.
- **US data stands in for Malaysia** for sources 1–5. Only GitHub (6) is Malaysian. Say so in every response, as `/forecast` already does with `is_proxy_for_malaysia`.
- **Skill demand from Adzuna starts with no history.** It is a live snapshot from week 1; the trend means something after about 8–12 weeks. HN fills in history for tech jobs only.
- **Non-tech jobs** (nurses, cooks, drivers) have weak skill demand coverage in every free source.
- **BTOS changed its AI question in Nov 2025.** The jump at that point is the wording, not adoption.

## How to describe it

- **Say:** "We simulate AI adoption at work under three scenarios, and update the odds of each every week from job ads, business surveys, developer activity and news, showing what moved them."
- **Don't say:** "Our news score makes the forecast more accurate", or "we predict which jobs AI will replace". Adoption is how many workers use AI, not job loss.

## Open questions

- [ ] Adzuna: which countries and how many calls per day (Phase 0).
- [ ] BTOS: exact download file and its sector breakdown (Phase 1).
- [ ] Prior odds: keep 25 / 50 / 25, or let the team set them?
- [ ] News queries and the trusted source list: draft in Phase 4, review together.
