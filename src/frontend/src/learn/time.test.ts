import { describe, expect, it } from 'vitest';
import { formatMinutes, weeksFor } from './time';

describe('learning time helpers', () => {
  it('writes minutes the way a person would say them', () => {
    expect(formatMinutes(45)).toBe('45 min');
    expect(formatMinutes(180)).toBe('3 h');
    expect(formatMinutes(95)).toBe('1 h 35 min');
    expect(formatMinutes(14 * 60 + 20)).toBe('14 h');
    expect(formatMinutes(-5)).toBe('0 min');
  });

  it('turns time left and hours per week into whole weeks', () => {
    expect(weeksFor(0, 5)).toBe(0);
    expect(weeksFor(30, 5)).toBe(1);
    expect(weeksFor(60 * 38, 5)).toBe(8);
    expect(weeksFor(60 * 10, 0)).toBe(10); // hours per week is never below 1
  });
});
