#!/usr/bin/env bash

# Clean up background processes on script exit (Ctrl+C)
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Copy .env if not already present
[ -f src/backend/.env ] || cp src/backend/.env.example src/backend/.env

# Start Backend (FastAPI on port 8000)
if command -v uv >/dev/null 2>&1; then
  uv run uvicorn app.main:app --app-dir src/backend --port 8000 &
else
  source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
  uvicorn app.main:app --app-dir src/backend --port 8000 &
fi

# Start Frontend (Vite on port 5173)
cd src/frontend
npm run dev
