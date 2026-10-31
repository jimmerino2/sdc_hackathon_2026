import { describe, expect, it } from 'vitest';
import { formatMinutes } from './time';

describe('learning time helpers', () => {
  it('writes minutes the way a person would say them', () => {
    expect(formatMinutes(45)).toBe('45 min');
    expect(formatMinutes(180)).toBe('3 h');
    expect(formatMinutes(95)).toBe('1 h 35 min');
    expect(formatMinutes(14 * 60 + 20)).toBe('14 h');
    expect(formatMinutes(-5)).toBe('0 min');
  });

});
