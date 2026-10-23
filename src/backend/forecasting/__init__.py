"""Point-in-time forecasting pipeline (rebuild of the old ml/ai_adoption_* scripts).

Modules, in pipeline order:
  registry    every data source, what it measures and which targets it may inform
  contracts   the three prediction targets and the source rules each must obey
  vintages    point-in-time store built from the Indeed git histories (one row per published vintage)
  features    skill-demand features computed only from the vintage available at each forecast origin
  models      baselines and candidate models behind one fit / predict interface
  evaluation  chronological origins, rolling-origin backtest, locked holdout, metrics, ablations
  run         CLI: ingest, backtest, forecast; writes timestamped outputs and the model registry

See data/documentation/FORECAST_REBUILD.md for the design and results.
"""
