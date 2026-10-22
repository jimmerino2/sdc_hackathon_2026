# Running on Replit

This imported project contains a Python FastAPI backend and a separate data
pipeline. There is no frontend application in the repository.

## Run

Use the **Run** button to start the **Start application** workflow, or run from
the repository root:

```sh
python -m uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 5000
```

The preview opens the interactive API documentation at `/docs` (the root
redirects there). `/health` returns `{"status":"ok"}`. The OpenAPI schema is at
`/openapi.json`.

Replit dependencies are tracked in the root `pyproject.toml` and `uv.lock`.
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
  extraction engine rather than the AI gateway.
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
