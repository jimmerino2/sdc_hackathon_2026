import { describe, expect, it } from 'vitest';
import type { JobMatch, MatchBreakdown, ScenarioOutlook } from '../api/jobs';
import { formulaLine, partCaption, postingChange } from './matchExplain';

const outlook: ScenarioOutlook = { scenario: 'Rapid AI', tab: 'AI accelerates', change_pct: 11.8, range_low_pct: 7, range_high_pct: 33, trend: 'growing', forecast_for: '2027-09' };
const job = {
  skills_owned: 2, skills_total: 3, skills_to_learn: ['Docker'],
  sdg_reasons: [{ sdg: 9, name: 'Industry', value: 1, interests: ['Robots', 'Energy'] }, { sdg: 7, name: 'Energy', value: 1, interests: ['Energy'] }],
} as unknown as JobMatch;

describe('partCaption', () => {
  it('counts key skills', () => expect(partCaption('skills', job, outlook)).toBe('2 of 3 key skills'));
  it('shows the forecast figure, or says there is none', () => {
    expect(partCaption('outlook', job, outlook)).toBe('Job ads +11.8% by Sep 2027');
    expect(partCaption('outlook', job, undefined)).toBe('No forecast yet');
  });
  it('names a real interest and counts the rest once', () => {
    expect(partCaption('interests', job, outlook)).toBe('Linked to Robots +1');
    expect(partCaption('interests', { ...job, sdg_reasons: [] }, outlook)).toBe('No link to your interests');
  });
  it('names the career stage', () => {
    expect(partCaption('education', job, outlook, 'fresh')).toBe('Fresh graduate');
    expect(partCaption('education', job, outlook)).toBe('Same for every role');
  });
});

describe('formatting', () => {
  it('shows a falling change without a plus', () => expect(postingChange({ ...outlook, change_pct: -3.2 })).toBe('-3.2% by Sep 2027'));
  it('exposes the curve', () => {
    const b: MatchBreakdown = { components: [], raw_score: 0.4, curve: 0.7, match_percent: 53 };
    expect(formulaLine(b)).toContain('40.0 out of 100');
    expect(formulaLine(b)).toContain('53%');
  });
});
