import { describe, expect, it } from 'vitest';
import { AI_LESSONS, AI_ROLE_CODES, lessonById, nextLesson, ROLE_AI_GUIDANCE } from './aiFluency';

describe('AI Fluency curriculum', () => {
  it('has the five planned lessons, each with a unique id', () => {
    expect(AI_LESSONS).toHaveLength(5);
    expect(new Set(AI_LESSONS.map((l) => l.id)).size).toBe(5);
  });

  it.each(AI_LESSONS.map((l) => [l.title, l] as const))('%s teaches, demonstrates, and says how to check', (_, l) => {
    expect(l.objectives.length).toBeGreaterThan(0);
    expect(l.why.length).toBeGreaterThan(0);
    expect(l.sections.length).toBeGreaterThan(0);
    expect(l.examples.length).toBeGreaterThan(0);
    expect(l.templates.length).toBeGreaterThan(0);
    expect(l.exercise.steps.length).toBeGreaterThan(0);
    expect(l.exercise.doneWhen).toBeTruthy();
    expect(l.checklist.length).toBeGreaterThan(0);
    expect(l.reading.length).toBeGreaterThan(0);
    expect(l.minutes).toBeGreaterThan(0);
    for (const r of l.reading) expect(r.url).toMatch(/^https:\/\//);
  });

  it('gives guidance for all eight tech roles, pointing at lessons that exist', () => {
    expect(Object.keys(ROLE_AI_GUIDANCE).sort()).toEqual([...AI_ROLE_CODES].sort());
    for (const g of Object.values(ROLE_AI_GUIDANCE)) {
      expect(g.skills.length).toBeGreaterThan(0);
      for (const id of g.lessons) expect(lessonById(id)).not.toBeNull();
    }
  });

  it('walks to the next lesson and stops at the last', () => {
    expect(nextLesson('prompting-fundamentals')?.id).toBe('context-engineering');
    expect(nextLesson(AI_LESSONS.at(-1)!.id)).toBeNull();
    expect(nextLesson('nope')).toBeNull();
  });
});
