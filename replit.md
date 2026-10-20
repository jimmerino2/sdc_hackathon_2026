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
  OpenRouter. Use a credential valid for that service.
- `OPENROUTER_MODEL`: optional model override; defaults to the value in
  `src/backend/app/config.py`.
- `SUPABASE_URL` and `SUPABASE_KEY`: needed when using the existing Supabase
  client. The current product endpoints do not call it: listing returns an
  empty list and creation returns a placeholder record without saving it.
- `CORS_ORIGINS`: optional JSON list of allowed frontend origins if a separate
  frontend is connected.

Chat requires the API key and was not tested against the external provider.
Supabase persistence is not implemented in the imported product service.

## Data pipeline

Pipeline dependencies are installed, but starting the API does not refresh data
or download datasets. Existing processed data is included in the repository.
See `pipeline/README.md` for refresh commands and manual O*NET/Economic Index
inputs. Raw data is gitignored and can be large; choose durable asset storage
before downloading it. The backend does not currently expose forecasting routes.
