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
  /** The role's place under this scenario, 1 = best. */
  rank?: number | null;
  /** How match_percent was made up. Null on a saved set that doesn't reconcile with today's formula. */
  breakdown?: MatchBreakdown | null;
}

/** One part of the match, as scored by the backend. */
export interface ScoreComponent {
  key: 'skills' | 'outlook' | 'interests' | 'education';
  score: number;
  /** Configured weight. These add up to 1.05, so show `share`. */
  weight: number;
  /** The share of the score it really carries; the shares add up to 1. */
  share: number;
  points: number;
}

export interface MatchBreakdown {
  components: ScoreComponent[];
  raw_score: number;
  curve: number;
  match_percent: number;
}

/** A key skill and how it counted. */
export interface SkillFit {
  name: string;
  importance_share: number;
  proficiency: number;
  via: string | null;
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
  /** Each key skill and how it counted. Missing on older saved sets. */
  skill_fit?: SkillFit[];
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
  /** The career stage behind the education part. */
  stage?: string | null;
}

export interface ScenarioComparison {
  scenario: ScenarioOutlook['scenario'];
  tab: string;
  current_percent: number;
  simulated_percent: number;
  change: number;
  current_rank: number;
  simulated_rank: number;
  current: MatchBreakdown | null;
  simulated: MatchBreakdown | null;
  outlook: ScenarioOutlook | null;
  explanation: string;
}

export interface RoleComparison {
  onet_code: string;
  title: string;
  icon: string;
  skills_owned_before: number;
  skills_owned_after: number;
  skills_total: number;
  skills_gained: { name: string; before: number; after: number; via: string | null }[];
  skills_replaced: string[];
  skills_remaining: string[];
  skill_fit: SkillFit[];
  sdg_reasons: SdgReason[];
  scenarios: ScenarioComparison[];
}

export interface SkillOption {
  name: string;
  current: number;
  trial: number;
  roles_listing: number;
  gap_roles: string[];
  gains: { scenario: ScenarioOutlook['scenario']; average_change: number; best_change: number; best_role: string }[];
  demand: { occupation: string; direction: 'rising' | 'falling' | 'flat'; last_share: number | null; forecast: number; target_month: string; evidence: string } | null;
  emerging: boolean;
}

export interface SimulateResult {
  profile_id: string;
  horizon_months: number;
  coverage_before: number;
  coverage_after: number;
  summary: { scenario: ScenarioOutlook['scenario']; tab: string; current_top: string; simulated_top: string; current_top_percent: number; simulated_top_percent: number }[];
  roles: RoleComparison[];
  /** The role the options are for. */
  focus_role: string;
  options: SkillOption[];
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

/** The matches now against the same profile with these skills added. Nothing is saved. */
/** `focusRole` (an O*NET code) picks the role the skill options are for; leave it out for the best match. */
export async function simulateSkills(profileId: string, skills: { name: string; score: number }[], focusRole?: string | null): Promise<SimulateResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/jobs/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId, skills, focus_role: focusRole ?? null }),
    });
  } catch {
    throw new JobsError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();
  if (res.status === 404) throw new JobsError('Jobee couldn’t find your profile. Log in again to try the simulator.');
  if (res.status === 409) throw new JobsError('Jobee needs at least one skill on your profile to run a simulation.');
  throw new JobsError('Jobee couldn’t run that simulation. Try again in a moment.');
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
