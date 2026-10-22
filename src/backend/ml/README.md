# ML: job-postings forecast

Forecasts how job postings will change over the next 3, 6, 9 and 12 months, for every sector and for every O*NET job, under three "AI adoption" scenarios. It powers `GET /forecast` and `GET /forecast/jobs` and the **AI signal** page in the frontend (Software Developers, O*NET `15-1252.00`).

> **Read this first:** the numbers are *indicative*. In backtests LightGBM did **not** beat simple baselines, and the three scenarios are **assumptions**, not something the model learned. See [How accurate is it?](#how-accurate-is-it).

## The idea in one minute

1. Indeed publishes a **job-postings index** per sector, monthly (100 = 1 Feb 2020). We also track the **share of postings that mention AI**.
2. A **LightGBM** model learns, from each sector's history, how much the index grows over the next *h* months.
3. A job has no postings history of its own, so it **inherits its sector's forecast** (a job in two sectors gets a weighted blend).
4. The **AI scenarios** (Slow / Baseline / Rapid AI) then nudge the forecast up or down based on how AI-exposed the job is. This is a fixed formula applied *after* the model.

```
Indeed index + AI-mention share
        │
        ▼
build_training_table.py   one row per sector × month, with lags and the future target
        │
        ▼
train_lgbm.py             one LightGBM model per horizon (3, 6, 9, 12)
        │                  + baselines, holdout scores, error ranges
        │                  + scenario shift  ──►  forecast_output.csv   (sector level)
        ▼
job_forecast.py           sector forecast → job forecast  ──►  job_forecast.csv   (O*NET job level)
        │
        ▼
backend/app/forecast      FastAPI serves the CSVs  ──►  frontend SignalView.vue
```

## Files

| File | What it does |
|---|---|
| `build_training_table.py` | Builds the training table for any horizon from `data/processed/signals.csv`: per-sector index lags, national index, AI-share features, and the target (the index *h* months later). Applies a 1-month publication lag so the model only uses data that was public at the time. |
| `train_lgbm.py` | Trains, validates and forecasts. Run this to regenerate everything in `output/`. |
| `job_forecast.py` | Converts sector forecasts into job forecasts using `crosswalk.csv` and `ai_exposure.csv`. |
| `output/forecast_output.csv` | Sector × scenario × horizon (about 564 rows). |
| `output/job_forecast.csv` | O*NET job × scenario × horizon (about 552 rows). |
| `output/lgbm_model_h{3,6,9,12}.txt` | The trained models. |
| `output/model_meta.json` | Data dates, features, model settings, holdout scores, error ranges. |

## Retraining

```
cd src/backend/ml
python train_lgbm.py                 # defaults: 300 trees, 12-month holdout
python train_lgbm.py --post-only     # drop the pandemic period
python train_lgbm.py --holdout 18 --trees 200
```

Needs `lightgbm`, `pandas`, `numpy`. Inputs are read from `data/processed/` (`model_table_US.csv`, `signals.csv`, `crosswalk.csv`, `ai_exposure.csv`, `ai_exposure_detail.csv`, `manifest.json`). The API reads the CSVs in `output/` at request time, so it does not need LightGBM installed.

## The LightGBM model

- **Target:** growth of the sector index over the horizon, `index_in_h_months / index_now − 1`. Predicting growth instead of the raw index lets one model learn across sectors with different index levels.
- **One model per horizon**, because a 3-month and a 12-month move behave differently.
- **Features** (all known at forecast time):

  | Feature | Meaning |
  |---|---|
  | `index` | Sector postings index now |
  | `mom` | Change vs last month |
  | `chg3` | Change vs 3 months ago |
  | `index_yoy` | Change vs 12 months ago |
  | `rel_nat` | Sector index ÷ national index (is the sector beating the market?) |
  | `ai_share_lag1`, `ai_chg3_lag1`, `ai_chg12_lag1` | National share of postings mentioning AI, last month, and its 3- and 12-month change. **Same value for every sector in a month.** |
  | `sector`, `period` | Categorical: which sector, and `pandemic` vs `post` |

- **Settings:** small, heavily regularised trees (`num_leaves=4`, `learning_rate=0.03`, `reg_lambda=5`, 300 trees, fixed seed 42). There are only about 2.6k to 3k rows (47 sectors, overlapping windows), so a bigger model would just memorise. There is deliberately no early stopping, since stopping on the holdout would flatter the holdout score.
- **Data:** US Indeed data stands in for Malaysia (Indeed has no Malaysia data), so output rows carry `is_proxy_geo = true`.

### Training and validation

For each horizon *h*, the last 12 months of origins are held out. Training only uses origins whose *h*-month outcome was already known when the holdout began (an *h*-month gap), so nothing from the future leaks in. After scoring, the model is refit on all labelled rows and forecasts from the latest month.

Three simple baselines are scored on the same holdout:

- **flat:** the index doesn't change.
- **yoy:** last year's pace repeats, scaled to *h* months.
- **constant:** every sector moves by the average training growth.

## Two forecasts per row

Each row has two forecasts:

| Column | Method | Used for |
|---|---|---|
| `index_pred` / `change_pct` | **Headline:** last year's growth pace repeats ("yoy"), plus scenario shift | The API's main `forecast` / `change_pct` |
| `index_model` / `model_change_pct` | **LightGBM** growth, plus scenario shift | `model_forecast` / `model_change_pct` ("for comparison"); what the AI signal page plots |

The headline is yoy because LightGBM did not beat simple baselines in testing (see below). The two can differ a lot: for Software Developers at 12 months, yoy gives about +19% and LightGBM about +10%.

## The scenarios

**The scenarios do not touch the LightGBM model.** The model is trained and run once per horizon and never sees a "scenario" input. The scenario is added afterwards as a fixed shift:

```
shift = scenario_effect × (AI exposure − average AI exposure) × (horizon_months / 12)
final_growth = model_growth + shift
```

| Scenario | `scenario_effect` | Meaning |
|---|---|---|
| Slow | **+0.10** | AI adoption is slow: exposed jobs do better than average, unexposed worse |
| Baseline | **0** | No shift, the plain model forecast |
| Rapid AI | **−0.10** | AI adoption is fast: exposed jobs do worse than average, unexposed better |

- `SCENARIO_EFFECT` lives in `train_lgbm.py`. It is a typed-in assumption, **not learned from data**. Doubling it doubles the gap between the lines without any new evidence.
- **Sector level:** the exposure is the sector's average, weighted by `crosswalk.weight`, centred on the mean across sectors.
- **Job level** (`job_forecast.py`): the job's *own* exposure is used, centred on the mean across jobs. So two jobs in the same sector can move differently under the same scenario.
- Example, Software Developers at 12 months (exposure 0.941, above average): Baseline +10.4%, Rapid AI +7.5%, Slow +13.4%.
- The "% likely" labels (45 / 35 / 20) on the frontend scenario cards are hardcoded in `frontend/src/data/flows.ts`. Nothing in the ML produces them.

## From sector to job

`job_forecast.py` joins each O*NET job to its sectors through `crosswalk.csv`, weights each sector's Baseline growth (and low/high range) by `weight` (weights sum to 1), then applies the job's own scenario shift. Each job also carries:

- `ai_exposure`: 0 to 1, how much AI is already used in the job's tasks.
- `automation_share` / `augmentation_share`: how much of that AI use replaces the worker versus assists them.
- `ai_exposure_low_sample`: true if the exposure rests on little data (a fallback value or a tied floor).

## Ranges

Low/high values are the **10th to 90th percentile of the holdout errors**, added to the forecast growth. There is a separate range for the headline method (`change_low_pct` / `change_high_pct`) and for LightGBM (`model_change_low_pct` / `model_change_high_pct`). Match the range to the line: the LightGBM line must use the LightGBM range. They are not symmetric around the forecast, because past errors weren't symmetric. The range width comes from past error, not from the scenario, so every scenario of a job has the same width.

## How accurate is it?

Holdout scores from `output/model_meta.json` (lower error is better; "direction" is how often up-versus-down was called right, where 50% is a coin flip):

| Horizon | LightGBM error | flat | constant | yoy | LightGBM direction |
|---|---|---|---|---|---|
| 3 months | 4.43% | 3.76% | 3.76% | 4.13% | 47.2% |
| 6 months | 6.32% | 5.23% | 5.22% | 6.55% | 52.3% |
| 9 months | 7.82% | 6.64% | 6.46% | 8.74% | 58.3% |
| 12 months | 8.43% | 7.78% | 7.16% | 10.33% | 64.9% |

What this means:

- **LightGBM did not beat "nothing changes" or "average growth" at any horizon.** That is why every forecast is marked `indicative` and not `validated`. A forecast is only `validated` if LightGBM beats the constant baseline.
- **Direction is close to chance at short horizons** and only modestly better at 12 months.
- **The scenario spread is untestable.** There is no data to check "what if AI adoption were faster".
- **Small, proxy data.** 47 sectors, about 2.6k to 3k rows, US standing in for Malaysia, and AI features that are national rather than per sector.

Use the output as a rough sense of up, flat or down, not as a precise percentage. Baseline is the most data-backed line. Rapid AI and Slow are what-ifs around it.

## Ideas to improve it

- Learn the AI effect: add per-sector AI-adoption features and fit the effect instead of assuming ±0.10 (needs more data to avoid noise).
- Real Malaysia postings data to replace the US proxy.
- More history or more sectors, since the training set is the main limit.
- Report the LightGBM versus headline disagreement in the UI as a confidence signal.
