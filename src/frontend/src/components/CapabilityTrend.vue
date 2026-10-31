<script setup lang="ts">
import { computed } from 'vue';
import type { EngineDetail, TrendClass } from '../api/outlook';
import ChartHover, { type HoverPoint } from './ChartHover.vue';

/** Secondary output: the model-estimated underlying growth trend under the observed frontier, and whether it is
 *  speeding up. Kept visually and verbally apart from the observed-frontier forecast. */
const props = defineProps<{ detail: EngineDetail; unit: string }>();

const u = computed(() => props.detail.units[props.unit]);
const t = computed(() => u.value?.trend ?? null);
const scores = computed(() => props.detail.backtest.trend ?? []);

const W = 680, H = 230, L = 54, R = 14, T = 10, B = 30;
const FROM = '2023-01';
const mi = (p: string) => { const [y, m] = p.split('-').map(Number); return (y - 1970) * 12 + (m - 1); };
function dur(min: number): string {
  if (min < 90) return `${Math.round(min)} min`;
  const h = min / 60;
  return h < 10 ? `${h.toFixed(1)} h` : `${Math.round(h).toLocaleString('en')} h`;
}
const pct = (v: number | undefined) => (v == null ? '–' : `${Math.round(v * 100)}%`);
const f1 = (v: number | null | undefined) => (v == null ? '–' : v.toFixed(1));
const f2 = (v: number | null | undefined) => (v == null ? '–' : v.toFixed(2));

const c = computed(() => {
  const d = t.value;
  if (!d || !u.value) return null;
  const x0 = mi(FROM), x1 = mi(d.forecast[d.forecast.length - 1].period) + 1;
  const hist = d.history.filter((p) => mi(p.period) >= x0 && p.minutes != null);
  const front = u.value.frontier.filter((p) => mi(p.period) >= x0 && p.minutes != null);
  const ys = [...hist.flatMap((p) => [p.low!, p.high!]), ...front.map((p) => p.minutes!), ...d.forecast.flatMap((p) => [p.low, p.high])];
  const lo = Math.log2(Math.min(...ys)) - 0.3, hi = Math.log2(Math.max(...ys)) + 0.3;
  const sx = (m: number) => L + ((m - x0) / (x1 - x0)) * (W - L - R);
  const sy = (min: number) => T + (1 - (Math.log2(min) - lo) / (hi - lo)) * (H - T - B);
  const mid = (p: string) => mi(p) + 0.5;
  const line = (pts: { x: number; y: number }[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ');
  const band = (pts: { x: number; lo: number; hi: number }[]) =>
    `${line(pts.map((p) => ({ x: p.x, y: p.lo })))} ${[...pts].reverse().map((p) => `L${sx(p.x).toFixed(1)},${sy(p.hi).toFixed(1)}`).join(' ')} Z`;
  const steps = front.map((f) => `M${sx(mi(f.period)).toFixed(1)},${sy(f.minutes!).toFixed(1)} L${sx(mi(f.period) + 1).toFixed(1)},${sy(f.minutes!).toFixed(1)}`).join(' ');
  const lastH = hist[hist.length - 1];
  const fc = [{ x: mid(lastH.period), lo: lastH.low!, hi: lastH.high!, y: lastH.minutes! },
    ...d.forecast.map((p) => ({ x: mid(p.period), lo: p.low, hi: p.high, y: p.minutes }))];
  const yt: { y: number; t: string }[] = [];
  for (const [min, label] of [[1, '1 min'], [15, '15 min'], [60, '1 h'], [240, '4 h'], [960, '16 h'], [3840, '64 h'], [15360, '256 h']] as const) {
    if (Math.log2(min) >= lo && Math.log2(min) <= hi) yt.push({ y: sy(min), t: label });
  }
  const xt: { x: number; t: string }[] = [];
  for (let y = 2023; y <= 2028; y++) if ((y - 1970) * 12 >= x0 && (y - 1970) * 12 <= x1) xt.push({ x: sx((y - 1970) * 12), t: String(y) });
  // one hover stop per month: the measured frontier, the estimated trend and, after the split, its projection
  const hover: HoverPoint[] = [];
  const short = (p: string) => new Date(`${p}-01`).toLocaleDateString('en', { month: 'short', year: 'numeric' });
  for (const p of hist) {
    const f = front.find((q) => q.period === p.period);
    hover.push({
      x: sx(mid(p.period)), title: short(p.period),
      rows: [
        ...(f ? [{ label: 'Measured frontier', value: dur(f.minutes!), color: 'var(--ink)' }] : []),
        { label: 'Estimated trend', value: dur(p.minutes!), color: '#1f6f66' },
        { label: '80% band', value: `${dur(p.low!)}–${dur(p.high!)}`, muted: true },
        ...(p.pace_per_year != null ? [{ label: 'Growth then', value: `${f1(p.pace_per_year)} doublings/yr`, muted: true }] : []),
      ],
      dots: [...(f ? [{ y: sy(f.minutes!) }] : []), { y: sy(p.minutes!), color: '#1f6f66' }],
    });
  }
  for (const p of d.forecast) {
    hover.push({
      x: sx(mid(p.period)), title: `${short(p.period)} · projection`,
      rows: [{ label: 'Projected trend', value: dur(p.minutes), color: '#1f6f66' }, { label: '80% band', value: `${dur(p.low)}–${dur(p.high)}`, muted: true }],
      dots: [{ y: sy(p.minutes), color: '#1f6f66' }],
    });
  }
  return {
    hover, steps, smooth: line(hist.map((p) => ({ x: mid(p.period), y: p.minutes! }))),
    smoothBand: band(hist.map((p) => ({ x: mid(p.period), lo: p.low!, hi: p.high! }))),
    fcLine: line(fc), fcBand: band(fc), yt, xt, split: sx(mi(lastH.period) + 1),
  };
});

const CLS: { key: TrendClass; label: string; color: string }[] = [
  { key: 'accelerating', label: 'Speeding up', color: '#eb6834' },
  { key: 'stable', label: 'Steady', color: '#9e9a92' },
  { key: 'decelerating', label: 'Slowing down', color: '#2a78d6' },
];
const score = (h: number, role: string) => scores.value.find((s) => s.h === h && s.role === role);
const skill = (h: number, role: string) => {
  const s = score(h, role);
  if (!s?.n || s.brier_model == null) return null;
  return s.brier_model < (s.brier_uniform ?? 1) && s.brier_model < (s.brier_base_rate ?? 1);
};
const shown = computed(() => {
  const hs = t.value?.horizons.map((h) => h.h) ?? [];
  return { both: hs.filter((h) => skill(h, 'selection') && skill(h, 'holdout')), recent: hs.filter((h) => skill(h, 'holdout')),
           earlier: hs.filter((h) => skill(h, 'selection')) };
});
</script>

<template>
  <details v-if="t && c" class="tr">
    <summary>
      <span class="sum-h">Is the underlying trend speeding up?</span>
      <span class="tag">Secondary · model-estimated, not a measurement</span>
    </summary>
    <p class="lead">
      The measured frontier (black steps) jumps whenever a stronger model is measured. A smoothing model estimates the
      steadier trend underneath it (teal) and how fast that trend is growing. This is an estimate, so it has its own
      uncertainty, and it can differ from what the frontier itself does over the next few months.
    </p>
    <ChartHover :w="W" :h="H" :top="T" :bottom="H - B" :points="c.hover">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img"
         :aria-label="`Estimated underlying trend: growing ${f1(t.pace_now)} doublings a year now, ${f1(t.past_pace)} on average over the past year.`">
      <g v-for="y in c.yt" :key="y.t">
        <line :x1="L" :x2="W - R" :y1="y.y" :y2="y.y" class="grid" />
        <text :x="L - 6" :y="y.y + 4" text-anchor="end" class="tick">{{ y.t }}</text>
      </g>
      <g v-for="x in c.xt" :key="x.t"><text :x="x.x + 3" :y="H - B + 18" class="tick">{{ x.t }}</text></g>
      <line :x1="L" :x2="W - R" :y1="H - B" :y2="H - B" class="axis" />
      <line :x1="c.split" :x2="c.split" :y1="T" :y2="H - B" class="now" />
      <path :d="c.smoothBand" class="band" />
      <path :d="c.fcBand" class="band fc" />
      <path :d="c.steps" class="front" />
      <path :d="c.smooth" class="smooth" />
      <path :d="c.fcLine" class="smooth dashed" />
    </svg>
    </ChartHover>
    <p class="key">
      <span><i class="k-front" /> measured frontier</span>
      <span><i class="k-smooth" /> estimated trend (80% band)</span>
      <span><i class="k-fc" /> trend projection</span>
    </p>

    <p class="stat">
      Estimated growth now: <b>{{ f1(t.pace_now) }} doublings a year</b> (±{{ f1(t.pace_now_sd) }})<template v-if="t.doubling_months">, a doubling every
      {{ t.doubling_months.toFixed(1) }} months</template>. Past 12 months on average: {{ f1(t.past_pace) }}.
    </p>
    <ul class="hz">
      <li v-for="h in t.horizons" :key="h.h">
        <span class="when">Next {{ h.h }} months</span>
        <span class="stack" role="img" :aria-label="CLS.map((k) => `${k.label} ${pct(h.p[k.key])}`).join(', ')">
          <span v-for="k in CLS" v-show="h.p[k.key] > 0" :key="k.key" class="seg" :style="{ flexGrow: h.p[k.key], background: k.color }" />
        </span>
        <span class="lg">
          <span v-for="k in CLS" :key="k.key"><i class="sw" :style="{ background: k.color }" />{{ k.label }} <b>{{ pct(h.p[k.key]) }}</b></span>
        </span>
      </li>
    </ul>
    <p class="verdict" :class="shown.both.length ? 'ok' : 'warn'">
      <template v-if="shown.both.length === t.horizons.length">These trend chances beat both a ⅓ guess and past frequencies in earlier and recent tests.</template>
      <template v-else-if="shown.recent.length">
        Skill not established: these chances beat a ⅓ guess in the recent tests ({{ shown.recent.join(', ') }} months) but not in the earlier ones.
        Treat them as experimental.
      </template>
      <template v-else-if="shown.earlier.length">
        Skill not established: these chances beat a ⅓ guess in the earlier tests ({{ shown.earlier.join(', ') }} months) but did worse than
        guessing in the recent ones. Treat them as experimental, not as a finding that progress is slowing or speeding up.
      </template>
      <template v-else>Skill not established: in past tests these chances did not beat a plain ⅓ guess. Treat them as experimental.</template>
    </p>
    <details class="sc">
      <summary>Trend test results</summary>
      <p class="small">Scored against the same smoother run on today’s data (what the trend turned out to be). Pace errors in doublings a year;
        “keep last year’s pace” is the simple reference. Brier: 0 perfect, ⅓ guess 0.67.</p>
      <table>
        <thead><tr><th scope="col">Horizon</th><th scope="col">Tests</th><th scope="col">Pace error</th><th scope="col">Keep last year’s</th><th scope="col">Brier</th><th scope="col">⅓ guess</th><th scope="col">Past freq.</th></tr></thead>
        <tbody>
          <template v-for="h in t.horizons" :key="h.h">
            <tr v-for="role in ['selection', 'holdout']" :key="role">
              <td>{{ h.h }} mo, {{ role === 'holdout' ? 'recent' : 'earlier' }}</td>
              <td>{{ score(h.h, role)?.n ?? 0 }}</td>
              <td>{{ f2(score(h.h, role)?.mae_pace) }}</td>
              <td>{{ f2(score(h.h, role)?.mae_persistence) }}</td>
              <td :class="skill(h.h, role) ? 'okc' : ''">{{ f2(score(h.h, role)?.brier_model) }}</td>
              <td>{{ f2(score(h.h, role)?.brier_uniform) }}</td>
              <td>{{ f2(score(h.h, role)?.brier_base_rate) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </details>
  </details>
</template>

<style scoped>
.tr { border-top: 2px solid var(--line); padding-top: 12px; }
.tr > * + * { margin-top: 8px; }
.tr > summary { cursor: pointer; display: flex; flex-direction: column; gap: 2px; list-style: none; }
.tr > summary::-webkit-details-marker { display: none; }
.sum-h { font-size: 16px; font-weight: 800; }
.sum-h::before { content: '+ '; color: var(--orange); font-weight: 900; }
.tr[open] .sum-h::before { content: '− '; }
.tag { font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: #1f6f66; }
h3 { font-size: 16px; }
.lead, .stat { font-size: 14px; line-height: 1.5; }
.lead { color: var(--muted); }
svg { width: 100%; height: auto; display: block; }
.grid { stroke: var(--line); stroke-width: 1; }
.axis { stroke: var(--line-strong); stroke-width: 1; }
.tick { font-size: 11px; fill: var(--muted); }
.now { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 3; }
.band { fill: #1f6f66; opacity: .14; }
.band.fc { opacity: .08; }
.front { fill: none; stroke: var(--ink); stroke-width: 2; }
.smooth { fill: none; stroke: #1f6f66; stroke-width: 2.5; }
.smooth.dashed { stroke-dasharray: 6 4; }
.key { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13px; font-weight: 700; color: var(--muted); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.key i { display: inline-block; width: 16px; }
.k-front { border-top: 2px solid var(--ink); }
.k-smooth { height: 8px; background: rgba(31, 111, 102, .18); border-top: 2.5px solid #1f6f66; }
.k-fc { border-top: 2.5px dashed #1f6f66; }
.hz { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.hz li { display: flex; flex-direction: column; gap: 4px; }
.when { font-size: 14px; font-weight: 800; }
.stack { display: flex; gap: 2px; height: 10px; }
.seg { border-radius: 4px; min-width: 4px; }
.lg { display: flex; flex-wrap: wrap; gap: 2px 12px; font-size: 14px; font-weight: 700; color: var(--muted); }
.lg b { color: var(--ink); }
.sw { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
.verdict { font-size: 14px; font-weight: 700; line-height: 1.45; }
.verdict.ok { color: #1e5e30; }
.verdict.warn { color: var(--amber-ink); }
.sc { font-size: 14px; }
.sc summary { cursor: pointer; font-weight: 800; }
.small { color: var(--muted); line-height: 1.45; margin: 4px 0; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 14px; }
th, td { text-align: right; padding: 4px 6px; border-bottom: 1px solid var(--line); }
th:first-child, td:first-child { text-align: left; }
th { font-weight: 800; color: var(--muted); font-size: 13px; }
.okc { color: #1e5e30; font-weight: 800; }
</style>
