import { beforeEach, describe, expect, it, vi } from 'vitest';

function fakeStorage(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  };
}

/** A fresh copy of the module, which reads storage once on load. */
async function load(storage: unknown) {
  vi.stubGlobal('localStorage', storage);
  vi.resetModules();
  return import('./aiProgress');
}

describe('AI Fluency progress', () => {
  beforeEach(() => vi.unstubAllGlobals());

  it('marks a lesson done and undoes it', async () => {
    const p = await load(fakeStorage());
    p.toggleLesson('p1', 'a');
    expect(p.completedLessons('p1')).toEqual(['a']);
    p.toggleLesson('p1', 'a');
    expect(p.completedLessons('p1')).toEqual([]);
  });

  it('keeps each profile’s lessons apart', async () => {
    const p = await load(fakeStorage());
    p.toggleLesson('p1', 'a');
    expect(p.completedLessons('p2')).toEqual([]);
    expect(p.completedLessons(null)).toEqual([]);
  });

  it('survives a reload', async () => {
    const storage = fakeStorage();
    const first = await load(storage);
    first.toggleLesson('p1', 'a');
    first.saveReflection('c1', { used: 'tests' });
    const second = await load(storage);
    expect(second.completedLessons('p1')).toEqual(['a']);
    expect(second.reflectionFor('c1').used).toBe('tests');
  });

  it('merges reflection answers', async () => {
    const p = await load(fakeStorage());
    p.saveReflection('c1', { used: 'tests' });
    p.saveReflection('c1', { changed: 'dropped a dependency' });
    expect(p.reflectionFor('c1')).toEqual({ used: 'tests', changed: 'dropped a dependency' });
  });

  it('ignores corrupt saved data', async () => {
    const p = await load(fakeStorage({ jobee_ai_lessons: '{oops', jobee_ai_reflections: '[1]' }));
    expect(p.completedLessons('p1')).toEqual([]);
    expect(p.reflectionFor('c1')).toEqual({});
  });

  it('keeps working when storage is blocked', async () => {
    const p = await load({ getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } });
    p.toggleLesson('p1', 'a');
    expect(p.completedLessons('p1')).toEqual(['a']);
  });
});
