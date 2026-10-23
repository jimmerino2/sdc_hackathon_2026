# forecasting

Point-in-time forecasting pipeline. It currently covers **skill demand**: the monthly share of job postings that mention AI, for 9 countries, 1, 3 and 6 months ahead. Design, audit, results and the model card are in `data/documentation/FORECAST_REBUILD.md`.

## Run

From `src/backend`, using the backend venv (`venv/Scripts/python.exe` on Windows):

```
python -m forecasting.vintages        # fetch Indeed's git histories, rebuild data/processed/forecasting/*_vintages.csv
python -m forecasting.run --no-pull   # backtest, select, holdout, ablations, forecast, promotion (~2 min)
python -m forecasting.run             # the same, fetching new vintages first
python -m pytest forecasting/tests    # offline tests, no credentials needed
```

The first run clones the two Indeed repos into `data/raw/vintages/` (gitignored). These are partial clones holding only the data-file history, about 35 MB.

## Outputs

These are in `output/`; every column is described in `data/documentation/STRUCTURE.md` §9.

- `latest_forecast.csv`: the forecast to show, from the promoted run per horizon. Each row carries its `status`, range and `warnings`.
- `model_registry.json`: the promoted model per horizon, and every attempt with its acceptance verdict.
- `forecast_log.csv`: append-only record of every forecast issued.
- `runs/<run_id>/`: the full backtest, `evaluation.json` and that run's forecast.

## Schedule

Run `python -m forecasting.run` weekly. Indeed publishes the AI share monthly and postings weekly.

- A failed fetch keeps the local history.
- A failed build keeps the previous tables.
- A run that fails acceptance keeps the previous promoted model, and the reason is recorded in `model_registry.json`.

## Modules

| Module | Role |
| --- | --- |
| `registry.py` | Sources: what each one measures, the domains it may label or feed, freshness |
| `contracts.py` | Targets per domain and `check_sources()`, which refuses invalid uses (e.g. BTOS for skill demand) |
| `vintages.py` | Ingestion: one row per published vintage, plus the `as_of()` lookup |
| `features.py` | Snapshots at a forecast origin, features and labels from that snapshot only |
| `models.py` | Baselines (naive, drift, damped drift, pooled mean), ridge, and a LightGBM challenger |
| `evaluation.py` | Origins, purged chronological split, backtest, metrics, selection, coverage, ablations |
| `run.py` | CLI, outputs, acceptance and promotion |
