/** Pure helpers for the occupational forecasting page (tested in format.test.ts). */

export const pct = (v: number | null | undefined, digits = 1): string =>
  v == null || Number.isNaN(v) ? '–' : `${(v * 100).toFixed(digits)}%`;

export const pp = (v: number | null | undefined, digits = 1): string =>
  v == null || Number.isNaN(v) ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(digits)} pp`;

/** '2026-09' -> 'Sep 2026'. */
export function month(m: string | null | undefined): string {
  if (!m || !/^\d{4}-\d{2}/.test(m)) return m ?? '–';
  const d = new Date(`${m.slice(0, 7)}-01T00:00:00Z`);
  return d.toLocaleDateString('en', { month: 'short', year: 'numeric', timeZone: 'UTC' });
}

/** '2026-10-09' -> '9 Oct 2026'. */
export function day(d: string | null | undefined): string {
  if (!d || !/^\d{4}-\d{2}-\d{2}/.test(d)) return d ?? '–';
  return new Date(`${d.slice(0, 10)}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

export const METHOD_NAMES: Record<string, string> = {
  persistence: '“No change” (last 3 months)',
  mean12: 'Last 12 months’ average',
  shrink: 'Recent share, steadied by the 12-month average',
  trend: 'Damped trend',
  ridge: 'Ridge regression (pooled)',
  blend: 'Average of steadied share and ridge',
  ewma: 'Recent share, weighted toward the latest months',
  dtrend: 'Damped trend (shrunk by evidence)',
  adaptive: 'Recent share plus tested trend',
};
export const methodName = (m: string) => METHOD_NAMES[m] ?? m;

export const STATUS_TEXT: Record<string, string> = {
  validated: 'Beat “no change” by 5% or more on the held-back test period',
  not_demonstrably_better: 'Chosen on validation; on the test period it was no worse than “no change”, but not 5% better',
  baseline_retained: 'Chosen method lost to “no change” on the test period, so “no change” is shown',
  baseline: '“No change” was the best method on validation',
};

export const TAXONOMY_TEXT: Record<string, string> = {
  known: 'Known',
  newly_detected: 'Newly detected',
  under_review: 'Under review',
  merged: 'Merged',
  deprecated: 'Deprecated',
};

/** Rising / falling over the last 6 months vs the 12 before, only when the 80% band excludes zero. */
export function trendOf(lb: number | null | undefined, ub: number | null | undefined): 'up' | 'down' | 'flat' {
  if (lb != null && lb > 0) return 'up';
  if (ub != null && ub < 0) return 'down';
  return 'flat';
}

/** A log growth (e.g. 0.4) as a percentage change string (+49%). */
export function growth(g: number | null | undefined): string {
  if (g == null || !Number.isFinite(g)) return '–';
  const v = (Math.exp(g) - 1) * 100;
  return `${v > 0 ? '+' : ''}${Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)}%`;
}

/** Scenario (not a forecast): the forecast share moved by `passThrough` (0-1) of a log-odds growth `g`. */
export function scenarioShare(forecast: number, g: number, passThrough: number): number {
  const p = Math.min(Math.max(forecast, 1e-4), 1 - 1e-4);
  const z = Math.log(p / (1 - p)) + passThrough * g;
  return 1 / (1 + Math.exp(-z));
}

/** Linear scale with a little padding; returns [scale, lo, hi]. */
export function linear(values: number[], from: number, to: number, pad = 0.06): [(v: number) => number, number, number] {
  const finite = values.filter((v) => Number.isFinite(v));
  let lo = Math.min(0, ...finite);
  let hi = Math.max(...finite, 0.01);
  const span = hi - lo || 1;
  hi += span * pad;
  if (lo < 0) lo -= span * pad;
  return [(v: number) => from + ((v - lo) / (hi - lo)) * (to - from), lo, hi];
}

/** Round tick values covering [lo, hi] (shares 0-1), about n of them. */
export function ticks(lo: number, hi: number, n = 4): number[] {
  const raw = (hi - lo) / n;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(Number(t.toFixed(10)));
  return out;
}

/** 'YYYY-MM' + k months. */
export function addMonths(m: string, k: number): string {
  const [y, mo] = m.split('-').map(Number);
  const t = y * 12 + (mo - 1) + k;
  return `${Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, '0')}`;
}

export function monthsBetween(a: string, b: string): number {
  const [ya, ma] = a.split('-').map(Number);
  const [yb, mb] = b.split('-').map(Number);
  return (yb - ya) * 12 + (mb - ma);
}
