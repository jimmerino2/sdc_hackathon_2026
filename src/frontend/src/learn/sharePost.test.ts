import { describe, expect, it } from 'vitest';
import { draftText, hashtagFor, wrapLines } from './sharePost';

describe('the post draft', () => {
  const facts = { role: 'Software Developers', skills: 36, sections: 5 };

  it('says what the learner did, with their numbers and the hashtags', () => {
    const text = draftText(facts);
    expect(text).toContain('I just completed a Jobee learning roadmap for Software Developers');
    expect(text).toContain('36 skills across 5 sections');
    expect(text).toContain('#Jobee #SoftwareDevelopers #Upskilling');
  });

  it('never claims a certification or a qualification', () => {
    expect(draftText(facts).toLowerCase()).not.toMatch(/certif|qualif|accredit|verified/);
  });

  it('uses the singular for one', () => {
    expect(draftText({ role: 'Analyst', skills: 1, sections: 1 })).toContain('1 skill across 1 section,');
  });

  it('makes a hashtag out of a role title with punctuation', () => {
    expect(hashtagFor('Computer & Information Research Scientists')).toBe('ComputerInformationResearchScientists');
    expect(hashtagFor('')).toBe('');
    expect(draftText({ role: '', skills: 2, sections: 1 })).toContain('#Jobee #Upskilling');
  });
});

describe('wrapping a title on the image', () => {
  const measure = (s: string) => s.length * 10;

  it('keeps short text on one line', () => {
    expect(wrapLines('Data Analysts', measure, 500, 2)).toEqual(['Data Analysts']);
  });

  it('breaks at spaces to fit the width', () => {
    expect(wrapLines('Software Developers and Testers', measure, 170, 3)).toEqual(['Software', 'Developers and', 'Testers']);
  });

  it('ends with an ellipsis when it would need more lines than allowed', () => {
    const lines = wrapLines('Computer and Information Research Scientists Everywhere', measure, 200, 2);
    expect(lines).toHaveLength(2);
    expect(lines[1].endsWith('…')).toBe(true);
    expect(measure(lines[1])).toBeLessThanOrEqual(200);
  });

  it('puts one very long word on its own line instead of looping', () => {
    expect(wrapLines('Supercalifragilisticexpialidocious', measure, 100, 2)).toEqual(['Supercalifragilisticexpialidocious']);
  });
});
