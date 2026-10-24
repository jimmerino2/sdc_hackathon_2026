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

export type Pace = 'faster' | 'same' | 'slower';
type PaceProbs = Record<Pace, number>;

/** Brier / log-loss scores of the pace chances on past forecasts (lower is better). */
export interface PaceScore {
  n?: number;
  brier_model?: number;
  brier_served?: number;
  brier_climatology?: number;
  brier_uniform?: number;
  log_loss_model?: number;
  log_loss_climatology?: number;
  log_loss_uniform?: number;
  class_counts?: PaceProbs;
}

/** Every ingredient of the faster / same pace / slower chances for one horizon. Paces are doublings per year. */
export interface RegimeExplained {
  h: number;
  unit: string;
  period_unit: string;
  model: string;
  status: OutlookStatus;
  last_observed: number;
  last_observed_period: string;
  current_model: string;
  current_saturated: boolean;
  forecast: number;
  low: number | null;
  high: number | null;
  target_period: string;
  /** observed_12m | bridged_12m | trend_prior | none */
  pace_basis: string;
  hist_pace: number;
  /** 10-90% of the past pace once measurement uncertainty is drawn. */
  hist_pace_range: [number, number];
  tolerance: number;
  same_band: [number, number];
  future_pace_median: number;
  future_pace_range: [number, number];
  /** Simulated future paces (40 bins between the 1st and 99th percentile). */
  pace_histogram: { edges: number[]; counts: number[] };
  n_sims: number;
  p_faster: number;
  p_same: number;
  p_slower: number;
  /** Shares straight from the simulation, before any shrink to the base rate. */
  p_simulated: PaceProbs;
  base_rate: PaceProbs;
  prior_assisted: boolean;
  shrink: number;
  /** Chance of no new frontier record by then (see no_record_method). */
  p_no_new_record: number | null;
  /** The two-stage model's own figure, shown when the base rate is served instead. */
  p_no_new_record_model: number | null;
  /** model | base_rate: which one is served, decided on the earlier tests. */
  no_record_method: string | null;
  /** raw | calibrated (temperature fitted on earlier forecasts only). */
  probability_method: string;
  temperature: number;
  p_calibrated: PaceProbs | null;
  components: Record<string, { q50: number; q10: number; q90: number; p: [number, number, number]; weight: number | null }>;
  methods: {
    method: string;
    served: boolean;
    weight: number | null;
    /** Typical miss as a factor (2 = typically twice or half the actual). */
    selection_typical_miss: number | null;
    holdout_typical_miss: number | null;
    holdout_coverage_80: number | null;
    n_holdout: number | null;
  }[];
  /** Brier scores of the chances shown, on the held-back test (lower is better); a 1/3-each guess scores brier_uniform. */
  reliability: { n: number; brier_model: number | null; brier_climatology: number | null; brier_uniform: number | null } | null;
  pace_scores: { selection: PaceScore | null; holdout: PaceScore | null };
  pace_rule: { selection_skill: boolean; shrink: number; rule: string } | null;
}

export const fetchRegime = (target: string, unit: string) =>
  get<RegimeExplained[]>(`/outlook/${encodeURIComponent(target)}/regime?unit=${encodeURIComponent(unit)}`);

/** One measured (or bridged) model on the capability chart; minutes of human work at 50% success. */
export interface EnginePoint {
  model: string;
  release_date: string;
  minutes: number;
  low: number;
  high: number;
  layer: 'observed' | 'bridged';
  saturated: boolean;
  frontier_relevant: boolean;
}

export interface EnginePointScore {
  h: number;
  role: 'selection' | 'holdout';
  candidate: string;
  n: number;
  n_origins: number;
  mae?: number | null;
  median_ae?: number | null;
  bias?: number | null;
  typical_factor?: number | null;
  coverage_80?: number | null;
  width_80?: number | null;
  interval_score_80?: number | null;
}

export interface EngineUnit {
  observed: EnginePoint[];
  bridged: EnginePoint[];
  frontier: { period: string; minutes: number | null; model: string | null; event: string }[];
  /** Forecast quantiles per month after the last complete one. */
  fan: { period: string; q10: number; q25: number; q50: number; q75: number; q90: number }[];
  last_period: string;
  current_minutes: number;
  current_model: string;
  current_saturated: boolean;
  pace_basis: string;
  horizons: {
    h: number; target_period: string; median_minutes: number; weights: Record<string, number>;
    p_no_new_record: number | null; p_no_new_record_model: number | null; no_record_method: string | null; no_record_n: number;
    probability_method: string; temperature: number;
  }[];
  /** Secondary output: the model-estimated underlying trend (not an observation). */
  trend: TrendDetail | null;
  components: Record<string, Record<string, unknown>>;
  bridge: { applied: boolean; credible?: boolean; n_pairs: number; slope?: number; intercept?: number; slope_ci80?: [number, number]; resid_sd?: number; reason?: string };
  iid_checks: { increment_lag1_autocorrelation: number | null; release_dispersion_index: number | null; months_with_new_record: number; months: number };
  n_observed: number;
  n_bridged: number;
}

export type TrendClass = 'accelerating' | 'stable' | 'decelerating';

export interface TrendDetail {
  /** Smoothed latent level (minutes) with its 80% band, and the growth rate then (doublings / year). */
  history: { period: string; minutes: number | null; low: number | null; high: number | null; pace_per_year: number | null }[];
  forecast: { period: string; minutes: number; low: number; high: number }[];
  past_pace: number;
  past_pace_sd: number;
  pace_now: number;
  pace_now_sd: number;
  doubling_months: number | null;
  horizons: { h: number; p: Record<TrendClass, number>; future_pace_q10_q50_q90: [number, number, number] }[];
}

export interface TrendScore {
  h: number;
  role: string;
  n: number;
  mae_pace?: number;
  mae_persistence?: number;
  coverage_80?: number;
  brier_model?: number;
  brier_base_rate?: number;
  brier_uniform?: number;
  class_counts?: Record<TrendClass, number>;
}

export interface RecordScore {
  h: number;
  role: string;
  variant: string;
  n: number;
  rate?: number;
  mean_p?: number;
  brier_model?: number;
  brier_base_rate?: number;
  brier_half?: number;
  log_loss_model?: number;
  log_loss_base_rate?: number;
}

export interface BootstrapResult {
  h: number;
  comparison: string;
  n: number;
  mean?: number;
  ci80?: [number, number];
  ci95?: [number, number];
  share_below_0?: number;
}

/** The capability engine's detail for the served run (GET /outlook/{target}/engine). */
export interface EngineDetail {
  config: Record<string, unknown> & { n_sims: number; pace_tol_abs: number; pace_tol_rel: number; saturation_hours: number };
  units: Record<string, EngineUnit>;
  backtest: {
    point: EnginePointScore[];
    pace: (PaceScore & { h: number; role: string; candidate: string })[];
    shrink: Record<string, { method: string; selection_skill: boolean; shrink: number }>;
    record_choice: Record<string, { method: string }>;
    non_overlapping: { h: number; n: number; n_holdout: number; mae_ensemble: number | null; mae_naive: number | null; mae_drift: number | null;
      brier_served: number | null; brier_uniform: number | null; brier_climatology: number | null }[];
    bootstrap: BootstrapResult[];
    record: RecordScore[];
    trend: TrendScore[];
    brier_definition: string;
    n_origins: number;
    origins_by_kind: Record<string, number>;
    note: string;
  };
  data: {
    source: string;
    metr_official_file: string | null;
    metr_official_check: { models_compared: number; max_relative_difference: number | null; matched_within_1pct: number } | null;
    metr_published_doubling_days: { from_2023_on?: { point_estimate: number; ci_low: number; ci_high: number } } | null;
    vintage: string;
    data_as_of: string;
    latest_complete_month: string;
    measurement_lag_months: number;
  };
  limitations: string[];
  decisions: {
    components: Record<string, { included: boolean; reason: string; ratio?: number; pairs?: number }>;
    members: string[];
    external_signals: Record<string, { kept: boolean; reason: string; n?: number; log_loss_change?: number; log_loss_change_vs_constant?: number }>;
    hazard: string;
    external_inventory: { benchmarks: { benchmark: string; available: boolean; first_in_epoch_archive?: string; release_from?: string; release_to?: string }[];
      models_file: string | null; features: string[] };
  };
}

export const fetchEngine = (target: string) => get<EngineDetail>(`/outlook/${encodeURIComponent(target)}/engine`);

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
