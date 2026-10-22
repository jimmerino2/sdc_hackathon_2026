import type { ScenarioKey } from '../data/flows';
import { API_URL } from './config';

/** Frontend scenario -> backend AI adoption scenario (ml/ai_adoption_mc.py). */
export const adoptionScenario: Record<ScenarioKey, AdoptionScenarioName> = {
  accelerates: 'AI accelerates',
  steady: 'AI holds',
  slows: 'AI declines',
};

export type AdoptionScenarioName = 'AI accelerates' | 'AI holds' | 'AI declines';

/** Share of workers using AI at work at one horizon: percentiles of the Monte Carlo paths, 0-1. */
export interface AdoptionPoint {
  horizon_months: number;
  forecast_for: string;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
}

export interface AdoptionScenario {
  scenario: AdoptionScenarioName;
  /** This week's odds, 0-1; the three sum to 1. */
  probability: number;
  outlook: AdoptionPoint[];
}

export interface AdoptionSignal {
  kind: 'structured' | 'news';
  source: string;
  /** Push on the score: + toward faster adoption, - toward slower. */
  value: number;
  label: string;
  url: string | null;
}

export interface AdoptionScore {
  week: string;
  score: number;
  structured_part: number | null;
  news_part: number | null;
  news_items: number;
  signals: AdoptionSignal[];
}

export interface AdoptionOutlook {
  soc_major: string;
  group: string;
  onet_code: string | null;
  title: string | null;
  country: string;
  is_proxy_for_malaysia: boolean;
  forecast_from: string;
  /** Estimated share using AI at work now, 0-1. */
  current_rate: number;
  expected: { horizon_months: number; forecast_for: string; rate: number }[];
  scenarios: AdoptionScenario[];
  score: AdoptionScore | null;
  data_as_of: string;
  note: string;
}

export interface OddsWeek {
  week: string;
  p_accelerates: number;
  p_holds: number;
  p_declines: number;
}

export interface SkillDemandPoint {
  week: string;
  skill: string;
  country: string;
  ads: number;
  share: number;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

/** One job's AI adoption outlook, or null if the job has no adoption data. */
export async function fetchJobAdoption(onetCode: string): Promise<AdoptionOutlook | null> {
  const rows = await get<AdoptionOutlook[]>(`/forecast/ai-adoption/jobs?onet_code=${encodeURIComponent(onetCode)}`);
  return rows[0] ?? null;
}

export const fetchOddsHistory = (group: string) =>
  get<OddsWeek[]>(`/forecast/ai-adoption/odds-history?group=${encodeURIComponent(group)}`);

export const fetchSkillDemand = (onetCode: string) =>
  get<SkillDemandPoint[]>(`/forecast/skill-demand?onet_code=${encodeURIComponent(onetCode)}`);

/** 0.7538 -> "75%". */
export const pct = (v: number) => `${Math.round(v * 100)}%`;

/** "2027-07" -> "Jul 2027". */
export function monthYear(ym: string) {
  const [y, m] = ym.split('-');
  return `${new Date(Number(y), Number(m) - 1).toLocaleString('en', { month: 'short' })} ${y}`;
}
