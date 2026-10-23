import { API_URL } from './config';
import type { SdgFocus, SdgReason } from './interests';

export interface ScenarioOutlook {
  scenario: 'Rapid AI' | 'Baseline' | 'Slow';
  tab: string;
  change_pct: number;
  range_low_pct: number;
  range_high_pct: number;
  trend: 'growing' | 'stable' | 'shrinking';
  forecast_for: string;
  /** The role's overall match under this scenario. Missing on sets saved before scenario scores existed. */
  match_percent?: number | null;
}

/** How much AI already touches a job (Anthropic Economic Index); null when unknown. */
export interface AiExposure {
  ai_exposure: number | null;
  automation_share: number | null;
}

/** A non-matched role shown for contrast on the demand-vs-AI chart. */
export interface ContextRole extends AiExposure {
  onet_code: string;
  title: string;
  outlook: ScenarioOutlook[];
}

/** The match parts that don't depend on the AI scenario, each 0-1. */
export interface MatchParts {
  education: number;
  /** Null if the learner picked no interests. */
  interests: number | null;
  skills: number;
}

/** A role's match under one AI future (backend scenario name), falling back to its headline match on older saved sets. */
export function matchPercent(job: JobMatch, scenario: ScenarioOutlook['scenario']): number {
  return job.outlook.find((o) => o.scenario === scenario)?.match_percent ?? job.match_percent;
}

export interface JobMatch extends AiExposure {
  rank: number;
  onet_code: string;
  title: string;
  icon: string;
  /** The overall match under the AI-accelerates scenario; use matchPercent() for the chosen one. */
  match_percent: number;
  match_parts?: MatchParts | null;
  skills_owned: number;
  skills_total: number;
  skills_you_have: string[];
  skills_to_learn: string[];
  description: string;
  outlook: ScenarioOutlook[];
  /** For each SDG the role serves, why it fits the learner's interests. Missing on sets saved before this existed. */
  sdg_reasons?: SdgReason[];
}

export interface Recommendations {
  profile_id: string;
  jobs: JobMatch[];
  context: ContextRole[];
  horizon_months: number;
  /** The SDGs the learner's interests point at, biggest first. Empty or missing if they picked no interests. */
  sdg_focus?: SdgFocus[];
  note: string;
  /** When the roles were worked out (ISO 8601). Missing on sets saved before this was recorded. */
  generated_at?: string | null;
}

/** A failed request, with a message that can be shown to the user as is. */
export class JobsError extends Error {}

export async function fetchRecommendations(profileId: string): Promise<Recommendations> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/jobs/recommend?profile_id=${encodeURIComponent(profileId)}`);
  } catch {
    throw new JobsError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();
  if (res.status === 404) throw new JobsError('Jobee couldn’t find your profile. Go back and finish the questions again.');
  if (res.status === 409) throw new JobsError('Jobee needs at least one skill to match roles. Go back and rate a few skills.');
  throw new JobsError('Jobee couldn’t match roles just now. Try again in a moment.');
}

/** Why a role fits one of the learner's interests, through one SDG they share. */
export interface InterestReason {
  sdg: number;
  interest_id: number;
  interest: string;
  /** One short sentence, written by the LLM the first time and then kept. */
  reason: string;
}

/** The interest reasons for one role. Slow the first time (the LLM writes them), instant after. */
export async function fetchInterestReasons(profileId: string, onetCode: string): Promise<InterestReason[]> {
  const res = await fetch(`${API_URL}/jobs/reasons?profile_id=${encodeURIComponent(profileId)}&onet_code=${encodeURIComponent(onetCode)}`);
  if (!res.ok) throw new JobsError(`Reasons request failed (${res.status})`);
  return res.json();
}

/** The roles last suggested to this profile, as they were then (nothing is recomputed). Null if none were saved. */
export async function fetchSuggested(profileId: string): Promise<Recommendations | null> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/jobs/suggested?profile_id=${encodeURIComponent(profileId)}`);
  } catch {
    throw new JobsError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();
  if (res.status === 404) return null;
  throw new JobsError('Jobee couldn’t load your suggested roles. Try again in a moment.');
}
