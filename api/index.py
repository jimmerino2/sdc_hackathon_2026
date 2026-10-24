"""Vercel entrypoint: the FastAPI app lives in src/backend (imports are `app.*`, `forecasting.*`, ...)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "backend"))

from app.main import app  # noqa: E402,F401
