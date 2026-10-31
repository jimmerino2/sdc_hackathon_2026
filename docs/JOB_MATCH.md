# FAQ

Questions about how Jobee works behind the scenes. Currently covers job matching, interests and the SDGs.

## Job matching

### How is a role's match score worked out?

By arithmetic. No AI model is involved in ranking any more. Each role gets four parts, each between 0 and 1, and the score is their weighted sum:

```
score = (0.10 × education + 0.25 × interests + 0.35 × skills + 0.35 × outlook) ÷ 1.05
```

The configured weights add up to 1.05, so the shares that really apply are below. The formula always divided by 1.05, so the 2026-10 change only corrected what was shown: the page and notes used to quote the configured 35/35/25/10 and now quote the real shares. Scores didn't change.

| Part | Share | What it measures |
| ---- | ------ | ---------------- |
| Skills | 33.3% | How much of the role's key skills the learner has, at their proficiency |
| Outlook | 33.3% | Whether job postings for the role are rising or dropping, for the chosen AI future |
| Interests | 23.8% | How well the learner's interests point at the SDGs the role serves |
| Education | 9.5% | The learner's career stage |

The weights add up to 1.05, so the sum is divided by 1.05 to keep it between 0 and 1. The displayed "% match" is then score<sup>0.7</sup> × 100. The curve lifts every match (0.40 shows as 53%, 0.66 as 75%) without changing the order between roles. The code is in `src/backend/app/jobs/scoring.py`, and `recommend()` in `src/backend/app/jobs/service.py` applies it to every tech role.

### How are skills scored?

A role has up to 10 key skills (6 tools and 4 abilities), each with an O\*NET importance. A skill the learner has counts at their proficiency: **Basic 0.33, Good 0.67, Strong 1**. A skill they don't have, or rated New, counts 0.

```
skills = Σ (importance × proficiency) ÷ Σ importance
```

**Trend momentum.** A key skill whose demand the Occupations page forecasts to rise (evidence above low, US, 6 months) counts **twice** its importance, in the sum and in the divisor. Only roles with an occupation in the skill-demand pipeline have this (Software Developers, Data Scientists and Data Analysts today; the weight is `TREND_WEIGHT` in `jobs/service.py`). The score therefore moves when the demand forecast moves, and learning a rising skill adds more than learning an ordinary one. Each skill in the breakdown says whether it was counted double (`trending`).

Close equivalents count too. Having Git covers GitHub and GitLab, Linux covers UNIX, and having Python covers the general "Programming" skill. If a learner has several equivalents, the best proficiency among them is used.

Scores already stored on profiles (0.4, 0.7, or a resume's decimal) are rounded to the nearest of the three steps.

### How is the outlook scored?

The forecast gives the expected change in job postings for each AI future (AI accelerates, AI holds steady, AI slows down). It becomes a multiplier: 1× if postings stay flat, above 1× if rising, below 1× if dropping, kept between 0.7× and 1.3×. The score stretches that to 0–1.

| Posting change | Multiplier | Outlook score |
| -------------- | ---------- | ------------- |
| −30% or worse | 0.7× | 0 |
| −4% | 0.96× | 0.43 |
| 0% | 1.0× | 0.5 |
| +11.8% | 1.118× | 0.70 |
| +30% or more | 1.3× | 1 |

### Why does the match change when I switch AI future?

Because the outlook part follows the chosen scenario. The backend works out a match for all three futures, and the page shows the one for the tab you are on. The roles are re-ordered by it, and the "Best match" tag moves with the order. The other three parts don't change between tabs. The headline `match_percent` the backend returns is the AI-accelerates one.

### How are interests scored?

For each interest the learner picked, take its score for each SDG and multiply it by the role's weight for that SDG. Add that up over all goals and all picked interests. The role with the biggest sum gets the full 25%, and every other role gets its share of that.

Because it is a sum, picking more interests raises the raw numbers, but since each role is compared to the best role, only the relative order matters.

### What if the learner picked no interests?

The interests part is left out, and the other three share the whole 100% (education 12.5%, skills 43.75%, outlook 43.75%).

### How is education scored?

From the learner's career stage: studying 1, fresh graduate 1.5, working 2.5, divided by the highest (2.5). So studying is 0.4, fresh graduate 0.6 and working 1.0.

The learner picks it in onboarding and can change it any time on the Profile page. A change is saved at once, and the matches pick it up the next time they use **Regenerate roles**.

It is the same for every role in the learner's job group, and only tech roles are matched for now. So a working learner scores higher on all of them, but it never changes the order between roles.

### Where can I change the weights and values?

In `src/backend/app/jobs/scoring.py`: the four weights (`W_EDUCATION`, `W_INTERESTS`, `W_SKILLS`, `W_OUTLOOK`), `STAGE_LEVEL` for education, the multiplier limits `MULT_MIN` and `MULT_MAX`, and `CURVE` (lower lifts every match more; 1 turns the curve off). The proficiency steps are in `proficiency()` there, and the skill check's own values are `LEVEL_SCORES` in `src/frontend/src/data/skills.ts`.

### Can I see how a score was made up?

Yes. Each role card and the role page's title card have an expandable "Why 71%?" with a bar per part. The "How it's calculated" dialog has each part's score, share and points and the curve, from `outlook[].breakdown`. `scoring.breakdown()` is the only place that adds them up.

### How does the What-If simulator work?

`POST /jobs/simulate` runs `service.score_roles`, the same function behind `GET /jobs/recommend`, on the profile and on a temporary copy with the tried skills added. If a skill is already on the profile, the higher level is kept. Nothing is saved.

Because O*NET rates many tools the same, a role's key skills favour tools the learner has among equally rated ones. So a tried skill can take the place of another key skill.

### Which skills can the simulator try, and why do some change nothing?

Every tool and ability O*NET lists for the matched roles (215), except ones the learner already has at Strong. Each is measured on its own through the matching engine.

About 130 of them show no change. Only a role's 10 key skills count, and tools fill those slots by importance: 4.0 for O*NET "In Demand", 3.5 for "Hot Technology" only. Every role has at least 6 In Demand tools, so a Hot Technology tool such as MongoDB can't enter unless it counts through an equivalent. Giving these skills an effect means widening the key skills, which would change every learner's match.

### Is there an AI model anywhere in this?

Not in scoring. It used to be: a model or OpenJev rated each role from the learner's skills. That is removed, so scores are repeatable, instant and testable. The `source` option on `GET /jobs/recommend` is still accepted but ignored.

The cost is that the old model could recognise related skills that aren't in a role's key list. Now only the equivalents listed in `service.py` count, so an unusual skill scores 0.

### Which roles are scored?

The 8 tech roles in `TECH_ROLES` in `service.py`. Four other roles (bookkeepers, customer service and so on) appear only as grey contrast dots on the chart and aren't scored.

### Worked example

A test profile (not a real user): Python (Good), SQL (Strong), JavaScript (Basic), working, picked "Gaming & Coding".

| Role | Skills | Interests | Education | Outlook (AI accelerates) | Match |
| ---- | ------ | --------- | --------- | ------------------------ | ----- |
| Software Developers | 0.27 | 1.00 | 1.0 | 0.70 | 74% |
| Computer Systems Analysts | 0.17 | 0.82 | 1.0 | 0.47 | 62% |

For Software Developers: (0.10 × 1.0 + 0.25 × 1.00 + 0.35 × 0.27 + 0.35 × 0.70) ÷ 1.05 ≈ 0.657, and 0.657<sup>0.7</sup> ≈ 0.74.

## Interests and SDGs

### What are the SDGs?

The UN's 17 Sustainable Development Goals, for example 3 Good Health and Well-being or 9 Industry, Innovation and Infrastructure.

### How do interests connect to jobs?

Both interests and roles point at SDGs:
- Each **interest** (Cooking & Baking, Gaming & Coding and so on) has up to 3 SDGs, each with a score, and the scores of one interest add up to 1. This is `interests.sdg`.
- Each **role** has up to 3 SDGs the same way. This is `onet_roles.sdg`.

A role and an interest are linked when they share a goal. The more of the interest's weight and the role's weight sit on the same goals, the higher the interests score.

### Where do the SDG weights come from?

They are our own judgement of which goals each interest and role serves, written into the migrations. They are not from an official source, so they are worth reviewing and are easy to change in the migration or the tables.

### What does "Why it was suggested" show on the role page?

The official UN tile for each SDG the role serves, in two groups:
- **Your interests:** goals that one or more of the learner's interests point at, with those interests as tags.
- **Job features:** goals that come only from the role itself, tagged with the role's title.

### Is the "Matched to the goals you care about" strip still shown?

It was removed from the onboarding roles page. It still appears on the logged-in roles page.

### Where do the SDG icons come from?

The official tiles from the UN's own site, saved in `src/frontend/public/sdg/`. A small credit line under the section says they are from the United Nations and that the UN has not approved the app. Check the UN's icon usage guidelines before using them beyond a hackathon.

## Setup

### Which migrations are needed for this?

Apply them in order:
1. `0013_interests.sql`: adds `interests` and `profile_interests`, seeds the 15 interests, and **drops `profiles.concerns`**.
2. `0014_onet_roles_sdg.sql`: adds `onet_roles.sdg` and fills it for all 46 roles.

Without 0013, saving a profile with interests fails. Without 0014, roles are scored without interests and the role page shows no SDG section.

### Do old saved suggestions still work?

They still load. They don't have per-scenario matches or SDG tags until the learner uses **Regenerate roles**. Until then the page falls back to the match that was saved.
