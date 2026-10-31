Checked against the Domain 1 Finalist Guide (must-haves in section 5, technical expectations in 6, good-to-haves in 7, impact in 8, rules in 9, Q&A in 12). ✅ = built, 🟡 = partly built or not verified, ❌ = nothing built. Rows with nothing built show "—".

**A missing or only-described must-have caps Problem-Solution Fit.** Open must-have gaps: no sample synthetic profile, HRD Corp courses that can't be set up from this repo (must-have 4), the path's SDG contribution not added up (must-have 5), and AI capability and skill trends that don't refresh live (must-have 2).

## Must-haves and demo journey (sections 4 and 5)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Sample synthetic profile ready for the demo (rules: no real CVs) | ❌ | — | Nothing found in the repo | Nowhere |
| Refresh or change trend data live | 🟡 Role forecasts only | **Sync** pulls Indeed, retrains the role forecasts and rescores matches when `FORECAST_REFRESH_ENABLED=true`. One figure can be changed in `signals.csv`. Worker adoption and business adoption are forecast again if their tables changed. AI capability and skill trends are still terminal runs. Not tried on the deployed app. | [pipeline/sync_trends.py](pipeline/sync_trends.py), [pipeline/refresh.py](pipeline/refresh.py), [occupational/run.py](src/backend/occupational/run.py) | **Roles** page Sync; the **Occupations** month picker doesn't affect matching |
| Results change when the data changes (the "change test", must-have 2) | 🟡 Built, not rehearsed | Sync clears the cached forecast tables, so a changed value reaches roles with no restart. Pressing Sync again goes back to Indeed's data. Tests cover the cache clearing with a stand-in for the script. | [forecast/sync.py](src/backend/app/forecast/sync.py), [forecast/service.py](src/backend/app/forecast/service.py) | Change a figure in `signals.csv`, press Sync on **Roles**, reload a role |
| Personalised to the learner | 🟡 Built, not yet run against the live model | Leaving the forecast page asks the model for a plain list of skills for the chosen role, seeing what the learner knows. The skills page starts with them added, so the matches show their effect, and the learner can add or remove any. The final list is then arranged into the roadmap. Tests cover the logic, not a real model call or database. | [roadmap/planner.py](src/backend/app/roadmap/planner.py), [roadmap/service.py](src/backend/app/roadmap/service.py), [GapView.vue](src/frontend/src/views/GapView.vue) | Onboarding: `/signal`, `/gap`, then the pathway; try two different profiles |
| Time estimates | 🟡 Built, not yet run live | Each step shows a time. 53 of 737 learning resources state a usable length (an hour or more) on their own page, read by a script; those steps use it. Every other step uses a written formula and is labelled an estimate. A Time left card shows the total and weeks at the learner's own hours a week. Needs migration 0024 applied, or every step is an estimate. | [roadmap/duration.py](src/backend/app/roadmap/duration.py), [fetch_durations.py](pipeline/fetch_durations.py), [TimeCard.vue](src/frontend/src/components/learn/TimeCard.vue) | **Learn**, the Time left card and a selected skill |
| Free or low-cost labels | 🟡 By site, not by course | Each skill's links are split into **Free** and **May cost**. A link counts as May cost if its site is on a list of sites that sell courses; everything else is called free, so an unlisted paid site would be labelled free. There is no separate low-cost label. | [learn/cost.ts](src/frontend/src/learn/cost.ts), [NextUpCard.vue](src/frontend/src/components/learn/NextUpCard.vue) | **Learn**, a selected skill |
| HRD Corp programmes | 🟡 Built, not set up from this repo | A **HRD Corp Verified** band lists up to 5 claimable courses for a skill, with fees and the date read from HRD Corp's public list. `migrations/0026_hrd_programmes.sql` and `data/hrdcorp/` are not in the repo, and the live table wasn't checked. Without the table every skill says no course turned up. | [hrd/service.py](src/backend/app/hrd/service.py), [load_hrd_programmes.py](pipeline/load_hrd_programmes.py), [HrdCard.vue](src/frontend/src/components/learn/HrdCard.vue) | **Learn**, a selected skill |
| Reason for each link | 🟡 Only role and interest pairs | An LLM writes one sentence the first time a role's details are opened, then it's stored. | [jobs/reasons.py](src/backend/app/jobs/reasons.py) | **Roles**, a role's SDGs tab |
| Every skill tagged | ✅ On the role page | All 273 skills have a main SDG, relevant SDGs and targets, from the database or else the CSV. The role page shows them for the role's key skills. The **Learn** page doesn't show them. | [sdg/service.py](src/backend/app/sdg/service.py), [onet_skills_sdg.csv](data/processed/onet_skills_sdg.csv), [RoleDetail.vue](src/frontend/src/components/RoleDetail.vue) | **Roles**, a role's SDGs tab |
| Chosen path's contribution | 🟡 Per role, no path total | All 46 roles show how they serve the SDGs, with targets. Nothing adds this up across the learner's own path, and **Learn** shows no SDGs. | [sdg/service.py](src/backend/app/sdg/service.py), [RoleDetail.vue](src/frontend/src/components/RoleDetail.vue) | **Roles**, a role's SDGs tab |
| Labelled as estimates | 🟡 Not on the role list | The note under the role chart says "Indicative, not a prediction" and names the US stand-in data. The role list no longer carries the label. | [RoleDetail.vue:407](src/frontend/src/components/RoleDetail.vue#L407) | **Roles**, a role's AI outlook tab |

## Technical expectations (section 6)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Trend pipeline, with fetch date stored | 🟡 Part of it refreshes in the demo | Each build writes a manifest with as-of dates, run ID and source health. Sync refreshes the role forecasts during the demo; the rest are terminal runs. | [manifest.json](data/processed/manifest.json), [occupational manifest](data/occupational_forecasting/manifest.json), [DataFreshness.vue](src/frontend/src/components/DataFreshness.vue) | **Occupations**, method tab; **Roles** |
| Citing sources | 🟡 Not on every recommendation | Roadmap steps carry source links, role and skill trends name their sources, the role list stamps Indeed, the role page cites eMASCO, and HRD Corp courses link to their list. SDG targets are not cited. | [Source schema](src/backend/app/roadmap/schemas.py), [SourceStamp.vue](src/frontend/src/components/SourceStamp.vue), [MascoMap.vue](src/frontend/src/components/MascoMap.vue) | **Learn**; **Occupations**; **Roles** |
| Say "no source exists" instead of guessing | 🟡 In some places | HRD Corp courses, SDGs, eMASCO and starter projects each say when nothing was found. Skills with no links and role matches have no such wording. | [HrdCard.vue:59](src/frontend/src/components/learn/HrdCard.vue#L59), [RoleDetail.vue:366](src/frontend/src/components/RoleDetail.vue#L366) | **Learn**; a role's Where it sits and SDGs tabs |
| Naming the LLM | 🟡 Privacy page and benchmark only | The model is set in config. The privacy page names Google Gemini and the benchmark tool shows the model. The role chart names LightGBM. The guide says to name it. | [config.py:24](src/backend/app/config.py#L24), [PrivacyView.vue:40](src/frontend/src/views/PrivacyView.vue#L40) | **Privacy Policy**; `/benchmark`, dev builds only |
| SDG mapping with reasons, added up for the path | 🟡 Mapping only | Roles and skills map to SDGs and targets, and interests get a written reason. Nothing adds them up for a path. | [0014_onet_roles_sdg.sql](migrations/0014_onet_roles_sdg.sql), [0026_onet_sdg_targets.sql](migrations/0026_onet_sdg_targets.sql) | **Roles**, a role's SDGs tab |
| Robustness: thin profile or unknown skill | 🟡 Thin profile only | A profile with no skills gets a 409, shown as a prompt to rate a few skills. An unknown skill still scores 0 with no message. | [jobs/router.py:35](src/backend/app/jobs/router.py#L35), [api/jobs.ts:174](src/frontend/src/api/jobs.ts#L174) | Try a profile with no skills |

## Good-to-haves (section 7)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Employer or HR view | ❌ | — | Nothing built | Nowhere |
| Automatic re-planning | 🟡 Manual only | The Sync button re-runs matching when the learner asks. | [SuggestedView.vue](src/frontend/src/views/SuggestedView.vue) | **Roles**, Sync |
| English, Bahasa Malaysia, Chinese | ❌ English only | — | Nothing built | Nowhere |
| Low-bandwidth | ❌ | — | Nothing built | Nowhere |
| Fairness checks | ❌ | — | Nothing built | Nowhere |
| Aggregated SDG view | ❌ | — | Nothing built | Nowhere |

## Impact and evidence (section 8: 20% of the score, every claim needs numbers)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Reach: who first, through which channel, how many | ❌ | — | Nothing found in the repo | Final report |
| Data freshness and cost: refresh rate and cost per user or month | ❌ | — | Nothing found in the repo | Final report |
| Learning cost: share of a pathway that is free or low-cost | ❌ | The Free and May cost labels now exist, so this can be counted; nobody has yet | Nothing built | Final report |
| Measured SDG impact against the Phase 1 baseline | ❌ | — | Nothing found in the repo | Final report |
| Privacy under PDPA | 🟡 Page written, gaps remain | A policy written to follow the PDPA covers what's collected, who it's shared with, retention and rights, and sign-up asks for consent. It tells users to contact the team but gives no address, and deleting everything isn't in the app. Not yet in the final report. | [PrivacyView.vue](src/frontend/src/views/PrivacyView.vue), [SyncView.vue](src/frontend/src/views/SyncView.vue) | **Privacy Policy** in the side nav; final report |
| Fairness check method | ❌ | — | Nothing built | Final report |
| Proof (bonus): code, formula or log that backs an impact claim | 🟡 | The scoring formula and forecast evaluation are documented and could back claims. | [JOB_MATCH.md](docs/JOB_MATCH.md), [evaluation.json](data/occupational_forecasting/latest/evaluation.json) | Final report, section 4.1 |

## Rules, pitch and submission (sections 9 to 13)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Technical and Tools Declaration: every API, model, dataset and AI tool | 🟡 Datasets only | Datasets are listed with sources and dates. APIs (LinkedIn), models (the LLM gateway model, LightGBM), AI tools and the newer data (HRD Corp, eMASCO) are not listed in one place. | [SOURCES.md](data/documentation/SOURCES.md) | Submission form |
| Human-centred: AI supports the decision, never makes it | 🟡 Not checked | Scores are formula-based and explained, but the wording on screen hasn't been checked against this rule. | — | **Roles**, **Learn** copy, including "Larp on LinkedIn" |
| Backup in case of connectivity problems (offline build or recording) | ❌ | — | Nothing found in the repo | Demo day |
| First-time user gets from profile to ranked roles and a plan in minutes (Design & UX) | 🟡 Not timed | The onboarding flows straight into roles and then the roadmap build. | [BuildingView.vue](src/frontend/src/views/BuildingView.vue) | Run it once with a stopwatch |
| Pitch: more than one teammate answers Q&A | ❌ | — | A team task, not code | Demo day |

## Q&A prep (section 12)
| Question judges may ask | Where the answer is | Ready? |
|---|---|---|
| "Please change the trend data now. What should change?" | Change a figure in `signals.csv` and press Sync: role forecasts and matches update with no restart. AI capability and skill trends don't | 🟡 Rehearse it |
| "Where does this recommendation come from? Is this course or number real?" | **Learn** links, **Occupations** sources, the Indeed stamp on the role list, eMASCO on a role | 🟡 Spot-check links first |
| "How do you keep the trend data current, and what does it cost?" | Sync, `refresh.py` and the sources' update frequency; no cost figures written down | ❌ |
