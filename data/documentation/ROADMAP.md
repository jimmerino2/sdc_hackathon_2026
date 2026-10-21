# Data Roadmap

Ideas for widening the dataset and improving the model **after the core features ship**. Nothing here is built or committed to. Current sources are in `SOURCES.md`; column meanings in `STRUCTURE.md`.

## Why expand

The dataset is narrower than the underlying sources:

- All 46 roles are hand-picked from O\*NET, which has about 1,000 occupations. Roughly 10 of the 46 are tech or engineering roles. The rest cover health, education, food service, driving, retail and so on.
- A third of `onet_role_skills` (1,488 of 4,548 rows) is `skill_type = tech`, meaning software tools, which mostly describe IT jobs.
- The Indeed sector crosswalk has several separate IT sectors (Software Development, IT Systems & Solutions, IT Infrastructure, Data & Analytics), while sectors such as hospitality, agriculture and wider healthcare are thin or absent.
- The Malaysia mapping uses only 8 broad ISCO major groups.

## Candidate sources

Licence and crosswalk notes below are from memory. **Verify each before relying on it**, as we still need to do for the DOSM licence.

| Source | What it adds | Effort | Notes |
| ------ | ------------ | ------ | ----- |
| **More of O\*NET** (same database we use) | More roles; more fields per role | Low | Same CC-BY-4.0 licence, no new vocabulary. `ai_exposure_detail` already has exposure for 746 occupations, so exposure data already exists for most new roles. |
| Other O\*NET files: Work Activities, Abilities, Work Context, Tasks, Related Occupations | Non-tech skills; task-level detail; career-change links | Low to medium | Related Occupations could drive the reskilling roadmap (Screens 4-5). |
| **MASCO** (Malaysia Standard Classification of Occupations, based on ISCO-08) | Finer Malaysian occupation mapping than 8 major groups | Medium | Could replace or refine `onet_to_my_group`. Check the current edition and licence with DOSM. |
| **NOSS** (National Occupational Skills Standards, Malaysia's skills development department JPK) | Local skill standards and training pathways | Medium | Malaysia-specific, so useful for the reskilling roadmap. Format and licence unchecked. |
| **ESCO** (EU) | About 3,000 occupations and 13,000+ skills, multilingual | Medium to high | Maps to ISCO, so it could link to O\*NET through an ISCO crosswalk. That crosswalk is an extra join with its own errors. |
| **Singapore SkillsFuture Skills Framework** | Sector-specific skills, regional relevance | Medium | Check availability and licence. |
| **Lightcast Open Skills** | Large skills vocabulary, good for matching resume text | Medium | Check licence and API terms. |

## Bottlenecks

1. **Hand-curated mappings.** `crosswalk.csv` (role to Indeed sector, with weights summing to 1) and `onet_to_my_group.csv` each need a human decision and a written rationale per role. Every new role or source needs this before the app can use it.
2. **Indeed sector coverage.** Forecasts exist only for sectors in the Indeed postings data. A role in a sector Indeed doesn't track has no demand trend, so we need a fallback or a "no data" state.
3. **US stands in for Malaysia.** The forecast uses US data (`is_proxy_geo: true`). More roles don't fix this. Malaysian demand data, if it's ever available at the needed granularity, would.
4. **Malaysian vacancy data is display only.** `my_vacancies` is a raw count with coverage breaks in 2021-Q3 and 2025-Q3, so it can't feed the model.
5. **Exposure gaps.** Some O\*NET occupations are missing from the Anthropic Economic Index (for example `49-9081.00`), and many have low-sample or blank metrics in `ai_exposure_detail`. More roles means more "no data" cases the app must handle.
6. **Skill vocabulary mismatch.** Mixing sources (O\*NET, ESCO, Lightcast) means mapping between different skill names and IDs. Pick one canonical vocabulary and map the others onto it, rather than merging them.
7. **Licensing.** Each new source needs a licence check and attribution in `SOURCES.md`.

## Suggested order

1. **Widen within O\*NET.** Add roughly 20 to 30 roles in the thin sectors. This needs no new licence, the exposure data mostly exists already, and the mapping work is the same kind we've done.
2. **Add O\*NET Work Activities, Abilities and Related Occupations**, to broaden the skills beyond software tools and to give the roadmap real career-change links.
3. **Add a MASCO mapping** to make the Malaysia context more specific.
4. **Evaluate NOSS, ESCO and Lightcast** only if the roadmap needs Malaysian training pathways or better resume skill matching.
5. **Model work** (the forecast, the proxy geography, scenarios) is tracked separately in `ALGORITHM_INTEGRATION.md`.

## Process for adding a role or source

1. Check the licence and add it to `SOURCES.md`.
2. Add a build step in `pipeline/` and wire it into `pipeline/refresh.py`, so the cross-table checks cover it.
3. Add the mapping rows (sector and Malaysian group) with a rationale.
4. Update `STRUCTURE.md`, add a numbered migration in `migrations/` if the schema changes, and reload with `pipeline/load_supabase.py`.
5. Check that the app handles nulls and "no data" for the new rows.
