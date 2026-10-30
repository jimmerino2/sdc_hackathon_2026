import { describe, expect, it } from 'vitest';
import { displayName, findKeywords } from './resumeKeywords';

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
