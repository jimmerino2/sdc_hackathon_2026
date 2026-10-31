import { describe, expect, it } from 'vitest';
import type { QuarterInfo } from '../api/forecast';
import { byYear, excludeAll, excludeAllBut, excludeBefore, formatSkip, keptCount, parseSkip, quarterSpan, rangeBetween, sameSet, toggleQuarter, toggleYear, yearSpan, yearState } from './quarterPick';

const q = (quarter: string): QuarterInfo => ({ quarter, months: 3, first_month: '', last_month: '', has_outcome: true });
const QUARTERS = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2025-Q1', '2025-Q2', '2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2', '2026-Q3'].map(q);

describe('quarter picking', () => {
  it('groups by year, newest first, with a gap where a quarter has no data', () => {
    const rows = byYear(QUARTERS);
    expect(rows.map((r) => r.year)).toEqual(['2026', '2025', '2024']);
    expect(rows[0].quarters.map((x) => x?.quarter ?? null)).toEqual(['2026-Q1', '2026-Q2', '2026-Q3', null]);
  });

  it('toggles a single quarter either way', () => {
    const off = toggleQuarter(new Set(), '2025-Q2');
    expect([...off]).toEqual(['2025-Q2']);
    expect(toggleQuarter(off, '2025-Q2').size).toBe(0);
  });

  it('a year button leaves a whole year out, and brings back a partly or fully left-out year', () => {
    const out = toggleYear('2025', QUARTERS, new Set());
    expect([...out].sort()).toEqual(['2025-Q1', '2025-Q2', '2025-Q3', '2025-Q4']);
    expect(yearState('2025', QUARTERS, out)).toBe('none');
    expect(toggleYear('2025', QUARTERS, out).size).toBe(0);
    const some = new Set(['2025-Q2']);
    expect(yearState('2025', QUARTERS, some)).toBe('some');
    expect(toggleYear('2025', QUARTERS, some).size).toBe(0); // a partly kept year comes back whole
  });

  it('only counts the quarters a year really has', () => {
    const out = toggleYear('2026', QUARTERS, new Set());
    expect([...out].sort()).toEqual(['2026-Q1', '2026-Q2', '2026-Q3']);
    expect(yearState('2026', QUARTERS, out)).toBe('none');
  });

  it('leaves out everything before a year', () => {
    expect([...excludeBefore(2025, QUARTERS)].sort()).toEqual(['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4']);
    expect(keptCount(QUARTERS, excludeBefore(2025, QUARTERS))).toBe(7);
  });

  it('writes a choice for the address, a whole year as its number', () => {
    const excluded = new Set(['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2026-Q3']);
    expect(formatSkip(excluded, QUARTERS)).toBe('2024,2026-Q3');
    expect(formatSkip(new Set(), QUARTERS)).toBeNull();
  });

  it('reads it back, ignoring what isn’t in the data', () => {
    expect([...parseSkip('2024,2026-Q3', QUARTERS)].sort()).toEqual(['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2026-Q3']);
    expect(parseSkip('1999,2030-Q1,nonsense,', QUARTERS).size).toBe(0);
    expect(parseSkip(null, QUARTERS).size).toBe(0);
  });

  describe('picking a range', () => {
    const span = (x: string | number, qs = QUARTERS) => (typeof x === 'number' ? { lo: x, hi: x } : quarterSpan(x, qs)!);

    it('finds where a quarter or a year sits', () => {
      expect(quarterSpan('2025-Q1', QUARTERS)).toEqual({ lo: 4, hi: 4 });
      expect(yearSpan('2025', QUARTERS)).toEqual({ lo: 4, hi: 7 });
      expect(yearSpan('2026', QUARTERS)).toEqual({ lo: 8, hi: 10 });
      expect(quarterSpan('1999-Q1', QUARTERS)).toBeNull();
      expect(yearSpan('1999', QUARTERS)).toBeNull();
    });

    it('covers the quarters between two quarters, in either order', () => {
      expect(rangeBetween(span('2024-Q4'), span('2025-Q2'), QUARTERS)).toEqual(['2024-Q4', '2025-Q1', '2025-Q2']);
      expect(rangeBetween(span('2025-Q2'), span('2024-Q4'), QUARTERS)).toEqual(['2024-Q4', '2025-Q1', '2025-Q2']);
      expect(rangeBetween(span('2025-Q1'), span('2025-Q1'), QUARTERS)).toEqual(['2025-Q1']);
    });

    it('a year as the start or the end takes in all its quarters', () => {
      const y = (year: string) => yearSpan(year, QUARTERS)!;
      expect(rangeBetween(y('2024'), y('2025'), QUARTERS)).toHaveLength(8);
      expect(rangeBetween(y('2025'), y('2024'), QUARTERS)).toHaveLength(8);
      // a year to a quarter reaches the near edge of the year on the far side
      expect(rangeBetween(y('2024'), span('2025-Q2'), QUARTERS)).toEqual(['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2025-Q1', '2025-Q2']);
      expect(rangeBetween(y('2026'), span('2025-Q3'), QUARTERS)).toEqual(['2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2', '2026-Q3']);
    });

    it('turns a kept range into the quarters to leave out', () => {
      const out = excludeAllBut(['2024-Q4', '2025-Q1'], QUARTERS);
      expect(out.size).toBe(9);
      expect(out.has('2024-Q4') || out.has('2025-Q1')).toBe(false);
      expect(keptCount(QUARTERS, out)).toBe(2);
    });

    it('leaves everything out, and compares sets', () => {
      expect(keptCount(QUARTERS, excludeAll(QUARTERS))).toBe(0);
      expect(sameSet(new Set(['a', 'b']), new Set(['b', 'a']))).toBe(true);
      expect(sameSet(new Set(['a']), new Set(['a', 'b']))).toBe(false);
    });
  });
});
