import { describe, expect, it } from 'vitest';
import { mayCost, splitByCost } from './cost';

describe('which links are free', () => {
  it('calls free reading, video and docs free', () => {
    for (const url of [
      'https://elearningindustry.com/activities-that-will-enhance-your-employees-critical-thinking-skills-2',
      'https://www.youtube.com/watch?v=abc',
      'https://github.com/someone/repo',
      'https://learn.microsoft.com/en-us/training/',
      'https://dev.to/post',
    ]) expect(mayCost(url)).toBe(false);
  });

  it('flags the sites that sell courses and credentials, with or without www or a subdomain', () => {
    for (const url of [
      'https://www.coursera.org/learn/python',
      'https://coursera.org/learn/python',
      'https://www.udemy.com/course/x',
      'https://www.credly.com/org/aws',
      'https://www.edx.org/learn',
      'https://mylearn.oracle.com/ou/course',
      'https://learning.oreilly.com/library',
    ]) expect(mayCost(url)).toBe(true);
  });

  it('does not match a look-alike host', () => {
    expect(mayCost('https://notcoursera.org/x')).toBe(false);
    expect(mayCost('https://example.com/?next=https://coursera.org')).toBe(false);
  });

  it('survives a bad url', () => {
    expect(mayCost('not a url')).toBe(false);
  });

  it('splits a list and keeps the order', () => {
    const links = [{ url: 'https://youtube.com/a' }, { url: 'https://coursera.org/b' }, { url: 'https://dev.to/c' }];
    const { free, mayCost: paid } = splitByCost(links);
    expect(free.map((l) => l.url)).toEqual(['https://youtube.com/a', 'https://dev.to/c']);
    expect(paid.map((l) => l.url)).toEqual(['https://coursera.org/b']);
  });
});
