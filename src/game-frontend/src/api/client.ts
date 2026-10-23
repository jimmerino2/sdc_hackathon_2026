import type {
  EvaluationResult,
  GameActionInput,
  GameActionResult,
  GameState,
  RequestResult,
  RouteRequest,
  RunnerHealth,
} from './types'
import { previewApi } from './preview'

const BASE = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/$/, '')

export const RUNNER_MODE: 'live' | 'preview' =
  import.meta.env.VITE_RUNNER_MODE === 'preview' ? 'preview' : 'live'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message)
  }
}

async function call<T>(path: string, init?: RequestInit, timeoutMs = 20000): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      signal: ctrl.signal,
    })
  } catch (e) {
    throw new ApiError(
      ctrl.signal.aborted ? 'The runner took too long to answer.' : 'Could not reach the platform backend.',
      null,
    )
  } finally {
    clearTimeout(timer)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? data)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail || `Backend returned ${res.status}`, res.status)
  }
  return (await res.json()) as T
}

export interface Api {
  health(): Promise<RunnerHealth>
  evaluate(missionId: string, code: string): Promise<EvaluationResult>
  request(missionId: string, code: string, req: RouteRequest): Promise<RequestResult>
  gameState(): Promise<GameState>
  gameAction(input: GameActionInput): Promise<GameActionResult>
}

const liveApi: Api = {
  health: () => call<RunnerHealth>('/runner/health', undefined, 5000),
  evaluate: (missionId, code) =>
    call<EvaluationResult>(`/runner/missions/${encodeURIComponent(missionId)}/evaluate`, {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
  request: (missionId, code, req) =>
    call<RequestResult>(`/runner/missions/${encodeURIComponent(missionId)}/request`, {
      method: 'POST',
      body: JSON.stringify({ code, request: req }),
    }),
  gameState: () => call<GameState>('/game/state'),
  gameAction: (input) =>
    call<GameActionResult>('/game/actions', { method: 'POST', body: JSON.stringify(input) }),
}

export const api: Api = RUNNER_MODE === 'preview' ? previewApi : liveApi
