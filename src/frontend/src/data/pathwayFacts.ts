import type { Roadmap, RoadmapNode } from '../api/roadmap';
import { skillLabel } from './skills';

export interface PathwayStep {
  title: string;
  /** What it is doing, and why (muted). */
  what: string;
  why: string;
  /** Up to three findings, shown one by one while the step is active. */
  found: string[];
  /** The one line left behind once the step is done. */
  summary: string;
}

const RESOURCE_WORDS: Record<string, string> = { project: 'projects', video: 'videos', activity: 'activities', certificate: 'certificates' };
const TYPE_WORDS: Record<RoadmapNode['skill_type'], string> = { tech: 'tools', skill: 'abilities', knowledge: 'knowledge areas' };

const plural = (n: number, one: string, many = one + 's') => `${n} ${n === 1 ? one : many}`;
const list = (items: string[]) => (items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`);

/** The longest run of "needs this first" links; previous_nodes hold skill ids. */
export function longestChain(nodes: RoadmapNode[]): RoadmapNode[] {
  const by = new Map(nodes.map((n) => [n.skill_id, n]));
  const memo = new Map<string, RoadmapNode[]>();
  const visiting = new Set<string>();
  function chainTo(n: RoadmapNode): RoadmapNode[] {
    const known = memo.get(n.skill_id);
    if (known) return known;
    if (visiting.has(n.skill_id)) return [n]; // a cycle shouldn't exist; don't loop on one
    visiting.add(n.skill_id);
    let best: RoadmapNode[] = [];
    for (const id of n.previous_nodes) {
      const p = by.get(id);
      if (p) {
        const c = chainTo(p);
        if (c.length > best.length) best = c;
      }
    }
    visiting.delete(n.skill_id);
    const out = [...best, n];
    memo.set(n.skill_id, out);
    return out;
  }
  return nodes.reduce<RoadmapNode[]>((best, n) => {
    const c = chainTo(n);
    return c.length > best.length ? c : best;
  }, []);
}

/** A section's most common areas, e.g. "Web Development, Databases"; falls back to its title. */
function sectionAreas(nodes: RoadmapNode[], title: string | null): string {
  const counts = new Map<string, number>();
  for (const n of nodes) if (n.skill_group) counts.set(n.skill_group, (counts.get(n.skill_group) ?? 0) + 1);
  const top = [...counts].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([g]) => g);
  return top.length ? top.join(', ') : (title ?? 'Mixed skills');
}

/** Step 1 needs only the role, so the page can show it before the roadmap has been built. */
export function roleStep(title: string, onetCode: string): PathwayStep {
  return {
    title: 'Locked in your role',
    what: `Matching your profile to ${title} in the O*NET occupation database.`,
    why: 'Every skill in your roadmap comes from what this role actually asks for, not a generic list.',
    found: [`Role: ${title}`, `O*NET code: ${onetCode}`],
    summary: `${title} · O*NET ${onetCode}`,
  };
}

/** The six steps, with every number and name taken from the roadmap Jobee built. */
export function pathwayFacts(r: Roadmap): PathwayStep[] {
  const units = r.sections.flatMap((s) => s.units);
  const nodes = units.flatMap((u) => u.nodes);
  const name = (n: RoadmapNode) => skillLabel(n.skill_name);

  const byType = (['tech', 'skill', 'knowledge'] as const)
    .map((t) => [t, nodes.filter((n) => n.skill_type === t).length] as const)
    .filter(([, c]) => c);
  const ranked = nodes.filter((n) => n.importance !== null).sort((a, b) => b.importance! - a.importance! || (b.level ?? 0) - (a.level ?? 0));
  const top = ranked[0];
  const low = ranked.length > 1 ? ranked.at(-1)! : undefined;

  const links = nodes.reduce((a, n) => a + n.previous_nodes.length, 0);
  const chain = longestChain(nodes);
  const several = nodes.find((n) => n.previous_nodes.length > 1);
  const start = nodes.filter((n) => !n.previous_nodes.length).length;
  const nameOf = new Map(nodes.map((n) => [n.skill_id, name(n)]));

  const res: Record<string, number> = {};
  for (const n of nodes) for (const s of n.sources) res[s.source_type] = (res[s.source_type] ?? 0) + 1;
  const resTotal = Object.values(res).reduce((a, b) => a + b, 0);
  const without = nodes.filter((n) => !n.sources.length);

  const ch = r.challenges?.[0];

  return [
    roleStep(r.title, r.onet_code),
    {
      title: 'Ranking the skills',
      what: 'Scoring every skill by importance (how much the role relies on it) and level (how advanced you need to be).',
      why: 'The most relied-on skills come first, so you learn what matters most for getting hired.',
      found: [
        `${plural(nodes.length, 'skill')} kept: ${byType.map(([t, c]) => `${c} ${TYPE_WORDS[t]}`).join(', ')}`,
        top ? `Most relied on: ${name(top)} (importance ${top.importance!.toFixed(1)} of 5)` : '',
        low ? `Least: ${name(low)} (${low.importance!.toFixed(1)} of 5), still included` : '',
      ].filter(Boolean),
      summary: `${plural(nodes.length, 'skill')} ranked by importance`,
    },
    {
      title: 'Grouping into sections and units',
      what: `Grouping related skills into ${plural(r.sections.length, 'section')} and ${plural(units.length, 'unit')}, so each stretch has one theme.`,
      why: 'Learning related skills together makes them stick, and gives you a clear finish line for each section.',
      found: r.sections.map((s) => {
        const inSection = s.units.flatMap((u) => u.nodes);
        return `Section ${s.section}: ${sectionAreas(inSection, s.title)} (${plural(inSection.length, 'skill')})`;
      }),
      summary: `${plural(r.sections.length, 'section')}, ${plural(units.length, 'unit')}`,
    },
    {
      title: 'Setting the order you learn them in',
      what: 'Finding which skills need others first, then putting prerequisites before what depends on them.',
      why: 'Skipping a prerequisite is how people get stuck. Locked skills open as soon as what they need is done.',
      found: [
        links ? `${plural(links, '“needs this first” link')}` : 'No skill needs another first, so you can learn them in any order',
        chain.length > 1 ? `Longest chain: ${chain.map(name).join(' → ')}` : '',
        several ? `${name(several)} needs ${list(several.previous_nodes.map((id) => nameOf.get(id) ?? 'an earlier skill'))} first` : '',
        links ? `${plural(start, 'skill')} ${start === 1 ? 'has' : 'have'} no prerequisite, so you can start there` : '',
      ].filter(Boolean),
      summary: links ? `${plural(links, 'prerequisite')} placed` : 'No prerequisites needed',
    },
    {
      title: 'Finding learning resources',
      what: 'Finding hands-on projects, videos, activities and certificates for each skill, ranked best first.',
      why: 'You learn faster by doing, so each skill leads with the kind of resource that suits it.',
      found: [
        `${plural(resTotal, 'resource')} across ${plural(nodes.length - without.length, 'skill')}`,
        Object.keys(RESOURCE_WORDS)
          .filter((k) => res[k])
          .map((k) => `${res[k]} ${RESOURCE_WORDS[k]}`)
          .join(', '),
        without.length ? `${list(without.slice(0, 3).map(name))}${without.length > 3 ? ` and ${without.length - 3} more` : ''}: none yet (we say so instead of guessing)` : '',
      ].filter(Boolean),
      summary: `${plural(resTotal, 'resource')} found`,
    },
    {
      title: 'Designing your first project',
      what: !ch
        ? 'Looking for a first project to go with this role.'
        : ch.sections.length
          ? `Designing a first challenge that uses what Section${ch.sections.length === 1 ? '' : 's'} ${list(ch.sections.map(String))} ${ch.sections.length === 1 ? 'teaches' : 'teach'}.`
          : 'Designing a first challenge around this role’s skills.',
      why: 'A real project proves a skill better than a quiz, and it is built around your interests so it stays fun.',
      found: ch
        ? [ch.title, `SDG ${ch.sdg}: ${ch.sdg_name}`, ch.interests.length ? `Your interest: ${ch.interests.join(', ')}` : ''].filter(Boolean)
        : ['No starter project for this role yet'],
      summary: ch ? ch.title : 'No starter project for this role yet',
    },
  ];
}
