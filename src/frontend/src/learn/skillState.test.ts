import { describe, expect, it } from 'vitest';
import type { Roadmap, RoadmapNode } from '../api/roadmap';
import { completeLocally, layoutGraph, layoutPath, progress, resolveNodes, resolveUnits, sectionCleared, trailPath } from './skillState';

function node(id: string, status: RoadmapNode['status'], prev: string[] = [], required = true): RoadmapNode {
  return {
    roadmap_detail_id: `d-${id}`, skill_id: id, skill_name: id.toUpperCase(), skill_type: 'skill', importance: 3, level: 3,
    source: null, sources: [], status, completed_at: status === 'completed' ? '2026-01-01T00:00:00Z' : null,
    previous_nodes: prev, previous_nodes_required: required,
  };
}
function roadmap(...units: RoadmapNode[][]): Roadmap {
  return {
    profile_id: 'p', onet_code: '15-1252.00', title: 'Software Developers', description: null, roadmap_id: 'r', status: 'in_progress',
    current: { section: 1, unit: 1 }, sections: [{ section: 1, title: null, units: units.map((nodes, i) => ({ unit: i + 1, nodes })) }],
  };
}
const stateOf = (r: Roadmap, id: string) => resolveNodes(r.sections.flatMap((s) => s.units.flatMap((u) => u.nodes))).get(`d-${id}`)!;

describe('skill state', () => {
  it('is done when completed, ready with no open prerequisite, locked behind one', () => {
    const r = roadmap([node('a', 'completed'), node('b', 'available'), node('c', 'locked', ['b'])]);
    expect(stateOf(r, 'a').state).toBe('done');
    expect(stateOf(r, 'b').state).toBe('ready');
    expect(stateOf(r, 'c').state).toBe('locked');
    expect(stateOf(r, 'c').blockers).toEqual(['B']);
  });

  it('stays locked until every required prerequisite is done', () => {
    const r = roadmap([node('a', 'completed'), node('b', 'available'), node('c', 'locked', ['a', 'b'])]);
    expect(stateOf(r, 'c').blockers).toEqual(['B']);
    const after = completeLocally(r, 'd-b');
    expect(stateOf(after, 'c').blockers).toEqual([]);
  });

  it('does not lock on recommended (not required) prerequisites', () => {
    const r = roadmap([node('a', 'available'), node('b', 'available', ['a'], false)]);
    expect(stateOf(r, 'b').state).toBe('ready');
    expect(stateOf(r, 'b').blockers).toEqual([]);
  });

  it('keeps nodes the server still holds back locked, even with no open prerequisite', () => {
    const r = roadmap([node('a', 'completed')], [node('b', 'locked', ['a'])]);
    expect(stateOf(r, 'b').state).toBe('locked');
  });

  it('ignores prerequisites that are not on the roadmap', () => {
    expect(stateOf(roadmap([node('a', 'available', ['gone'])]), 'a').state).toBe('ready');
  });
});

describe('completing a skill', () => {
  const r = roadmap([node('a', 'available'), node('b', 'available'), node('c', 'locked', ['a'])]);

  it('raises progress by one without changing the original', () => {
    expect(progress(r)).toEqual({ done: 0, total: 3 });
    const after = completeLocally(r, 'd-a');
    expect(progress(after)).toEqual({ done: 1, total: 3 });
    expect(progress(r).done).toBe(0);
    expect(stateOf(after, 'a').state).toBe('done');
  });

  it('refuses to complete a locked node', () => {
    expect(progress(completeLocally(r, 'd-c')).done).toBe(0);
  });

  it('reports a cleared section once all its nodes are done', () => {
    expect(sectionCleared(r, 1)).toBe(false);
    expect(sectionCleared(completeLocally(completeLocally(r, 'd-a'), 'd-b'), 1)).toBe(false);
    const all = roadmap([node('a', 'completed'), node('b', 'completed')]);
    expect(sectionCleared(all, 1)).toBe(true);
  });
});

describe('path layout', () => {
  it('places a unit label before its nodes and winds nodes along the trail', () => {
    const units = resolveUnits(roadmap([node('a', 'available'), node('b', 'locked', ['a'])], [node('c', 'locked', ['b'])]), 1);
    const { items, pts, height } = layoutPath(units);
    expect(items.map((i) => i.type)).toEqual(['unit', 'node', 'node', 'unit', 'node']);
    expect(pts).toHaveLength(3);
    expect(height).toBeGreaterThan(pts[2]![1]);
    expect(trailPath(pts).startsWith(`M${pts[0]![0]} ${pts[0]![1]}`)).toBe(true);
    expect(trailPath([])).toBe('');
  });
});

describe('AI study guide', () => {
  const guide = (): RoadmapNode => ({ ...node('ai:guide:1', 'available'), kind: 'ai_guide', skill_name: 'AI for basics', guide: { title: 'AI for basics', description: 'Use AI.', steps: [], sources: [] } });
  const unit = () => roadmap([guide(), node('a', 'locked', ['ai:guide:1']), node('b', 'locked', ['ai:guide:1'])]);

  it('keeps the skills locked until the guide is done, then opens them', () => {
    expect(stateOf(unit(), 'a').state).toBe('locked');
    expect(stateOf(unit(), 'a').blockers).toEqual(['AI for basics']);
    const done = completeLocally(unit(), 'd-ai:guide:1');
    expect(stateOf(done, 'ai:guide:1').state).toBe('done');
    expect(stateOf(done, 'a').blockers).toEqual([]);
  });

  it('is drawn above the skills of its unit and at least 1.5 times as wide as one', () => {
    const units = resolveUnits(unit(), 1);
    const nodes = layoutGraph(units, () => 'Programming Languages').items.filter((i) => i.type === 'node');
    const g = nodes.find((i) => i.skill.node.kind === 'ai_guide')!;
    const others = nodes.filter((i) => i !== g);
    expect(others.every((o) => o.y > g.y)).toBe(true);
    expect(g.w).toBeGreaterThanOrEqual(others[0]!.w * 1.5);
  });

  it('gets a line to every skill that waits for it', () => {
    const { edges } = layoutGraph(resolveUnits(unit(), 1), () => 'Programming Languages');
    expect(edges).toHaveLength(2);
  });
});
