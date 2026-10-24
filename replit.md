# Running on Replit

This imported project contains a Vue 3/Vite frontend at `src/frontend`, a
Python FastAPI backend at `src/backend`, and a separate data pipeline.

## Run

Use the **Run** button to start the frontend and backend together. The frontend
is served on port 5000; its `/api` requests are proxied to the backend on port
8000. To run the services separately from the repository root:

```sh
npm --prefix src/frontend run dev -- --host 0.0.0.0 --port 5000
python -m uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 8000
```

The preview opens the frontend. The backend API docs and health check are
available at `/docs` and `/health`; API requests from the frontend use `/api`.

Frontend dependencies are tracked in `src/frontend/package.json` and
`src/frontend/package-lock.json`; backend dependencies are tracked in the root
`pyproject.toml` and `uv.lock`.
The original backend and pipeline requirements files remain in their existing
locations. No manually created virtual environment is needed.

## External services and current limits

The API starts without external credentials. Add credentials using Replit
Secrets, not source files:

- `OPENROUTER_API_KEY`: required for `POST /llm/chat`. Despite its name, the
  existing implementation sends requests to `https://llm.grafilab.ai/v1`, not
  OpenRouter. Use a credential valid for that service. AI resume extraction,
  job-fit scoring, and roadmap generation also depend on an AI service.
- `OPENROUTER_MODEL`: optional model override; defaults to the value in
  `src/backend/app/config.py`.
- `SUPABASE_URL` and `SUPABASE_KEY`: required for Supabase authentication
  and database access.
- `SUPABASE_SERVICE_KEY`: server-only service-role key needed by profile,
  recommendation, and roadmap endpoints. Apply the existing SQL migrations
  to the intended Supabase project before using database-backed features.
- `OPENJEV_URL` and `OPENJEV_TOKEN`: needed if using the OpenJev resume
  extraction engine rather than the AI gateway. `OPENJEV_URL` is the RunPod
  Serverless endpoint address.
- `CORS_ORIGINS`: optional JSON list of allowed frontend origins if a separate
  frontend is connected.

External AI calls and database-backed flows have not been verified because
their credentials are not configured. No replacement database or mock
credentials were created.

Verified on Replit: `/health`, `/docs`, `/openapi.json`, `/forecast/sectors`,
`/forecast?horizon=3`, and `/forecast/jobs?horizon=3` return successful responses.
An unsupported forecast horizon returns HTTP 422. Forecasts use the included
precomputed outputs and do not require external credentials.

## Data pipeline

Pipeline dependencies are installed, but starting the API does not refresh data
or download datasets. Existing processed data is included in the repository.
See `pipeline/README.md` for refresh commands and manual O*NET/Economic Index
inputs. Raw data is gitignored and can be large; choose durable asset storage
before downloading it. Forecasting routes are available under `/forecast`;
the included outputs are in `src/backend/ml/output/`.

## Production deployment (Replit Autoscale)

Migrated from Vercel. The deployment builds the frontend with `VITE_API_URL=/api` and runs
`app.serve:asgi`, which serves `src/frontend/dist` and mounts the API under `/api` on the
same origin. A separate frontend origin is not needed, so CORS is not required for this
deployment. `api/index.py` and `vercel.json` are kept only for the Vercel deployment.
Set the secrets listed above in the Replit deployment before publishing. Node.js 22 is
configured because locked frontend dependencies require Node.js 22.18 or newer.
