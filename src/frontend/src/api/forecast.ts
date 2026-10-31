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

/** One quarter of data the forecast can be trained up to. */
export interface QuarterInfo {
  /** e.g. 2026-Q3 */
  quarter: string;
  months: number;
  first_month: string;
  last_month: string;
  /** False while its outcome is still unknown: the model can't learn from it, so leaving it out only moves where the forecast starts. */
  has_outcome: boolean;
}

export interface Quarters {
  /** Oldest first. */
  quarters: QuarterInfo[];
  latest_quarter: string;
  source: 'supabase' | 'csv';
  refresh_enabled: boolean;
  default_trained_rows: number | null;
}

/** A forecast from a model retrained without some quarters. */
export interface Retrained {
  /** The quarters left out, oldest first. */
  excluded_quarters: string[];
  forecast_from: string;
  trained_rows: number;
  default_trained_rows: number | null;
  holdout_origins: string[];
  model_status: 'indicative' | 'validated';
  source: 'supabase' | 'csv';
  seconds: number;
  cached: boolean;
  forecasts: JobForecast[];
}

/** A failed forecast request, with a message that can be shown to the user as is. */
export class ForecastError extends Error {}

export async function fetchQuarters(): Promise<Quarters> {
  const res = await fetch(`${API_URL}/forecast/quarters`);
  if (!res.ok) throw new ForecastError('Couldn’t load the quarters.');
  return res.json();
}

/**
 * The job's forecast from a model retrained without the `excluded` quarters (none = all the data). Takes 2-3 seconds
 * the first time for a set of quarters, then it is instant. `signal` cancels the request when the learner picks again.
 */
export async function retrainForecast(onetCode: string, excluded: string[], signal?: AbortSignal): Promise<Retrained> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/forecast/retrain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ onet_code: onetCode, excluded_quarters: excluded }),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ForecastError('Couldn’t reach the forecast service.');
  }
  if (res.status === 422) {
    const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
    throw new ForecastError(detail ?? 'Those quarters can’t be used.');
  }
  if (!res.ok) throw new ForecastError('The forecast couldn’t be retrained just now. Try again.');
  return res.json();
}

/** Makes the server re-read the stored series, so the next retrain sees changed rows. Only works where the server allows it. */
export async function refreshForecastData(): Promise<void> {
  const res = await fetch(`${API_URL}/forecast/refresh`, { method: 'POST' });
  if (!res.ok) throw new ForecastError('Refreshing isn’t turned on for this server.');
}

export interface SyncState {
  as_of: string | null;
  forecast_from: string;
}

export interface AiSync {
  target: string;
  /** The name on the page, like Worker adoption. */
  name: string;
  /** Only `updated` means a new forecast is showing. */
  status: 'updated' | 'stale' | 'failed';
}

/** What a sync did to the trend data. */
export interface TrendSync {
  /** False if Indeed couldn't be reached, or the data was edited by hand and nothing was pulled. */
  pulled: boolean;
  /** Figures edited by hand in signals.csv, so the page can say so. */
  manual_edits: number;
  before: SyncState;
  after: SyncState;
  /** The AI forecasts run again because their tables changed. */
  ai: AiSync[];
}

/** Pulls the newest trend data, retrains the role forecasts and any AI forecast whose data changed. Null where the server doesn't allow it: the roles are then only scored again. */
export async function syncTrends(): Promise<TrendSync | null> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/forecast/sync`, { method: 'POST' });
  } catch {
    throw new ForecastError('Couldn’t reach the forecast service.');
  }
  if (res.status === 403) return null;
  if (res.ok) return res.json();
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  throw new ForecastError(detail ?? 'The sync failed, so the current data was kept.');
}
