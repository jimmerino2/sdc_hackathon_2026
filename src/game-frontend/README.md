# The Coding Frontier — web client

Vue 3 + Vite + TypeScript + Pinia. Code editing uses CodeMirror 6. The isometric Frontier is a small canvas renderer in `src/game/` with no game-engine dependency.

This app lives in `src/game-frontend` so it doesn't clash with the team's `src/frontend` app.

## Run

```sh
cd src/game-frontend
npm install
npm run dev            # http://localhost:5174, proxies /api → VITE_BACKEND_URL (default http://127.0.0.1:8000)
```

The backend must be running with the runner image built (see `src/backend/README.md`). Set the backend address in `.env.local` (gitignored), for example:

```sh
VITE_BACKEND_URL=http://127.0.0.1:8001
```

To click through the UI before the runner exists, start it in **preview mode**:

```sh
VITE_RUNNER_MODE=preview npm run dev
```

Preview mode never executes learner code. Every result is flagged `simulated`, the UI shows a striped banner, and progress is saved under a separate storage key. Do not use it as evidence that an implementation works.

`npm run build` type-checks and builds to `dist/`.

## Layout

| Path | Purpose |
|---|---|
| `src/content/missions.ts` | Data-driven mission definitions: lesson blocks, starter code, test descriptions, hints, feedback per test/error category, XP, unlocks. |
| `src/content/dialogue.ts` | Scripted, event-driven lines for Wick, the companion. |
| `src/stores/` | `progress` (XP, unlocks, achievements; idempotent completion), `workspace` (learner code per mission, shared by Academy/Frontier/Workshop), `runner`, `game`, `companion`. |
| `src/lib/storage.ts` | Key-value persistence interface (localStorage today). |
| `src/game/` | World map + canvas engine. The engine only renders and handles input. It never decides outcomes. |
| `src/api/` | Backend contract (`types.ts`), HTTP client, and preview simulator. |

## Backend contract

These are implemented in `src/backend/app/frontier/`. Learner code runs only in the Docker sandbox, never in the API process.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/runner/health` | – | `RunnerHealth` (`isolation` names the real boundary, e.g. `docker`) |
| POST | `/runner/missions/{id}/evaluate` | `{ code }` | `EvaluationResult`: one `TestOutcome` per test, `id`s matching `missions.ts` |
| POST | `/runner/missions/{id}/request` | `{ code, request: RouteRequest }` | `RequestResult`: the real HTTP exchange with the learner's app (via TestClient inside the sandbox) |
| GET | `/game/state` | – | `GameState` |
| POST | `/game/actions` | `{ command, target, mission_id?, code? }` | `GameActionResult` |

Rules the backend owns (the client trusts these and nothing else):

- `mine` builds the request from **its own** state (resource of the node, the player's equipped tool). It calls the learner route through the runner, then validates the response (`200` + `{"mined": true, "resource": <node resource>, "amount": 1}`) before applying effects. Anything else maps to `REJECTED_BY_ROUTE`, `ROUTE_ERROR` or `INVALID_RESPONSE`, and the world does not change.
- Node depletion, inventory and rewards are server-side and idempotent. `Reward.granted` is `false` on replays.
- `state.version` increases monotonically. The client ignores older states.
- Failures return a learner-readable `reason`/`message` and an `ErrorCategory` that the companion maps to hints.

Exact field shapes are in [`src/api/types.ts`](src/api/types.ts).

## Known limitations

- Mission completion and XP are tracked client-side in localStorage. When the backend has persistence, move `completeMission` behind an endpoint so rewards can't be granted by editing storage.
- Test *descriptions* are in `missions.ts`. The test *code* is in `src/backend/runner/harness/missions.py`. Keep the ids in sync.
- Gameplay is desktop-first. Small screens get a usable layout, but the Frontier is best with a keyboard.
