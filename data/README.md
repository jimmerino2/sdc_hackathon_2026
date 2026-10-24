# Data

The data behind our model, which forecasts job demand 12 months ahead and how AI affects it.

## Folders

| Folder           | What's inside                                                        |
| ---------------- | -------------------------------------------------------------------- |
| `documentation/` | Where the data comes from (`SOURCES.md`) and what every table and column means (`STRUCTURE.md`) |
| `processed/`     | Clean tables used by the model and the app, plus `manifest.json` (as-of dates and row counts) |
| `raw/`           | Source downloads (gitignored, can be large). Filled by `pipeline/refresh.py` or by hand, see `pipeline/README.md` |
| `pending/`       | Candidate sources not yet processed or documented. Planned additions |
| `occupational_forecasting/` | The separate occupational forecasting domain (skill demand, emerging skills, AI adoption per country x occupation). See its README |

## Tables in `processed/`

| Table                  | Purpose                                              |
| ---------------------- | ---------------------------------------------------- |
| `signals.csv`          | Monthly job-posting and AI-mention trends            |
| `model_table_US.csv`   | Trends arranged for forecasting (lags, 12-month target) |
| `crosswalk.csv`        | Maps jobs to Indeed sectors                          |
| `onet_roles.csv`       | The 46 jobs the app covers                           |
| `onet_role_skills.csv` | Skills each job requires                             |
| `ai_exposure.csv`      | How much AI is already used for each job             |
| `my_vacancies.csv`     | Malaysia online job vacancies (display only)         |
| `onet_to_my_group.csv` | Maps the 46 jobs to Malaysian occupation groups      |
| `forecasting/ai_share_vintages.csv` | Every published vintage of Indeed's AI share, by country and month |
| `forecasting/postings_vintages.csv` | Monthly vintages of Indeed's postings index, by country and month |
| `forecasting/btos_ai_observations.csv` | Census BTOS: % of firms using / expecting to use AI, by sector, wording and fortnight, with publication dates |
| `forecasting/btos_calendar.csv` | BTOS fortnight calendar (numbering, reference dates, publication dates) |
| `forecasting/rps_observations.csv` | RPS: % of workers using GenAI, by SOC major group and quarter |
| `forecasting/capability_vintages.csv` | Epoch AI: METR time horizons and ECI per model, one set per archived vintage |

## Refreshing

Tables are rebuilt with `python pipeline/refresh.py`. The scripts live in `pipeline/` at the repo root; how to run them, and which inputs you must download by hand, is in `pipeline/README.md`.

The `forecasting/` tables belong to the rebuilt forecast. From `src/backend` they are rebuilt with `python -m forecasting.vintages` (Indeed), `python -m forecasting.btos`, `python -m forecasting.rps` and `python -m forecasting.capability`, or all at once with `python -m forecasting.run` (see `src/backend/forecasting/README.md` and `documentation/FORECAST_REBUILD.md`).
