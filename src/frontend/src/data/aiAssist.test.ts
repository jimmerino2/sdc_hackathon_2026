import { describe, expect, it } from 'vitest';
import { ASSIST_TIPS, guidanceFor, tipsFor, type ChallengeContext } from './aiAssist';
import { lessonById } from './aiFluency';

const challenge = (over: Partial<ChallengeContext> = {}): ChallengeContext => ({
  title: 'Clinic Finder',
  stage: 1,
  onet_code: '15-1252.00',
  role_title: 'Software Developers',
  tech_stack: [{ area: 'Backend', skills: ['Python'] }],
  ...over,
});
const ids = (c: ChallengeContext) => tipsFor(c).map((t) => t.id);

describe('AI Assist tips', () => {
  it('always offers the four core tips', () => {
    expect(ids(challenge())).toEqual(expect.arrayContaining(['debugging', 'code-generation', 'testing', 'code-review']));
  });

  it('suits the stage: a plan in round 1, a map of the changes in round 2', () => {
    expect(ids(challenge())).toContain('plan-the-brief');
    expect(ids(challenge())).not.toContain('round-2-changes');
    expect(ids(challenge({ stage: 2 }))).toContain('round-2-changes');
    expect(ids(challenge({ stage: 2 }))).not.toContain('plan-the-brief');
  });

  it('suits the stack', () => {
    expect(ids(challenge())).not.toContain('frontend-accessibility');
    expect(ids(challenge({ tech_stack: [{ area: 'Frontend', skills: ['React'] }] }))).toContain('frontend-accessibility');
    expect(ids(challenge({ tech_stack: [{ area: 'Data', skills: ['PostgreSQL'] }] }))).toContain('data-queries');
  });

  it('suits the role', () => {
    expect(ids(challenge())).not.toContain('security-review');
    expect(ids(challenge({ onet_code: '15-1212.00' }))).toContain('security-review');
  });

  it('fills in the project and stack, and leaves the learner’s placeholders', () => {
    const plan = tipsFor(challenge()).find((t) => t.id === 'plan-the-brief')!;
    expect(plan.prompt).toContain('"Clinic Finder" using Python');
    expect(plan.prompt).toContain('[paste the project brief]');
    for (const t of tipsFor(challenge())) expect(t.prompt).not.toMatch(/\{(project|stack|role)\}/);
  });

  it('copes with an empty stack', () => {
    const debug = tipsFor(challenge({ tech_stack: [] })).find((t) => t.id === 'debugging')!;
    expect(debug.prompt).toContain('my chosen stack');
  });

  it('links every tip to a real lesson', () => {
    for (const t of ASSIST_TIPS) expect(lessonById(t.lessonId)).not.toBeNull();
  });

  it('only has role guidance for tech roles', () => {
    expect(guidanceFor('15-2051.00')?.title).toBe('Data Scientists');
    expect(guidanceFor('43-3031.00')).toBeNull();
  });
});
