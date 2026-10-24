import { describe, expect, it } from 'vitest';
import { addMonths, linear, month, monthsBetween, pct, pp, ticks, trendOf } from './format';

describe('occupational format helpers', () => {
  it('formats shares and point changes, with a dash for missing values', () => {
    expect(pct(0.1234)).toBe('12.3%');
    expect(pct(null)).toBe('–');
    expect(pp(1.25)).toBe('+1.3 pp');
    expect(pp(-0.5)).toBe('-0.5 pp');
    expect(pp(undefined)).toBe('–');
  });

  it('formats months', () => {
    expect(month('2026-09')).toBe('Sep 2026');
    expect(month(null)).toBe('–');
  });

  it('calls a trend only when the band excludes zero', () => {
    expect(trendOf(0.2, 3)).toBe('up');
    expect(trendOf(-3, -0.1)).toBe('down');
    expect(trendOf(-1, 1)).toBe('flat');
    expect(trendOf(null, null)).toBe('flat');
  });

  it('does month arithmetic across years', () => {
    expect(addMonths('2026-11', 3)).toBe('2027-02');
    expect(addMonths('2026-01', -1)).toBe('2025-12');
    expect(monthsBetween('2025-10', '2026-09')).toBe(11);
  });

  it('builds a scale that starts at zero and covers the data', () => {
    const [s, lo, hi] = linear([0.1, 0.3], 0, 100);
    expect(lo).toBe(0);
    expect(hi).toBeGreaterThan(0.3);
    expect(s(0)).toBe(0);
    expect(s(hi)).toBeCloseTo(100);
  });

  it('picks round ticks', () => {
    expect(ticks(0, 0.32)).toEqual([0, 0.1, 0.2, 0.3]);
  });
});
