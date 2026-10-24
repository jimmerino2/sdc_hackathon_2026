import { API_URL } from './config';

/** How a forecast fared in its out-of-sample test (see data/documentation/FORECAST_REBUILD.md §6). */
export type OutlookStatus = 'validated' | 'baseline' | 'not_demonstrably_better' | 'baseline_retained';

export interface HorizonStatus {
  h: number;
  model: string;
  chosen_model: string | null;
  status: OutlookStatus;
  holdout_mase_vs_naive: number | null;
  run_id: string;
  made_at: string;
}

export interface TargetSummary {
  target: string;
  domain: 'skill_demand' | 'business_adoption' | 'occupation_adoption' | 'ai_capability';
  definition: string;
  label_source: string;
  unit_kind: string;
  value_unit: string;
  period_unit: string;
  error_unit: string;
  horizons: number[];
  promoted: HorizonStatus[];
  history_warning: string;
  source_health: Record<string, { status?: string; last_available_at?: string; last_complete_period?: string }>;
  has_regimes: boolean;
}

export interface OutlookRow {
  target: string;
  unit: string;
  unit_kind: string;
  segment: string | null;
  h: number;
  period_unit: string;
  last_observed_period: string;
  last_observed: number;
  target_period: string;
  value_unit: string;
  forecast: number;
  low: number | null;
  high: number | null;
  model: string;
  chosen_model: string | null;
  status: OutlookStatus;
  holdout_mae: number | null;
  naive_holdout_mae: number | null;
  p_acceleration: number | null;
  p_stable: number | null;
  p_slowdown: number | null;
  warnings: string[];
  data_as_of: string;
  run_id: string;
  made_at: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`Outlook request failed (${res.status})`);
  return res.json();
}

export const fetchTargets = () => get<TargetSummary[]>('/outlook');
export const fetchOutlook = (target: string) => get<OutlookRow[]>(`/outlook/${encodeURIComponent(target)}`);

/** One method's result on the held-back test data (naive = "no change"). */
export interface MethodScore {
  method: string;
  /** Average absolute error, in error_unit (pp, or doublings for time horizons). */
  mae: number;
  /** Average error; negative = forecasts were too low. */
  bias: number;
  n: number;
}

/** How every method did on the held-back test data for one unit at one horizon. */
export interface UnitAccuracy {
  h: number;
  unit: string;
  served_model: string;
  chosen_model: string | null;
  error_unit: string;
  n_test_points: number;
  served_mae: number | null;
  naive_mae: number | null;
  /** null when the forecast shown is "no change" itself. */
  beats_naive: boolean | null;
  methods: MethodScore[];
  all_units: MethodScore[];
  run_id: string;
}

export const fetchAccuracy = (target: string, unit: string) =>
  get<UnitAccuracy[]>(`/outlook/${encodeURIComponent(target)}/accuracy?unit=${encodeURIComponent(unit)}`);
