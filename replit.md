# Running on Replit

This project contains a Vue 3/Vite frontend in `src/frontend`, a Python FastAPI
backend in `src/backend`, and a separate data pipeline. The frontend currently
uses sample flow data and does not call the backend yet.

## Run

Use the **Run** button to start the Vue frontend preview. To run it manually:

```sh
cd src/frontend
npm ci
PORT=5000 npm run dev
```

The frontend README's default development port is 5173; the Replit workflow sets
port 5000 for the web preview. Frontend routes follow `/:persona/:step`.

To run the backend separately on port 8000:

```sh
python -m uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 8000
```

Its interactive API documentation is at `/docs`, `/health` returns
`{"status":"ok"}`, and the OpenAPI schema is at `/openapi.json`.

Backend and pipeline Python dependencies are tracked in the root `pyproject.toml`
and `uv.lock`; frontend dependencies are tracked in
`src/frontend/package.json` and `src/frontend/package-lock.json`. The original
backend and pipeline requirements files remain in their existing locations.

## External services and current limits

The API starts without external credentials. Add credentials using Replit
Secrets, not source files:

- `OPENROUTER_API_KEY`: required for `POST /llm/chat`. Despite its name, the
  existing implementation sends requests to `https://llm.grafilab.ai/v1`, not
  OpenRouter. Use a credential valid for that service.
- `OPENROUTER_MODEL`: optional model override; defaults to the value in
  `src/backend/app/config.py`.
- `SUPABASE_URL` and `SUPABASE_KEY`: needed when using the existing Supabase
  client. The current product endpoints do not call it: listing returns an
  empty list and creation returns a placeholder record without saving it.
- `CORS_ORIGINS`: optional JSON list of allowed origins if the frontend is later
  connected to the backend.

Chat requires the API key and was not tested against the external provider.
Supabase persistence is not implemented in the imported product service.

## Data pipeline

Pipeline dependencies are installed, but starting the API does not refresh data
or download datasets. Existing processed data is included in the repository.
See `pipeline/README.md` for refresh commands and manual O*NET/Economic Index
inputs. Raw data is gitignored and can be large; choose durable asset storage
before downloading it. The backend does not currently expose forecasting routes.
