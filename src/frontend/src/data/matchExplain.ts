import type { JobMatch, MatchBreakdown, ScenarioOutlook, ScoreComponent } from '../api/jobs';

export const COMPONENT_LABELS: Record<ScoreComponent['key'], string> = { skills: 'Skills', outlook: 'Job outlook', interests: 'Interests', education: 'Career stage' };

export const SCORE_TOOLTIP = 'Your match score compares your skills, the role’s job outlook, your interests and your career stage. It helps you compare roles. It doesn’t predict your chances of being hired.';

const STAGE_LABELS: Record<string, string> = { under: 'Studying', fresh: 'Fresh graduate', working: 'Working' };

/** "+11.8% by Sep 2027". */
export function postingChange(o: ScenarioOutlook): string {
  const [y, m] = o.forecast_for.split('-');
  const month = new Date(Number(y), Number(m) - 1).toLocaleString('en', { month: 'short' });
  return `${o.change_pct > 0 ? '+' : ''}${o.change_pct.toFixed(1)}% by ${month} ${y}`;
}

/** One part of a match in a few words, for the line beside its bar. Every name and figure comes from the job as scored. */
export function partCaption(key: ScoreComponent['key'], job: JobMatch, outlook: ScenarioOutlook | undefined, stage?: string | null): string {
  if (key === 'skills') return `${job.skills_owned} of ${job.skills_total} key skills`;
  if (key === 'outlook') return outlook ? `Demand ${postingChange(outlook)}` : 'No forecast yet';
  if (key === 'interests') {
    const shared = [...new Set((job.sdg_reasons ?? []).flatMap((r) => r.interests))];
    if (!shared.length) return 'No link to your interests';
    return shared.length > 1 ? `Linked to ${shared[0]} +${shared.length - 1}` : `Linked to ${shared[0]}`;
  }
  return (stage && STAGE_LABELS[stage]) || 'Same for every role';
}

/** Each part's slice of the final match, in whole points that add up to it exactly. */
export function matchSlices(b: MatchBreakdown): { key: ScoreComponent['key']; points: number }[] {
  const raw = b.components.reduce((a, c) => a + c.points, 0);
  if (raw <= 0) return b.components.map((c) => ({ key: c.key, points: 0 }));
  const exact = b.components.map((c) => (c.points / raw) * b.match_percent);
  const slices = b.components.map((c, i) => ({ key: c.key, points: Math.floor(exact[i]!) }));
  let left = b.match_percent - slices.reduce((a, s) => a + s.points, 0);
  // The largest remainders take the leftover points.
  for (const i of exact.map((_, i) => i).sort((x, y) => (exact[y]! % 1) - (exact[x]! % 1))) {
    if (left-- <= 0) break;
    slices[i]!.points++;
  }
  return slices;
}

/** How the final number comes from the parts, for the "How it’s calculated" dialog. */
export function formulaLine(b: MatchBreakdown): string {
  return `The parts add up to ${(b.raw_score * 100).toFixed(1)} out of 100. Jobee then applies a curve (score^${b.curve}) that lifts every score without changing their order, giving ${b.match_percent}%.`;
}
