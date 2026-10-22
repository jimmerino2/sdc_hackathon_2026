import { API_URL } from './config';

export interface ScenarioOutlook {
  scenario: 'Rapid AI' | 'Baseline' | 'Slow';
  tab: string;
  change_pct: number;
  range_low_pct: number;
  range_high_pct: number;
  trend: 'growing' | 'stable' | 'shrinking';
  forecast_for: string;
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

export interface JobMatch extends AiExposure {
  rank: number;
  onet_code: string;
  title: string;
  icon: string;
  match_percent: number;
  skills_owned: number;
  skills_total: number;
  skills_you_have: string[];
  skills_to_learn: string[];
  description: string;
  outlook: ScenarioOutlook[];
}

export interface Recommendations {
  profile_id: string;
  jobs: JobMatch[];
  context: ContextRole[];
  horizon_months: number;
  note: string;
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
