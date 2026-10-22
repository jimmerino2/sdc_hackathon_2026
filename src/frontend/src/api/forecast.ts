import type { ScenarioKey } from '../data/flows';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

/** O*NET code for Software Developers. */
export const SOFTWARE_DEVELOPERS_ONET = '15-1252.00';

/** Frontend scenario -> backend AI-adoption scenario. */
export const backendScenario: Record<ScenarioKey, 'Rapid AI' | 'Baseline' | 'Slow'> = {
  accelerates: 'Rapid AI',
  steady: 'Baseline',
  slows: 'Slow',
};

export interface JobHorizon {
  horizon_months: number;
  forecast_for: string;
  trend: 'growing' | 'stable' | 'shrinking';
  change_pct: number;
  range: { low: number; high: number };
  /** LightGBM forecast, percent change in postings from today. */
  model_change_pct: number;
  /** Likely range of the LightGBM forecast, in percent. */
  model_range: { low: number; high: number };
  reliability: { status: 'indicative' | 'validated'; note: string };
}

export interface JobForecast {
  onet_code: string;
  title: string;
  scenario: 'Slow' | 'Baseline' | 'Rapid AI';
  sectors: string;
  country: string;
  is_proxy_for_malaysia: boolean;
  forecast_from: string;
  ai_exposure: number | null;
  data_as_of: string | null;
  outlook: JobHorizon[];
}

export async function fetchJobForecasts(onetCode: string): Promise<JobForecast[]> {
  const res = await fetch(`${API_URL}/forecast/jobs?onet_code=${encodeURIComponent(onetCode)}`);
  if (!res.ok) throw new Error(`Forecast request failed (${res.status})`);
  return res.json();
}
