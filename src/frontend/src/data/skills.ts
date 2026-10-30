import type { SkillScore } from '../api/resume';

/** O*NET skill names asked about in the skill check when the resume doesn't fill the list. */
export const DEFAULT_SKILLS = [
  'Programming',
  'Python',
  'Oracle Java',
  'JavaScript',
  'Structured query language SQL',
  'Git',
] as const;

/** How many skills the skill check shows; resume skills come first. */
export const SKILL_CHECK_SIZE = 8;

/** Skill check level (New, Basic, Good, Strong) -> the 0-1 score stored on the profile. New means "don't have it". */
export const LEVEL_SCORES = [0, 0.33, 0.67, 1] as const;

/** Starting level for a skill the resume showed, from how strongly it showed it: a clear, specific
 * mention (score 0.8+) starts at Strong; anything vaguer starts at Good. */
export function levelFromScore(score: number): number {
  return score >= 0.9 ? 3 : 2;
}

/** Shorter names for O*NET skills whose official names read badly on a chip. */
const LABELS: Record<string, string> = {
  'Structured query language SQL': 'SQL',
  'Oracle Java': 'Java',
  'Amazon Web Services AWS software': 'AWS',
  'Microsoft Azure software': 'Azure',
  'RESTful API': 'REST APIs',
  'JavaScript Object Notation JSON': 'JSON',
  'Hypertext markup language HTML': 'HTML',
  'Cascading style sheets CSS': 'CSS',
};

export function skillLabel(name: string): string {
  return LABELS[name] ?? name.replace(/ software$/, '');
}

/** The same skill can come from the resume and the skill check; the user's own rating wins. */
export function mergeSkills(rated: SkillScore[], resume: SkillScore[]): SkillScore[] {
  const out = new Map<string, SkillScore>();
  for (const s of resume) out.set(s.name.toLowerCase(), s);
  for (const s of rated) out.set(s.name.toLowerCase(), s);
  return [...out.values()].filter((s) => s.score > 0).sort((a, b) => b.score - a.score);
}
