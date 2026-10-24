import { API_URL } from './config';

/** Occupational forecasting API (src/backend/app/occupational). Independent of the AI outlook endpoints. */

export type ModelStatus = 'validated' | 'baseline' | 'not_demonstrably_better' | 'baseline_retained';

export interface Headline {
  served: string;
  chosen_on_validation: string;
  status: ModelStatus;
  test_mae_pp: number | null;
  persistence_test_mae_pp: number | null;
  test_n: number | null;
  coverage_80: number | null;
  interval_width_pp: number | null;
}

export interface OccMeta {
  run_id: string;
  made_at: string;
  model_version: string;
  data_version: string;
  taxonomy_version: string;
  registry_version: number;
  last_complete_month: string;
  partial_month: string;
  history_start: string;
  history_months: string[];
  horizons: number[];
  headline: Record<string, Headline>;
  taxonomy: {
    version: string;
    sectors: { id: string; name: string; occupations: { id: string; name: string; onet_codes: string[]; onet_note: string }[] }[];
    countries: Record<string, string>;
    curated_skills: number;
    onet_release: string | null;
  };
  cells: { occupation: string; country: string; ads_last_12m: number }[];
  asof_origins: string[];
  source_health: Record<string, { status?: string; [k: string]: unknown }>;
  counts: { ads: number; eligible: number; classified: number; series: number; registry: Record<string, number> };
  split: Record<string, string>;
  target: string;
  rules: OccRules;
  post_hoc_methods: string[];
}

/** Pipeline rules from evaluation.json; numbers plus nested selection / tuning settings. */
export interface OccRules {
  min_target_ads: number;
  material_change_pp: number;
  direction_label_pp?: number;
  [k: string]: unknown;
}

export interface MethodAccuracy {
  method: string;
  served: boolean;
  n: number;
  mae_pp: number;
  bias_pp: number;
  direction_acc?: number;
  mae_ratio_vs_persistence?: number;
}

export interface CellSummary {
  ads_last_12m: number;
  ads_last_month: number;
  accuracy: MethodAccuracy[];
}

export interface SkillRow {
  skill_id: string;
  skill_name: string;
  skill_status: string;
  skill_origin: string;
  category: string | null;
  in_onet: boolean | null;
  h: number;
  origin_month: string;
  target_month: string;
  forecast: number;
  low: number | null;
  high: number | null;
  model: string;
  model_status: ModelStatus;
  last_share_3m: number | null;
  last_ads_3m: number;
  last_count_3m: number;
  share_12m: number | null;
  ads_12m: number;
  count_12m: number;
  evidence: 'high' | 'medium' | 'low';
  backtested: boolean;
  /** Forecast minus the last 3 months' share, in share points; `direction` is its label (flat = about stable). */
  direction: 'rising' | 'falling' | 'flat';
  baseline_share?: number | null;
  change_pp?: number | null;
  change_pp_recent_vs_base: number | null;
  growth_lb_pp: number | null;
  growth_ub_pp: number | null;
}

export interface AsOfRow {
  skill_id: string;
  skill_name: string;
  forecast: number;
  actual: number;
  actual_ads: number;
  share_12m: number;
  share_3m?: number | null;
  target_month: string;
  model: string;
}

export type SkillsResponse =
  | { mode: 'latest'; rows: SkillRow[]; cell: CellSummary }
  | { mode: 'asof'; origin: string; rows: AsOfRow[]; cell: CellSummary };

export interface RegistryEntry {
  skill_id: string;
  name: string;
  category: string;
  status: string;
  origin: string;
  in_onet: boolean;
  aliases_seen: string[];
  reason: string;
  first_seen?: string;
  confidence?: string;
  possible_alias_of?: string | null;
  evidence?: { ad_id: string; month: string; employer: string; url: string; snippet: string }[] | null;
}

export interface HistoryPoint {
  month: string;
  n_ads: number;
  n_ads_skill: number;
  is_partial: boolean;
  share_3m: number | null;
  share_month: number | null;
}

export interface BacktestPoint {
  origin_month: string;
  target_month: string;
  h: number;
  method: string;
  role: string;
  forecast: number;
  actual: number;
  actual_n: number;
}

export interface SkillDetail {
  skill: RegistryEntry;
  history: HistoryPoint[];
  forecast: SkillRow[];
  backtest: BacktestPoint[];
  adzuna: { retrieved_at: string; n_ads: number; n_ads_skill: number; share: number }[];
  examples: { source: string; month: string; employer: string; title_raw: string; url: string }[];
}

export interface EmergingRow {
  skill_id: string;
  name: string;
  status: string;
  origin: string;
  category: string;
  in_onet: boolean;
  in_onet_for_occupation: boolean;
  first_seen: string;
  first_seen_any: string | null;
  k_recent: number;
  k_base: number;
  n_recent: number;
  n_base: number;
  share_recent: number | null;
  share_base: number | null;
  change_pp: number | null;
  growth_lb_pp: number;
  growth_ratio: number;
  employers: number;
  months_present: number;
  confidence: 'high' | 'medium' | 'low';
  meets_evidence_minimum: boolean;
  reason: string | null;
  possible_alias_of: string | null;
  evidence: RegistryEntry['evidence'];
  aliases_seen: string[];
  recent_window: string;
  base_window: string;
}

export interface BackcheckSkill {
  skill_id: string;
  name: string;
  first_flagged: string | null;
  first_newly_detected: string | null;
  share_reached_2pct_us_swe: string | null;
}

export interface EmergingResponse {
  rows: EmergingRow[];
  registry: { version: number; built_at: string; thresholds: Record<string, unknown>; statuses: Record<string, number> };
  backcheck: { as_of_months: string[]; reference: string; skills: BackcheckSkill[] } | null;
}

export interface WorkerUsage {
  year: number;
  occupation: string;
  country: string;
  n_respondents: number;
  n_using: number;
  share_using: number | null;
  ci_low: number | null;
  ci_high: number | null;
  published_ok: boolean;
  devtypes: string;
  wording: string;
  fielded: string;
  population: string;
  comparability_note: string | null;
  source_url: string;
}

export interface AdoptionResponse {
  worker_usage: WorkerUsage[];
  worker_usage_context: { quarter: string; group: string; share_using: number; population: string; occupation_scope: string }[];
  employer_signal: { month: string; country: string; occupation: string; n_ads: number; n_ads_skill: number; share_3m: number | null; definition: string }[];
  task_exposure: { onet_code: string; onet_title: string; usage_percentile: number; as_of: string; definition: string }[];
  sources: { id: string; target: string; measure_type: string; name: string; population: string; definition: string; period: string; geography: string; limitation?: string; url?: string }[];
  not_found: Record<string, string>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`Occupational request failed (${res.status})`);
  return res.json();
}

const q = (o: Record<string, string | number | undefined>) =>
  new URLSearchParams(Object.entries(o).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)])).toString();

export const fetchOccMeta = () => get<OccMeta>('/occupational/meta');
export const fetchSkills = (country: string, occupation: string, h: number, origin?: string) =>
  get<SkillsResponse>(`/occupational/skills?${q({ country, occupation, h, origin })}`);
export const fetchSkill = (skill: string, country: string, occupation: string) =>
  get<SkillDetail>(`/occupational/skills/${encodeURIComponent(skill)}?${q({ country, occupation })}`);
export const fetchEmerging = (country: string, occupation: string) => get<EmergingResponse>(`/occupational/emerging?${q({ country, occupation })}`);
export const fetchAdoption = (occupation: string) => get<AdoptionResponse>(`/occupational/adoption?${q({ occupation })}`);

export interface SignalIndicator {
  source: 'pypi' | 'npm';
  package: string;
  latest_month: string | null;
  downloads_3m: number | null;
  growth_vs_6m_before: number | null;
  growth_vs_12m_before: number | null;
  window: string;
  months_of_history: number;
  quality: 'strong' | 'moderate' | 'weak';
  fresh: boolean;
  url: string;
}

export interface SignalRow {
  skill_id: string;
  skill_name: string;
  forecast: number;
  low: number | null;
  high: number | null;
  baseline_share: number | null;
  change_pp: number | null;
  direction: 'rising' | 'falling' | 'flat';
  target_month: string;
  last_ads_3m: number;
  evidence_cell: 'large' | 'medium' | 'low';
  /** Log growth (not %) of relative downloads / related-skill logit share; null = no data. */
  adoption_g6: number | null;
  adoption_g12: number | null;
  related_g6: number | null;
  related_g12: number | null;
  signal: 'accelerating' | 'contradictory' | 'some_acceleration' | 'slowing' | 'some_slowing' | 'no_signal';
  adjusted_forecast: number | null;
  rise_probability: number | null;
  rise_alert: boolean;
  indicators: SignalIndicator[];
  related_skills: string[];
}

export interface RadarScores { n: number; positives: number; alerts: number; true_alerts: number; precision: number | null; recall: number | null; false_positive_rate: number | null; base_rate: number | null; average_precision: number | null }

export interface SignalsResponse {
  status: 'ok' | 'not_built' | 'failed';
  error?: string;
  horizon: number;
  baseline_method: string;
  adjusted_forecast: { validated: boolean; best_on_validation: string; rule: string };
  radar: { validated: boolean; hybrid_beats_own_ap_in_bootstrap: number; rise_pp: number; min_ads_3m: number };
  radar_test: Record<'own' | 'hybrid', RadarScores>;
  test_summary: Record<'baseline' | 'control' | 'hybrid', { n: number; mae_pp: number; bias_pp: number; direction_acc?: number; selection_score: number }>;
  relationship: { period: string; features: Record<string, { n: number; corr: number | null; slope: number | null }> };
  coverage: { skills_with_adoption_indicators: string[]; package_months: Record<string, [string, string]> };
  package_health?: { status: string; latest_month?: string; failed?: string[] };
  sources: Record<string, { name: string; url: string }>;
  rows: SignalRow[];
}

export const fetchSignals = (country: string, occupation: string) => get<SignalsResponse>(`/occupational/signals?${q({ country, occupation })}`);

export interface MethodScores { n: number; mae_pp: number; wmae_pp: number; bias_pp: number; direction_acc?: number; mae_ratio_vs_persistence?: number }
export interface OccEvaluation {
  run_id: string;
  made_at: string;
  target: string;
  split: Record<string, string>;
  rules: OccRules;
  methods: Record<string, string>;
  post_hoc_methods: string[];
  horizons: Record<string, {
    chosen_on_validation: string;
    served: string;
    status: ModelStatus;
    scores: Record<'train' | 'validation' | 'test', Record<string, MethodScores>>;
    interval_test: Record<string, { coverage_80: number; mean_width_pp: number }>;
  }>;
}
export const fetchOccEvaluation = () => get<OccEvaluation>('/occupational/evaluation');
