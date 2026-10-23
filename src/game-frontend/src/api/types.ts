// Contract between the web client and the trusted platform backend.
// The backend owns learner-code execution (isolated runner), the evaluation
// tests and the game simulation. The client never decides whether code passed
// or what the world gains — it only renders what these responses say.

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface RunnerHealth {
  status: 'ok' | 'degraded'
  /** How learner code is isolated, e.g. "docker". "none" must never be shown as safe. */
  isolation: string
  /** True when responses come from the labelled preview simulator, not real execution. */
  simulated?: boolean
}

/** Error categories the runner maps failures into; the companion reacts to these. */
export type ErrorCategory =
  | 'syntax'
  | 'name'
  | 'type'
  | 'missing_return'
  | 'wrong_value'
  | 'wrong_status'
  | 'validation'
  | 'runtime'
  | 'timeout'
  | 'resource_limit'

export interface TestOutcome {
  id: string
  name: string
  passed: boolean
  /** Learner-readable explanation of what was expected vs. what happened. */
  message?: string
  category?: ErrorCategory
}

export interface CodeError {
  type: string
  message: string
  line?: number
  category: ErrorCategory
}

export interface EvaluationResult {
  run_id: string
  mission_id: string
  status: 'passed' | 'failed' | 'error' | 'timeout'
  tests: TestOutcome[]
  stdout: string
  stderr: string
  error?: CodeError
  duration_ms: number
  simulated?: boolean
}

export interface RouteRequest {
  method: HttpMethod
  path: string
  query: Record<string, string>
  headers: Record<string, string>
  body: unknown
}

export interface RouteResponse {
  status_code: number
  headers: Record<string, string>
  body: unknown
}

export interface RequestResult {
  run_id: string
  request: RouteRequest
  /** Absent when the learner app failed to load or the request crashed. */
  response?: RouteResponse
  error?: CodeError
  logs: string
  duration_ms: number
  simulated?: boolean
}

export interface ResourceNodeState {
  id: string
  resource: string
  remaining: number
}

/** Trusted simulation state. Only the backend mutates it. */
export interface GameState {
  inventory: Record<string, number>
  equipped: string | null
  nodes: Record<string, ResourceNodeState>
  /** Monotonic version, lets the client discard stale responses. */
  version: number
}

export type GameCommand = 'mine' | 'pickup' | 'equip'

export type GameActionCode =
  | 'OK'
  | 'REJECTED_BY_ROUTE' // learner route answered with a 4xx — a deliberate refusal
  | 'ROUTE_ERROR' // learner code crashed / 5xx / failed to load
  | 'INVALID_RESPONSE' // route answered but the simulator refused the payload
  | 'NODE_DEPLETED'
  | 'MISSION_LOCKED'
  | 'NOT_ALLOWED'

export interface GameEffect {
  type: 'inventory_add' | 'inventory_remove' | 'node_update' | 'equip'
  item?: string
  qty?: number
  node_id?: string
}

export interface Reward {
  xp: number
  achievement_ids: string[]
  /** False when this reward was already granted before (idempotent replay). */
  granted: boolean
}

export interface GameActionResult {
  action_id: string
  command: GameCommand
  target: string
  accepted: boolean
  code: GameActionCode
  /** Learner-readable explanation from the trusted simulator. */
  reason: string
  /** The HTTP exchange with the learner's route, when one happened. */
  trace?: RequestResult
  effects: GameEffect[]
  state: GameState
  reward?: Reward
  simulated?: boolean
}

export interface GameActionInput {
  command: GameCommand
  target: string
  mission_id?: string
  /** Learner source to execute for code-backed commands such as mine. */
  code?: string
}
