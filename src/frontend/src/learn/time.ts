/** Time helpers for the Learn page (tested in time.test.ts). */

/** 45 -> "45 min", 180 -> "3 h", 95 -> "1 h 35 min"; over ten hours the minutes are dropped. */
export function formatMinutes(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return h >= 10 || rest === 0 ? `${h} h` : `${h} h ${rest} min`;
}

/** Whole weeks to cover `minutes` at `hoursPerWeek`; at least 1 when there is anything left, 0 when there is not. */
export function weeksFor(minutes: number, hoursPerWeek: number): number {
  if (minutes <= 0) return 0;
  return Math.max(1, Math.ceil(minutes / 60 / Math.max(1, hoursPerWeek)));
}

export const DEFAULT_HOURS_PER_WEEK = 5;
export const MIN_HOURS_PER_WEEK = 1;
export const MAX_HOURS_PER_WEEK = 40;
