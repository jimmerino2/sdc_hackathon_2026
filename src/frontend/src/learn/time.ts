/** Time helpers for the Learn page (tested in time.test.ts). */

/** 45 -> "45 min", 180 -> "3 h", 95 -> "1 h 35 min"; over ten hours the minutes are dropped. */
export function formatMinutes(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return h >= 10 || rest === 0 ? `${h} h` : `${h} h ${rest} min`;
}
