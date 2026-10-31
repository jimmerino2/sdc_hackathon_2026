# Jobee

> A career guide for students and early-career tech workers that shows which roles are growing as AI changes the job market, and which skills to build to get there.

---

## Team Information

| Field                 | Details                                      |
| --------------------- | -------------------------------------------- |
| **Team Name**         | Claypot Chicken Rice                         |
| **Team Domain**       | Domain 1                                     |
| **SDG Track (1–17)**  | SDG 8 — Decent Work and Economic Growth      |
| **Team Leader**       | Lam Way Hou                                  |
| **University**        | Sunway University, Universiti Putra Malaysia |
| **Number of Members** | 5                                            |

## Links

| Resource          | Link                                                          |
| ----------------- | ------------------------------------------------------------- |
| GitHub Repository | https://github.com/jimmerino2/sdc_hackathon_2026              |
| Live Demo         | https://jobee-sdchack.replit.app/                             |
| Slide Deck        | https://canva.link/9ogvetmkxddtzag                            |
| Demo Video        | https://youtu.be/xLT6an0eAq4                                  |

---

## Overview

### Problem

AI is changing which tech jobs are hiring, and which are shrinking, faster than most courses and career advice can keep up with. Students and recent graduates often choose a path based on job titles that may be fading, with no way to see how the market is moving or which skills would hold up. Career guidance is generic, and it rarely shows the trade-offs between roles.

### Solution

Jobee takes a short onboarding conversation (where you are in your journey, your interests, your skills) and matches you against tech roles. Each match is scored by arithmetic, not a black-box model: skills you have, interests that point at the UN Sustainable Development Goals, your career stage, and whether job postings for the role are rising or falling under the AI future you pick. A forecasting pipeline supplies the outlook, using published AI-adoption and job-posting data, and the app shows the forecast as a chart with its error range. An LLM writes a learning roadmap for the role you pick, and optional "Bonus Quests" let you prove a skill with a small project.

### Key Features

- **Role matching** — Ranks tech roles by skills, interests, career stage and outlook, using plain arithmetic. See [docs/JOB_MATCH.md](docs/JOB_MATCH.md) for how it works.
- **AI-future outlook** — Forecasts for job postings and AI use under different AI futures, with the model's error range shown.
- **Resume reading** — Extracts skills from an uploaded resume with the LLM gateway.
- **Learning pathway** — Generates a roadmap for a chosen role.
- **Challenges** — Two-stage projects built in a GitHub repo and scored by an LLM against a rubric. Passing a stage earns a stinger.
- **Hive and Social** — A co-op boss fight for up to four friends, paid for with stingers, plus pollen points and a friends leaderboard.
- **Occupation insights** — Skill-demand forecasts and emerging-skill signals by job type.
- **Companion bees** — Four guide characters the learner can pick, each with its own look.

### Tech Stack

| Layer           | Technology                                                                        |
| --------------- | --------------------------------------------------------------------------------- |
| Frontend        | Vue 3, Vite, TypeScript, Vue Router                                               |
| Backend         | Python 3.12, FastAPI, Pydantic                                                    |
| Database / Auth | Supabase (Postgres + auth)                                                        |
| Forecasting     | pandas, NumPy, scikit-learn, LightGBM                                             |
| AI              | LLM gateway for roadmaps, quests and resume extraction                            |
| Hosting / Dev   | Replit Autoscale (live demo) and development; Vercel as an alternate deployment   |

---

## Project Structure

```
.
├── api/
│   └── index.py             # Vercel entry point for the FastAPI app (alternate deployment)
├── src/
│   ├── backend/             # FastAPI app (app/), forecasting/, occupational/, ml/
│   └── frontend/            # Vue 3 + Vite app
├── data/
│   ├── processed/           # Forecast and skill data the API reads
│   ├── occupational_forecasting/
│   ├── documentation/       # Data and pipeline documentation
│   └── raw/                 # Downloads (gitignored; placed by the pipeline)
├── pipeline/                # Data refresh scripts
├── migrations/              # Supabase SQL migrations
├── supabase/                # Supabase templates and config
├── docs/                    # JOB_MATCH.md: how role scores are worked out
├── submission/              # Required submission documents
├── .replit                  # Replit run and deployment configuration
├── replit.md                # Replit setup and deployment notes
├── vercel.json              # Vercel build and function config
├── pyproject.toml, uv.lock  # Python dependencies
├── LICENSE
└── README.md
```

### Architecture

```
Browser ──► Vue frontend
                │  /api requests
                ▼
        FastAPI backend ──► Supabase (auth, profiles, roadmaps)
                │
                └──► LLM gateway (roadmaps, quests, resume skills)
```

---

## How to Run

### Option 1 — Run on Replit

1. Import this repository via **Create Repl → Import from GitHub**.
2. Open **Secrets** (🔒) and add the variables from [`src/backend/.env.example`](src/backend/.env.example).
3. Click **Run**. `.replit` starts the frontend on port 5000 and the backend on port 8000. Frontend `/api` requests are proxied to the backend.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/jimmerino2/sdc_hackathon_2026.git
cd sdc_hackathon_2026

# 2. Backend: install Python dependencies (uv) and start the API on port 8000
uv sync
cp src/backend/.env.example src/backend/.env     # then fill in your values
uv run uvicorn app.main:app --app-dir src/backend --port 8000

# 3. Frontend: in a second terminal
cd src/frontend
npm install
npm run dev                                       # serves on port 5173, proxies /api to the backend
```

The API docs are at `http://localhost:8000/docs` and the health check at `/health`.

The API starts without external credentials. Forecast endpoints use the precomputed outputs in `data/`. Supabase and LLM features need the keys in `.env`.

### Supabase setup

The app uses Supabase for authentication, profiles, role/skill reference data,
and learning roadmaps. Judges can create a fresh Supabase project and connect
it to a local checkout as follows:

1. Create a project at [supabase.com](https://supabase.com), then open
   **Project Settings → API**.
2. Copy the **Project URL** into `SUPABASE_URL` in
   [`src/backend/.env`](src/backend/.env). Copy the **Publishable (anon) key**
   into `SUPABASE_KEY`.
3. Copy the **service-role key** into `SUPABASE_SERVICE_KEY`. This key bypasses
   Row Level Security, so keep it in the local `.env` or shell environment and
   never commit it or expose it to the frontend.
4. Open the Supabase **SQL Editor**. Run every SQL file in
   [`migrations/`](migrations) in numeric filename order, starting with
   [`0001_initial_schema.sql`](migrations/0001_initial_schema.sql). Run both
   files with the `0010` prefix; their order does not matter. The migrations
   create the tables, security policies, and app-specific columns, and must be
   applied before loading data. Do not edit a migration that has already been
   run.
5. From the repository root, load the checked-in reference data. With `uv`
   (recommended):

   ```bash
   export SUPABASE_SERVICE_KEY="your-service-role-key"
   uv run python pipeline/load_supabase.py
   ```

   On Windows PowerShell, use
   `$env:SUPABASE_SERVICE_KEY = "your-service-role-key"` instead. The loader
   reads `SUPABASE_URL` from `src/backend/.env` and upserts the CSV data in
   `data/processed/`. Re-running it is safe.

6. Start the backend and frontend using the local instructions above. Confirm
   that `http://localhost:8000/health` responds and that the app can load
   roles. The migration details, table list, loader options, and expected row
   counts are documented in [`migrations/README.md`](migrations/README.md).

Use the publishable key for normal app reads. Profile, recommendation, roadmap,
and other write operations require `SUPABASE_SERVICE_KEY`; without it those
features intentionally return an error rather than writing with the public key.

## How We Use Replit _(Required)_

- **Designing**: the team did preliminary designs and included animations for the prototypes after developing the core functionality with Claude Code and Antigravity
- **Hosting:** the live demo is a Replit Autoscale deployment. `.replit` builds the frontend, then runs `app.serve:asgi`, one process that serves the built frontend and mounts the API at `/api` on the same origin, so no CORS is needed. Vercel configs (`api/index.py`, `vercel.json`) are kept as an alternate deployment.
- **Development:** the team built and ran the project in a shared Repl. The `.replit` file runs the frontend and backend together, and the Replit preview serves the app during development.
- **Secrets:** API keys are stored in Replit Secrets, and `.env` files are gitignored.
- **Configuration:** `.replit` defines the run commands and ports, so anyone who imports the repo can start it with one click.

📄 Proof of use: [`submission/SDC2026_Claypot_Chicken_Rice_Replit_POU.pdf`](submission/SDC2026_Claypot_Chicken_Rice_Replit_POU.pdf)

## How We Use RunPod _(Required)_

We used RunPod to host our OpenJev resume-skill engine. It first ran on a Pod and now runs as a Serverless endpoint, so it scales to zero and isn't billed while idle. The backend calls it over HTTP at `OPENJEV_URL` (the RunPod endpoint address), authenticated with `OPENJEV_TOKEN`, when a learner uploads a resume.

If the endpoint is unreachable or the call fails, the backend automatically falls back to the OpenRouter LLM gateway, so resume reading keeps working. The fallback is only used when the call to OpenJev fails.

📄 Proof of use: [`submission/SDC2026_Claypot_Chicken_Rice_Runpod_POU.pdf`](submission/SDC2026_Claypot_Chicken_Rice_Runpod_POU.pdf)

---

## Challenges & Learnings

- **Understanding forecasting.** Learning how and when to apply regression models, mathematical algorithms etc was very challenging due to our inexperience in data science
- **Explainable matching.** Role scores are plain arithmetic over skills, interests, stage and outlook rather than a model, so every part of a score can be shown and checked (see [docs/JOB_MATCH.md](docs/JOB_MATCH.md)).
- **Stand-in data.** Job-posting forecasts use US data as a proxy for Malaysia, and Malaysian vacancy data has coverage breaks, so it is shown but not used to train.

## Future Improvements

- [ ] Widen matching beyond the 8 tech roles scored today
- [ ] Include different verification methods for roles that are non-tech related
- [ ] Have additional ways to maintain user retention, preventing them from leaving after finding a job
- [ ] Use Malaysian demand data and local occupation standards (MASCO, NOSS) in place of the US proxy

## Team

| Name                 | Role             | GitHub                         |
| -------------------- | ---------------- | ------------------------------ |
| Lam Way Hou          | Project Lead     | https://github.com/jimmerino2  |
| Foo Jia Seng         | Tech Lead        | https://github.com/skyfoojs    |
| Tan Li Yang          | Data Analyst     | https://github.com/Li-Yang-Tan |
| Chung Hao Jun        | Frontend Lead    | https://github.com/oscar-chj   |
| Justin Chai Xing Wei | Business Analyst | https://github.com/ChaiXingWei |

---

## Submission Checklist

- [x] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [x] Slide deck link added
- [x] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod used, with proof of use in `submission/`
- [x] Preliminary submission completed (`SDC2026_TeamName_Preliminary.pdf`)
- [x] Technology declaration completed (`SDC2026_TeamName_TechDeclaration.pdf`)
- [x] Submission files renamed with your team name (replace `TeamName`)
- [ ] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
