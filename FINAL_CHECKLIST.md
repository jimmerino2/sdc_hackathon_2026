Checked against the Domain 1 Finalist Guide (must-haves in section 5, technical expectations in 6, good-to-haves in 7, impact in 8, rules in 9, Q&A in 12). ✅ = built, 🟡 = partly built or not verified, ❌ = nothing built. Rows with nothing built show "—".

**A missing or only-described must-have caps Problem-Solution Fit.** Open must-have gaps: time estimates, free or low-cost labels and HRD Corp programmes (must-have 4), skills tagged to SDGs and the path's SDG contribution (must-have 5), refreshing trend data live (must-have 2).

## Must-haves and demo journey (sections 4 and 5)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Sample synthetic profile ready for the demo (rules: no real CVs) | ❌ | — | Nothing found in the repo | Nowhere |
| Refresh or change trend data live | 🟡 Role forecasts only | **Sync** pulls Indeed, retrains the role forecasts and rescores matches when `FORECAST_REFRESH_ENABLED=true`. One figure can be changed in `signals.csv`. Worker adoption and business adoption are forecast again if their tables changed. AI capability and skill trends are still terminal runs. | [pipeline/sync_trends.py](pipeline/sync_trends.py), [pipeline/refresh.py](pipeline/refresh.py), [occupational/run.py](src/backend/occupational/run.py) | **Roles** page Sync; the **Occupations** month picker doesn't affect matching |
| Results change when the data changes (the "change test", must-have 2) | 🟡 After a restart | Dates update on screen straight away, but the forecast tables behind roles are cached in memory, so a changed value shows only after a restart. | [forecast/service.py](src/backend/app/forecast/service.py) | Edit the data, restart, reload a role |
| Personalised to the learner | 🟡 Built, not yet run against the live model | Leaving the forecast page asks the model for a plain list of skills for the chosen role, seeing what the learner knows. The skills page starts with them added, so the matches show their effect, and the learner can add or remove any. The final list is then arranged into the roadmap. Tests cover the logic, not a real model call or database. | [roadmap/planner.py](src/backend/app/roadmap/planner.py), [roadmap/service.py](src/backend/app/roadmap/service.py), [GapView.vue](src/frontend/src/views/GapView.vue) | Onboarding: `/signal`, `/gap`, then the pathway; try two different profiles |
| Time estimates | 🟡 Built, not yet run live | Each step shows a time. 53 of 737 learning resources state a usable length (an hour or more) on their own page, read by a script; those steps use it. Every other step uses a written formula and is labelled an estimate. A Time left card shows the total and weeks at the learner's own hours a week. Needs migration 0024 applied, or every step is an estimate. | [roadmap/duration.py](src/backend/app/roadmap/duration.py), [fetch_durations.py](pipeline/fetch_durations.py), [TimeCard.vue](src/frontend/src/components/learn/TimeCard.vue) | **Learn**, the Time left card and a selected skill |
| Free or low-cost labels | ❌ Free links exist, unlabelled | — | Only in link titles | Nowhere |
| HRD Corp programmes | ❌ | — | Nothing built | Nowhere |
| Reason for each link | 🟡 Only role and interest pairs | An LLM writes one sentence the first time a role's details are opened, then it's stored. | [jobs/reasons.py](src/backend/app/jobs/reasons.py) | Same section, on the interest cards |
| Every skill tagged | ❌ | — | Nothing built | Nowhere |
| Chosen path's contribution | ❌ | — | Nothing built | Nowhere |
| Labelled as estimates | 🟡 Not on the role page | The role list says "Indicative, not a prediction" and the AI outlook page discloses the US stand-in data. The note under the role chart was removed, so the role page no longer carries the label. | [RoleList.vue](src/frontend/src/components/RoleList.vue), [OutlookView.vue](src/frontend/src/views/OutlookView.vue) | **Roles** list; **AI outlook** |

## Technical expectations (section 6)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Trend pipeline, with fetch date stored | 🟡 Stored, but no in-demo refresh | Each build writes a manifest with as-of dates, run ID and source health. The guide also asks for a refresh during the demo. | [manifest.json](data/processed/manifest.json), [occupational manifest](data/occupational_forecasting/manifest.json) | **Occupations**, method tab |
| Citing sources | 🟡 Not on every recommendation | Roadmap steps carry source links, and role and skill trends now name their sources. Role matches themselves don't cite one. | [Source schema](src/backend/app/roadmap/schemas.py) | **Learn**; **Occupations**; **Roles** |
| Say "no source exists" instead of guessing | ❌ | — | Nothing found in the frontend | Nowhere |
| Naming the LLM | 🟡 Benchmark page only | The model is set in config and only appears in the benchmark tool. The guide says to name it. | [config.py:24](src/backend/app/config.py#L24) | `/benchmark`, dev builds only |
| SDG mapping with reasons, added up for the path | 🟡 Mapping only | The role-to-SDG weights exist, but nothing adds them up for a path. | [0014_onet_roles_sdg.sql](migrations/0014_onet_roles_sdg.sql) | **Roles**, then a role |
| Robustness: thin profile or unknown skill | 🟡 No crash, but no help either | A profile with no skills returns a 409, and an unknown skill scores 0. | [jobs/router.py:35](src/backend/app/jobs/router.py#L35) | Try a profile with no skills |

## Good-to-haves (section 7)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Employer or HR view | ❌ | — | Nothing built | Nowhere |
| Automatic re-planning | 🟡 Manual only | A button re-runs matching when the learner asks. | [SuggestedView.vue](src/frontend/src/views/SuggestedView.vue) | **Roles**, Regenerate roles |
| English, Bahasa Malaysia, Chinese | ❌ English only | — | Nothing built | Nowhere |
| Low-bandwidth | ❌ | — | Nothing built | Nowhere |
| Fairness checks | ❌ | — | Nothing built | Nowhere |
| Aggregated SDG view | ❌ | — | Nothing built | Nowhere |

## Impact and evidence (section 8: 20% of the score, every claim needs numbers)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Reach: who first, through which channel, how many | ❌ | — | Nothing found in the repo | Final report |
| Data freshness and cost: refresh rate and cost per user or month | ❌ | — | Nothing found in the repo | Final report |
| Learning cost: share of a pathway that is free or low-cost | ❌ | Needs the free or low-cost labels first | Nothing built | Final report |
| Measured SDG impact against the Phase 1 baseline | ❌ | — | Nothing found in the repo | Final report |
| Privacy under PDPA | ❌ | — | No mention of PDPA anywhere in the repo | Final report |
| Fairness check method | ❌ | — | Nothing built | Final report |
| Proof (bonus): code, formula or log that backs an impact claim | 🟡 | The scoring formula and forecast evaluation are documented and could back claims. | [JOB_MATCH.md](docs/JOB_MATCH.md), [evaluation.json](data/occupational_forecasting/latest/evaluation.json) | Final report, section 4.1 |

## Rules, pitch and submission (sections 9 to 13)
| Goal | Achieved? | How we achieved it | Where we achieved it | Where to see it |
|---|---|---|---|---|
| Technical and Tools Declaration: every API, model, dataset and AI tool | 🟡 Datasets only | Datasets are listed with sources and dates. APIs, models (the LLM gateway model, LightGBM) and AI tools are not listed in one place. | [SOURCES.md](data/documentation/SOURCES.md) | Submission form |
| Human-centred: AI supports the decision, never makes it | 🟡 Not checked | Scores are formula-based and explained, but the wording on screen hasn't been checked against this rule. | — | **Roles**, **Learn** copy |
| Backup in case of connectivity problems (offline build or recording) | ❌ | — | Nothing found in the repo | Demo day |
| First-time user gets from profile to ranked roles and a plan in minutes (Design & UX) | 🟡 Not timed | The onboarding flows straight into roles and then the roadmap build. | [BuildingView.vue](src/frontend/src/views/BuildingView.vue) | Run it once with a stopwatch |
| Pitch: more than one teammate answers Q&A | ❌ | — | A team task, not code | Demo day |

## Q&A prep (section 12)
| Question judges may ask | Where the answer is | Ready? |
|---|---|---|
| "Please change the trend data now. What should change?" | Source cards and dates update from the data; role forecasts need a restart; no refresh button yet | 🟡 |
| "Where does this recommendation come from? Is this course or number real?" | **Learn** links, **Occupations** sources, Source Data cards on a role | 🟡 Spot-check links first |
| "How do you keep the trend data current, and what does it cost?" | `refresh.py` and the sources' update frequency; no cost figures written down | ❌ |
