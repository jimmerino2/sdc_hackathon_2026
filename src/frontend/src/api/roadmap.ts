import { API_URL } from './config';

export interface RoadmapNode {
  roadmap_detail_id: string;
  skill_id: string;
  skill_name: string;
  skill_type: 'skill' | 'knowledge' | 'tech';
  importance: number | null;
  level: number | null;
  /** URL of the learning material, if any. */
  source: string | null;
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

/** This profile's roadmap for the role, or null if none has been built yet. */
export async function getRoadmap(profileId: string, onetCode: string): Promise<Roadmap | null> {
  const res = await call(`?profile_id=${encodeURIComponent(profileId)}&onet_code=${encodeURIComponent(onetCode)}`);
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
