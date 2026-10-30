import { API_URL } from './config';

/** LLM forecast benchmark API (src/backend/app/llm_bench). An experiment: it never changes the served forecasts. */

export type Benchmark = 'skills' | 'capability';
export type Mode = 'zero' | 'few' | 'zero_named' | 'few_named';

export interface ModelInfo {
  id: string;
  prompt: number | null;
  completion: number | null;
  request: number;
  supported: string[];
  context_length: number | null;
  listed: boolean;
  free: boolean;
}

export interface BenchInfo {
  settings: { model: string; compare_model: string; max_spend_usd: number; batch_size: number; max_output_tokens: number; reasoning: string };
  key_configured: boolean;
  modes: { primary: Mode[]; exploratory: Mode[] };
  prompt_version: string;
  benchmarks: Record<Benchmark, { label: string; horizons: number[]; default_horizons: number[]; target: string; units: string; origins: string }>;
  running: { run_id: string } | null;
  models: Record<string, ModelInfo>;
  free_models: string[];
  models_error?: string;
}

export interface BenchRequest {
  benchmark: Benchmark;
  horizons: number[];
  n_series: number;
  n_origins: number;
  modes: Mode[];
  model?: string;
  batch_size: number;
  max_spend_usd: number;
  few_shot_k: number;
  max_examples: number;
  max_requests: number;
  dry_run: boolean;
  confirm?: boolean;
}

export interface Estimate {
  sample_id: string;
  n_cases: number;
  n_requests: number;
  est_prompt_tokens: number;
  max_output_tokens_total: number;
  max_cost_usd: number | null;
  expected_cost_usd: number | null;
  within_budget: boolean | null;
  budget_usd: number;
  key_configured: boolean;
  model: ModelInfo;
}

/** Scores of one method; skills fields are in pp of share, capability fields in doublings / minutes. */
export type Scores = Record<string, number | null>;
export interface Compared { llm: Scores; existing: Scores; naive: Scores }
export interface ModeResult {
  mode: Mode;
  n_cases: number;
  n_valid: number;
  overall: Compared | Record<string, never>;
  by_h: Record<string, Compared>;
  by_origin: Record<string, Compared>;
  by_volume?: Record<string, Compared>;
  by_level?: Record<string, Compared>;
  verdict?: { metric: string; llm: number | null; existing: number | null; llm_lower_error: boolean | null; llm_better_direction?: boolean | null };
}

export interface RunStatus {
  state: string;
  done: number;
  total: number;
  spent_usd: number;
  remaining_usd?: number;
  budget_usd: number;
  stop_reason?: string | null;
  requests_not_completed?: number;
  cases_not_completed?: number;
  last_request_status?: string;
}

export interface Report {
  run_id: string;
  benchmark: Benchmark;
  model: string;
  dry_run: boolean;
  label: string;
  status: RunStatus;
  usage: { requests_sent: number; requests_planned: number; by_status?: Record<string, number>; retries?: number; prompt_tokens?: number; completion_tokens?: number; reasoning_tokens?: number; cost_usd?: number; cost_by_source?: Record<string, number>; requests_without_usage?: number; budget_usd: number; remaining_usd: number };
  full_sample: { existing: Scores; naive: Scores };
  modes: Record<string, { statuses: Record<string, number>; n_cases: number; invalid_rate: number; request_failure_rate: number }>;
  primary: Record<string, ModeResult>;
  exploratory: Record<string, ModeResult>;
  bootstrap: Record<string, { mean_diff: number; p05: number; p95: number; units: string; n: number; note: string } | null>;
}

export interface RunSummary {
  run_id: string;
  made_at: string;
  benchmark: Benchmark;
  model: string;
  modes: Mode[];
  dry_run: boolean;
  horizons: number[];
  sample_id: string;
  free: boolean | null;
  state: string | null;
  done: number | null;
  total: number | null;
  spent_usd: number | null;
  stop_reason: string | null;
}

export interface RunDetail {
  run_id: string;
  config: BenchRequest & { model: string };
  model: ModelInfo;
  sample_id: string;
  sample: { n_cases: number; served: Record<string, string>; target: string; [k: string]: unknown };
  status: RunStatus;
  report: Report;
  running: boolean;
}

export interface CaseRow {
  case_id: string;
  anon_id: string;
  origin: string;
  target_month: string;
  h: number;
  existing_method: string;
  existing: number | null;
  naive: number | null;
  actual: number | null;
  series_key?: string;
  unit?: string;
  [k: string]: unknown;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail ?? ''; } catch { /* not JSON */ }
    throw new Error(detail || `Benchmark request failed (${res.status})`);
  }
  return res.json();
}

const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });

export const fetchBenchInfo = () => req<BenchInfo>('/llm-bench/info');
export const estimateRun = (body: BenchRequest) => post<Estimate>('/llm-bench/estimate', body);
export const startRun = (body: BenchRequest) => post<{ run_id: string }>('/llm-bench/runs', body);
export const fetchRuns = () => req<RunSummary[]>('/llm-bench/runs');
export const fetchRun = (id: string) => req<RunDetail>(`/llm-bench/runs/${encodeURIComponent(id)}`);
export const fetchCases = (id: string, mode?: string, status?: string) =>
  req<{ n: number; modes: Mode[]; rows: CaseRow[] }>(`/llm-bench/runs/${encodeURIComponent(id)}/cases?${new URLSearchParams(
    Object.entries({ mode, status, limit: '500' }).filter(([, v]) => v) as [string, string][]).toString()}`);
export const stopRun = (id: string) => post<{ stopping: boolean }>(`/llm-bench/runs/${encodeURIComponent(id)}/stop`);
export const resumeRun = (id: string, confirm: boolean) => post<{ run_id: string }>(`/llm-bench/runs/${encodeURIComponent(id)}/resume?confirm=${confirm}`);

export interface SummaryRow {
  run_id: string;
  model: string;
  reasoning: string;
  mode: Mode;
  horizons: number[];
  n_valid: number;
  n_cases: number;
  llm: number | null;
  existing: number | null;
  naive: number | null;
  llm_lower_error: boolean | null;
  cost_usd: number | null;
}

export interface BenchSummary {
  benchmark: Benchmark;
  metric: string;
  units: 'pp' | 'doublings';
  full_sample: { existing?: number | null; naive?: number | null };
  n_runs: number;
  any_better: boolean;
  total_cost_usd: number;
  rows: SummaryRow[];
}

export const fetchBenchSummary = (benchmark: Benchmark) =>
  req<BenchSummary>(`/llm-bench/summary?benchmark=${benchmark}`);
