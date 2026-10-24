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
  /** Average % the forecast was off from the actual value. */
  pct_off: number;
  /** Average of smaller / larger of forecast and actual, in % (100 = exact). */
  accuracy_pct: number;
  /** Average |forecast - actual| in the value's own unit (pp, or minutes). */
  avg_miss: number;
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

/** Every ingredient of the faster / same pace / slower chances for one horizon (growth factors: 2 = doubled). */
export interface RegimeExplained {
  h: number;
  unit: string;
  period_unit: string;
  model: string;
  last_observed: number;
  last_observed_period: string;
  /** Growth over the past 12 months. */
  past_growth: number;
  /** The same pace, over this horizon. */
  same_pace_growth: number;
  band_low_growth: number;
  band_high_growth: number;
  tolerance_pct: number;
  forecast_growth: number;
  forecast: number;
  /** Today's forecast change plus one past error of the method, each. */
  possible_outcomes: { growth: number; origin: string; role: string }[];
  p_faster: number;
  p_same: number;
  p_slower: number;
  n_faster: number;
  n_slower: number;
  n: number;
  methods: {
    method: string;
    chosen: boolean;
    served: boolean;
    /** Typical miss as a factor (2 = typically twice or half the actual). */
    selection_typical_miss: number | null;
    holdout_typical_miss: number | null;
  }[];
  /** Brier scores of these chances on past tests (lower is better); a plain 1/3-each guess scores brier_uniform. */
  reliability: { n: number; brier_model: number | null; brier_climatology: number | null; brier_uniform: number | null } | null;
}

export const fetchRegime = (target: string, unit: string) =>
  get<RegimeExplained[]>(`/outlook/${encodeURIComponent(target)}/regime?unit=${encodeURIComponent(unit)}`);

export const fetchAccuracy = (target: string, unit: string) =>
  get<UnitAccuracy[]>(`/outlook/${encodeURIComponent(target)}/accuracy?unit=${encodeURIComponent(unit)}`);

/** One model's task lengths (human minutes) at several success rates, from METR's success curve. */
export interface SuccessModel {
  model: string;
  epoch_model: string | null;
  release_date: string | null;
  source: string;
  /** true = full curve fitted from METR's raw runs; false = only the official 50% / 80% numbers exist. */
  fitted: boolean;
  intercept: number | null;
  slope: number | null;
  /** Success rate in % -> task length in human minutes (null when not available). */
  horizons: Record<string, number | null>;
  /** Observed success rate per task-length group, from the raw attempts. */
  observed: { bin: string; median_human_minutes: number; attempts: number; success_rate: number }[];
}

export interface SuccessCurves {
  levels: number[];
  longest_task_minutes: number;
  models: SuccessModel[];
  note: string;
}

export const fetchSuccessCurves = () => get<SuccessCurves>('/outlook/capability/success-curves');
