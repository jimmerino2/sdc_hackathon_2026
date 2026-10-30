# Supabase setup

How the reference data gets into Supabase. Column meanings are in `data/documentation/STRUCTURE.md`; sources in `SOURCES.md`.

## What's here

| File | Purpose |
| ---- | ------- |
| `0001_initial_schema.sql` | Creates the 7 tables, primary/foreign keys, and Row Level Security |
| `0002_onet_role_skills_source.sql` | Adds nullable `onet_role_skills.source` (http(s) URL, checked) |
| `0003_roadmap.sql` | Adds `roadmap` (one row per role; `section`/`unit` = current step) and `roadmap_detail` (skill nodes, each with its own `section`/`unit`, status and prerequisites), with RLS |
| `0004_profiles.sql` | Adds `profiles` (one row per email: name, career stage, concerns, skills, experience), service-role access only |
| `0005_roadmap_detail_id.sql` | Adds a unique `roadmap_detail.roadmap_detail_id` (uuid) so one node can be addressed by a single id |
| `0006_onet_roles_icon.sql` | Adds `onet_roles.icon`, a Lucide icon name per role for the frontend (kept when `onet_roles` is reloaded) |
| `0007_profiles_skill_scores.sql` | Changes `profiles.skills` from `text[]` to a jsonb array of `{name, score}` (O*NET names, score 0-1) |
| `0008_roadmap_profile.sql` | Ties each `roadmap` to a profile (`profile_id`, one roadmap per profile and role) and makes roadmaps private (service role only). Older ownerless roadmaps are kept with a null `profile_id` and ignored |
| `0010_roadmap_created_at.sql` | Adds `roadmap.created_at`, so a profile's most recent roadmap can be found without naming the role |
| `0011_profiles_suggested_roles.sql` | Adds `profiles.suggested_roles` (jsonb) and `suggested_at`: the roles last suggested to the learner, saved so they can be shown again without recomputing |
| `0012_onet_role_skills_group.sql` | Adds `onet_role_skills.skill_group`: all 260 skills in 27 areas (e.g. HTML, CSS and JavaScript are "Web Development"), used to label roadmap nodes and group the learned skills on the profile |
| `0013_interests.sql` | Adds `interests` (15 seeded interests, each with up to 3 UN SDGs as jsonb `{sdg, value}` whose values add up to 1; public read) and `profile_interests` (links profiles to interests, service role only). Drops `profiles.concerns` |
| `0014_onet_roles_sdg.sql` | Adds `onet_roles.sdg` (jsonb `{sdg, value}`, up to 3 goals per role, values adding up to 1) and fills it for all 46 roles. Used to match roles to a learner's interests and to explain why a role was suggested |
| `0015_role_interest_reasons.sql` | Adds `role_interest_reasons`: one LLM-written sentence per role, SDG and interest explaining why the role fits that interest, written the first time a role's details are opened (`GET /jobs/reasons`) and reused after. Service role only |
| `0016_roadmap_challenge.sql` | Adds `roadmap_challenge`: the Bonus Quests of a tech-role roadmap, one per two sections (an odd last section joins the final one). Each has an LLM-written title, brief, SDG, tech stack and weighted rubric, plus the latest GitHub repo submitted and its per-criterion score, reasoning and tips. Service role only |
| `0017_onet_role_skills_forecast_gap.sql` | Inserts 16 `onet_role_skills` tech rows for Software Engineer and Data Analyst: named tools the occupational-forecasting dataset (`/occupations`) tracks with real recent job-ad evidence that weren't already in O*NET's technology-skills list for that role (also added to `data/processed/onet_role_skills.csv`) |
| `0018_onet_role_skills_forecast_demand.sql` | Adds `onet_role_skills.forecast_demand` (0-1, nullable): the occupational-forecasting dataset's 6-month share-of-ads forecast for a skill, matched by name against the curated taxonomy, filled for the 3 roles that dataset covers. Read by the roadmap planner alongside `importance` |
| `0019_roadmap_section_titles.sql` | Adds `roadmap.section_titles` (jsonb array, nullable): the LLM's own title for each section (index = section - 1), now that the planner groups skills by subject-matter coherence instead of a fixed stage template and names each section itself |
| `0020_challenge_stages.sql` | Recreates `roadmap_challenge` (drops 0016's rows): two-stage challenges owned by a profile and a tech role, any number per role, linked to a roadmap only optionally (building a tech roadmap writes one; deleting the roadmap only clears the link). Stage 1 uses the roadmap's sections 1-2 or the role's foundational skills; passing it (score 85+) lets Robbee rewrite it into a harder stage 2, stage 1's result moving into `history`. Adds `stinger_award`, one row per passed stage (a learner's stingers are its row count). Service role only |
| `0021_social.sql` | Adds `profiles.total_pollen` (0 to start; `add_pollen()` changes it atomically) and `social_friendship`: friend requests addressed by email (so they can wait for someone who hasn't signed up), pending until accepted. The leaderboard ranks the learner and their accepted friends by pollen. Service role only |
| `0009_profiles_bee.sql` | Adds `profiles.bee`, the learner's companion (Libbee by default; Phoebee, Tobee or Barnabee), checked against that list |
| `../pipeline/load_supabase.py` | Loads `data/processed/*.csv` into those tables |

Tables: `onet_roles`, `onet_role_skills`, `ai_exposure`, `ai_exposure_detail`, `crosswalk`, `onet_to_my_group`, `my_vacancies`.

Not included: `forecast_output` (shape not agreed yet) and the training files `signals.csv` and `model_table_US.csv`, which stay as files. Add new tables as `0002_...sql`, `0003_...sql`, and so on. Don't edit applied migrations.

## Two keys, two jobs

| Key | Where it lives | Can do |
| --- | -------------- | ------ |
| Publishable (anon) key | `src/backend/.env` as `SUPABASE_KEY` | **Read only.** Used by the app at runtime |
| Service-role key | Your shell only, **never in a file or git** | Bypasses RLS, so it can create and write. Used only to load data |

The one exception is `POST /roadmap`, which writes the roadmap tables and so needs the service-role key at runtime: set `SUPABASE_SERVICE_KEY` in the backend's environment (`src/backend/.env` is git-ignored; a shell variable also works). Without it the endpoint returns 503.

The schema enables RLS with a select-only policy for `anon` and no write policies. So the publishable key cannot load data: an upsert with it is rejected. Do not add a write policy for `anon` to get around this, because the data would be publicly writable.

## First-time setup

1. Create the tables. Open the Supabase SQL editor, paste `migrations/0001_initial_schema.sql`, and run it. Run it once; it has no `if not exists`.
2. Get the service-role key from Project Settings → API.
3. Install the dependencies. Pick the option that matches your setup:

   | Your setup | Install | Run Python scripts with |
   | ---------- | ------- | ----------------------- |
   | **`uv` installed** (recommended; the project has `pyproject.toml` and `uv.lock`) | `uv sync` | `uv run python ...` |
   | **No `uv`, plain Python** | `python -m pip install supabase` | `python ...` |

   - If `pip` is "not recognized" on Windows, use `python -m pip` as above. Don't call `pip` directly.
   - If `python -m pip` fails with "externally-managed-environment" (common with MSYS2 or system Pythons), use `uv`, or create a virtual environment first: `python -m venv .venv`, then activate it and install.
   - `uv` install instructions: https://docs.astral.sh/uv/getting-started/installation/

4. Load the data. Set the key in your shell, then run the loader.

   PowerShell (with `uv`):
   ```powershell
   $env:SUPABASE_SERVICE_KEY = "<service role key>"
   uv run python pipeline/load_supabase.py
   ```

   PowerShell (plain Python):
   ```powershell
   $env:SUPABASE_SERVICE_KEY = "<service role key>"
   python pipeline/load_supabase.py
   ```

   macOS / Linux / Git Bash: use `export SUPABASE_SERVICE_KEY="<service role key>"` instead of the `$env:` line.

   `SUPABASE_URL` is read from `src/backend/.env`, or set it in the shell.
5. Check row counts in the Table Editor: 46, 4,548, 46, 746, 51, 46 and 3,969 for the tables in the order above.

## Loader options

```
python pipeline/load_supabase.py --dry-run                      # parse and validate CSVs, no network
python pipeline/load_supabase.py --tables onet_roles crosswalk  # load a subset
```

(Prefix with `uv run` if you use `uv`. `--dry-run` needs no extra packages.)

- Rows upsert on each table's primary key, so re-running is safe.
- Rows removed from a CSV are **not** deleted in Supabase. Truncate the table first if you need that.
- Blank CSV cells load as `NULL`. The app must handle nulls (for example `onet_role_skills.level`, and `automation_share` for 3 jobs).
- Tables load in foreign-key order (`onet_roles` first).

## Refreshing data

1. Rebuild the CSVs with `python pipeline/refresh.py` (see `pipeline/README.md`).
2. Re-run `python pipeline/load_supabase.py`.
3. Don't hand-edit rows in Supabase. Fix the pipeline and reload.

## Schema changes

Add a new numbered `.sql` file, run it in the SQL editor, and update `STRUCTURE.md`. Keep the provenance columns (`source`, `source_url`, `as_of_date`) because the app's "last updated" badge reads them.

## Gotchas

- `my_vacancies` is display only. It's a raw count, and totals jump about 2x in 2021-Q3 and 2025-Q3, so never compare across those quarters. 2026 is partial.
- `49-9081.00` (Wind Turbine Service Technicians) has `exposure = 0.000` as a fallback, and is missing from `ai_exposure_detail`. Show it as "no data".
- The US stands in for Malaysia in the forecast. The UI should say so.
