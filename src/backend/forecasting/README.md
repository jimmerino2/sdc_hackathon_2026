# forecasting

Point-in-time forecasting pipeline with three separate targets. None of them feeds another.

| Target | Domain | Source | Unit | Horizons |
| --- | --- | --- | --- | --- |
| `ai_mention_share` | skill demand | Indeed AI Tracker (+ postings) | country × month | 1, 3, 6 months |
| `btos_ai_use_rate` | business adoption | Census BTOS | NAICS sector × wording × fortnight | 6, 13 fortnights |
| `worker_genai_use_rate` | occupation adoption | RPS worker survey | SOC major group × quarter | 1, 2 quarters |

Design, audit, results and model cards are in `data/documentation/FORECAST_REBUILD.md`.

## Run

From `src/backend`, using the backend venv (`venv/Scripts/python.exe` on Windows):

```
python -m forecasting.run                                   # all targets, fetching new data first (~3 min)
python -m forecasting.run --no-pull                         # from local data only
python -m forecasting.run --target btos_ai_use_rate --skip-ingest
python -m forecasting.vintages                              # Indeed: rebuild the vintage tables
python -m forecasting.btos                                  # BTOS: download (dated copy kept), rebuild
python -m forecasting.rps                                   # RPS: download, rebuild (ALFRED vintages if FRED_API_KEY is set)
python -m pytest forecasting/tests                          # offline tests, no credentials needed
```

- **First run:** it clones the two Indeed repos into `data/raw/vintages/` (gitignored). These are partial clones holding only the data-file history, about 35 MB.
- **Optional:** a free `FRED_API_KEY` gives RPS real historical vintages.
- **Not used:** Adzuna. The account is on the free tier, so it is context only.

## Outputs

These are in `output/<target>/`; every column is described in `data/documentation/STRUCTURE.md` (sections 9–11 and "Forecast outputs").

- `latest_forecast.csv`: the forecast to show, from the promoted run per horizon. Each row carries its `status`, range and `warnings`. A horizon with no promoted model is absent.
- `model_registry.json`: the promoted model per horizon, and every attempt with its acceptance verdict.
- `forecast_log.csv`: append-only record of every forecast issued.
- `runs/<run_id>/`: the full backtest, `evaluation.json` and that run's forecast.

## Schedule

Run `python -m forecasting.run` weekly. The sources publish at different rates:

- Indeed: AI share monthly, postings weekly;
- BTOS: fortnightly;
- RPS: quarterly.

Failure handling:

- A failed fetch keeps the local data.
- A failed build keeps the previous tables.
- A run that fails acceptance keeps the previous promoted model, and the reason is recorded in `model_registry.json`.

## Modules

| Module | Role |
| --- | --- |
| `registry.py` | Sources: what each one measures, the domains it may label or feed, freshness |
| `contracts.py` | Targets per domain and `check_sources()`, which refuses invalid uses (e.g. BTOS for skill demand or occupations) |
| `vintages.py`, `btos.py`, `rps.py` | Ingestion: point-in-time tables per source |
| `targets/` | One module per target exposing a `TargetSpec`: load, origins (snapshots), truth, features, labels |
| `features.py` | Shared snapshot, logit, lag-feature and label code |
| `models.py` | Baselines (naive, drift, damped drift, pooled mean), ridge, and a LightGBM challenger |
| `evaluation.py` | Purged chronological split, rolling-origin backtest, metrics, selection, coverage, ablations |
| `run.py` | CLI, outputs, acceptance and promotion |
