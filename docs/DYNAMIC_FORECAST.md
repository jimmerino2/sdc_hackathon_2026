# Dynamic forecast: making results change when the data changes

Status: **plan, nothing built yet.** Written 31 Oct 2026 after reviewing the finalist guide (must-have 2, "Results change when the data changes"; technical expectation "Trend pipeline": store the fetch date with each snapshot and make a refresh possible during the demo).

## 1. Goal

A judge can say "change the trend data now" and see the results change on screen, with the source and date updating too. Specifically:

- The role forecasts, the match scores and ranks, and the source dates move when the data moves.
- The data lives in a database table, not in local files, because the Replit Autoscale deployment has a temporary filesystem that is not shared between instances.
- Refreshing is a deliberate action by an admin, never automatic.

## 2. What was agreed

1. **Horizon toggle.** Let judges switch the forecast horizon between 3, 6 and 12 months.
   - Skills: Occupations already has a "Forecast horizon" dropdown (default 6 months).
   - Roles: the backend already accepts `horizon` of 3, 6, 9 or 12 on `GET /jobs/recommend`, but the app always uses 12. The toggle needs wiring up, and changing it recomputes the matches.
   - The "3 months" seen on the skills screens is something else: skill shares are measured over rolling 3-month windows set by the offline pipeline. We toggle the forecast horizon, not that window.
2. **Store the trend data in a table** (Supabase, already in the stack) instead of CSV and JSON files.
3. **Admin panel.** It contains AI Outlook, Occupations and LLM Benchmark. Only two accounts are admins: `lamwayhou@gmail.com` and `lytan0714@gmail.com`.
4. **No automatic updates.** Refreshing the data is a button in the admin panel, on the relevant page.

Open question on item 3, see section 7 (Occupations is the Future Skills Radar the judges must see).

## 3. How it works today (why the change test fails)

| Part | Where the data comes from | Result when data changes |
|---|---|---|
| Role forecasts (rising and declining roles) | `src/backend/ml/output/forecast_output.csv` and `job_forecast.csv`, built by an offline training script (`train_lgbm.py`) | Nothing. `refresh.py` updates `data/processed/*` but does not rebuild these |
| Role history on the chart | `data/processed/model_table_US.csv` | Cached in memory (`lru_cache`) until restart |
| Match scores and ranks | The role forecast above feeds the outlook part (35% of the score) | Only change if the forecast files change |
| Saved role suggestions | Stored per profile when generated | Stay as they were until "Regenerate roles" |
| Source dates | `data/processed/manifest.json`, read on each call | Update straight away |
| Skill trends (Occupations) | `data/occupational_forecasting/latest/*` (about 4 MB signals, 1.7 MB as-of, 420 KB evaluation), built by `occupational/run.py` | Only after a long offline run |
| AI Outlook "chances" | `src/backend/forecasting/output/*` | Only after its own offline run |
| Skill demand used by the roadmap | `forecast_demand` column in the `onet_role_skills` table, loaded by a migration | Static |

Dates update live but numbers do not, so a judge editing data would see a new date next to old numbers.

## 4. Proposed design

### 4.1 Snapshots, not overwrites

- A `trend_snapshots` table: id, source, `fetched_at`, `as_of`, kind (`source` or `edited`), created by, note, and an active flag.
- A `trend_points` table: snapshot id, series (e.g. a sector), month, value. About 3,700 monthly rows for the sector index; small enough for the free tier.
- Large artifacts (skill forecasts, evaluation JSON) go in a storage bucket or JSON column, not one row per value.
- Exactly one snapshot is active. Rolling back is switching the active flag, which also covers the guide's "fall back to the last good snapshot".
- A `data_version` value bumps whenever the active snapshot changes.

### 4.2 Role trends computed live

- The main role forecast is "last year's pace repeats", plus a scenario shift (±0.25 × the role's AI exposure relative to average, scaled by horizon). That is plain arithmetic on the sector index, so it can run when data is read, with no retraining.
- The match scores and ranks then change on their own, because the outlook part of the score reads these forecasts.
- The LightGBM forecast is a comparison only. See issue 6.3.

### 4.3 Recomputing saved suggestions

- Each saved suggestion set records the `data_version` it was made with.
- When a profile opens a set from an older version, recompute it then (lazily), instead of recomputing every profile when data changes.

### 4.4 Horizon toggle

- Roles: a 3 / 6 / 12 month control that calls the matching with that horizon. Decide whether the result is saved or just shown (recommendation: just shown, with the saved set staying at 12).
- Skills: use the existing dropdown, defaulting to the same value.

### 4.5 Admin panel

- Pages: AI Outlook, Occupations, LLM Benchmark (see question in section 7).
- Controls per page: a "Refresh from source" button, an edit control (pick a sector or role, change a value), a "Reset to source" button, and the active snapshot with its dates.
- Edits create a separate `edited` snapshot. Every source card and role page shows an "edited" badge with the date while one is active.

### 4.6 Refresh button

- Role trends: pulls the Indeed files, writes a new snapshot, validates it, then activates it. Takes seconds.
- Skill trends: a separate button for the long run (minutes), with live progress.
- A failed run leaves the active snapshot unchanged and tells the admin what went wrong.

## 5. Admin access

Findings from the code (so the plan does not assume what is not there):

- There is no admin concept today.
- The frontend identifies a user by a profile id kept in the browser, and the backend does not check it. The existing `get_current_user` dependency is not used on any route.
- Email login verifies a one-time code with Supabase, but the backend discards the session it gets back and returns only the profile.

So an admin check in the frontend alone would be cosmetic, and the refresh and edit endpoints would be open to anyone.

Plan:

1. On a verified email login, the backend returns a signed token that includes the email.
2. Every admin endpoint requires that token and checks the email is in an `ADMIN_EMAILS` setting on the server (set in the environment, not in frontend code).
3. The frontend hides admin pages for other users and guards the routes, as a convenience, not as the protection.
4. Only the write endpoints (refresh, edit, reset, benchmark runs) are gated. The read endpoints stay public, because other screens use them.
5. Both admins need a profile synced with those emails, because login works only for a synced email.

## 6. Issues to resolve

### 6.1 Critical

1. **Occupations is part of the demo journey.** Step 2 of the judges' journey is the Future Skills Radar with rising and declining skills, and that is the Occupations page (demand and emerging tabs). If only the two admins can see it, a judge on a normal account cannot. AI Outlook feeds the "% chance" numbers on role screens, though only the page itself would be hidden. Recommendation: keep read-only Occupations and AI Outlook for everyone, put the controls in the admin panel, and make only LLM Benchmark fully admin-only.
2. **No real admin check.** See section 5.
3. **The LightGBM forecast goes stale.** If the main forecast is recomputed live, the model forecast beside it still comes from the old training run, under a fresh date. Either retrain on refresh (needs the LightGBM library and takes minutes) or hide or label the model forecast whenever it is older than the data.

### 6.2 Important

4. **Refresh is long-running on Autoscale.** Skill trends need minutes and cannot finish inside one request. An instance can scale down mid-run, and two admins could click at once. Use a run-status row in the database so only one refresh runs at a time across instances, show progress, and keep the active snapshot if a run fails.
5. **The skill pipeline writes files and needs heavy libraries.** It writes to `data/occupational_forecasting/` and imports modelling packages that may not be installed on the deployed runtime. Outputs must go to the database or a storage bucket.
6. **Outbound network and keys.** Refresh needs access to GitHub (Indeed), Hacker News and the Census site. Adzuna needs its API key as a secret. A live pull in front of judges can fail, so the failure path must keep the current data and say so.
7. **Edits need an audit trail.** Store who edited, when and what; show an "edited" badge; offer reset. This protects against the guide's warning about hard-coded output presented as live.
8. **Caches across instances.** Replace `lru_cache` on the forecast and matching data with a short `data_version` check, otherwise one instance updates while another keeps old numbers.
9. **Source dates come from `manifest.json`.** The Source Data cards read dates from that file. With a table, they must read the active snapshot.
10. **Saved suggestions go stale.** See 4.3.

### 6.3 Smaller

- **LLM Benchmark costs credits.** If it moves into production, runs need the admin check, a confirm and a spending limit.
- **Offline backup.** The guide asks for an offline build or recording. Keep a CSV export so a backup build works without Supabase, and keep the current files as a read-only fallback when the table is unreachable (the README promises the app starts without Supabase credentials).
- **The roadmap's `forecast_demand`** stays static unless it too is refreshed from the snapshot. Lower priority.
- **Row-level security.** Public key read-only; writes only with the service key on the server, never in the frontend.
- **Before the demo.** Save a known-good snapshot, test Reset once, and run a refresh on the deployed app, not just locally.

## 7. Open questions

1. Should Occupations and AI Outlook stay visible (read-only) to everyone, with controls in the admin panel? (Recommended.)
2. Is a fast role-trend refresh plus a separate slow skill-trend refresh acceptable?
3. Is it fine to hide or label the LightGBM comparison when it is older than the data, rather than retrain on every refresh?
4. Does the horizon toggle on roles only display, or also save the result?

## 8. Suggested build order

1. Snapshot tables, and read the sector index and sources from them (CSV fallback kept).
2. Live role forecasts from the active snapshot, with the version check replacing the caches.
3. Lazy recompute of saved suggestions by `data_version`.
4. Admin token and the admin-only write endpoints.
5. Admin panel: edit, reset, role-trend refresh, edited badges.
6. Horizon toggle on roles.
7. Skill-trend and AI-outlook refresh with progress.
8. Tests: admin check, snapshot activation and rollback, forecast arithmetic against the current files (it should reproduce them), and a before-and-after change test.

## 9. Test for "done"

Edit one sector's latest value in the admin panel. Within a few seconds:

- the role chart and its percentage change move,
- the match scores and ranks on the Roles page change after reload,
- the Source Data card shows an "edited" badge and the new date,
- Reset to source puts everything back.
