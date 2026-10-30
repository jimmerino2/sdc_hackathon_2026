import { describe, expect, it } from 'vitest';
import type { Roadmap, RoadmapNode } from '../api/roadmap';
import { longestChain, pathwayFacts } from './pathwayFacts';

const node = (id: string, over: Partial<RoadmapNode> = {}): RoadmapNode => ({
  roadmap_detail_id: 'd' + id,
  skill_id: id,
  skill_name: id,
  skill_type: 'tech',
  importance: 3,
  level: 3,
  skill_group: 'Web Development',
  source: null,
  sources: [],
  status: 'available',
  completed_at: null,
  previous_nodes: [],
  previous_nodes_required: true,
  ...over,
});

const roadmap = (nodes: RoadmapNode[][], challenges?: Roadmap['challenges']): Roadmap => ({
  profile_id: 'p',
  onet_code: '15-1252.00',
  title: 'Software Developers',
  description: null,
  roadmap_id: 'r',
  status: 'available',
  current: null,
  sections: nodes.map((n, i) => ({ section: i + 1, title: 'Basics', units: [{ unit: 1, nodes: n }] })),
  challenges,
});

describe('longestChain', () => {
  it('follows previous_nodes to the longest run', () => {
    const a = node('a');
    const b = node('b', { previous_nodes: ['a'] });
    const c = node('c', { previous_nodes: ['b'] });
    const d = node('d', { previous_nodes: ['a'] });
    expect(longestChain([a, b, c, d]).map((n) => n.skill_id)).toEqual(['a', 'b', 'c']);
  });

  it('survives a cycle and ids that are not on the roadmap', () => {
    const a = node('a', { previous_nodes: ['b'] });
    const b = node('b', { previous_nodes: ['a', 'zzz'] });
    expect(longestChain([a, b]).length).toBeGreaterThan(0);
  });
});

describe('pathwayFacts', () => {
  const steps = pathwayFacts(
    roadmap([
      [
        node('a', { importance: 4.5, skill_type: 'tech', sources: [{ source_type: 'video', rank: 1, title: 't', url: 'u' }] }),
        node('b', { importance: 2, skill_type: 'knowledge', previous_nodes: ['a'] }),
      ],
      [node('c', { importance: 3, skill_type: 'skill', previous_nodes: ['a', 'b'], skill_group: null })],
    ]),
  );

  it('has the six steps, each with something to show', () => {
    expect(steps).toHaveLength(6);
    for (const s of steps) expect(s.found.length).toBeGreaterThan(0);
  });

  it('reports the role and the mix of skills', () => {
    expect(steps[0].found).toEqual(['Role: Software Developers', 'O*NET code: 15-1252.00']);
    expect(steps[1].found[0]).toBe('3 skills kept: 1 tools, 1 abilities, 1 knowledge areas');
    expect(steps[1].found[1]).toContain('importance 4.5 of 5');
    expect(steps[1].found[2]).toContain('2.0 of 5');
  });

  it('counts sections, units and prerequisites', () => {
    expect(steps[2].summary).toBe('2 sections, 2 units');
    expect(steps[2].found[1]).toBe('Section 2: Basics (1 skill)');
    expect(steps[3].summary).toBe('3 prerequisites placed');
    expect(steps[3].found.some((f) => f.includes('c needs a and b first'))).toBe(true);
  });

  it('counts resources and says which skills have none', () => {
    expect(steps[4].summary).toBe('1 resource found');
    expect(steps[4].found.at(-1)).toBe('b and c: none yet (we say so instead of guessing)');
  });

  it('says so when there is no first project', () => {
    expect(steps[5].summary).toBe('No starter project for this role yet');
  });

  it('describes the first project when there is one', () => {
    const ch = { title: 'Eco tracker', sdg: 13, sdg_name: 'Climate Action', interests: ['Gaming'], sections: [1, 2] } as unknown as Roadmap['challenges'] extends (infer C)[] | undefined ? C : never;
    const s = pathwayFacts(roadmap([[node('a')]], [ch]))[5];
    expect(s.found).toEqual(['Eco tracker', 'SDG 13: Climate Action', 'Your interest: Gaming']);
    expect(s.what).toContain('Sections 1 and 2 teach');
  });
});
