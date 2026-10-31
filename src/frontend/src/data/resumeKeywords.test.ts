import { describe, expect, it } from 'vitest';
import { displayName, findKeywords, limitInferred, MAX_INFERRED } from './resumeKeywords';

const keys = (text: string) => findKeywords(text).map((h) => h.key);

describe('findKeywords', () => {
  it('does not match Java inside JavaScript, or SQL inside NoSQL', () => {
    expect(keys('Built apps in JavaScript and NoSQL stores')).toEqual(['JavaScript']);
  });

  it('prefers the longest alias and maps aliases to one display name', () => {
    expect(keys('Amazon Web Services, AWS, RESTful API, REST')).toEqual(['AWS', 'AWS', 'REST APIs', 'REST APIs']);
  });

  it('matches case-insensitively and reports the offsets of the matched text', () => {
    const [hit] = findKeywords('Used postgres daily');
    expect(hit).toEqual({ key: 'PostgreSQL', start: 5, end: 13 });
  });

  it('handles symbols in names', () => {
    expect(keys('C++, C# and CI/CD with .NET')).toEqual(['C++', 'C#', 'CI/CD', '.NET']);
  });
});

describe('limitInferred', () => {
  const skills = ['Python', 'Programming', 'Docker', 'Linux', 'Git', 'Agile', 'Scrum', 'Jira', 'Figma'].map((name) => ({ name }));

  it('keeps named skills and only the strongest inferred ones', () => {
    const kept = limitInferred(skills, { counts: { Python: 2 }, text: 'python' }).map((s) => s.name);
    expect(kept).toEqual(['Python', 'Programming', 'Docker', 'Linux', 'Git', 'Agile']);
    expect(kept.length - 1).toBe(MAX_INFERRED);
  });

  it('does not count a skill written in the resume but missing from the keyword list as inferred', () => {
    const kept = limitInferred(skills, { counts: {}, text: 'figma, jira and scrum' }).map((s) => s.name);
    expect(kept).toEqual(expect.arrayContaining(['Figma', 'Jira', 'Scrum']));
    expect(kept).toHaveLength(MAX_INFERRED + 3);
  });
});

describe('displayName', () => {
  it.each([
    ['Amazon Web Services AWS software', 'AWS'],
    ['Structured query language SQL', 'SQL'],
    ['RESTful API', 'REST APIs'],
    ['Oracle Java', 'Java'],
    ['Microsoft Azure software', 'Azure'],
    ['Amazon Redshift', 'Redshift'],
    ['Programming', 'Programming'],
  ])('%s -> %s', (api, shown) => expect(displayName(api)).toBe(shown));
});
