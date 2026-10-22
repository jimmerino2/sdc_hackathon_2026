import type { RoadmapSummary } from '../api/roadmap';

export type RoadmapStatusKey = 'none' | 'ready' | 'started' | 'completed';

/** How a role's roadmap is described on the roles pages. No summary means no roadmap has been generated for the role. */
export function roadmapStatus(r?: RoadmapSummary): { key: RoadmapStatusKey; label: string } {
  if (!r) return { key: 'none', label: 'No roadmap yet' };
  if (r.status === 'completed') return { key: 'completed', label: 'Roadmap completed' };
  if (r.completed > 0 || r.status === 'in_progress') return { key: 'started', label: `In progress · ${r.completed}/${r.total}` };
  return { key: 'ready', label: `Roadmap ready · ${r.total} skills` };
}
