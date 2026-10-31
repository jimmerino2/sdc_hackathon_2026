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

/** A section's AI study guide: it comes first in its unit and the unit's skills wait for it. */
export const isGuide = (s: ResolvedSkill): boolean => s.node.kind === 'ai_guide';

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

/* ---------- graph layout: each unit is a set of category columns; rows follow learning order ---------- */
const COLS = 3; // category columns before the smallest ones share the last
const SLOT_MAX = 150; // width of one skill
const SLOT_MIN = 110;
const ORB = 64;
const GRAPH_ROW = 156; // orb + label + room for the line to the next row
const GUIDE_SCALE = 1.5; // an AI study guide is drawn this much bigger than a skill
const GUIDE_ORB = ORB * GUIDE_SCALE;
const GUIDE_EXTRA = 44; // the rows under a guide sit this much lower, for its bigger orb and label
const GRAPH_UNIT_H = 64;
const UNIT_GAP = 20;
const OTHER = 'Other';
const MORE = 'More skills'; // the shared column of the smallest categories

export type GraphItem =
  | { type: 'unit'; label: string; y: number }
  | { type: 'node'; skill: ResolvedSkill; x: number; y: number; w: number; k: number };

export interface GraphEdge {
  d: string;
  /** The prerequisite is done, so the line is lit. */
  done: boolean;
}

/** One unit worked out before any pixels: which column and row each skill takes. */
interface UnitPlan {
  label: string;
  columns: string[];
  crowded: boolean;
  cells: Map<string, ResolvedSkill[]>; // "col:row" -> the skills side by side there
  colSlots: number[]; // widest row of each column, in skills
  rows: number;
  /** The unit's AI study guides, above row 0 of everything else and centred across the unit. */
  guides: ResolvedSkill[];
}

function planUnit(u: ResolvedUnit, groupOf: (s: ResolvedSkill) => string | null | undefined): UnitPlan {
  // Only required prerequisites hold a skill back; recommended ones don't move it down.
  const gating = (s: ResolvedSkill) => (s.node.previous_nodes_required ? s.node.previous_nodes : []);
  const bySkill = new Map(u.skills.map((s) => [s.node.skill_id, s]));
  const depth = new Map<string, number>();
  const depthOf = (s: ResolvedSkill): number => {
    const id = s.node.skill_id;
    if (!depth.has(id)) {
      depth.set(id, 0); // guards against a cycle in hand-edited data
      const prev = gating(s).map((p) => bySkill.get(p)).filter((p): p is ResolvedSkill => !!p);
      depth.set(id, prev.length ? 1 + Math.max(...prev.map(depthOf)) : 0);
    }
    return depth.get(id)!;
  };

  // A guide sits on its own row above the skills, so it is kept out of the category columns.
  const guides = u.skills.filter(isGuide);
  const skills = u.skills.filter((s) => !isGuide(s));

  // One column per category, in the order they first appear; past COLS the smallest share the last column.
  const sizes = new Map<string, number>();
  for (const s of skills) {
    const g = groupOf(s) || OTHER;
    sizes.set(g, (sizes.get(g) ?? 0) + 1);
  }
  const ranked = [...sizes.keys()];
  const crowded = ranked.length > COLS;
  const keep = crowded ? [...ranked].sort((a, b) => sizes.get(b)! - sizes.get(a)!).slice(0, COLS - 1) : ranked;
  const columns = ranked.filter((g) => keep.includes(g));
  if (crowded) columns.push(MORE);
  const colOf = (s: ResolvedSkill) => {
    const g = groupOf(s) || OTHER;
    return columns.indexOf(keep.includes(g) ? g : MORE);
  };

  // Vertical order is learning order: a skill sits below its required prerequisites and never above a skill
  // that comes before it. Skills with the same footing share a row, side by side within their category.
  const cells = new Map<string, ResolvedSkill[]>();
  const rowOf = new Map<string, number>(guides.map((g) => [g.node.skill_id, 0]));
  let floor = guides.length ? 1 : 0;
  let rows = floor;
  for (const s of [...skills].sort((a, b) => depthOf(a) - depthOf(b))) { // stable: ties keep the server's order
    const prev = gating(s).filter((p) => rowOf.has(p)).map((p) => rowOf.get(p)!);
    const row = Math.max(floor, prev.length ? 1 + Math.max(...prev) : 0);
    const key = `${colOf(s)}:${row}`;
    cells.set(key, [...(cells.get(key) ?? []), s]);
    rowOf.set(s.node.skill_id, row);
    floor = row;
    rows = Math.max(rows, row + 1);
  }
  const colSlots = columns.map((_, col) => Math.max(1, ...[...cells].filter(([k]) => k.startsWith(`${col}:`)).map(([, v]) => v.length)));
  return { label: u.label, columns, crowded, cells, colSlots, rows, guides };
}

/**
 * Lay a section's units out as a dependency graph. Inside a unit, skills sit in a column per category (at most
 * COLS; a unit with more categories folds the smallest into one shared column). Category only picks left or
 * right: a skill's row follows learning order, so a skill is never above one that comes before it, and skills
 * that can start together share a row. Categories widen to hold the skills they have side by side. Each
 * prerequisite inside the unit is joined to the skill that needs it, unless the two are level.
 */
export function layoutGraph(units: ResolvedUnit[], groupOf: (s: ResolvedSkill) => string | null | undefined): { items: GraphItem[]; edges: GraphEdge[]; height: number; width: number } {
  const plans = units.map((u) => planUnit(u, groupOf));
  const widest = Math.max(1, ...plans.map((p) => p.colSlots.reduce((a, b) => a + b, 0)));
  const slotW = Math.max(SLOT_MIN, Math.min(SLOT_MAX, STAGE_W / widest));
  const width = Math.max(STAGE_W, widest * slotW);

  const items: GraphItem[] = [];
  const edges: GraphEdge[] = [];
  let y = 8;
  let k = 0;
  plans.forEach((plan) => {
    items.push({ type: 'unit', label: plan.label, y });
    y += GRAPH_UNIT_H;
    const total = plan.colSlots.reduce((a, b) => a + b, 0);
    let left = (width - total * slotW) / 2;
    const colLeft = plan.colSlots.map((n) => {
      const x = left;
      left += n * slotW;
      return x;
    });
    const top = y;

    const placed = new Map<string, { cx: number; y: number; orb: number; skill: ResolvedSkill }>();
    const nodes: GraphItem[] = [];
    const lower = plan.guides.length ? GUIDE_EXTRA : 0;
    for (const g of plan.guides) {
      const gw = Math.min(width, slotW * GUIDE_SCALE);
      nodes.push({ type: 'node', skill: g, x: (width - gw) / 2, y: top, w: gw, k: k++ });
      placed.set(g.node.skill_id, { cx: width / 2, y: top, orb: GUIDE_ORB, skill: g });
    }
    for (const [key, skills] of plan.cells) {
      const [col, row] = key.split(':').map(Number) as [number, number];
      const start = colLeft[col]! + (plan.colSlots[col]! * slotW - skills.length * slotW) / 2; // a short row is centred
      skills.forEach((s, i) => {
        const x = start + i * slotW + 5;
        const ny = top + row * GRAPH_ROW + (row > 0 ? lower : 0);
        nodes.push({ type: 'node', skill: s, x, y: ny, w: slotW - 10, k: k++ });
        placed.set(s.node.skill_id, { cx: x + (slotW - 10) / 2, y: ny, orb: ORB, skill: s });
      });
    }
    items.push(...nodes);
    y = top + plan.rows * GRAPH_ROW + lower + UNIT_GAP;

    for (const to of placed.values()) {
      for (const id of to.skill.node.previous_nodes) {
        const from = placed.get(id);
        if (!from || from.y === to.y) continue; // level skills get no line
        // A recommended prerequisite can sit below the skill it suggests; the line still joins them.
        const [hi, lo] = from.y < to.y ? [from, to] : [to, from];
        const [x1, y1, x2, y2] = [hi.cx, hi.y + hi.orb, lo.cx, lo.y];
        const m = (y2 - y1) * 0.5;
        edges.push({ d: `M${x1} ${y1} C${x1} ${y1 + m} ${x2} ${y2 - m} ${x2} ${y2}`, done: from.skill.state === 'done' });
      }
    }
  });
  return { items, edges, height: y + PAD, width };
}
