# Forecast Rebuild: Design, Audit and Results

Branch `feat/ai-prediction`. This replaces the AI-adoption forecasting on `feat/ai-adoption-mc` (left unchanged, reference only) with a pipeline that is point-in-time, source-separated and tested out of time. The brief is `AI_PREDICTION_ADOPTION.md`; progress is logged in `FORECAST_REBUILD_PROGRESS.md`.

**Status (24 Oct 2026):** three separate targets run end to end on one shared engine. Each goes: ingest point-in-time data → features → train → rolling-origin backtest → locked holdout → ablations → timestamped forecast → promotion.

| Target | Domain | Data | Horizons |
| --- | --- | --- | --- |
| `ai_mention_share` | skill demand | Indeed, 9 countries, monthly | 1, 3, 6 months |
| `btos_ai_use_rate` | business adoption | Census BTOS, US + 19 sectors, per wording, fortnightly | 6, 13 fortnights |
| `worker_genai_use_rate` | occupation adoption | RPS worker survey, 22 SOC groups + all workers, quarterly | 1, 2 quarters |
| `frontier_time_horizon` | AI capability | METR 50% task time horizon of the best model, via Epoch AI, per METR suite version, monthly | 3, 6, 12 months, with P(faster / same / slower), from the capability engine (§8c) |

None feeds another.

- **Capability is one dimension.** The Epoch Capabilities Index is stored but not modelled: it only appears in Epoch's data from Sep 2026, and it is refitted jointly, so it cannot be backtested honestly yet.
- **There is no scenario engine.**
- **Adzuna is context only:** the account is on the free tier, so its snapshots will stay too thin to train on (decision of 24 Oct 2026).

---

## 1. Audit of the previous implementation

### What it did

| Component (on `feat/ai-adoption-mc`) | What it did |
| --- | --- |
| `pipeline/build_btos_ai.py` | Census BTOS: % of firms using AI / expecting to, per NAICS sector, biweekly, two question wordings kept apart |
| `pipeline/build_ai_adoption.py` | RPS worker survey via FRED: % of workers using GenAI per SOC major group, quarterly |
| `src/backend/ml/ai_adoption_mc.py` | Monte Carlo of worker adoption with hand-set scenario drifts (+0.5 / 0 / −1.5 × national slope) |
| `src/backend/ml/ai_adoption_forecast.py` | Trained forecast: BTOS sector rates → SOC groups → workers → jobs, with scenario odds |
| `src/backend/ml/ai_signal_score.py` | Weekly score: 0.6 × structured z-scores + 0.4 × LLM-read news, moves scenario odds |
| `pipeline/collect_adzuna.py`, `ad_skills.py` | Weekly Adzuna snapshots: AI share per category, O\*NET tools named in ads |
| `pipeline/collect_news.py`, `build_news_feed.py` | GDELT article lists from trusted domains, keyword topic tags |
| Frontend `AdoptionSignalView.vue`, `AdoptionRolesView.vue`, `api/adoption.ts` | Pages showing the adoption forecast and odds |

### Why it became BTOS-biased

1. **BTOS was both the label and the main predictor.** `ai_adoption_forecast.py` names `btos_ai.csv` "the target and the main predictor". Every feature but one (`gap`, `trend`, `trend_missing`, `new_wording`) came from BTOS itself.
2. **Occupation adoption came from BTOS by construction.** The worker forecast was `λ × forecast business change` of the group's BTOS sectors, with `λ = RPS trend / BTOS trend` (step 6). Whatever BTOS did, every occupation followed.
3. **A firm survey spread over occupations by hand.** `btos_sector_soc_map.csv` mapped NAICS sectors to SOC groups with hand-chosen weights. Nothing validated it. Jobs then kept a fixed logit gap to their group, so no job had evidence of its own.
4. **Scenarios were defined by BTOS.** "AI accelerates / holds / declines" were the top, middle and bottom thirds of past BTOS sector changes, and the odds were shares of the BTOS forecast range.
5. **Other sources only adjusted BTOS.** Indeed entered as one 3-month-change feature, and it was set to **0.0 when missing** (silent zero imputation). The news and structured score was mixed at fixed 0.6 / 0.4 weights, not learned.

### Evaluation weaknesses

- **No data vintages.** All backtests read today's revised files. Indeed's AI share has been revised by 0.39 pp on average and up to 1.6 pp (section 4). That is the same size as the forecast errors, so old backtest scores carried look-ahead.
- **Ranges tuned on the evaluation.** In `ai_adoption_mc.py` the design effect `DEFF = 3.0` was "set so the backtest's 10–90% ranges hold ~80%".
- **Untestable assumptions served as forecasts.** The scenario drifts (MC), the ±0.25 scenario shift and the 45/35/20 odds (main-line LightGBM) were all typed-in assumptions.
- **No source ablations,** so nobody could tell whether removing BTOS changed anything.
- **Main-line LightGBM** (`src/backend/ml/README.md`) did not beat the "no change" or "constant growth" baselines at any horizon, but it is still served as the "model" line.

## 2. Reuse / replace / discard

| Component | Verdict | Reason |
| --- | --- | --- |
| Indeed Hiring Lab repos as sources (`refresh.py` clones) | **Reused, replaced the fetch** | Valid, licensed sources. The shallow clone was replaced by a partial clone of the **full history**, because each commit is a published vintage |
| `build_signals.py` monthly-mean and partial-month logic | **Reused (reimplemented)** in `forecasting/vintages.monthly` | Verified behaviour. The original stays for the existing app |
| Existing app (`signals.csv`, `train_lgbm.py`, `job_forecast.py`, `/forecast` API, frontend) | **Kept unchanged, not used** | Still serves the app. Not validated: its own README shows it loses to baselines |
| Python stack (pandas, scikit-learn, LightGBM, pytest in `src/backend/venv`) | **Reused** | No new dependencies |
| `build_btos_ai.py` (old branch) | **Reused (design), reimplemented** as `forecasting/btos.py` | Its good parts were kept: wordings apart, SE kept, suppressed cells blank. Added: Census publication dates (availability), `.` (not asked) kept apart from `S` (suppressed), the full fortnight calendar including the three unasked fortnights, and dated raw copies. Used **only** as the business-adoption label and features |
| `build_ai_adoption.py` (RPS) | **Partly reused** in `forecasting/rps.py` | Only the verified FRED series → SOC mapping was kept. The invented `respondents_per_quarter` (pooled ÷ waves) is **dropped**. Availability dates come from ALFRED with a key; without one they are assumed and labelled |
| `collect_adzuna.py`, `ad_skills.py` | **Not used for models** | Sound design, but the account stays on the free tier (25 calls/day), so snapshots will not reach a trainable history. Registered as context only |
| `collect_news.py`, `build_news_feed.py` | **Reuse later as context** | GDELT article lists are useful context. A feature needs the timeline mode and must pass the ablation test before use |
| `ai_adoption_mc.py` | **Discarded** | Hand-set scenario drifts; DEFF tuned on the backtest |
| `ai_adoption_forecast.py` | **Discarded** | BTOS-as-everything design (section 1) |
| `ai_signal_score.py` | **Discarded** | Fixed weights, LLM-scored news moving odds, clamps chosen by hand |
| Adoption frontend pages and `api/adoption.ts` | **Not ported** | They show discarded outputs. The UI will be rebuilt on `latest_forecast.csv` |

## 3. Targets and data contracts

`src/backend/forecasting/contracts.py` declares one target per domain. `registry.py` records what each source measures and the domains it may be a **label** or a **feature** for. `check_sources()` runs before any model is fitted and refuses every other use. A second hard-coded list of forbidden substitutions still applies if someone loosens the registry (tested).

| Target | Domain | Label source | Status |
| --- | --- | --- | --- |
| `ai_mention_share`: monthly % of new Indeed postings mentioning AI terms, per country | skill demand | Indeed AI Tracker | **implemented** |
| `btos_ai_use_rate`: % of US firms using AI, within one wording | business adoption | Census BTOS | **implemented** |
| `worker_genai_use_rate`: % of workers in a SOC group using GenAI | occupation adoption | RPS | **implemented** |
| `frontier_time_horizon`: longest METR 50% time horizon among models released by each month, per METR suite version | AI capability | METR via Epoch AI | **implemented** |

Refused by contract (each one tested): BTOS as a skill-demand feature; BTOS or task exposure (Anthropic EI) as an occupation-adoption label; AI skill demand as adoption; posting volume as skill demand; news volume as capability.

The three implemented models use only their own source: skill demand uses Indeed, business adoption uses BTOS, and occupation adoption uses RPS. A test checks this for every target.

**Engine:** each target is a module in `forecasting/targets/` exposing a `TargetSpec`. The spec says how to load the data, cut a snapshot at an origin, build features, label periods, and how much history to require. Feature code (`features.py`), models (`models.py`), evaluation (`evaluation.py`) and promotion (`run.py`) are shared. After the refactor, the skill-demand backtest reproduced all 26,040 earlier predictions exactly.

## 4. Data: point-in-time vintages

- **Raw layer:** `data/raw/vintages/ait_full`, `jpt_full` (gitignored). These are partial git clones of `hiring-lab/ai-tracker` and `hiring-lab/job_postings_tracker` holding the data-file blobs of every commit. A vintage is identified by its commit SHA and blob SHA, and is available from its commit time (UTC).
- **Normalised layer:** `data/processed/forecasting/ai_share_vintages.csv` (35 vintages, Apr 2024 → Oct 2026) and `postings_vintages.csv` (the last vintage of each month per country, Feb 2021 → Oct 2026). Columns are in `STRUCTURE.md` §9.
- **Lookup:** `vintages.as_of(table, T)` returns the latest vintage with `available_at ≤ T`. The AI tracker is one file, so all countries come from one vintage. Postings are one file per country, so each country uses its own latest vintage.

What the history showed:

- **Revisions are large.** Between the first and latest vintage, the same country-month moved by 0.39 pp on average and up to 1.58 pp.
- **Four schema changes.** The value column was renamed four times; the early files use day-first dates (`29/3/24`); and before mid-2021 postings were published as % change rather than an index. The parser picks the date format that makes each file's dates run day by day. An unknown column fails the build.
- **Two vintages (mid-2024) also publish counts** (`AI_count`, `total`). They are kept as `numerator` / `denominator`, and left blank everywhere else, never set to 0.
- **The country set changes** (ES, IN, SG and JP appear and disappear).
- **Publication lag** is 1 month (2 at most).
- **No vintage exists before 29 Apr 2024.** Origins before then are *reconstructed*: the first vintage cut at the origin's month, published 2 months later. They carry later revisions, so they are flagged `vintage_kind = reconstructed` and reported apart. The holdout uses real vintages only.

## 5. Features and models

- **Modelling scale** (set per target):
  - shares use the logit;
  - METR time horizons use log₂ (minutes), so a constant doubling time is a straight line.

  The label at anchor period *p* is `y[p+h] − y[p]` on that scale. Training rows are every unit × anchor period whose *p + h* is inside the origin's snapshot.
- **Errors** are reported in percentage points for shares and in **doublings** for time horizons. On a minutes scale, a 20% miss at 1,000 minutes would count 100× a 20% miss at 10 minutes.
- **Feature groups** (each one can be dropped in an ablation):
  - `level`: `lvl`
  - `own_trend`: `d1 d3 d6 d12`
  - `cross_country`: `xc_d3 xc_d12`
  - `postings`: `post_d3 post_d12`, from Indeed postings
- **Missing values** stay NaN. Ridge imputes medians with missing-indicator columns, fitted on the training rows only. Drift-type baselines treat a missing trend as "no change".

| Candidate | What it is |
| --- | --- |
| naive | No change |
| drift | The country's last 12-month change continues |
| damped_drift | Drift with a damping factor φ fitted on the snapshot |
| pooled_mean | Average h-month change across countries over the last 12 months |
| local_trend | Local-linear-trend state-space model (the spec's primary capability model). Observation = level + noise; the level moves by a slope that drifts. Variances are fitted by Kalman-filter maximum likelihood on the snapshot. Forecast = level + h × slope. Runs as a candidate for every target |
| ridge | Ridge on all feature groups. α is chosen by time-ordered inner CV with an h-month gap |
| lightgbm | Challenger: 4 leaves, ≥30 rows per leaf, λ = 5, 150 trees, no early stopping |

## 6. Evaluation procedure

- **Origins:** one per last observed month: 38 reconstructed (L = 2021-01 → 2024-02) and 27 real (L = 2024-03 → 2026-09). At each origin every candidate is refit on that origin's snapshot alone.
- **Outcome:** the latest vintage's value for L + h, in percentage points. Origins whose outcome is not yet published are reported as unavailable, never as zero error.
- **Split, fixed before scoring:**
  - **Holdout:** the last 20% (at least 6) of origins that can be scored at h = 6, plus every later origin. On this run that means origins from 14 Feb 2025 on: 18 origins, all real vintages.
  - **Selection:** the earlier origins, *purged*: any (origin, h) whose outcome month falls after the first holdout origin's last observed month is dropped.
- **Selection rule:** the lowest selection MAE (pp) wins. A simpler candidate within 2% of the best is preferred. The winner is scored **once** on the holdout, next to naive.
- **Metrics:**
  - MAE, RMSE and bias, in pp.
  - MASE against naive, on the same pairs.
  - 80% interval coverage on the holdout. Ranges are the 10th–90th percentiles of out-of-sample logit residuals; holdout coverage uses residuals from the selection period only.
- **Ablations:** ridge and LightGBM are rerun without each feature group, on the same origins.
- **Promotion** (`model_registry.json`): a run replaces the promoted model for a horizon only if:
  - the target source is fresh;
  - the holdout has ≥ 6 origins;
  - the scores are finite;
  - there are ≥ 12 selection origins.

  A rejected run is kept in `runs/` and the log, and the previous model stays in service (tested).
- **Status label:**
  - `validated`: the chosen model's holdout error is at least 5% below naive's (MASE ≤ 0.95);
  - `baseline`: naive was chosen;
  - `not_demonstrably_better`: the chosen model is between 5% better and equal to naive on the holdout;
  - `baseline_retained`: the chosen model was *worse* than naive on the holdout, so naive is served instead. The chosen model is still recorded (`chosen_model`).

  Both the 5% margin and the `baseline_retained` gate were added after seeing results, and they are disclosed here:
  - the margin after an RPS run labelled a 0.03% "gain" on three noisy origins as `validated`;
  - the gate after BTOS h=13 chose `local_trend`, which then lost to naive by 70% on the new-wording holdout.

  Neither re-selects on the holdout. They only stop a model that failed the baseline comparison from being labelled or served as if it had passed (spec 16.1).
- **Second baseline:** every run also reports holdout MASE against **drift** (`holdout_mase_vs_drift`). For trending series, beating "no change" is easy; beating trend extrapolation is the real bar.
- **Ranges:** forecast ranges use all out-of-sample residuals of the served model. If they all fall on one side (the model has always under- or over-forecast), the point lies outside its own range. The forecast then says so in `warnings`, and the range should be read rather than the point. This happens for BTOS h=13 naive, which has always under-forecast the new wording.
- **Regime probabilities** (capability only), per spec 10.1:
  - the forecast change over the next h months is compared with the trailing rate (change over the last 12 months, scaled to h);
  - it counts as **acceleration** or **slowdown** only beyond ±25% of that rate (and at least 0.02 log₂ per month);
  - probabilities are the share of past out-of-sample residuals, added to the forecast, that fall in each band, so they sum to 1;
  - they are scored on the holdout with the **Brier score**, against climatology (the selection period's regime frequencies) and a uniform ⅓ each.
- **Per target:** the minimum holdout and selection sizes are set in each `TargetSpec`. Skill demand and BTOS require 6 holdout and 12 selection origins. RPS has only 9 quarters, so it requires 2 and 3, and every RPS forecast carries a short-history warning.

## 7. Results: skill demand (promoted run `20261024T043443Z-3b51da`)

MAE in percentage points. Selection covers 42–47 origins; the holdout covers 12–17 real-vintage origins with 9 countries each.

| h | Chosen | Selection MAE (naive) | Holdout MAE (naive) | MASE vs naive | MASE vs drift | Best on holdout (not usable for choosing) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | pooled_mean | 0.362 (0.374) | 0.371 (0.484) | 0.77 | 0.95 | pooled_mean / ridge 0.371 |
| 3 | pooled_mean | 0.411 (0.432) | 0.709 (1.075) | 0.66 | 0.97 | pooled_mean |
| 6 | naive | 0.523 (0.523) | 2.045 (2.045) | 1.00 | 1.65 | drift 1.242 |

Holdout 80% interval coverage of the chosen models: 0.84 (h1), 0.90 (h3), **0.57 (h6)**.

What the results mean:

- At 1 and 3 months the chosen simple models beat "no change" on data they never saw, by 23% and 34%. Against drift the edge is small (3–5%).
- **h=1 changed** from drift to pooled_mean when `local_trend` joined the candidates. `local_trend` scored best in selection (0.359), which put drift (0.367) just outside the 2% band. The holdout error improved from 0.389 to 0.371.
- **At 6 months the selection period picked naive, which then did badly on the holdout.** AI-mention shares rose much faster from 2025 on than in 2021–24, and naive's 80% range held only 57% of outcomes. The rule was not changed after seeing this; choosing again on the holdout would be tuning on it. The 6-month forecast is served as `baseline`, and this failure is the most important known weakness.
- **Ridge, LightGBM and local_trend** never won selection by more than the 2% band, so none is deployed.
- **Ablations:** removing the postings group changes selection MAE by −0.009 to +0.024 pp depending on model and horizon, with no consistent sign. Posting volume therefore adds no demonstrated value. Removing cross-country trends *improves* h = 6 by about 0.04 pp. Neither changes which model is chosen.
- **Real vs reconstructed:** naive's selection MAE is 0.43 pp on reconstructed origins and 0.50 pp on real ones. Reconstructed scores are, if anything, not flattering, but they should still be read as approximate.
- All forecasts underpredicted during the holdout (naive bias −1.1 pp). The ranges are therefore skewed upward, which is visible in `latest_forecast.csv`.

## 8. Model card: `ai_mention_share`

- **Intended use:** an indicative outlook for the share of new job ads mentioning AI, per country, 1/3/6 months past the last published month.
- **Not a measure of:** AI adoption, employment, or Malaysian demand. There is no Malaysia series; the 9 countries are AU, CA, DE, FR, GB, IE, IT, NL and US.
- **Training data:** the Indeed AI Tracker vintage available at the forecast time, 2019-01 onward, plus Indeed postings vintages (feature group, no demonstrated gain).
- **Versions:** each run records `model_version` (a hash of the code), `git_commit`, the AI vintage IDs and `data_as_of`.
- **Supported claims:** h1 and h3 beat persistence on a 2025–26 holdout built from real vintages. For h6 there is no supported claim beyond "naive baseline". Its range under-covered (57%) in a period of fast growth.
- **Failure modes:**
  - sudden regime changes, such as the 2026 jump (CA 5.6% → 18.4% within a year);
  - keyword-definition changes at Indeed;
  - revisions of up to 1.6 pp.
- **Promotion status:** see `src/backend/forecasting/output/ai_mention_share/model_registry.json`.

## 8a. Business adoption (`btos_ai_use_rate`)

**Data** (`forecasting/btos.py` → `data/processed/forecasting/btos_ai_observations.csv`, `btos_calendar.csv`):

- Q7 (used AI in the last two weeks) and Q24 (expects to within six months), for the US and 19 NAICS sectors, with standard errors.
- **Old wording** ("AI in producing goods or services"): fortnights 202319–202520 (54).
- **Not asked:** 202521–202523, published as `.`.
- **New wording** ("SI/AI in any business function"): 202524–202621 (24). The national level jumps from 10.0% to 17.3% at the change.
- Each wording is its own series, so no feature, label or lag crosses the break (tested). A fortnight is available from the end of its Census publication day.
- Estimates are assumed unrevised once published. Every download is kept with its date, so this can be checked from now on.

**Features:**

- `level`
- `own_trend`: d1, d3, d6, d13 fortnights
- `cross_sector`: mean change over all units
- `expectation`: logit(% expecting) − logit(% using), same unit and fortnight

All of these come from BTOS. Here BTOS is the label, so using it is legitimate.

**Split:** selection is entirely old-wording data (41 origins at h=6, 27 at h=13). The holdout (from 26 Sep 2025) is entirely new-wording data (18 and 11 origins). It therefore tests whether a choice made on one wording holds on the other.

| h (fortnights) | Chosen | Selection MAE (naive) | Holdout MAE (naive) | Holdout MASE | 80% coverage | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 6 (~3 months) | naive | 1.11 (1.11) | 2.34 (2.34) | 1.00 | 0.91 | baseline |
| 13 (~6 months) | local_trend → **naive served** | 1.45 (2.15) | 7.15 (4.21) | 1.70 | 0.54 | baseline_retained |

h=13 changed after `local_trend` joined the candidates. Before that, ridge was chosen and beat naive by 11% (MASE 0.89). `local_trend` won selection on the old wording by 1%, then failed on the new wording: with few post-break fortnights it extrapolates unstable slopes. Naive is therefore served. Its range lies above its point forecast (adoption has always risen faster than "no change"), and the forecast carries that warning.

What it means:

- **Sampling noise is a large part of the error.** Under the new wording the mean sector standard error is 1.9 pp, against 0.3 pp nationally. That puts a floor under any sector forecast.
- **Every model under-forecast the new wording** (naive bias −1.6 pp at h6, −4.0 pp at h13): national adoption rose from 17.3% to 24.6% in under a year. pooled_mean would have done best on the holdout (MASE 0.85 / 0.68), but it was not chosen on the selection data, and the rule was kept.
- **Ablations:** dropping the expectation gap makes ridge worse (+0.065 pp at h6). Firms' own expectations carry signal for firm adoption. Dropping cross-sector averages helps (−0.09 pp at h6).
- **Model card:**
  - Intended use: US firm-level AI use, by sector, about 3 and 6 months ahead, in the new wording only.
  - Not a measure of worker or occupation adoption, and not transferable to other countries.
  - Supported claim: none beyond the baseline at either horizon. Both serve naive, and naive has consistently under-forecast the new wording, so read the ranges.

## 8b. Occupation adoption (`worker_genai_use_rate`)

**Data** (`forecasting/rps.py` → `rps_observations.csv`): the Real-Time Population Survey, the % of employed US adults using GenAI for their job. It covers 22 SOC major groups plus all workers ("00"), quarterly from 2024-Q3, 9 readings per group. It is worker-level evidence, so **no BTOS or task-exposure input is used**.

**Availability:**

- With `FRED_API_KEY` set (read from `src/backend/.env`), `rps.py` reads every FRED release (ALFRED). FRED first published the whole series on **18 Jun 2026**, then revised it on **16 Oct 2026**. For example, all workers in 2025-Q4 went from 40.73 to 40.65, and 2026-Q1 from 43.41 to 42.84. Q3 2026 appeared on 16 Oct.
- That gives **2 real origins** (Jun and Oct 2026). Earlier quarters are cut from the first FRED release and labelled `reconstructed`.
- FRED's date is an upper bound: the authors published earlier on their own site.
- Without a key, values are today's, each assumed available 21 days after its quarter ends (kind `current_only`).

**Features:** `level`, `own_trend` (d1, d2, d4 quarters) and `all_workers` (mean change over groups).

**Evaluation:** 7 origins (2025-Q1 → 2026-Q3; 5 reconstructed, 2 real): 3 for selection and 4 holdout. Run `20261024T055908Z-4dcc4c`, with FRED vintages.

| h (quarters) | Chosen | Selection MAE (naive) | Holdout MAE (naive) | Holdout MASE | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | pooled_mean → **naive served** | 6.98 (7.26) | 6.71 (6.55) | 1.03 | baseline_retained |
| 2 | pooled_mean | 7.88 (8.50) | 9.08 (6.84) | 1.33 | **not promoted**: insufficient history (2 selection origins) |

With today's values and assumed dates, pooled_mean tied naive at h=1 (MASE 1.00). Scored against the revised FRED values it is slightly worse, so the baseline is served. Only one holdout origin is a real vintage.

What it means:

- Errors of 6–9 pp come mostly from survey noise in small groups. For example, Management reads 55.9 → 48.1 → 51.9 → 49.6 → 61.4 over five quarters.
- With 2–3 scored origins, nothing can be shown to beat "no change". The served 1-quarter forecast is effectively the current level plus the recent average change, with a wide range (e.g. computer and mathematical occupations: 68.8% now, 57–79%).
- **Model card:**
  - Intended use: a cautious near-term view of US worker GenAI use, by broad occupation group.
  - Supported claims: none beyond "indicative".
  - Will improve as quarters accumulate and if ALFRED vintages are enabled.

## 8c. AI capability (`frontier_time_horizon`)

**Data** (`forecasting/capability.py` → `capability_vintages.csv`):

- METR's 50% task time horizons (minutes) as published in Epoch AI's benchmark data. One vintage per month comes from Wayback Machine captures of `epoch.ai/data/benchmark_data.zip`: 17 captures from Mar 2025, 14 of which contain METR data (from Jun 2025).
- Some captures are served gzip-encoded; they are decompressed.
- Availability is Epoch's own Last-Modified time where the archive recorded it, else the capture time. Both are upper bounds on publication.
- Release dates missing from the two earliest files (28 rows) are filled from later vintages by model name and flagged `joined`. A release date is public at release.

**Two decisions the data forced:**

1. **METR suite versions are separate units.** v1.1 (in Epoch's data from Mar 2026) re-measured older models and moved them a lot: Claude 3.5 Sonnet 18.7 → 11.4 minutes, GPT-5.1-Codex-Max 162 → 224. METR also later deleted some legacy v1.0 rows.
   - A version is used only in the vintages where it is the current suite: v1.0 from Jun 2025 to Feb 2026, v1.1 from Mar 2026.
   - Its truth is its last active vintage.
   - A retired series is never scored as if it had stopped improving.
2. **Measurement lag.** METR measures a model 38–139 days after release (median 64; the upper end is inflated by gaps between captures). A vintage therefore counts as complete only up to **3 months** before it was published. Later months are "not yet measured", not "no progress".

**Target and features:**

- **Target:** frontier = the longest horizon among models released by each month, on log₂ minutes.
- **Features:** `level`, and `own_trend` (d1, d3, d6, d12).
- **Origins:** 40, from 2023-03 (26 reconstructed, 7 mixed, 7 real). Reconstructed origins started at 2024-01 in the first run, then moved to 2023-01 after that run left too few selection origins at h=6 and h=12 (a post-run change of the evaluation window, disclosed here).
- **Stale frontier = unknown** (added 24 Oct 2026 after a user question). A month has a measured frontier only if a measured model was released in the previous 12 months.
  - Why: METR measured almost no models from 2019–2022, and davinci-002 has no release date. So in Feb 2023 the "frontier" was GPT-2 (2019, 0.04 minutes), and the next year's GPT-4-class models looked like a ×215 jump.
  - Effect: that artefact was the largest past error behind the regime chances. Origins before GPT-4 (Mar 2023) are now skipped, since there was nothing recent to forecast from.
  - Also: LightGBM falls back to the mean change when it has fewer than 60 training rows, instead of failing.

**Previous results** (run `20261024T082956Z-cb5caa`, generic engine, kept for comparison): ridge was chosen at 3 and 6 months (holdout MAE 0.65 / 0.83 doublings, beaten by drift-type baselines), and at 12 months every method tied in selection, so "no change" was served (holdout 3.27 doublings, ×9.7 typical miss, range not containing its own point). The regime chances came from residual counts and scored **worse than a ⅓ guess** at 3 and 6 months.

### Capability engine (`forecasting/capability_engine.py`, 25 Oct 2026)

Brief: `AI_CAPABILITY_IMPROVEMENT.md`. Same target (frontier METR 50% horizon), horizons, origins, split and truth as the generic engine. The generic candidates still run and are reported next to it. Wired in through `TargetSpec.engine`; `run.py` is otherwise unchanged.

**Why the generic models were inaccurate here.** They saw only the monthly staircase (flat months, then jumps), not the models behind it: no measurement CIs, no saturation, no use of the older suite, and a 12-month `trend` column that is missing for the first year of every unit (so all methods tied at h=12). The regime chances were not a forecast distribution.

**Data layers** (never mixed):
- *A, observed:* the model-level rows behind each origin's frontier, from that origin's vintage and cut (`snapshot().extras["models"]`): value, 95% CI (as two log₂ SEs, so asymmetric), release date, suite. Cross-checked against METR's own file (`SOURCES.md` §8a): 23 of 23 match.
- *B, bridged:* v1.0-only models mapped onto v1.1 through the models measured on both, from the same vintage (Theil-Sen line in log₂ hours, 300 bootstraps). Latest bridge: 9 pairs, slope 1.18 (80% 1.08–1.29: v1.1 rates old models lower and new ones higher), residual SD 0.24 doublings. Below 6 pairs or with an implausible slope it falls back to slope 1 with doubled spread (weak prior). Bridged rows feed only the jump model's trend and release rate, at half weight, with the mapping's uncertainty added; they are never frontier values or outcomes.
- *C, simulated:* 5,000 trajectories (2,000 per backtest origin), seeded; used for ranges and pace chances only.

**Components** (log₂ hours; every trajectory is non-decreasing and floored at the current frontier):
- *damped_trend:* last 12 months' slope, damping φ fitted on the snapshot's own history, spread from its own in-snapshot h-month errors.
- *robust_local_trend:* local linear trend with Huber-robust updates; variances by MAP (robust likelihood plus log-normal priors: observation 0.3, level 0.15, slope 0.01 doublings per month, log-variance sd 1.5); predictive variance computed exactly.
- *jump_process:* frontier-relevant models (within 1 doubling of the frontier when released) arrive as a Poisson process (Gamma posterior on the rate; prior = the unit's long-run rate, worth 12 months); each scores trend + Student-t(4) noise. Trend: recency-weighted (half-life 18 months) Huber fit, bootstrapped over models and their measurement error, slope shrunk by precision towards the long-run slope (models since 2023). Points above 16 h are left out of the fit (METR's rule). Checks reported, not used to switch models: lag-1 autocorrelation of monthly frontier changes −0.20; release dispersion index 0.82 (≈ Poisson).
- *ensemble:* a mixture; trajectories per component ∝ weights = 50% equal + 50% inverse squared MAE on cases resolved before the origin (equal below 6 cases). The served forecast is the ensemble by design, not by contest.

**Pace chances.** Past pace = change of the measured frontier over the last 12 months (doublings/year), each end drawn from its CI per trajectory. Future pace = (12/h)(frontier at T+h − frontier at T) per trajectory. "Same" = within max(0.25 doublings/year, 20% of the past pace). Chances = shares of trajectories, so they sum to 1. Fallbacks, labelled in `pace_basis`: bridged 12-month history, then the trend's slope. If the selection-period Brier score does not beat both a ⅓ guess and the rolling base rate on ≥10 cases, 25% of each chance is moved to the base rate and the row says "prior-assisted". In this run all three horizons showed selection skill, so nothing is shrunk.

**Results** (run `20261024T161031Z-3451f0`; MAE in doublings on exactly the same cases; holdout = origins from Mar 2025, real and reconstructed):

| h | Ensemble holdout (selection) | Drift | Naive | Damped / local / jump (holdout) | 80% coverage holdout (selection) | Holdout cases |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | **0.38** (0.73) | 0.45 (0.66) | 0.83 (0.75) | 0.46 / 0.46 / 0.48 | 100% (67%) | 16 |
| 6 | **0.53** (0.99) | 0.80 (1.04) | 1.66 (1.16) | 0.66 / 0.63 / 0.70 | 100% (61%) | 14 |
| 12 | **0.96** (1.61) | 1.30 (2.05) | 3.27 (2.05) | 1.26 / 1.40 / 1.46 | 100% (48%) | 6 |

Pace chances (Brier; lower is better; ⅓ guess = 0.67):

| h | Selection: model / base rate (n) | Holdout: model / base rate (n) |
| --- | --- | --- |
| 3 | 0.61 / 0.73 (39) | 0.56 / 0.90 (16) |
| 6 | 0.52 / 0.58 (33) | 0.50 / 1.23 (14) |
| 12 | 0.40 / 0.67 (21) | 0.55 / 1.80 (6) |

Log loss is also below the ⅓ guess in every cell. Calibration tables per class are in `engine.json`.

What it means:
- The ensemble beats naive and drift on the holdout at every horizon and is promoted as `validated`. In the **selection** period drift was better at 3 months (0.66 vs 0.73), so the ensemble is not uniformly better.
- **The 80% range is not calibrated:** it is too narrow in the selection period (2023–24 growth outran every method) and too wide in the holdout. It is labelled a predictive interval, not a calibrated one.
- The pace chances beat both simple references in both periods, but the margins are modest, and the 12-month holdout has only 6 cases.
- Served forecast (data complete through Jul 2026; current frontier Claude Mythos Preview, 17.4 h, CI 8.5–55 h): 33 h at 3 months (80%: 16–76 h), 56 h at 6 months (23–151 h), 162 h at 12 months (48–566 h). Chances faster / same / slower: 44/13/43%, 39/20/41%, 33/29/38%. The ranges start below today's value because today's measurement is itself uncertain (it is above 16 h, near the top of the suite).
- The jump model's trend implies a doubling every 3.8 months; METR's own fit since 2023 is 4.2 months (3.4–5.2). Not an input; shown for comparison.

**Changed after the first engine run (disclosed; none re-selects on the holdout):**
1. A unit complete only to an earlier month than the snapshot was held flat up to the snapshot's month (v1.0 vs v1.1 at mixed origins), so "not yet measured" read as "no progress". It is now skipped, as the generic engine does. Bug fix.
2. Damped and local-trend noise was a random walk inside a running maximum, which pushes medians up. Now each trajectory draws one quantile across horizons (correct marginals, still non-decreasing). Bug fix.
3. The local trend's maximum-likelihood variances were degenerate on the staircase (slope variance 0, or slopes of 20+ doublings/year; 12-month holdout error 6.6 doublings). I added the MAP priors above. This modelling change was made after seeing that result; the priors were set from what the variances mean (how much a slope may drift in a year), not tuned to scores.

**Model card:**
- **Intended use:** an indicative outlook for one capability dimension (software-task time horizons of frontier models under METR's conditions) and whether its pace is speeding up or slowing down.
- **Not a measure of:** general intelligence, capability in other domains, adoption, or labour-market impact.
- **Supported claim:** on a mostly reconstructed backtest, the ensemble's median beat "no change" and trend extrapolation on the held-back months at 3, 6 and 12 months, and its pace chances beat a ⅓ guess and the base rate. Not supported: calibrated ranges, or any claim from the 12-month holdout alone (6 cases).
- **Known gaps:** only METR-evaluated models are seen (selection bias); the bridge rests on 9 models; real point-in-time vintages exist only from Jun 2025.

### Second round (`AI_CAPABILITY_IMPROVEMENT_V2.MD`, 25 Oct 2026)

New modules: `capability_record.py` (two-stage record model), `capability_trend.py` (smoothed trend, secondary output), `capability_eval.py` (Brier definition, temperature calibration, non-overlapping cases, block bootstrap), `capability_signals.py` (external candidate predictors). The engine runs in two passes: components, record-chance variants and the trend forecast at every origin; then decisions on selection cases only; then the ensemble at every origin with weights and a temperature fitted on cases resolved before it.

**Brier score** (everywhere in the capability engine and on the page): sum over classes of (p − outcome)², averaged; 0 perfect, 2 worst; a ⅓ guess scores 0.67 for three classes, a 50/50 guess 0.5 for yes/no.

**Two-stage record model** (`record_jump`). Stage A: a constant monthly chance of a new record (Beta posterior, last 24 months, prior worth 12 months at the unit's rate); a record never becomes "due". Stage B: log-normal jump size, Normal-Inverse-Gamma posterior with a conservative prior (median 0.7 doublings), so 13 observed jumps cannot pin the tail. Only months in the latest unbroken stretch of measured frontier count: before a gap, METR measured too little to know whether a record could have happened. The constant hazard is supported by the record rate not rising with months since the last record (reported in `iid_checks`).

**Decisions, all on selection cases only:**

| Decision | Rule | Result |
| --- | --- | --- |
| Components with the damped trend | interval score ≤ 1.10 × the damped trend's on ≥ 10 shared cases | jump model in (1.06, 21 cases), two-stage record model in (0.99, 57), robust local trend out (1.19, 72) |
| External signals in stage A | beats the same logistic model without it in ≥ 90% of block-bootstrap resamples, and beats the constant hazard | neither kept: compute growth raised log loss (+0.061); lab releases lowered it in only 4% of resamples |
| Pace chances | raw or temperature-calibrated (lower selection log loss), then the existing shrink rule | raw at 3 and 12 months, calibrated at 6; no shrink (selection skill shown) |
| Chance of no new record | stage A if its selection log loss beats the rolling base rate, else the base rate | base rate at every horizon: stage A said 23% / 33% / 50% for a record within 3 / 6 / 12 months when 78% / 95% / 100% happened |

External data looked at: Epoch AI models data (2,080 language models, approximately point-in-time: only today's file exists; release dates are public, compute is estimated later), tested as above. SWE-bench Verified, LiveBench, Terminal-Bench and Aider Polyglot (via Epoch's benchmark archive) were inventoried and **not tested**: they appear in Epoch's archive only from Nov 2025 and cover releases from Feb 2024 – Jun 2025 onwards, so validating them would need the holdout. LiveBench's own site and data were reachable but have the same coverage problem.

**Leakage:** the v1.0 → v1.1 bridge is no longer fitted at origins where v1.1 was not yet published (it would use the 2026 file). External features use only releases up to each month.

**Results** (run `20261024T165353Z-56a2b9`; MAE in doublings; same cases for every method):

| h | Ensemble holdout (selection) | Damped trend | Drift | Naive | Two-stage record | 80% coverage holdout (selection) |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | 0.45 (0.74) | 0.50 (0.71) | 0.45 (0.66) | 0.83 (0.75) | 0.62 (0.98) | 100% (69%) |
| 6 | **0.57** (0.99) | 0.74 (0.90) | 0.80 (1.04) | 1.66 (1.16) | 0.94 (1.47) | 100% (67%) |
| 12 | **0.96** (1.53) | 1.41 (1.47) | 1.30 (2.05) | 3.27 (2.05) | 1.93 (2.14) | 100% (48%) |

Dependence-aware checks (all scored cases):

| h | Non-overlapping cases | MAE ensemble / drift / naive | Ensemble − drift, 80% (95%) block bootstrap | Pace Brier − ⅓ guess, 80% (95%) |
| --- | --- | --- | --- | --- |
| 3 | 19 | 0.64 / 0.55 / 0.77 | +0.06: 0.00 to 0.11 (−0.03 to 0.14) | −0.07: −0.16 to −0.00 (−0.20 to 0.04) |
| 6 | 9 | 1.03 / 0.90 / 1.36 | −0.10: −0.18 to −0.01 (−0.22 to 0.04) | −0.16: −0.26 to −0.10 (−0.30 to −0.07) |
| 12 | 3 | 1.08 / 0.85 / 1.92 | −0.48: −0.55 to −0.38 (−0.57 to −0.32) | −0.25: −0.28 to −0.15 (−0.31 to −0.12) |

Pace chances (served): Brier 0.62 / 0.51 / 0.39 in selection and 0.54 / 0.49 / 0.49 in holdout at 3 / 6 / 12 months, against 0.67 for a ⅓ guess and 0.58–1.80 for the base rate; log loss below the ⅓ guess everywhere.

What it means:
- **Against naive:** better at every horizon, robustly.
- **Against drift:** worse at 3 months (bootstrap 80% interval above 0); better at 6 months but not at 95%; clearly better at 12 months on all scored cases. The non-overlapping cases (19 / 9 / 3) favour drift at every horizon, and the 12-month subset has 3 cases. **The non-overlapping evaluation does not support a claim that the ensemble beats trend extrapolation.**
- **Against its simplest component:** in the selection period the ensemble's median missed by more than the damped trend at every horizon (0.74 / 0.99 / 1.53 vs 0.71 / 0.90 / 1.47), with interval scores within 1% and pace Brier slightly better. It is better on the holdout. The ensemble is served because it was declared the forecast before any scores existed (first round); V2's "if inconclusive, keep the simpler model" would serve the damped trend. Left to the owner.
- **Pace chances:** better than a ⅓ guess at 6 and 12 months even allowing for overlap (95% intervals below 0); at 3 months only at 80%.
- **No new record:** the two-stage model under-predicted records throughout (the record rate rose as METR measured more models); the base rate is served. Served: 18% / 4% / 3% within 3 / 6 / 12 months.

**Secondary output: underlying trend.** Smooth-trend state-space model (level moves only through a slowly drifting growth rate; staircase jumps are deviations), robust updates, MAP variances, Rauch-Tung-Striebel smoother. Estimand: mean growth rate over the next h months vs the past 12, in doublings/year, same tolerance as the frontier pace; scored against the same smoother run on the latest data. Current estimate: 2.0 doublings/year now (±1.3) vs 3.1 over the past 12 months, so P(decelerating) ≈ 0.57–0.58.

| h | Brier selection / holdout (⅓ guess 0.67) | Base rate selection / holdout | Pace MAE vs "keep last year's" (selection; holdout) |
| --- | --- | --- | --- |
| 3 | 0.61 / 1.04 | 0.79 / 0.94 | 1.68 vs 1.81; 2.35 vs 1.65 |
| 6 | 0.61 / 1.15 | 0.94 / 1.03 | 1.76 vs 1.79; 2.27 vs 1.56 |
| 12 | 0.60 / 1.17 | 0.67 / 0.99 | 1.44 vs 1.34; 3.58 vs 1.77 |

**No demonstrated skill:** better than both references in the selection period, worse than guessing on the holdout, and its pace forecasts lose to "keep last year's pace" on the holdout. The page says so and labels it experimental and model-estimated; it is not blended into the frontier chances.

**Changed after seeing V2 results (disclosed):**
1. Record months before a measurement gap no longer count (bug: the GPT-2 year read as 12 months without a record, giving a 1.5% monthly record chance).
2. A kept external signal must also beat the constant hazard (both signals had passed only against a miscalibrated logistic baseline).
3. Trend chances use the difference between current and past growth (they share most of their uncertainty); the first version treated them as independent, which pushed every chance towards ⅓.
4. The trend model's level has no shocks of its own (the first version followed the staircase step by step, so it was not a smoothed trend).
5. The no-record chance falls back to the base rate when stage A does not beat it (rule added after stage A's selection scores).

## 9. How this answers the BTOS problem

| Old weakness | Now |
| --- | --- |
| BTOS as label + main feature + scenario definition | BTOS is registered only as a `business_adoption` label. Contracts refuse it for skill demand and as an occupation label, even if the registry is edited |
| Occupation adoption derived from firm data | Targets are separate. Occupation adoption is now modelled on worker-level evidence (RPS) only, and BTOS is a business-adoption model of its own. Nothing maps firms to occupations; the old hand-made sector→SOC weights are gone |
| BTOS wording break handled inside one model (`new_wording` flag) | Each wording is its own series and no feature crosses the break. Selection uses the old wording and the holdout tests on the new |
| Backtests on revised data | Every origin sees only the vintage published by then. Reconstructed origins are flagged and kept out of the holdout |
| Ranges tuned until the backtest looked right | Ranges come from residuals in the selection period, and holdout coverage is reported as measured (including the 57%) |
| Assumptions served as forecasts | No hand-set scenarios or odds. A scenario engine will come only after the capability model exists and is tested |
| No ablations | Each feature group, and so each source, is dropped and rescored on every run. BTOS is shown as excluded by contract |
| Missing → 0 | Missing stays missing: blank counts, NaN features, unscored outcomes |

## 10. Running it

From `src/backend` with the backend venv:

```
python -m forecasting.run                                   # all four targets, fetching new data first (~6 min)
python -m forecasting.run --no-pull                         # from local data only
python -m forecasting.run --target btos_ai_use_rate --skip-ingest   # one target, tables as they are
python -m forecasting.vintages | forecasting.btos | forecasting.rps | forecasting.capability  # one source
python -m pytest forecasting/tests                          # 61 tests, offline, no credentials
```

- **Optional:** set `FRED_API_KEY` (free) to give RPS real vintages.
- **Scheduling:** run `python -m forecasting.run` weekly. The sources publish at different rates:
  - Indeed: AI share monthly, postings weekly;
  - BTOS: fortnightly;
  - RPS: quarterly;
  - Epoch AI: irregular (the capability ingest also stores today's file, so real vintages keep accumulating).

  A failed fetch keeps the local history. A failed build leaves the previous tables in place. A failed acceptance keeps the previous promoted model. Each target's outputs are in `src/backend/forecasting/output/<target>/`.
- **Freshness:** `registry.health()` marks a source stale after 2× its cadence. A stale target blocks promotion and is written into the forecast `warnings`.
- **API** (read-only, added alongside the existing `/forecast`, which is unchanged). New runs show up without a restart. Every row carries `status`, its range and `warnings`:
  - `GET /outlook` lists the targets with promoted horizons, status and source health;
  - `GET /outlook/{target}?unit=&h=` returns the promoted forecasts;
  - `GET /outlook/{target}/evaluation` returns the newest run's evaluation;
  - `GET /outlook/{target}/accuracy?unit=` returns, for one unit, every method's average holdout error per published horizon, and whether the published forecast beat "no change" for that unit.
- **Reproducibility (checked 24 Oct 2026):** on a fresh clone of the branch, with no raw data, the 65 tests pass. `python -m forecasting.run --skip-ingest` reproduces all 69,388 backtest predictions of the main checkout exactly (same code-version hash).

## 11. Limitations and next steps

1. **Long horizons under-forecast fast growth** (skill demand h6, BTOS h13, RPS). `local_trend` was tested and did not fix it: it was unstable on the short post-break BTOS series. Next to test under the same procedure: a shorter or weighted training window.
2. **Data:**
   - skill-demand origins before Apr 2024 are reconstructed;
   - BTOS is assumed unrevised;
   - RPS has FRED vintages only from Jun 2026, so its earlier origins are reconstructed;
   - capability origins are mostly reconstructed or mixed (real METR vintages only from Jun 2025; v1.1 from Mar 2026);
   - in every case the truth is the latest data, which may itself be revised.
3. **RPS is too short** (9 quarters) for any supported claim. Group-level noise is 6–9 pp.
4. **Skill-level demand** (named skills, not just "AI") has no source with history. Adzuna's free tier can't build one.
5. **AI capability is one dimension** (METR time horizons). Planned additions, each as a separate series:
   - ECI, once about 12 monthly vintages exist (from Sep 2026), or a per-origin index fitted only on data available then;
   - cost-adjusted capability;
   - GDELT news as a candidate leading feature, kept only if the ablation shows a gain.
6. **Scenario engine:** connecting capability regimes to adoption and skill demand needs a tested link between them. None is estimated yet, so no scenarios are produced.
7. **UI:** the **AI outlook** tab (`src/frontend/src/views/OutlookView.vue`, route `/outlook`, in the sidebar) shows all four targets from `/outlook`. Each card has:
   - a unit picker;
   - the latest value;
   - per-horizon forecast markers with their 80% ranges;
   - the test results **for the selected unit**: how many held-back forecasts it was tested on, the shown method's average error next to "no change", a beats / does-not-beat verdict, a warning below 5 test points, and an expandable table of every method (this unit and all series pooled). The pooled status chip was removed: the pooled choice can hide a unit where another method, or "no change", did better;
   - an inline note when the point falls outside its range;
   - the warnings (collapsed);
   - the data date.

   The capability card also has a time-horizon chart (`CapabilityChart.vue`: measured models with CIs, bridged estimates hollow, the measured frontier, the 50% / 80% forecast fan, the 16 h line and the not-yet-measured months), a collapsible methodology and diagnostics panel (`CapabilityMethod.vue`), and a step-by-step explainer of the pace chances (`RegimeExplainer.vue`).

   The capability card also shows the regime probabilities as a labelled bar. Its colours (orange `#eb6834` / grey `#9e9a92` / blue `#2a78d6`) were checked with the dataviz palette validator. Every segment carries a text label, so colour is never the only cue.

   Not done: the old adoption pages on `feat/ai-adoption-mc` show discarded outputs and were not ported; and the page does not yet link to role pages.
8. **Merge gate:** do not merge to `main` until both of these hold:
   - the tests pass on a fresh clone — **done** 24 Oct 2026;
   - a second run on newer data has been promoted or rejected by the rules above — **pending**. The sources next publish in early November 2026: BTOS around 5 Nov, Indeed's AI share in the first half of the month.
