# FAQ

Questions about how Jobee works behind the scenes. Currently covers job matching, interests and the SDGs.

## Job matching

### How is a role's match score worked out?

By arithmetic. No AI model is involved in ranking any more. Each role gets four parts, each between 0 and 1, and the score is their weighted sum:

```
score = 0.10 × education + 0.25 × interests + 0.35 × skills + 0.35 × outlook
```

| Part | Weight | What it measures |
| ---- | ------ | ---------------- |
| Skills | 35% | How much of the role's key skills the learner has, at their proficiency |
| Outlook | 35% | Whether job postings for the role are rising or dropping, for the chosen AI future |
| Interests | 25% | How well the learner's interests point at the SDGs the role serves |
| Education | 10% | The learner's career stage |

The displayed "% match" is the score × 100. The code is in `src/backend/app/jobs/scoring.py`, and `recommend()` in `src/backend/app/jobs/service.py` applies it to every tech role.

### How are skills scored?

A role has up to 10 key skills (6 tools and 4 abilities), each with an O\*NET importance. A skill the learner has counts at their proficiency: **Basic 0.33, Good 0.67, Strong 1**. A skill they don't have, or rated New, counts 0.

```
skills = Σ (importance × proficiency) ÷ Σ importance
```

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

In `src/backend/app/jobs/scoring.py`: the four weights (`W_EDUCATION`, `W_INTERESTS`, `W_SKILLS`, `W_OUTLOOK`), `STAGE_LEVEL` for education, and the multiplier limits `MULT_MIN` and `MULT_MAX`. The proficiency steps are in `proficiency()` there, and the skill check's own values are `LEVEL_SCORES` in `src/frontend/src/data/skills.ts`.

### Can I see how a score was made up?

The API returns the three parts that don't depend on the AI future in `match_parts` (education, interests, skills), and each scenario's own match in `outlook[].match_percent`. The page doesn't show a breakdown yet.

### Is there an AI model anywhere in this?

Not in scoring. It used to be: a model or OpenJev rated each role from the learner's skills. That is removed, so scores are repeatable, instant and testable. The `source` option on `GET /jobs/recommend` is still accepted but ignored.

The cost is that the old model could recognise related skills that aren't in a role's key list. Now only the equivalents listed in `service.py` count, so an unusual skill scores 0.

### Which roles are scored?

The 8 tech roles in `TECH_ROLES` in `service.py`. Four other roles (bookkeepers, customer service and so on) appear only as grey contrast dots on the chart and aren't scored.

### Worked example

A test profile (not a real user): Python (Good), SQL (Strong), JavaScript (Basic), working, picked "Gaming & Coding".

| Role | Skills | Interests | Education | Outlook (AI accelerates) | Match |
| ---- | ------ | --------- | --------- | ------------------------ | ----- |
| Software Developers | 0.27 | 1.00 | 1.0 | 0.70 | 66% |
| Computer Systems Analysts | 0.17 | 0.82 | 1.0 | 0.47 | 50% |

For Software Developers: 0.10 × 1.0 + 0.25 × 1.00 + 0.35 × 0.27 + 0.35 × 0.70 ≈ 0.66.

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
