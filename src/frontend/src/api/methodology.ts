import { API_URL } from './config';

/** How one forecast works (GET /methodology). Null means the pipeline's output doesn't hold it. */
export interface ForecastHorizon {
  h: number;
  model: string;
  is_baseline: boolean;
  status: string;
  status_text: string | null;
  chosen_model: string | null;
}

export interface ForecastTest {
  h: number;
  model_error: number | null;
  baseline: string;
  baseline_error: number | null;
  /** Null when the forecast shown is the baseline itself. */
  outperformed: boolean | null;
  n: number | null;
  origins: number | null;
  coverage_80: number | null;
  machine_learning_error?: number | null;
}

export interface ForecastSource {
  source: string;
  url: string;
  used_for: string;
  license: string;
  last_updated: string | null;
}

export interface ForecastInfo {
  id: string;
  title: string;
  provenance: { source: string; url: string | null; geography: string; population: string; period: string | null; last_updated: string | null; coverage: string[]; license?: string; also_uses?: ForecastSource[] };
  measure: { metric: string; unit: string; denominator: string; value_type: string };
  configuration: { frequency: string; horizon_unit: string; issued: string | null; last_observation: string | null; horizons: ForecastHorizon[]; selection_rule: string | null };
  reliability: {
    method: string;
    window: string | null;
    origins: number | null;
    origins_detail: Record<string, number> | null;
    held_back_origins: number | null;
    error_unit: string;
    horizons: ForecastTest[];
  };
  uncertainty: { label: string; how: string; detail: string | null };
  limitations: string[];
}

export interface Methodology {
  forecasts: Record<string, ForecastInfo>;
  emerging: { source: string; kind: string; rule: string; strong: string; weak: string; history: string; built: string | null } | null;
  scenarios: { summary: string; futures: { scenario: string; tab: string; effect_12m: number | null }[]; chances: string };
  geography: { note: string; malaysia: string };
}

let cached: Promise<Methodology> | null = null;

/** Read once per visit; a failed read isn't kept, so the next panel tries again. */
export function fetchMethodology(): Promise<Methodology> {
  cached ??= fetch(`${API_URL}/methodology`)
    .then((res) => {
      if (!res.ok) throw new Error(`Methodology request failed (${res.status})`);
      return res.json();
    })
    .catch((e) => {
      cached = null;
      throw e;
    });
  return cached;
}
