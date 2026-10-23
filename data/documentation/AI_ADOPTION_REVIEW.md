# AI Adoption Forecast: Review and Handover

Written 23 Oct 2026 as a handover. It covers how the AI adoption forecast works today, the problems we found, the experiments we ran, and the redesign we suggest. Read it together with [AI_ADOPTION_PLAN.md](AI_ADOPTION_PLAN.md) (the original build plan), [SOURCES.md](SOURCES.md) and [src/backend/ml/README.md](../../src/backend/ml/README.md).

## TL;DR

- The two test pages, `/lab/adoption-roles` and `/lab/adoption-signal`, show the **share of workers who use generative AI at work**, now and 3 to 12 months ahead, under three scenarios (AI accelerates / holds / declines), each with weekly odds.
- The numbers are a **Monte Carlo simulation** run offline once a quarter on a US worker survey. The **odds** come from a separate weekly score built from job-ad data, a business survey and LLM-read news headlines. The odds never change the simulated numbers.
- **Main weakness:** most of what matters is hand-set rather than learned or tested: the scenario speeds, the 25/50/25 starting odds, the odds formula and the news weights. In practice "holds" always sits between 38% and 50%, "accelerates" can never go past about 52%, and the odds have never been checked against what actually happened.
- **What the experiments showed:**
  - The Census business survey's **"expect to use AI in the next 6 months"** answer predicts actual use 6 months later much better than the trend does (40–56% lower error). We download it but don't use it.
  - **Model releases** add no separate, measurable effect on top of the trend.
  - **News volume** (GDELT) is a weak and inconsistent predictor.
- **Suggested next step:** replace the Monte Carlo and hand-made odds with a trained forecast built on business expectations plus the trend, with ranges calibrated on past errors and probabilities we can score. Keep news as context only. See [Suggested redesign](#suggested-redesign).

---

## 1. What exists today

### Pages

| Page | File | What it shows |
|---|---|---|
| `/lab/adoption-roles` | [AdoptionRolesView.vue](../../src/frontend/src/views/AdoptionRolesView.vue) | Card per role. Under the chosen scenario tab: the odds ("X% likely"), today's AI use, the median (p50) at 12 months, the p10–p90 range, a trend arrow (±2 pts), and O*NET skill chips |
| `/lab/adoption-signal` | [AdoptionSignalView.vue](../../src/frontend/src/views/AdoptionSignalView.vue) | One role: a 12-month chart of all 3 scenarios with the selected one's p10–p90 band, scenario buttons with their odds, "Why the odds moved" (this week's signals), "Odds over time", "Live job ads" (skill demand, **empty**), and the skill gap |

Both are test pages outside the main flow, in [router.ts](../../src/frontend/src/router.ts) under `labPages`. The API client is [api/adoption.ts](../../src/frontend/src/api/adoption.ts).

**Where the roles come from:** both pages use `loadJobs()` → `GET /jobs/recommend`, exactly like the existing `/roles` page, sharing the same app state.
- `/jobs/recommend` only matches **8 tech roles** (`TECH_ROLES` in [jobs/service.py](../../src/backend/app/jobs/service.py)), all in SOC group 15.
- With no profile, adoption-roles shows 3 sample roles instead: Software Developer, Accountant, Registered Nurse.

**Skill chips** come from **O*NET only**: each role's top 6 tools and top 4 abilities by importance in `onet_role_skills.csv`, marked as have or need against the user's profile skills. They don't come from news or job ads.

**`/jobs/recommend` is an API endpoint, not a page.**
- Opening `<site>/jobs/recommend` hits the Vue catch-all and redirects to `/landing`.
- The working form is `<site>/api/jobs/recommend?profile_id=<id>`. The id is in the `jobee_profile_id` cookie.
- It reruns matching (OpenJev, falling back to the LLM) and overwrites the saved suggestions. `/api/jobs/suggested?profile_id=<id>` returns the saved result without recomputing.

### How it differs from the existing `/signal` page

| | `/signal` (main flow) | `/lab/adoption-signal` |
|---|---|---|
| Predicts | **Job postings** index per sector, inherited by each job | **% of workers using AI** per occupation group and job |
| Model | LightGBM ([train_lgbm.py](../../src/backend/ml/train_lgbm.py)) | Monte Carlo ([ai_adoption_mc.py](../../src/backend/ml/ai_adoption_mc.py)) |
| The 3 scenarios | Rapid / Baseline / Slow AI: a fixed ±0.25 × AI-exposure shift added after the model | Fixed multiples of the adoption trend |
| Odds | None | Weekly, from [ai_signal_score.py](../../src/backend/ml/ai_signal_score.py) |

### Backend

[forecast/service.py](../../src/backend/app/forecast/service.py) (from line 166) reads the precomputed CSVs and adds the latest odds. Endpoints:

| Endpoint | Returns |
|---|---|
| `GET /forecast/ai-adoption?group=&horizon=` | Per SOC major group |
| `GET /forecast/ai-adoption/jobs?onet_code=&title=` | Per job; uses its group's odds and signals |
| `GET /forecast/ai-adoption/odds-history?group=` | Weekly odds history |
| `GET /forecast/skill-demand?onet_code=` | Adzuna skill counts; empty for now |

Each response also has an `expected` rate, the odds-weighted average of the three p50s. **No page uses it yet.**

**Nothing is simulated when a page loads.** The CSVs are regenerated by hand: the Monte Carlo quarterly, the score weekly.
- The loading text "Running the Monte Carlo scenarios…" is misleading.
- The heading "How much AI will X use?" suggests intensity, but the number is the **share of workers who use AI at all**.

---

## 2. Data sources

| Source | What it gives | Where | Used for |
|---|---|---|---|
| **Real-Time Population Survey (RPS)**, Bick, Blandin & Deming, on FRED (`RPSGENAIUSAGESHAREOCC1–22`, `RPSGENAIUSAGESHAREWORK`) | % of employed US adults (18–64) answering yes to *"Do you use Generative AI for your job?"*, per SOC major group, **quarterly, Jul 2024 → Jul 2026 (9 quarters)** | [build_ai_adoption.py](../../pipeline/build_ai_adoption.py) → `data/processed/ai_adoption.csv` | The Monte Carlo's actual readings |
| **RPS occupation adoption index** (the authors' Google Sheet) | Same question pooled over 4 rounds (Aug 2025 – May 2026), by SOC broad / minor / major, with respondent counts | → `data/processed/ai_adoption_jobs.csv` | Each job's starting rate |
| **Indeed AI Tracker** | % of job ads mentioning AI, monthly since 2019, 9 countries | `signals.csv` (`ai_postings_share`) | Structured signal |
| **Census BTOS** | % of businesses using AI (`ai_use_rate`) and **expecting to use AI in the next 6 months (`ai_expect_rate`)**, biweekly since Sep 2023, 21 sectors. **The question wording changed in Nov 2025**, which breaks the series | [build_btos_ai.py](../../pipeline/build_btos_ai.py) → `btos_ai.csv` | Structured signal (`ai_use_rate` only) |
| **Adzuna API** (free tier: 25 calls/day, US only, no Malaysia site) | Live ad counts per category: AI share, skill counts | [collect_adzuna.py](../../pipeline/collect_adzuna.py) | AI share enters the score after 6+ weekly runs (1 so far) |
| **GDELT DOC 2.0** | News headlines (no article text) from a trusted-domain list ([news_sources.csv](../../pipeline/news_sources.csv), 56 domains in 3 trust tiers, mostly US and Malaysian) | [collect_news.py](../../pipeline/collect_news.py) → `news_articles.csv` | News part of the score |

The RPS is called "real-time" because it publishes within weeks; it is still quarterly. Everything except the Malaysian news is **US data standing in for Malaysia**, flagged with `is_proxy_for_malaysia`.

### Adzuna storage
- **Processed and in git:** `data/processed/adzuna_ai_share.csv` (22 rows for 2026-W43) and `data/processed/skill_demand.csv` (doesn't exist yet).
- **Raw and gitignored:** `data/raw/adzuna/` holds `calls_log.csv` (calls per day, used to enforce the 20/day budget), `<date>/<query>.json` (cached responses) and `categories_us.json`.
- **The raw folder lives on the machine that ran the collector (Replit), not in git.** Copy it over before running the collector elsewhere, or the daily call count starts from zero.
- **What counts as an "AI ad":** any of `ai llm chatgpt copilot genai openai` (`what_or`). The bare word "ai" may match ads that aren't about AI; spot-check it.

---

## 3. How the Monte Carlo works

File: [ai_adoption_mc.py](../../src/backend/ml/ai_adoption_mc.py). Outputs in `src/backend/ml/output/`:
- `ai_adoption_mc.csv`: group × scenario × horizon
- `ai_adoption_mc_jobs.csv`: the same per job
- `ai_adoption_mc_meta.json`: parameters and backtest

### Plain version
```
next quarter = this quarter + growth per quarter + random luck
```
Everything is computed on the **logit** (log-odds) of the rate, `x = ln(p / (1 − p))`, then converted back with `p = 1 / (1 + e^(−x))`. This keeps results between 0 and 100% and makes growth slow down near the top, like an S-curve.

A Monte Carlo still needs history because the equation has three unknowns that one reading can't give:
1. **Today's true level:** survey readings are noisy; Legal has about 25 respondents a quarter.
2. **Growth speed:** a trend line through the past quarters.
3. **Size of the luck:** how much the history wobbles.

### Steps
1. **Survey noise:** a reading's variance on the logit scale is `DEFF / (n · p · (1 − p))`, with design effect `DEFF = 3.0`.
2. **Trend:** a weighted line through the all-workers series gives the national slope. Each group's own slope is pulled toward it (empirical Bayes). With the current data the between-group spread `tau2 = 0`, so **every group uses the national slope** (`shrink_to_own = 0`).
3. **Today's level:** a Kalman filter (local level plus drift) separates real change from sampling noise. The process noise `q` is fitted by maximum likelihood.
4. **Paths:** 10,000 per group and scenario, 4 quarters ahead, using a fixed seed per data quarter:
   ```
   x0 ~ Normal(filtered level, its variance)
   b  ~ Normal(group slope, slope SE) + shift × national slope
   x(t) = x0 + b·t + (sum of t quarterly shocks, each ~ Normal(0, q))
   ```
5. **Scenarios** (assumptions, not learned). Because every group currently uses the national slope, these work out to 1.5×, 1× and −0.5× the trend:

   | Scenario | shift |
   |---|---|
   | AI accelerates | +0.5 |
   | AI holds | 0 |
   | AI declines | −1.5 |

6. **Jobs:** each job keeps its logit gap to its group: `x_job(t) = x_group(t) + logit(job pooled rate) − logit(group pooled rate)`.
7. **Output:** p10, p25, p50, p75 and p90 of the 10,000 paths at 3, 6, 9 and 12 months.

### Current fitted values (data up to Jul 2026)
- National slope: **0.0695 logit per quarter**
- Process noise q: **0.006**
- All workers today: **42.3%**. At 12 months: holds ≈ 49%, accelerates ≈ 53%, declines ≈ 39%.

### Where a job's starting rate comes from
It's the share of people in that job who said yes in the survey, nudged forward to the latest quarter. Software Developers as the example:

| Step | Value |
|---|---|
| Occupation index, "Software & web developers", 471 respondents, pooled Aug 2025 – May 2026 | 75.5% |
| Its group (Computer & Math) pooled over the same rounds | 72.8% |
| Group level today (Kalman-filtered FRED series, Jul 2026) | 72.7% |
| **Starting rate:** today's group level + the job's logit gap | **75.4%** |

If a cell has fewer than 20 respondents, the job falls back to its minor group, then its major group.

### Backtest of the "holds" scenario (in the meta file)
- The 10–90% range contained the real reading **79–84%** of the time. That calibration is good, and DEFF was tuned to reach it.
- The median forecast is about as accurate as "last reading repeats" at 3–6 months, and slightly better at 9–12 months:

| Horizon | p50 error | "Last reading repeats" error |
|---|---|---|
| 3 months | 6.5 pts | 6.4 pts |
| 12 months | 7.5 pts | 9.1 pts |

### Why the bands are almost symmetric
All randomness is normally distributed, with no fat tails or jumps. The only asymmetry comes from the logit near 100%. For Software Developers under "holds" at 12 months: p10 75.6%, p50 80.2%, p90 84.1%. The model puts all asymmetry *between* the scenarios instead of within them. Fat tails or jump shocks could be added, but they would be assumptions.

---

## 4. How the weekly score and odds work

File: [ai_signal_score.py](../../src/backend/ml/ai_signal_score.py). Outputs:

| File | Contents |
|---|---|
| `ai_signal_score.csv` | Week × group: score S, its two parts, the signals behind it |
| `scenario_odds_history.csv` | Week × group: odds of each scenario |
| `news_signals.csv` | Every headline the LLM read, with its labels |
| `llm_calls.csv` | Every LLM call |

So far there has been **one run (2026-W43)**.

### Structured ("Data") part
Each source asks: *is the latest change unusually fast or slow for this series?*
```
z     = (latest change − mean of past changes) / SD of past changes      (changes measured on the logit)
value = tanh(z / 2)                                                      (squashed to −1…+1)
```

| Source | Change measured | Groups |
|---|---|---|
| Indeed | 3-month change | National: the same value for every group |
| BTOS | 6-week change per sector, never across the wording break | Mapped to SOC groups via `btos_sector_soc_map.csv` |
| Adzuna | Weekly change | Only after 6+ weeks |

The structured part is the average of the sources covering a group. Example, Indeed (Sep 2026): the share went 5.88% → 7.15% in 3 months, a change of +0.21 logit against a past mean of +0.045 and SD of 0.12. That gives z = 1.38 and a value of **+0.60**.

### News part
1. **The LLM labels each headline.** It's `qwen/qwen3.7-flash` (`OPENROUTER_MODEL`, through the `llm.grafilab.ai` gateway), reading **headlines only**, 12 per call, at most 8 calls a run. For each headline it gives:
   - `direction`: accelerate / hold / decline
   - `strength`: 1–3
   - `soc_majors`: affected groups, or ALL
   - `region`
   - `is_fact`: true if it happened, false if it's an announcement. The LLM decides this from the headline alone; no rule in code checks it.
2. **Fixed rules in code weight each headline:**
   ```
   weight = direction(+1/0/−1) × strength × tier (1.0/0.8/0.5) × 0.5^(age/30 days)
            × (1 if fact else 0.5) × region (1 for MY/US/GLOBAL, else 0.5)
   ```
   - A strength-3 headline drops to 2 unless another domain reports a similar story within 14 days.
   - Only the last 60 days count.
   - At most one item per outlet, day and direction.
3. **News part** = `tanh(sum of weights / 5)`.

In the W43 run, several LLM calls timed out or returned invalid JSON, and **only 10 headlines counted**. The labelling is also loose: *"AI challenges maths by solving the unsolvable"* counted as acceleration.

### Score and odds
```
S = 0.6 × structured + 0.4 × news        (renormalised if one part is missing; S moves at most 0.3 per week)
odds(s) ∝ prior(s) × exp(K × S × direction(s))
prior = 25 / 50 / 25,  K = 1,  direction = +1 / 0 / −1,  each odds clipped to 10–60%
```
Worked example, Computer & Math: structured 0.42, news −0.24, so S = 0.16. The weights become 0.25·e^0.16, 0.50 and 0.25·e^−0.16, which normalise to **29% / 50% / 21%**.

| S | Accelerates | Holds | Declines |
|---|---|---|---|
| −1 | 10% | 38% | 52% |
| 0 | 25% | 50% | 25% |
| +0.16 (now, group 15) | 29% | 50% | 21% |
| +0.5 | 38% | 47% | 15% |
| +1 (maximum) | 52% | 38% | 10% |

**What happens with a huge AI breakthrough:**

| Case | S | Accelerates |
|---|---|---|
| Today, group 15 | 0.16 | 29% |
| + one major, corroborated headline | 0.35 | ~34% |
| + three of them (hits the weekly cap) | 0.46 | ~38% |
| Theoretical maximum | 1.0 | ~52% |

And even at 100% odds, "accelerates" is still only 1.5× today's trend: about 82% instead of 80% for Software Developers at 12 months.

### Why every role shows the same "What we saw"
Signals are per **SOC group**, not per job.
- All 8 matched roles are in group 15, so they get identical signals.
- Across groups the lists are still nearly the same: Indeed is national, BTOS varies a little by sector, and most news is tagged ALL.

---

## 5. Known problems

1. **The odds are hand-built and untested.** Starting odds, K, the clip limits and the news weights are all chosen by us, and the odds have never been scored against outcomes.
2. **The odds hardly move.** "Holds" stays between 38% and 50%, and "accelerates" can't pass about 52%.
3. **The scenarios are fixed multipliers.** No evidence can produce a future faster than 1.5× the trend.
4. **Thin target data:** 9 quarters × 22 groups, US only.
5. **News is headline-only and the labelling is loose.** LLM calls often fail (timeouts, invalid JSON), and `is_fact` is pure LLM judgement.
6. **The skill demand panel is empty, and the current Adzuna `--skills` design wouldn't fill it well.** It searches one O*NET tool per job as an exact phrase, and the O*NET names aren't how ads are written:
   - "Structured query language SQL"
   - "Amazon Web Services AWS"
   - "The MathWorks MATLAB"
   - "Orion Law Management Systems Orion"

   Most would return close to 0 ads, and it would use most of a day's free calls. **Don't run `--skills` as it is.**
7. **Text problems on the pages:** misleading loading text, the intensity-sounding heading, and `expected` unused (see section 1).
8. **Docs out of date:**
   - The architecture diagram in AI_ADOPTION_PLAN.md still lists GitHub Innovation Graph, which was dropped.
   - The plan says 5 calls × 40 headlines; the code uses 8 × 12.

---

## 6. Comparison with the LightGBM job-postings model

| | LightGBM (postings) | Monte Carlo (adoption) |
|---|---|---|
| History | Monthly since 2020, 53 sectors, 6 countries (~22k rows) | 9 quarters, 22 groups, US |
| Learns from data | Yes, trees on lags and AI share | Only a trend line and noise levels |
| Beats simple baselines? | **No.** 3-month MAPE: LightGBM 4.43% vs "flat" 3.76% (`model_meta.json`). The app shows a "last year's pace repeats" (yoy) headline instead | About equal to "last reading repeats" |
| AI scenarios | Assumption: ±0.25 × exposure | Assumption: trend multipliers |

**Both have the same core gap: the effect of AI is assumed in both, never learned.**

---

## 7. Experiments (23 Oct 2026)

These were quick checks to see whether a redesign is worth doing. The scripts were run from a temporary folder and are **not in the repo**; the methods below are enough to reproduce them. All scores are out-of-sample: fitted on earlier data and scored on later data.

### Check 1: Do BTOS expectations predict actual use? ✅ Yes, strongly
**Method:** for each sector and each biweekly period t, forecast `ai_use_rate` 13 periods (~6 months) later. Data:
- old wording only (Sep 2023 – Sep 2025), 16 sectors
- 287 training and 160 test pairs; the test set is the last third of dates

| Forecast | 6-month MAE |
|---|---|
| No change | 2.70 pts |
| Last 6 months' trend repeats | 1.98 pts |
| Fitted trend | 1.56 pts |
| Fitted trend + (expect − use) gap | 1.37 pts |
| **`ai_expect_rate` taken literally** | **1.19 pts** |

- Correlation between the expectation gap and the next 6 months' change: **0.56** on the test set.
- **At ~3 months:**
  - Old wording: fitted trend + gap 1.17 vs trend 1.31 vs no change 1.42.
  - New wording (since Nov 2025): only 3-month pairs are possible yet. Expectation 2.23 vs no change 2.98, but a tie with the fitted trend (2.04).
- **Caveat:** the test period was a steady rise, so this should be rechecked as new data arrives.

### Check 2: Do major model releases speed up adoption? ❌ No separate effect
**Method:** an event study with 13 hand-listed releases, dated to the month from memory, so worth verifying:

| Date | Release | Tier |
|---|---|---|
| 2022-11 | ChatGPT | A |
| 2023-03 | GPT-4 | A |
| 2023-11 | Microsoft 365 Copilot GA | A |
| 2023-12 | Gemini 1.0 | B |
| 2024-03 | Claude 3 | B |
| 2024-05 | GPT-4o | A |
| 2024-06 | Claude 3.5 Sonnet | B |
| 2024-09 | OpenAI o1 | A |
| 2025-01 | DeepSeek R1 | A |
| 2025-03 | Gemini 2.5 | B |
| 2025-05 | Claude 4 | B |
| 2025-08 | GPT-5 | A |
| 2025-11 | Gemini 3 | A |

For each release, abnormal change = (logit change over the window after the release) − (the 12-month pre-trend scaled to the window). This was compared with 4,000 sets of random placebo dates.

Indeed AI share, all 13 releases:

| Window | US abnormal | p (placebo) | Countries with p < 0.10 |
|---|---|---|---|
| 3 months | +0.05 | 0.16 | 0 / 9 |
| 6 months | +0.11 | 0.23 | 0 / 9 |
| 9 months | +0.19 | 0.28 | 0 / 9 |
| 12 months | +0.29 | 0.33 | 0 / 9 |

Tier-A-only gives the same picture, and so does BTOS (p = 0.41–0.76).

**Reading:** the abnormal change grows with the window, but random dates grow just as much.
- With a release every 2–3 months since 2023, every month is within 6 months of some release. A slow, cumulative release effect can't be told apart from the trend: it *is* the trend.
- So: no single release adds a visible effect beyond ongoing growth. A separate "big news → raise odds" step would likely count the effect twice.
- **A better test,** not done yet: use **release size** (e.g. benchmark score jumps) and check whether bigger jumps lead to faster growth 6–12 months later. With about 13 events the result would still be uncertain.

### Check 3: Does the amount of AI news predict adoption? ❌ Weak and inconsistent
**Method:** monthly attention series. Target: the next 3-month logit change. Model: own trend vs own trend plus attention (3-month change and level vs its 12-month mean). Expanding window, test from 2024-07.

| Series | Trend only | + Wikipedia pageviews | + GDELT AI-at-work volume |
|---|---|---|---|
| Indeed US | 0.069 | 0.075 | 0.067 |
| Indeed GB | 0.066 | 0.073 | 0.073 |
| Indeed CA | 0.206 | 0.191 | 0.193 |
| Indeed AU | 0.092 | 0.081 | 0.096 |
| BTOS US (7 test months) | 0.100 | 0.165 | **0.066** |

Values are MAE in logit units. "GDELT AI-at-work volume" is the sum of the `ChatGPT`, `"generative AI"`, `Copilot` and `"AI tools"` timelines.
- GDELT volume helps BTOS, but that rests on only 7 test months.
- GDELT regulation/ban volume *also* "predicts" faster BTOS growth (correlation +0.48), which is the wrong direction for a real effect. Volume seems to track "more AI news overall", which rises with the trend.

### Why GDELT kept failing (HTTP 429)
- The limit isn't only "1 request per 5 seconds". The 429 message adds *"or contact us for larger queries. High-traffic users should switch to our ngrams dataset."* **Heavy queries are throttled:** several OR terms plus `sourcelang` over 6 years of daily data kept failing even at 12–45 second spacing, while a single-word query over the same span worked.
- Throttling also seems to depend on server load: single-word queries sometimes needed 1–2 retries at 15–45 seconds.
- **Terms shorter than 3 characters are rejected** with a plain-text, non-JSON reply. For example, `"AI" layoffs` fails.
- **Workaround for history:** one simple query per term, spaced 15+ seconds apart, retrying on 429. For bulk history, use GDELT's ngrams dataset or BigQuery.

---

## 8. Suggested redesign

**Idea:** forecast series with long, frequent history, use the signal that actually predicts (business expectations), and only show probabilities that can be checked against outcomes.

| Now | Replace with |
|---|---|
| Monte Carlo on 9 RPS quarters with hand-set scenario multipliers | A **trained forecast per BTOS sector**: `use(t+h) = use(t) + β·(expect(t) − use(t)) + γ·trend`, possibly as LightGBM quantile regression pooled over sectors (and Indeed countries), with **ranges calibrated on past errors** (conformal) |
| Odds from a hand-made score S | **Probabilities read from the forecast distribution.** Scenarios defined by data, e.g. growth in the top / middle / bottom third of past changes. Scored every period with a **Brier score** |
| News moves the odds | **News as context only** ("what happened this week"). Optionally re-test GDELT volume as a feature once there are more months |
| Group → job | Keep: BTOS sector → SOC group (`btos_sector_soc_map.csv`) → job. **Convert "% of businesses" to "% of workers"** by calibrating against the RPS series |
| LightGBM postings model's ±0.25 AI shift | Later: use the forecast AI adoption change as a learned input to the postings model |

**Build approach:** a new `src/backend/ml/ai_adoption_forecast.py` next to the current files. Compare side by side, then switch the endpoints. Keep the existing endpoints' responses unchanged until then, as the original plan required.

**Limits that stay:**
- It's still US data standing in for Malaysia.
- The post-ChatGPT history is only about 3 years.
- The new-wording BTOS series is short, about 23 periods so far.

---

## 9. Parked: live skill demand from job ads

Agreed but not started. It replaces the current one-tool phrase search (problem 6).

```
Adzuna search per job title (results_per_page=50, ~500-char description snippets)
  → LLM extracts the skills mentioned, normalised to the resume vocab (app/resume/vocab.py)
  → % of ads mentioning each skill, per job and rolled up per SOC group
  → flag skills common in ads but missing from O*NET as "emerging"
```

- O*NET key skills stay the baseline. Live demand reorders and extends them.
- Scope first to the 8 tech roles: about 8–16 Adzuna calls and 8–12 LLM calls a month.
- **News was rejected as a source for this:** we only get headlines, about 10 relevant ones a week, and they rarely name skills. An optional "trending tech" tag from news could be shown as hints only.
- The "Live job ads" panel should then show the user's key skills with "% of live ads in this field asking for it", marked have or need.

---

## 10. Open decisions for whoever picks this up

1. Build the redesign in section 8, or first run the release-size test from check 2?
2. Interim fixes if the current model stays for the demo:
   - raise K to 2 and/or add a "breakthrough" scenario (e.g. 3× trend, ~5% prior)
   - show `expected` as the headline number
   - fix the loading text and heading
3. Whether to keep the LLM news step at all. If kept, fix the timeouts and invalid-JSON failures, and add a stricter relevance filter.
4. When to build the job-ad skill demand pipeline (section 9).
5. Copy `data/raw/adzuna/` from Replit before running Adzuna anywhere else.

## Refresh cheat sheet (current system)

| When | Run |
|---|---|
| Weekly | `pipeline/collect_adzuna.py` (AI share, 22 calls, ≤20/day), `pipeline/collect_news.py`, `src/backend/ml/ai_signal_score.py` |
| Monthly | `pipeline/refresh.py` (Indeed, BTOS), then `ai_signal_score.py`. **Not** `collect_adzuna.py --skills` until problem 6 is fixed |
| Quarterly | Delete `data/raw/rps/`, run `pipeline/build_ai_adoption.py`, then `src/backend/ml/ai_adoption_mc.py` |
