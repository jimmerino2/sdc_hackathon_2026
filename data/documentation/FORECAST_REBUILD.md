# Forecast Rebuild: Design, Audit and Results

Branch `feat/ai-prediction`. This replaces the AI-adoption forecasting on `feat/ai-adoption-mc` (left unchanged, reference only) with a pipeline that is point-in-time, source-separated and tested out of time. The brief is `AI_PREDICTION_ADOPTION.md`; progress is logged in `FORECAST_REBUILD_PROGRESS.md`.

**Status (24 Oct 2026):** three separate targets run end to end on one shared engine. Each goes: ingest point-in-time data → features → train → rolling-origin backtest → locked holdout → ablations → timestamped forecast → promotion.

| Target | Domain | Data | Horizons |
| --- | --- | --- | --- |
| `ai_mention_share` | skill demand | Indeed, 9 countries, monthly | 1, 3, 6 months |
| `btos_ai_use_rate` | business adoption | Census BTOS, US + 19 sectors, per wording, fortnightly | 6, 13 fortnights |
| `worker_genai_use_rate` | occupation adoption | RPS worker survey, 22 SOC groups + all workers, quarterly | 1, 2 quarters |

None feeds another. **AI capability progress** is still only a contract (no benchmark data yet), and there is **no scenario engine**. Adzuna is context only: the account is on the free tier, so its snapshots will stay too thin to train on (decision of 24 Oct 2026).

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
| `frontier_capability_index` (definition pending) | AI capability | benchmarks (Epoch / METR) | planned |

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

- **Modelling scale:** logit of the share. The label at anchor month *m* is `logit(share[m+h]) − logit(share[m])`. Training rows are every country × anchor month whose *m + h* is inside the origin's snapshot.
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
  - `not_demonstrably_better`: anything else.

  The 5% margin was added after an RPS run labelled a 0.03% "gain" on three noisy origins as `validated`. It changes labels only, never which model is chosen.
- **Per target:** the minimum holdout and selection sizes are set in each `TargetSpec`. Skill demand and BTOS require 6 holdout and 12 selection origins. RPS has only 9 quarters, so it requires 2 and 3, and every RPS forecast carries a short-history warning.

## 7. Results: skill demand (promoted run `20261023T180055Z-bd0071`, same numbers as the first run)

MAE in percentage points. Selection covers 42–47 origins; the holdout covers 12–17 real-vintage origins with 9 countries each.

| h | Chosen | Selection MAE (naive) | Holdout MAE (naive) | Holdout MASE | Best on holdout (not usable for choosing) |
| --- | --- | --- | --- | --- | --- |
| 1 | drift | 0.367 (0.374) | 0.389 (0.484) | 0.80 | pooled_mean / ridge 0.371 |
| 3 | pooled_mean | 0.411 (0.432) | 0.709 (1.075) | 0.66 | pooled_mean |
| 6 | naive | 0.523 (0.523) | 2.045 (2.045) | 1.00 | drift 1.242 |

Holdout 80% interval coverage of the chosen models: 0.85 (h1), 0.90 (h3), **0.57 (h6)**.

What the results mean:

- At 1 and 3 months the chosen simple models beat "no change" on data they never saw, by 20% and 34%.
- **At 6 months the selection period picked naive, which then did badly on the holdout.** AI-mention shares rose much faster from 2025 on than in 2021–24, and naive's 80% range held only 57% of outcomes. The rule was not changed after seeing this; choosing again on the holdout would be tuning on it. The 6-month forecast is served as `baseline`, and this failure is the most important known weakness.
- **Ridge and LightGBM never beat the best simple baseline** in selection, so neither is deployed.
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
| 13 (~6 months) | ridge | 1.47 (2.15) | 3.76 (4.21) | 0.89 | 0.80 | validated |

What it means:

- **Sampling noise is a large part of the error.** Under the new wording the mean sector standard error is 1.9 pp, against 0.3 pp nationally. That puts a floor under any sector forecast.
- **Every model under-forecast the new wording** (naive bias −1.6 pp at h6, −4.0 pp at h13): national adoption rose from 17.3% to 24.6% in under a year. pooled_mean would have done best on the holdout (MASE 0.85 / 0.68), but it was not chosen on the selection data, and the rule was kept.
- **Ablations:** dropping the expectation gap makes ridge worse (+0.065 pp at h6). Firms' own expectations carry signal for firm adoption. Dropping cross-sector averages helps (−0.09 pp at h6).
- **Model card:**
  - Intended use: US firm-level AI use, by sector, about 3 and 6 months ahead, in the new wording only.
  - Not a measure of worker or occupation adoption, and not transferable to other countries.
  - Supported claim: h13 ridge beat persistence by 11% on the post-break holdout. For h6 there is no claim beyond the baseline.

## 8b. Occupation adoption (`worker_genai_use_rate`)

**Data** (`forecasting/rps.py` → `rps_observations.csv`): the Real-Time Population Survey, the % of employed US adults using GenAI for their job. It covers 22 SOC major groups plus all workers ("00"), quarterly from 2024-Q3, 9 readings per group. It is worker-level evidence, so **no BTOS or task-exposure input is used**.

**Availability:**

- There is no FRED key, so FRED's past vintages (ALFRED) can't be read. Values are today's, each assumed available 21 days after its quarter ends; the 2026-Q3 value was already online on 22 Oct.
- Origins are labelled `current_only` and every forecast says so.
- Setting a free `FRED_API_KEY` makes `rps.py` read real vintages, with no code change.

**Features:** `level`, `own_trend` (d1, d2, d4 quarters) and `all_workers` (mean change over groups).

**Evaluation:** 7 origins (2025-Q1 → 2026-Q3): 3 for selection and 4 holdout.

| h (quarters) | Chosen | Selection MAE (naive) | Holdout MAE (naive) | Holdout MASE | 80% coverage | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | pooled_mean | 6.99 (7.27) | 6.56 (6.57) | 1.00 | 0.71 | not_demonstrably_better (promoted, with warnings) |
| 2 | pooled_mean | 7.89 (8.51) | 8.67 (6.62) | 1.31 | 0.76 | **not promoted**: insufficient history (2 selection origins) |

What it means:

- Errors of 6–9 pp come mostly from survey noise in small groups. For example, Management reads 55.9 → 48.1 → 51.9 → 49.6 → 61.4 over five quarters.
- With 2–3 scored origins, nothing can be shown to beat "no change". The served 1-quarter forecast is effectively the current level plus the recent average change, with a wide range (e.g. computer and mathematical occupations: 68.8% now, 57–79%).
- **Model card:**
  - Intended use: a cautious near-term view of US worker GenAI use, by broad occupation group.
  - Supported claims: none beyond "indicative".
  - Will improve as quarters accumulate and if ALFRED vintages are enabled.

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
python -m forecasting.run                                   # all three targets, fetching new data first (~3 min)
python -m forecasting.run --no-pull                         # from local data only
python -m forecasting.run --target btos_ai_use_rate --skip-ingest   # one target, tables as they are
python -m forecasting.vintages | forecasting.btos | forecasting.rps  # rebuild one source's tables
python -m pytest forecasting/tests                          # 50 tests, offline, no credentials
```

- **Optional:** set `FRED_API_KEY` (free) to give RPS real vintages.
- **Scheduling:** run `python -m forecasting.run` weekly. The sources publish at different rates:
  - Indeed: AI share monthly, postings weekly;
  - BTOS: fortnightly;
  - RPS: quarterly.

  A failed fetch keeps the local history. A failed build leaves the previous tables in place. A failed acceptance keeps the previous promoted model. Each target's outputs are in `src/backend/forecasting/output/<target>/`.
- **Freshness:** `registry.health()` marks a source stale after 2× its cadence. A stale target blocks promotion and is written into the forecast `warnings`.

## 11. Limitations and next steps

1. **Long horizons under-forecast fast growth** in all three domains (skill demand h6, BTOS h13, RPS). Candidates worth testing next, under the same procedure: a local-linear-trend state-space model, and a shorter or weighted training window.
2. **Data:**
   - skill-demand origins before Apr 2024 are reconstructed;
   - BTOS is assumed unrevised;
   - RPS availability dates are assumed until a FRED key is set;
   - in every case the truth is the latest data, which may itself be revised.
3. **RPS is too short** (9 quarters) for any supported claim. Group-level noise is 6–9 pp.
4. **Skill-level demand** (named skills, not just "AI") has no source with history. Adzuna's free tier can't build one.
5. **AI capability** (benchmarks such as Epoch AI or METR) is not started. Scenarios come only after it exists and is tested.
6. **API/UI:** serve each target's `latest_forecast.csv` and evaluation through `/forecast` and show freshness. The current app endpoints are untouched.
7. **Merge gate:** do not merge to `main` until the tests pass on a fresh clone, and a second run on newer data has been promoted or rejected by the rules above.
