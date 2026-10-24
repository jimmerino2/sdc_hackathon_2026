<script setup lang="ts">
import { computed } from 'vue';
import type { EngineUnit } from '../api/outlook';
import ChartHover, { type HoverPoint } from './ChartHover.vue';

/** Time-horizon chart: measured models, bridged estimates, the measured frontier and the forecast fan (log scale). */
const props = defineProps<{ unit: EngineUnit; saturationHours: number; lagMonths: number }>();

const W = 680, H = 300, L = 54, R = 14, T = 12, B = 34;
const FROM = '2023-01';

const mi = (d: string) => { const [y, m, day] = d.split('-').map(Number); return (y - 1970) * 12 + (m - 1) + ((day ?? 1) - 1) / 30.4; };
const monthEnd = (p: string) => mi(`${p}-01`) + 1;
const short = (p: string) => new Date(`${p.slice(0, 7)}-01`).toLocaleDateString('en', { month: 'short', year: 'numeric' });
function dur(min: number): string {
  if (min < 1) return `${Math.round(min * 60)} s`;
  if (min < 90) return `${Math.round(min)} min`;
  const h = min / 60;
  return h < 10 ? `${h.toFixed(1)} h` : `${Math.round(h).toLocaleString('en')} h`;
}

const c = computed(() => {
  const u = props.unit;
  const x0 = mi(`${FROM}-01`);
  const x1 = monthEnd(u.fan[u.fan.length - 1].period);
  const inRange = (p: { release_date: string }) => mi(p.release_date) >= x0;
  const obs = u.observed.filter(inRange);
  const bri = u.bridged.filter(inRange);
  const ys = [...obs.map((p) => p.minutes), ...bri.map((p) => p.minutes), ...u.fan.flatMap((f) => [f.q10, f.q90])];
  const lo = Math.log2(Math.max(Math.min(...ys), 0.5)) - 0.4, hi = Math.log2(Math.max(...ys)) + 0.3;
  const sx = (m: number) => L + ((m - x0) / (x1 - x0)) * (W - L - R);
  const sy = (min: number) => T + (1 - (Math.log2(min) - lo) / (hi - lo)) * (H - T - B);

  // measured frontier as a staircase (gaps where no recent measured model exists)
  const steps: string[] = [];
  let pen = false;
  for (const f of u.frontier) {
    const a = mi(`${f.period}-01`);
    if (a + 1 < x0) continue;
    if (f.minutes == null) { pen = false; continue; }
    const y = sy(f.minutes).toFixed(1);
    steps.push(`${pen ? 'L' : 'M'}${sx(Math.max(a, x0)).toFixed(1)},${y} L${sx(a + 1).toFixed(1)},${y}`);
    pen = true;
  }

  // forecast fan from the end of the last complete month, starting at today's frontier
  const last = monthEnd(u.last_period);
  const pts = [{ x: last, q10: u.current_minutes, q25: u.current_minutes, q50: u.current_minutes, q75: u.current_minutes, q90: u.current_minutes },
    ...u.fan.map((f) => ({ x: monthEnd(f.period), ...f }))];
  const band = (a: 'q10' | 'q25', b: 'q90' | 'q75') =>
    `M${pts.map((p) => `${sx(p.x).toFixed(1)},${sy(p[a]).toFixed(1)}`).join(' L')} L${[...pts].reverse().map((p) => `${sx(p.x).toFixed(1)},${sy(p[b]).toFixed(1)}`).join(' L')} Z`;
  const median = `M${pts.map((p) => `${sx(p.x).toFixed(1)},${sy(p.q50).toFixed(1)}`).join(' L')}`;
  const marks = u.horizons.map((h) => ({ h: h.h, x: sx(monthEnd(h.target_period)), y: sy(h.median_minutes), v: h.median_minutes, p: h.target_period }));

  const yt: { y: number; t: string }[] = [];
  for (const [min, t] of [[1, '1 min'], [4, '4 min'], [15, '15 min'], [60, '1 h'], [240, '4 h'], [960, '16 h'], [3840, '64 h'], [15360, '256 h'], [61440, '1,024 h']] as const) {
    if (Math.log2(min) >= lo && Math.log2(min) <= hi) yt.push({ y: sy(min), t });
  }
  const xt: { x: number; t: string }[] = [];
  for (let y = 2023; y <= 2028; y++) {
    const m = (y - 1970) * 12;
    if (m >= x0 && m <= x1) xt.push({ x: sx(m), t: String(y) });
  }
  const sat = props.saturationHours * 60;
  return {
    sx, sy, obs, bri, steps: steps.join(' '), outer: band('q10', 'q90'), inner: band('q25', 'q75'), median, marks, yt, xt,
    lastX: sx(last), lagX: sx(last + props.lagMonths), sat: Math.log2(sat) <= hi && Math.log2(sat) >= lo ? sy(sat) : null,
    hidden: u.observed.length - obs.length,
  };
});

/** One hover stop per month: the best measured so far, models released that month, or the forecast. */
const hover = computed<HoverPoint[]>(() => {
  const u = props.unit, { sx, sy, obs, bri } = c.value;
  const x0 = mi(`${FROM}-01`), last = monthEnd(u.last_period);
  const out: HoverPoint[] = [];
  for (const f of u.frontier) {
    const a = mi(`${f.period}-01`);
    if (a < x0) continue;
    const released = [...obs, ...bri].filter((p) => p.release_date.startsWith(f.period));
    const rows = [];
    if (f.minutes != null) rows.push({ label: `Best so far${f.model ? ` (${f.model})` : ''}`, value: dur(f.minutes), color: 'var(--ink)' });
    for (const p of released) rows.push({ label: `${p.model}${p.layer === 'bridged' ? ' (bridged)' : ''}`, value: dur(p.minutes), muted: true });
    if (a + 1 > last) rows.push({ label: 'Still being measured', value: '', muted: true });
    if (!rows.length) continue;
    out.push({
      x: sx(a + 0.5), title: short(f.period), rows,
      dots: [...(f.minutes != null ? [{ y: sy(f.minutes) }] : []), ...released.map((p) => ({ y: sy(p.minutes), color: '#c9c4ba' }))],
    });
  }
  for (const f of u.fan) {
    const hz = u.horizons.find((h) => h.target_period === f.period);
    out.push({
      x: sx(monthEnd(f.period)), title: `${short(f.period)}${hz ? ` · ${hz.h}-month forecast` : ' · forecast'}`,
      rows: [
        { label: 'Median', value: dur(f.q50), color: 'var(--amber-ink)' },
        { label: '50% range', value: `${dur(f.q25)}–${dur(f.q75)}` },
        { label: '80% range', value: `${dur(f.q10)}–${dur(f.q90)}`, muted: true },
      ],
      dots: [{ y: sy(f.q50), color: 'var(--amber-ink)' }],
    });
  }
  return out;
});

const label = computed(() => {
  const u = props.unit;
  const h = u.horizons.map((x) => `${x.h} months: ${dur(x.median_minutes)}`).join(', ');
  return `Time horizon of the best measured AI model, ${short(FROM)} to ${short(u.fan[u.fan.length - 1].period)}, log scale. Latest ${dur(u.current_minutes)} (${u.current_model}). Forecast medians: ${h}.`;
});
</script>

<template>
  <figure class="cc">
    <ChartHover :w="W" :h="H" :top="T" :bottom="H - B" :points="hover">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="label">
      <g v-for="t in c.yt" :key="t.t">
        <line :x1="L" :x2="W - R" :y1="t.y" :y2="t.y" class="grid" />
        <text :x="L - 6" :y="t.y + 4" text-anchor="end" class="tick">{{ t.t }}</text>
      </g>
      <g v-for="t in c.xt" :key="t.t">
        <line :x1="t.x" :x2="t.x" :y1="H - B" :y2="H - B + 5" class="axis" />
        <text :x="t.x + 3" :y="H - B + 18" class="tick">{{ t.t }}</text>
      </g>
      <line :x1="L" :x2="W - R" :y1="H - B" :y2="H - B" class="axis" />

      <!-- months after the last complete one: models released then are still being measured -->
      <rect :x="c.lastX" :y="T" :width="Math.max(0, c.lagX - c.lastX)" :height="H - T - B" class="lag" />
      <line :x1="c.lastX" :x2="c.lastX" :y1="T" :y2="H - B" class="now" />
      <template v-if="c.sat != null">
        <line :x1="L" :x2="W - R" :y1="c.sat" :y2="c.sat" class="sat" />
        <text :x="L + 4" :y="c.sat - 4" class="sat-t">{{ saturationHours }} h: METR’s task suite thins out above this</text>
      </template>

      <path :d="c.outer" class="fan80" />
      <path :d="c.inner" class="fan50" />
      <path :d="c.steps" class="frontier" />
      <path :d="c.median" class="median" />

      <g v-for="p in c.bri" :key="'b' + p.model">
        <circle :cx="c.sx(mi(p.release_date))" :cy="c.sy(p.minutes)" r="4" class="bridged">
          <title>{{ p.model }} ({{ p.release_date }}): about {{ dur(p.minutes) }}, estimated from METR’s older suite (bridged), likely {{ dur(p.low) }}–{{ dur(p.high) }}</title>
        </circle>
      </g>
      <g v-for="p in c.obs" :key="'o' + p.model">
        <line :x1="c.sx(mi(p.release_date))" :x2="c.sx(mi(p.release_date))" :y1="c.sy(p.low)" :y2="c.sy(p.high)"
              class="ci" :class="{ rel: p.frontier_relevant }" />
        <circle :cx="c.sx(mi(p.release_date))" :cy="c.sy(p.minutes)" r="4.5" class="obs" :class="{ rel: p.frontier_relevant, sat: p.saturated }">
          <title>{{ p.model }} ({{ p.release_date }}): {{ dur(p.minutes) }} measured, 95% CI {{ dur(p.low) }}–{{ dur(p.high) }}{{ p.saturated ? '; above 16 h, so not used to fit the trend' : '' }}</title>
        </circle>
      </g>

      <g v-for="(m, i) in c.marks" :key="m.h">
        <circle :cx="m.x" :cy="m.y" r="5" class="mark" />
        <!-- alternate below / above so neighbouring horizons don't collide; the last one sits left of its point -->
        <text v-for="up in [i % 2 === 1 || i === c.marks.length - 1]" :key="'t'" :x="m.x + (up ? -7 : 6)" :y="up ? m.y - 9 : m.y + 18"
              :text-anchor="up ? 'end' : 'start'" class="mark-t">{{ m.h }} mo: {{ dur(m.v) }}</text>
      </g>
    </svg>
    </ChartHover>
    <figcaption class="key">
      <span><i class="k-obs" /> measured model (line = 95% CI)</span>
      <span><i class="k-bri" /> older-suite model, bridged estimate</span>
      <span><i class="k-front" /> best measured so far</span>
      <span><i class="k-med" /> forecast (median)</span>
      <span><i class="k-fan" /> 80% / 50% predictive range</span>
      <span><i class="k-lag" /> still being measured</span>
    </figcaption>
    <p v-if="c.hidden" class="note">{{ c.hidden }} models released before {{ short(FROM) }} are measured too but not drawn.</p>
  </figure>
</template>

<style scoped>
.cc { margin: 4px 0 0; }
svg { width: 100%; height: auto; display: block; }
.grid { stroke: var(--line); stroke-width: 1; }
.axis { stroke: var(--line-strong); stroke-width: 1; }
.tick { font-size: 11px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.lag { fill: #f0efec; }
.now { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 3; }
.sat { stroke: #a12a22; stroke-width: 1; stroke-dasharray: 2 4; opacity: .7; }
.sat-t { font-size: 10.5px; fill: #a12a22; font-weight: 700; }
.fan80 { fill: var(--cream); stroke: none; }
.fan50 { fill: var(--yellow); opacity: .45; stroke: none; }
.frontier { fill: none; stroke: var(--ink); stroke-width: 2; }
.median { fill: none; stroke: var(--amber-ink); stroke-width: 2.5; stroke-dasharray: 6 4; }
.ci { stroke: #b9b4aa; stroke-width: 1; }
.ci.rel { stroke: var(--muted); }
.obs { fill: #c9c4ba; stroke: #fff; stroke-width: 1.5; }
.obs.rel { fill: var(--ink); }
.obs.sat { fill: #a12a22; }
.bridged { fill: #fff; stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 2 2; }
.mark { fill: var(--amber-ink); stroke: #fff; stroke-width: 2; }
.mark-t { font-size: 11px; font-weight: 800; fill: var(--amber-ink); paint-order: stroke; stroke: #fff; stroke-width: 3px; }
.key { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 6px; font-size: 11px; font-weight: 700; color: var(--muted); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.key i { display: inline-block; }
.k-obs { width: 9px; height: 9px; border-radius: 50%; background: var(--ink); }
.k-bri { width: 9px; height: 9px; border-radius: 50%; border: 1.5px dashed var(--muted); background: #fff; }
.k-front { width: 16px; border-top: 2px solid var(--ink); }
.k-med { width: 16px; border-top: 2.5px dashed var(--amber-ink); }
.k-fan { width: 16px; height: 9px; border-radius: 2px; background: linear-gradient(var(--cream), var(--cream)); box-shadow: inset 0 0 0 3px var(--cream), inset 0 0 0 9px rgba(255, 193, 7, .45); }
.k-lag { width: 12px; height: 9px; background: #f0efec; border: 1px solid var(--line-strong); }
.note { font-size: 11px; color: var(--muted); margin-top: 2px; }
</style>
