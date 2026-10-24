import { API_URL } from './config';

/** One place to learn a skill. */
export interface RoadmapSource {
  source_type: 'project' | 'certificate' | 'video' | 'activity';
  /** 1 = first pick. */
  rank: number;
  title: string;
  url: string;
}

export interface RoadmapNode {
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

/** A Bonus Quest: an optional project built from the skills of a couple of sections (tech roles only). */
export interface RoadmapChallenge {
  challenge_id: string;
  sections: number[];
  /** Shown after this section. */
  after_section: number;
  title: string;
  /** The brief; may hold "- " feature lines. */
  description: string;
  sdg: number;
  sdg_name: string;
  /** The learner's interests it is themed on. */
  interests: string[];
  /** Skills by area, as O*NET names (pass them through skillLabel). */
  tech_stack: { area: string; skills: string[] }[];
  rubric: RubricCriterion[];
  /** True until every skill in its sections is done. */
  locked: boolean;
  status: 'open' | 'judging' | 'judged';
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
  /** Bonus Quests; empty (or missing, on an older backend) for non-tech roles. */
  challenges?: RoadmapChallenge[];
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

/** This profile's roadmap for the role, built by the AI model first if it doesn't exist yet (that takes a little while). */
export async function ensureRoadmap(profileId: string, onetCode: string): Promise<Roadmap> {
  const existing = await getRoadmap(profileId, onetCode);
  if (existing) return existing;
  const res = await call('', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, onet_code: onetCode }),
  });
  if (res.ok) return res.json();
  if (res.status === 409) {
    // Built by another tab in the meantime.
    const built = await getRoadmap(profileId, onetCode);
    if (built) return built;
  }
  throw new RoadmapError('Jobee couldn’t build your roadmap just now. Try again in a moment.');
}

export async function completeNode(profileId: string, roadmapDetailId: string): Promise<Roadmap> {
  const res = await call(`/complete/${encodeURIComponent(roadmapDetailId)}?profile_id=${encodeURIComponent(profileId)}`, { method: 'POST' });
  if (!res.ok) throw new RoadmapError('Couldn’t save that. Try again.');
  return res.json();
}

/** Have a public GitHub repo judged against a Bonus Quest; takes up to a minute. Returns the challenge with its score. */
export async function submitChallenge(profileId: string, challengeId: string, repoUrl: string): Promise<RoadmapChallenge> {
  const res = await call(`/challenge/${encodeURIComponent(challengeId)}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId, repo_url: repoUrl }),
  });
  if (res.ok) return res.json();
  // The backend's messages for a bad link, a locked or busy challenge, or GitHub limits are written for the learner.
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  throw new RoadmapError(res.status < 500 || res.status === 503 ? detail ?? 'That didn’t work. Check the link and try again.' : 'Jobee couldn’t judge that just now. Try again in a moment.');
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
