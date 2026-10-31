import { API_URL } from './config';
import { takeSseEvents } from './resume';

/** One place to learn a skill. */
export interface RoadmapSource {
  source_type: 'project' | 'certificate' | 'video' | 'activity' | 'reference';
  /** 1 = first pick. */
  rank: number;
  title: string;
  url: string;
  /** How long the resource says it takes, where its page states it. */
  duration_minutes?: number | null;
}

/** What was written for an AI study guide node. */
export interface RoadmapGuide {
  title: string;
  /** How AI can help the learner study this section's skills. */
  description: string;
  /** Concrete things to do, in order. */
  steps: string[];
  /** Where to read more; empty when the guide is only the AI's description. */
  sources: RoadmapSource[];
}

export interface RoadmapNode {
  /** ai_guide: a section's AI study guide, to be done before the section's skills. Missing on an older backend, meaning skill. */
  kind?: 'skill' | 'ai_guide';
  guide?: RoadmapGuide | null;
  roadmap_detail_id: string;
  skill_id: string;
  skill_name: string;
  skill_type: 'skill' | 'knowledge' | 'tech';
  importance: number | null;
  level: number | null;
  /** The area the skill belongs to, e.g. 'Web Development'. Null until the groups migration is applied. */
  skill_group?: string | null;
  /** URL of the learning material, if any. */
  source: string | null;
  /** Where to learn it, best first. Empty when none are known. */
  sources: RoadmapSource[];
  status: 'locked' | 'available' | 'completed';
  completed_at: string | null;
  previous_nodes: string[];
  previous_nodes_required: boolean;
  /** How long this step takes, in minutes. Missing on an older backend. */
  minutes?: number | null;
  /** stated: a resource's own page gives its length. estimated: our written formula. */
  minutes_basis?: 'stated' | 'estimated' | null;
  /** Title of the resource whose stated length was used. */
  minutes_source?: string | null;
}

/** One weighted line of a Bonus Quest's rubric. */
export interface RubricCriterion {
  key: string;
  criterion: string;
  /** What earns a high score. */
  description: string;
  /** Share of the total score; a challenge's weights add up to 100. */
  weight: number;
}

/** How a submitted repo did on one rubric criterion. */
export interface CriterionResult {
  key: string;
  /** 0-100. */
  score: number;
  why: string;
  improve: string;
}

/** How an earlier stage of a challenge ended. */
export interface StageResult {
  stage: number;
  title: string;
  repo_url: string | null;
  score: number | null;
  summary: string | null;
  judged_at: string | null;
}

/**
 * A challenge for a tech role, in two stages, optionally tied to the role's roadmap; a learner may have several per
 * role. Stage 1 is built from foundational skills; passing it lets Robbee rewrite it into a harder stage 2. The brief
 * and result fields describe the current stage.
 */
export interface RoadmapChallenge {
  challenge_id: string;
  onet_code: string;
  role_title: string;
  /** The roadmap it is tied to, if any. */
  roadmap_id: string | null;
  stage: 1 | 2;
  /** The roadmap sections the current stage draws on; empty without a roadmap. */
  sections: number[];
  title: string;
  /** The brief; may hold "- " feature lines. */
  description: string;
  /** Stage 2: what Robbee changed, one line. */
  twist: string | null;
  sdg: number;
  sdg_name: string;
  /** The learner's interests it is themed on. */
  interests: string[];
  /** Skills by area, as O*NET names (pass them through skillLabel). */
  tech_stack: { area: string; skills: string[] }[];
  rubric: RubricCriterion[];
  /** passed: the current stage scored pass_score+ (at stage 1, Robbee's rewrite is due); advancing: it is being written. */
  status: 'open' | 'judging' | 'passed' | 'advancing';
  pass_score: number;
  /** Earlier stages, oldest first. */
  history: StageResult[];
  completed_at: string | null;
  created_at: string;
  repo_url: string | null;
  result: CriterionResult[] | null;
  /** Weighted total of the latest judgement, 0-100. */
  score: number | null;
  summary: string | null;
  files_read: string[];
  attempts: number;
  judged_at: string | null;
}

export interface Roadmap {
  profile_id: string;
  onet_code: string;
  title: string;
  description: string | null;
  roadmap_id: string | null;
  status: 'locked' | 'available' | 'in_progress' | 'completed' | null;
  current: { section: number; unit: number } | null;
  sections: { section: number; /** What this section covers, e.g. "Web Fundamentals"; null on a roadmap built before this was tracked. */ title: string | null; units: { unit: number; nodes: RoadmapNode[] }[] }[];
  /** The challenges tied to this roadmap, oldest first; empty (or missing, on an older backend) for non-tech roles. */
  challenges?: RoadmapChallenge[];
  /** Minutes for every step, and for the steps not yet completed; with how many come from a stated length or the formula. Missing on an older backend. */
  minutes_total?: number;
  minutes_left?: number;
  stated_steps?: number;
  estimated_steps?: number;
}

/** A failed roadmap request, with a message that can be shown to the user as is. */
export class RoadmapError extends Error {}

async function call(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}/roadmap${path}`, init);
  } catch {
    throw new RoadmapError('Couldn’t reach Jobee. Check your connection and try again.');
  }
}

/** This profile's roadmap for the role, or its most recently built one when no role is given. Null if there is none. */
export async function getRoadmap(profileId: string, onetCode?: string): Promise<Roadmap | null> {
  const role = onetCode ? `&onet_code=${encodeURIComponent(onetCode)}` : '';
  const res = await call(`?profile_id=${encodeURIComponent(profileId)}${role}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new RoadmapError('Jobee couldn’t load your roadmap. Try again in a moment.');
  return res.json();
}

/** What the server reports while it builds a roadmap (POST /roadmap/stream), plus `building`, sent once it is known there is none yet. */
export type RoadmapEvent =
  | { type: 'building' }
  | { type: 'role'; title: string; onet_code: string }
  | { type: 'plan'; reused: boolean; already_known?: number }
  /** The roadmap as stored, before the challenges (the slow part, for tech roles) are written. */
  | { type: 'roadmap'; roadmap: Roadmap };

const BUILD_FAILED = 'Jobee couldn’t build your roadmap just now. Try again in a moment.';

/** Reads the stream of a build; returns the finished roadmap, or null if the server says another tab built it first. */
async function readBuild(res: Response, onEvent?: (event: RoadmapEvent) => void): Promise<Roadmap | null> {
  if (!res.body) throw new RoadmapError(BUILD_FAILED);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  let result: Roadmap | null = null;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      const taken = takeSseEvents(buffer + value);
      buffer = taken.rest;
      for (const event of taken.events) {
        if (event.type === 'result') result = event as unknown as Roadmap;
        else if (event.type === 'failed') {
          if (event.status === 409) return null;
          throw new RoadmapError(BUILD_FAILED);
        } else onEvent?.(event as unknown as RoadmapEvent);
      }
    }
  } catch (e) {
    if (e instanceof RoadmapError) throw e;
    throw new RoadmapError(BUILD_FAILED);
  }
  if (!result) throw new RoadmapError(BUILD_FAILED);
  return result;
}

/**
 * This profile's roadmap for the role, built by the AI model first if it doesn't exist yet (that takes a little while).
 * onEvent hears the build's progress, and `building` first when there is something to build; with a roadmap already
 * there it never fires. A server that can't stream (an older one) gets the plain request instead.
 * prioritySkills only matter for a new roadmap: an existing one and its progress are left as they are.
 * `skills` (names) are the learner's final list: the model then only arranges them, instead of choosing. With a list the roadmap is always
 * built fresh (replacing one that exists, keeping the steps already completed), so nothing is reused from an earlier build.
 */
export async function ensureRoadmap(profileId: string, onetCode: string, onEvent?: (event: RoadmapEvent) => void, prioritySkills: string[] = [], skills: string[] | null = null): Promise<Roadmap> {
  // A chosen skill list means a new roadmap: build it fresh even if one exists (progress is carried over by the server).
  const rebuild = skills !== null;
  if (!rebuild) {
    const existing = await getRoadmap(profileId, onetCode);
    if (existing) return existing;
  }
  onEvent?.({ type: 'building' });
  const init: RequestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, onet_code: onetCode, priority_skills: prioritySkills, skills, replace: rebuild }),
  };
  let res = await call('/stream', init);
  if (res.status === 404 || res.status === 405) res = await call('', init);
  else if (res.ok) {
    const built = (await readBuild(res, onEvent)) ?? (await getRoadmap(profileId, onetCode)); // null: built by another tab
    if (built) return built;
    throw new RoadmapError(BUILD_FAILED);
  }
  if (res.ok) return res.json();
  if (res.status === 409) {
    // Built by another tab in the meantime.
    const built = await getRoadmap(profileId, onetCode);
    if (built) return built;
  }
  throw new RoadmapError(BUILD_FAILED);
}

export async function completeNode(profileId: string, roadmapDetailId: string): Promise<Roadmap> {
  const res = await call(`/complete/${encodeURIComponent(roadmapDetailId)}?profile_id=${encodeURIComponent(profileId)}`, { method: 'POST' });
  if (!res.ok) throw new RoadmapError('Couldn’t save that. Try again.');
  return res.json();
}

/** Every challenge across the profile's roadmaps, newest first, and the stingers earned. */
export interface ChallengeList {
  challenges: RoadmapChallenge[];
  /** Stingers earned. */
  stingers: number;
  /** Earned stingers not yet spent on Robbee. */
  stingers_available: number;
}

export async function fetchChallenges(profileId: string): Promise<ChallengeList> {
  const res = await call(`/challenges?profile_id=${encodeURIComponent(profileId)}`);
  if (!res.ok) throw new RoadmapError('Jobee couldn’t load your challenges. Try again in a moment.');
  return res.json();
}

/** A tech role a challenge can be started for. */
export interface ChallengeRole {
  onet_code: string;
  title: string;
  icon: string | null;
  /** One of the roles last suggested to the learner. */
  suggested: boolean;
  /** How many challenges the learner already has for it. */
  challenges: number;
}

/** The tech roles to start a challenge for, the learner's suggested roles first. */
export async function fetchChallengeRoles(profileId: string): Promise<ChallengeRole[]> {
  const res = await call(`/challenges/roles?profile_id=${encodeURIComponent(profileId)}`);
  if (!res.ok) throw new RoadmapError('Jobee couldn’t load the roles. Try again in a moment.');
  return res.json();
}

/** Start a new challenge for a tech role; the AI model writes it, which takes 20-40 seconds. */
export async function createChallenge(profileId: string, onetCode: string): Promise<RoadmapChallenge> {
  const res = await call('/challenges', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, onet_code: onetCode }),
  });
  if (res.ok) return res.json();
  throw await failure(res, 'Jobee couldn’t write a challenge just now. Try again in a moment.');
}

/** A judged submission: the challenge with its score, and whether it passed the stage. */
export interface SubmitResult {
  challenge: RoadmapChallenge;
  passed: boolean;
  stinger_awarded: boolean;
  /** The learner's stinger total after this submission. */
  stingers: number;
  /** Earned stingers not yet spent on Robbee. */
  stingers_available: number;
}

/** The backend's message for a failed challenge request, if it is one written for the learner. */
async function failure(res: Response, fallback: string): Promise<RoadmapError> {
  // Its messages for a bad link, a locked or busy challenge, or GitHub limits are written for the learner.
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  return new RoadmapError(res.status < 500 || res.status === 503 ? detail ?? 'That didn’t work. Check the link and try again.' : fallback);
}

/** Have a public GitHub repo judged against the challenge's current stage; takes up to a minute. */
export async function submitChallenge(profileId: string, challengeId: string, repoUrl: string): Promise<SubmitResult> {
  const res = await call(`/challenge/${encodeURIComponent(challengeId)}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, repo_url: repoUrl }),
  });
  if (res.ok) return res.json();
  throw await failure(res, 'Jobee couldn’t judge that just now. Try again in a moment.');
}

/** Robbee rewrites a passed stage 1 into the harder stage 2; takes 20-40 seconds. */
export async function advanceChallenge(profileId: string, challengeId: string): Promise<RoadmapChallenge> {
  const res = await call(`/challenge/${encodeURIComponent(challengeId)}/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId }),
  });
  if (res.ok) return res.json();
  throw await failure(res, 'Robbee couldn’t rewrite the brief just now. Try again in a moment.');
}

/** Delete the profile's roadmap for a role, with its progress. Already gone counts as deleted. */
export async function deleteRoadmap(profileId: string, onetCode: string): Promise<void> {
  const res = await call(`?profile_id=${encodeURIComponent(profileId)}&onet_code=${encodeURIComponent(onetCode)}`, { method: 'DELETE' });
  if (!res.ok && res.status !== 404) throw new RoadmapError('Jobee couldn’t delete that roadmap. Try again in a moment.');
}

/** One of a profile's roadmaps in brief: which role, how far along. */
export interface RoadmapSummary {
  onet_code: string;
  title: string;
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  total: number;
  completed: number;
}

/** Every roadmap the profile has, newest first. */
export async function fetchRoadmapSummaries(profileId: string): Promise<RoadmapSummary[]> {
  const res = await call(`/summary?profile_id=${encodeURIComponent(profileId)}`);
  if (!res.ok) throw new RoadmapError('Jobee couldn’t check your roadmaps. Try again in a moment.');
  return res.json();
}

/** The same, keyed by role. Empty if there are none. */
export async function listRoadmaps(profileId: string): Promise<Record<string, RoadmapSummary>> {
  return Object.fromEntries((await fetchRoadmapSummaries(profileId)).map((r) => [r.onet_code, r]));
}

/** A skill the learner has completed on a roadmap. */
export interface LearnedSkill {
  skill_name: string;
  skill_type: 'skill' | 'knowledge' | 'tech';
  skill_group: string | null;
  completed_at: string;
}

/** The skills completed across all the profile's roadmaps, each once, ordered by group then name. */
export async function fetchLearnedSkills(profileId: string): Promise<LearnedSkill[]> {
  const res = await call(`/learned?profile_id=${encodeURIComponent(profileId)}`);
  if (!res.ok) throw new RoadmapError('Jobee couldn’t load the skills you’ve learned. Try again in a moment.');
  return res.json();
}

/** The skills proposed for a roadmap: a plain list, not yet arranged. `source` is "fallback" when the model couldn't be used. */
export interface SkillSelection {
  onet_code: string;
  title: string;
  skills: { skill_id: string; skill_name: string; skill_type: 'skill' | 'knowledge' | 'tech' }[];
  source: 'ai' | 'fallback';
}

/** Step one of a roadmap: which skills to include for this learner and role. Nothing is saved. */
export async function suggestRoadmapSkills(profileId: string, onetCode: string): Promise<SkillSelection> {
  const res = await call('/skills', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, onet_code: onetCode }),
  });
  if (!res.ok) throw new RoadmapError('Jobee couldn’t pick skills for this role just now.');
  return res.json();
}
