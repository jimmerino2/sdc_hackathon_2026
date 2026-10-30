import type { ScenarioKey } from '../data/flows';
import { API_URL } from './config';

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

export interface HistoryPoint {
  month: string;
  /** Postings that month vs the latest month, in percent. 0 at the latest month. */
  change_pct: number;
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
  /** Past months, oldest first, ending at forecast_from. */
  history: HistoryPoint[];
  outlook: JobHorizon[];
}

export async function fetchJobForecasts(onetCode: string): Promise<JobForecast[]> {
  const res = await fetch(`${API_URL}/forecast/jobs?onet_code=${encodeURIComponent(onetCode)}`);
  if (!res.ok) throw new Error(`Forecast request failed (${res.status})`);
  return res.json();
}

export interface DataSource {
  id: string;
  name: string;
  publisher: string;
  url: string;
  license: string;
  used_for: string;
  /** Date the data was last published, YYYY-MM-DD. */
  as_of: string | null;
  /** Latest month the forecast uses, YYYY-MM. */
  latest_month: string | null;
  is_proxy_for_malaysia: boolean;
}

let sourcesCache: Promise<DataSource[]> | undefined;

/** The datasets behind the role trends. Fetched once per page load; a failure is not cached so the next caller retries. */
export function fetchForecastSources(): Promise<DataSource[]> {
  sourcesCache ??= fetch(`${API_URL}/forecast/sources`)
    .then((res) => {
      if (!res.ok) throw new Error(`Sources request failed (${res.status})`);
      return res.json() as Promise<DataSource[]>;
    })
    .catch((e) => {
      sourcesCache = undefined;
      throw e;
    });
  return sourcesCache;
}
