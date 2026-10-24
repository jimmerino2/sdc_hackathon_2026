# data/occupational_forecasting

Local storage for occupational forecasting, built by `python -m occupational.run` from `src/backend`. The code and method are described in `src/backend/occupational/README.md`.

None of these tables feeds the industry or AI-outlook models, and none of them is in Supabase.

## Data types

| Type | Where |
| --- | --- |
| Real observations | `datasets/`, `adoption/worker_ai_usage*.csv`, `normalized/` (from HN, Adzuna, Stack Overflow, RPS, O\*NET) |
| Model outputs | `latest/forecast.csv.gz` and `latest/asof.csv.gz` (forecasts), `latest/evaluation.json` (tests) |
| Proxies | `adoption/employer_ai_tool_signal.csv`. An ads-based signal, not a deployment rate |
| Exposure | `adoption/task_exposure.csv`. Not adoption |
| Synthetic data | None here. The tests build their own synthetic ads in a temporary folder |

## Folders

| Path | Git | What |
| --- | --- | --- |
| `raw/` | ignored | Source downloads: `hn/` (threads), `adzuna/<date>/` (snapshots), `so_survey/<year>.csv`, `onet/` |
| `taxonomy/occupations.json`, `geo.json`, `curated_skills.csv`, `registry_overrides.csv` | tracked | Hand-written inputs. Reviewer decisions on skills go in `registry_overrides.csv` (`skill,status,merged_into,note`) |
| `taxonomy/skill_registry.json` | tracked | Built. Every skill with its status (known, newly_detected, under_review, merged, deprecated), O\*NET coverage, spellings seen, first seen, confidence, reason and evidence links. Versioned; earlier versions are in `registry_history/` |
| `normalized/ads.csv.gz` | tracked | One row per ad, without its text (see below) |
| `normalized/ad_skills.csv.gz` | tracked | `ad_id, skill_id`: each skill an ad names (curated and registered discovered skills) |
| `normalized/ads_text.csv.gz`, `known_skill_cache.*` | ignored | Ad text, and cached matches |
| `datasets/demand_totals.csv` | tracked | `month, country, occupation, n_ads, is_partial`. `n_ads` is the denominator: eligible HN ads in that cell |
| `datasets/demand_counts.csv.gz` | tracked | `month, country, occupation, skill_id, n_ads_skill` |
| `datasets/emerging.csv` | tracked | Per country × occupation × skill: recent (6 months) and base (12 months before) counts and shares, `change_pp`, `growth_lb_pp` / `growth_ub_pp` (80% band of the change), employers, months present, confidence, registry status, O\*NET coverage |
| `datasets/discovery_backcheck.csv` | tracked | Withheld-skill back-check: per skill × quarterly as-of month, whether the detector flagged it from data available then |
| `datasets/adzuna_snapshots.csv` | tracked | `retrieved_at, country, occupation, skill_id, n_ads, n_ads_skill, share` from Adzuna snippets |
| `datasets/coverage.csv` | tracked | Per source × month: ads, duplicates, eligible, classified, with a country, multi-occupation |
| `adoption/worker_ai_usage.csv` | tracked | Stack Overflow survey per year × occupation × country: n, share using AI tools, 95% Wilson interval, wording, dev types, comparability note. Shares with n < 30 are flagged `published_ok = False` |
| `adoption/worker_ai_usage_context.csv` | tracked | RPS quarterly GenAI use, SOC group 15 and all workers (US) |
| `adoption/employer_ai_tool_signal.csv` | tracked | Monthly HN ads expecting AI-tool use per cell (proxy) |
| `adoption/task_exposure.csv` | tracked | Anthropic Economic Index usage percentile for the occupations' O\*NET codes |
| `adoption/sources.json` | tracked | Population, definition, period, geography and limitation of every adoption source, plus what was looked for and not found |
| `latest/` | tracked except `backtest.csv.gz` | The served run: `forecast.csv.gz` (per cell × skill × horizon: forecast, 80% range, last shares and counts, evidence, method, status), `evaluation.json`, `cell_accuracy.csv` (test errors per cell × horizon × method), `asof.csv.gz` (validation and test forecasts of the served method and persistence, with actuals) |
| `runs/<run_id>/` | ignored | The last 5 runs, in full |
| `runs/run_log.jsonl` | ignored | Every run attempt, ok or failed |
| `manifest.json` | tracked | Run id, model / data / taxonomy / registry versions, latest observation, source health, counts |
