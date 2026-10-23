import type { Roadmap, RoadmapNode, RoadmapSource } from '../api/roadmap';

export type SkillState = 'ready' | 'done' | 'locked';

/** A roadmap node with the state the Learn page draws it in. */
export interface ResolvedSkill {
  node: RoadmapNode;
  id: string; // roadmap_detail_id
  state: SkillState;
  /** Names of the required prerequisites that aren't done yet. */
  blockers: string[];
}

export interface ResolvedUnit {
  id: string;
  label: string;
  skills: ResolvedSkill[];
}

export function allNodes(roadmap: Roadmap | null): RoadmapNode[] {
  return roadmap?.sections.flatMap((s) => s.units.flatMap((u) => u.nodes)) ?? [];
}

/**
 * done: completed. locked: a required prerequisite isn't done, or the server still holds the node back
 * (nodes beyond the current unit stay locked). ready: everything else.
 * Prerequisites marked "recommended" (previous_nodes_required false) never lock a node.
 */
export function resolveNodes(nodes: RoadmapNode[], label: (n: RoadmapNode) => string = (n) => n.skill_name): Map<string, ResolvedSkill> {
  const bySkill = new Map(nodes.map((n) => [n.skill_id, n]));
  const out = new Map<string, ResolvedSkill>();
  for (const n of nodes) {
    const blockers = n.previous_nodes_required
      ? n.previous_nodes.map((id) => bySkill.get(id)).filter((p): p is RoadmapNode => !!p && p.status !== 'completed').map(label)
      : [];
    const state: SkillState = n.status === 'completed' ? 'done' : blockers.length || n.status === 'locked' ? 'locked' : 'ready';
    out.set(n.roadmap_detail_id, { node: n, id: n.roadmap_detail_id, state, blockers });
  }
  return out;
}

/** The units of one roadmap section, with every node resolved. */
export function resolveUnits(roadmap: Roadmap, section: number, label?: (n: RoadmapNode) => string): ResolvedUnit[] {
  const resolved = resolveNodes(allNodes(roadmap), label);
  const sec = roadmap.sections.find((s) => s.section === section);
  return (sec?.units ?? []).map((u) => ({ id: `s${section}u${u.unit}`, label: `Unit ${u.unit}`, skills: u.nodes.map((n) => resolved.get(n.roadmap_detail_id)!) }));
}

/** A copy of the roadmap with one node marked completed (the optimistic update; the server's answer replaces it). */
export function completeLocally(roadmap: Roadmap, roadmapDetailId: string): Roadmap {
  return {
    ...roadmap,
    sections: roadmap.sections.map((s) => ({
      ...s,
      units: s.units.map((u) => ({
        ...u,
        nodes: u.nodes.map((n) => (n.roadmap_detail_id === roadmapDetailId && n.status !== 'locked' ? { ...n, status: 'completed' as const, completed_at: n.completed_at ?? new Date().toISOString() } : n)),
      })),
    })),
  };
}

export function progress(roadmap: Roadmap | null): { done: number; total: number } {
  const nodes = allNodes(roadmap);
  return { done: nodes.filter((n) => n.status === 'completed').length, total: nodes.length };
}

/** True when every node in the section is completed. */
export function sectionCleared(roadmap: Roadmap, section: number): boolean {
  const sec = roadmap.sections.find((s) => s.section === section);
  const nodes = sec?.units.flatMap((u) => u.nodes) ?? [];
  return nodes.length > 0 && nodes.every((n) => n.status === 'completed');
}

/** Where a learner can learn a skill: its sources, or the single legacy link. */
export function learningLinks(n: RoadmapNode): { title: string; url: string; kind: RoadmapSource['source_type'] | 'link' }[] {
  if (n.sources.length) return n.sources.map((s) => ({ title: s.title, url: s.url, kind: s.source_type }));
  return n.source ? [{ title: 'Learning material', url: n.source, kind: 'link' }] : [];
}

/* ---------- path layout (a 520px-wide stage; nodes wind along a sine wave) ---------- */
export const STAGE_W = 520;
const CENTER = 190;
const ROW = 100;
const UNIT_H = 76; // leaves room for the START tag that floats above the first node
const PAD = 36;

export type PathItem =
  | { type: 'unit'; label: string; y: number }
  | { type: 'node'; skill: ResolvedSkill; x: number; y: number; k: number };

export function layoutPath(units: ResolvedUnit[]): { items: PathItem[]; pts: [number, number][]; height: number } {
  let y = 8;
  let k = 0;
  const items: PathItem[] = [];
  const pts: [number, number][] = [];
  for (const u of units) {
    items.push({ type: 'unit', label: u.label, y });
    y += UNIT_H;
    for (const skill of u.skills) {
      const c = CENTER + Math.round(Math.sin(k * 1.2) * 68);
      items.push({ type: 'node', skill, x: c - 32, y, k });
      pts.push([c, y + 32]);
      y += ROW;
      k++;
    }
  }
  return { items, pts, height: y + PAD };
}

/** SVG path string joining the node centres with smooth vertical curves. */
export function trailPath(pts: [number, number][]): string {
  if (!pts.length) return '';
  let d = `M${pts[0]![0]} ${pts[0]![1]}`;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1]!;
    const b = pts[i]!;
    const m = (b[1] - a[1]) * 0.5;
    d += ` C${a[0]} ${a[1] + m} ${b[0]} ${b[1] - m} ${b[0]} ${b[1]}`;
  }
  return d;
}

export const CENTER_X = CENTER;
