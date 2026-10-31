"""Run pipeline/sync_trends.py for POST /forecast/sync, then make the app read what it wrote.

One run at a time. The script builds in a temporary folder, so a failed run leaves the current forecasts in place.
"""
import json
import subprocess
import sys
import threading
from pathlib import Path

from app.forecast import retrain, service

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "pipeline" / "sync_trends.py"
TIMEOUT = 480  # seconds: the pull (at most 90), the rebuild, then the AI forecasts running side by side (at most 300)
_running = threading.Lock()


class SyncBusy(Exception):
    """Another sync is already running."""


class SyncFailed(Exception):
    """The script failed. The current data was kept."""


def run() -> dict:
    """Pull, rebuild and retrain, then forget everything read from the old files. Returns the script's summary."""
    if not _running.acquire(blocking=False):
        raise SyncBusy
    try:
        try:
            done = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired as e:
            raise SyncFailed("timed out") from e
        if done.returncode != 0:
            print(done.stdout[-2000:], done.stderr[-2000:])
            raise SyncFailed(done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "the script failed")
        retrain.clear()
        service.clear_caches()
        return json.loads(done.stdout.strip().splitlines()[-1])
    finally:
        _running.release()
