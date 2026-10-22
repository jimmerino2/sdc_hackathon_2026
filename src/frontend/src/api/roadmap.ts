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

export interface Roadmap {
  profile_id: string;
  onet_code: string;
  title: string;
  description: string | null;
  roadmap_id: string | null;
  status: 'locked' | 'available' | 'in_progress' | 'completed' | null;
  current: { section: number; unit: number } | null;
  sections: { section: number; units: { unit: number; nodes: RoadmapNode[] }[] }[];
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
