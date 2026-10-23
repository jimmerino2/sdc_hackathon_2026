"""Persistence for the trusted game state. A JSON file today; swap for a database later."""

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

DEFAULT_PATH = Path(__file__).resolve().parents[2] / ".frontier" / "game_state.json"


class StateStore(Protocol):
    def load(self) -> dict | None: ...
    def save(self, state: dict) -> None: ...


class JsonFileStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path

    def load(self) -> dict | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-rename so a crash never leaves a half-written file.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, self.path)


class MemoryStore:
    def __init__(self):
        self.state: dict | None = None

    def load(self) -> dict | None:
        return json.loads(json.dumps(self.state)) if self.state else None

    def save(self, state: dict) -> None:
        self.state = json.loads(json.dumps(state))
