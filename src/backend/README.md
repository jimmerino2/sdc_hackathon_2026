# Backend

## Setup with uv (recommended)

```
cd src/backend
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
cp .env.example .env   # fill in values
uv run fastapi dev app/main.py
```

`uv run` uses the `.venv` automatically, so activating it is optional.

## Setup with pip

```
cd src/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
fastapi dev app/main.py
```

Docs: http://localhost:8000/docs

## Coding Frontier: runner and game simulator

`app/frontier/` serves the endpoints the Vue client in `src/game-frontend` calls (`/runner/*`, `/game/*`).

**Learner code never runs in this process.** Every evaluation or request is a fresh Docker container started from `runner/`:

- no network, read-only root filesystem, and a 16 MB `noexec` `/tmp`
- non-root user (uid 10001), all capabilities dropped, `no-new-privileges`
- 256 MB memory, 1 CPU, 64 processes, 15 s wall clock (2–3 s per test inside)
- code is capped at 20,000 characters and output is truncated

One-time setup (needs Docker Desktop running):

```
docker build -t frontier-runner:latest runner
```

Rebuild the image after changing `runner/harness/`. If Docker or the image is missing, `/runner/health` returns 503 with the fix, and nothing falls back to running code locally.

- Evaluation tests live in `runner/harness/missions.py`. Test ids match `src/game-frontend/src/content/missions.ts`.
- `app/frontier/simulator.py` is the trusted game. It builds the `/mine` request from its own state and validates the route's answer before changing anything. First-ore rewards are granted once.
- Game state is saved to `.frontier/game_state.json` (gitignored). Call `POST /game/reset` to start over.

Tests (the sandbox tests are skipped when Docker is unavailable):

```
pip install pytest
python -m pytest tests
```

Known limitation: tests run in the same process as the learner's code, inside the sandbox. A determined learner could forge their own test results. That only affects their own progress. Game effects are still validated by the simulator.
