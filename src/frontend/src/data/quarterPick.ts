import type { QuarterInfo } from '../api/forecast';

/** One year of the picker: its four quarters, null where the data has none (yet). */
export interface YearRow {
  year: string;
  quarters: (QuarterInfo | null)[];
}

export type YearState = 'all' | 'some' | 'none';

/** The quarters grouped by year, newest year first. */
export function byYear(quarters: QuarterInfo[]): YearRow[] {
  const years = [...new Set(quarters.map((q) => q.quarter.slice(0, 4)))].sort().reverse();
  return years.map((year) => ({
    year,
    quarters: [1, 2, 3, 4].map((n) => quarters.find((q) => q.quarter === `${year}-Q${n}`) ?? null),
  }));
}

const inYear = (year: string, quarters: QuarterInfo[]) => quarters.filter((q) => q.quarter.startsWith(year)).map((q) => q.quarter);

/** Whether all, some or none of a year's quarters are kept. */
export function yearState(year: string, quarters: QuarterInfo[], excluded: ReadonlySet<string>): YearState {
  const mine = inYear(year, quarters);
  const left = mine.filter((q) => excluded.has(q)).length;
  return left === 0 ? 'all' : left === mine.length ? 'none' : 'some';
}

export function toggleQuarter(excluded: ReadonlySet<string>, quarter: string): Set<string> {
  const next = new Set(excluded);
  if (!next.delete(quarter)) next.add(quarter);
  return next;
}

/** A year with every quarter kept is left out whole; any other state brings the whole year back. */
export function toggleYear(year: string, quarters: QuarterInfo[], excluded: ReadonlySet<string>): Set<string> {
  const next = new Set(excluded);
  const mine = inYear(year, quarters);
  if (yearState(year, quarters, excluded) === 'all') mine.forEach((q) => next.add(q));
  else mine.forEach((q) => next.delete(q));
  return next;
}

/** Leave out every quarter before `year` (the pandemic years, say). */
export function excludeBefore(year: number, quarters: QuarterInfo[]): Set<string> {
  return new Set(quarters.filter((q) => Number(q.quarter.slice(0, 4)) < year).map((q) => q.quarter));
}

/** How many quarters are kept. */
export const keptCount = (quarters: QuarterInfo[], excluded: ReadonlySet<string>): number => quarters.filter((q) => !excluded.has(q.quarter)).length;

/** The address form of a choice: "2020,2021,2026-Q3" (a whole year by its number, otherwise single quarters); null for none. */
export function formatSkip(excluded: ReadonlySet<string>, quarters: QuarterInfo[]): string | null {
  const tokens: string[] = [];
  for (const row of byYear(quarters).reverse()) {
    const mine = inYear(row.year, quarters);
    if (mine.every((q) => excluded.has(q))) tokens.push(row.year);
    else tokens.push(...mine.filter((q) => excluded.has(q)));
  }
  return tokens.length ? tokens.join(',') : null;
}

/** The reverse of formatSkip. Anything that isn't a year or a quarter in the data is ignored. */
export function parseSkip(param: string | null | undefined, quarters: QuarterInfo[]): Set<string> {
  const out = new Set<string>();
  for (const token of (param ?? '').split(',').map((t) => t.trim())) {
    if (/^\d{4}$/.test(token)) inYear(token, quarters).forEach((q) => out.add(q));
    else if (quarters.some((q) => q.quarter === token)) out.add(token);
  }
  return out;
}

/** Where a quarter, or a whole year, sits in the list of quarters: the first and last index it covers. */
export interface Span {
  lo: number;
  hi: number;
}

export function quarterSpan(quarter: string, quarters: QuarterInfo[]): Span | null {
  const i = quarters.findIndex((q) => q.quarter === quarter);
  return i < 0 ? null : { lo: i, hi: i };
}

export function yearSpan(year: string, quarters: QuarterInfo[]): Span | null {
  const idx = quarters.map((q, i) => (q.quarter.startsWith(year) ? i : -1)).filter((i) => i >= 0);
  return idx.length ? { lo: idx[0], hi: idx[idx.length - 1] } : null;
}

/** The quarters from one end of a range to the other, in either order. A year reaches from its first quarter to its last. */
export function rangeBetween(a: Span, b: Span, quarters: QuarterInfo[]): string[] {
  const lo = Math.min(a.lo, b.lo);
  const hi = Math.max(a.hi, b.hi);
  return quarters.slice(lo, hi + 1).map((q) => q.quarter);
}

/** Leave out everything except `kept`. */
export function excludeAllBut(kept: Iterable<string>, quarters: QuarterInfo[]): Set<string> {
  const keep = new Set(kept);
  return new Set(quarters.filter((q) => !keep.has(q.quarter)).map((q) => q.quarter));
}

export const excludeAll = (quarters: QuarterInfo[]): Set<string> => new Set(quarters.map((q) => q.quarter));

export const sameSet = (a: ReadonlySet<string>, b: ReadonlySet<string>): boolean => a.size === b.size && [...a].every((x) => b.has(x));
