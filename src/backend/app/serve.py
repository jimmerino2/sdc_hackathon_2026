"""Single-process production entrypoint (Replit deployment).

Serves the built Vue frontend and mounts the existing API under /api, matching the
dev setup where Vite proxies /api to the backend. `app.main:app` is unchanged.
Run: uvicorn app.serve:asgi --app-dir src/backend
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.main import app as api_app

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

asgi = FastAPI(title="SDC Hackathon 2026 (web)", docs_url=None, redoc_url=None, openapi_url=None)


@asgi.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


asgi.mount("/api", api_app)


@asgi.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if not DIST.is_dir():
        return JSONResponse({"detail": "Frontend not built (src/frontend/dist missing)"}, status_code=503)
    target = (DIST / path).resolve()
    if path and target.is_file() and DIST.resolve() in target.parents:
        return FileResponse(target)
    return FileResponse(DIST / "index.html")
