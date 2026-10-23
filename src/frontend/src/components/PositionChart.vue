<script setup lang="ts">
import { computed } from 'vue';
import type { ContextRole, JobMatch, ScenarioOutlook } from '../api/jobs';

const props = defineProps<{
  jobs: JobMatch[];
  context: ContextRole[];
  scenario: ScenarioOutlook['scenario'];
  selected: string | null;
}>();
const emit = defineEmits<{ select: [code: string] }>();

// Geometry: x = postings change (%), y = AI automation exposure (0-1).
const W = 760, H = 520;
const L = 64, R = 24, T = 16, B = 52;
const RISK_SPLIT = 0.5; // roughly the average across all jobs
// Short names so labels fit in the crowded top band; anything else uses its full title.
const SHORT: Record<string, string> = {
  '15-1211.00': 'Systems Analysts', '15-1212.00': 'Info Security Analysts', '15-1232.00': 'User Support',
  '15-1252.00': 'Software Developers', '15-1255.00': 'Web & UI Designers', '15-2031.00': 'Ops Research Analysts',
  '15-2051.00': 'Data Scientists', '15-2051.01': 'BI Analysts', '43-3031.00': 'Bookkeeping clerks',
  '43-4051.00': 'Customer service reps', '43-9021.00': 'Data entry keyers', '29-1141.00': 'Registered nurses',
};
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

interface Point {
  code: string;
  title: string;
  x: number;
  y: number;
  r: number;
  match: number | null;
  o: ScenarioOutlook;
}

/** Exposure × automation share: how much of the job's AI use does the work rather than assist with it. */
function risk(e: { ai_exposure: number | null; automation_share: number | null }) {
  return e.ai_exposure == null || e.automation_share == null ? null : e.ai_exposure * e.automation_share;
}

function toPoint(role: JobMatch | ContextRole, match: number | null): Point | null {
  const o = role.outlook.find((x) => x.scenario === props.scenario);
  const y = risk(role);
  if (!o || y == null) return null;
  return { code: role.onet_code, title: role.title, x: o.change_pct, y, r: match == null ? 6 : 7 + (match / 100) * 9, match, o };
}

const mine = computed(() => props.jobs.map((j) => toPoint(j, j.match_percent)).filter((p): p is Point => !!p));
const others = computed(() => props.context.map((c) => toPoint(c, null)).filter((p): p is Point => !!p));
const chosen = computed(() => mine.value.find((p) => p.code === props.selected) ?? null);

const xRange = computed(() => {
  const xs = [0, ...mine.value.map((p) => p.x), ...others.value.map((p) => p.x)];
  if (chosen.value) xs.push(chosen.value.o.range_low_pct, chosen.value.o.range_high_pct);
  return { lo: Math.floor((Math.min(...xs) - 2) / 10) * 10, hi: Math.ceil((Math.max(...xs) + 2) / 10) * 10 };
});
const sx = (v: number) => L + ((v - xRange.value.lo) / (xRange.value.hi - xRange.value.lo)) * (W - L - R);
const sy = (v: number) => H - B - v * (H - T - B);
const xTicks = computed(() => {
  const out: number[] = [];
  for (let t = xRange.value.lo; t <= xRange.value.hi; t += 10) out.push(t);
  return out;
});
const byWhen = computed(() => {
  const o = mine.value[0]?.o ?? others.value[0]?.o;
  if (!o) return '';
  const [y, m] = o.forecast_for.split('-');
  return `by ${months[Number(m) - 1]} ${y}`;
});

/**
 * Each label tries right, left, above, then below its dot, taking the first spot that clears every dot and every
 * label already placed. Your best matches are placed first so they get the best spots.
 */
const labels = computed(() => {
  type Box = { x0: number; x1: number; y0: number; y1: number };
  const hit = (a: Box, b: Box) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
  const inside = (b: Box) => b.x0 >= L && b.x1 <= W - R && b.y0 >= T && b.y1 <= H - B;
  const all = [...mine.value.map((p) => ({ p, mine: true })), ...others.value.map((p) => ({ p, mine: false }))];
  const taken: Box[] = all.map(({ p }) => ({ x0: sx(p.x) - p.r, x1: sx(p.x) + p.r, y0: sy(p.y) - p.r, y1: sy(p.y) + p.r }));
  const c = chosen.value; // labels also keep off the selected role's range line
  const line: Box[] = c ? [{ x0: sx(c.o.range_low_pct), x1: sx(c.o.range_high_pct), y0: sy(c.y) - 7, y1: sy(c.y) + 7 }] : [];
  return all.map(({ p, mine }) => {
    const text = `${SHORT[p.code] ?? p.title}${mine ? ` · ${p.match}%` : ''}`;
    const w = text.length * (mine ? 6.6 : 6.1), hgt = 12;
    const cx = sx(p.x), cy = sy(p.y), gap = p.r + 5;
    const spots = [
      { x: cx + gap, y: cy + 4, anchor: 'start', x0: cx + gap },
      { x: cx - gap, y: cy + 4, anchor: 'end', x0: cx - gap - w },
      { x: cx, y: cy - gap, anchor: 'middle', x0: cx - w / 2 },
      { x: cx, y: cy + gap + 10, anchor: 'middle', x0: cx - w / 2 },
      { x: cx + gap, y: cy + 17, anchor: 'start', x0: cx + gap },
      { x: cx - gap, y: cy - 9, anchor: 'end', x0: cx - gap - w },
      { x: cx, y: cy - gap - 12, anchor: 'middle', x0: cx - w / 2 },
      { x: cx, y: cy + gap + 22, anchor: 'middle', x0: cx - w / 2 },
    ];
    const own = taken.findIndex((b) => b.x0 === cx - p.r && b.y0 === cy - p.r);
    const others = [...taken.filter((_, i) => i !== own), ...line];
    const box = (s: (typeof spots)[number]): Box => ({ x0: s.x0, x1: s.x0 + w, y0: s.y - hgt + 2, y1: s.y + 2 });
    // First clear spot; if none is clear, the one that overlaps least.
    const clashes = (s: (typeof spots)[number]) => (inside(box(s)) ? 0 : 99) + others.filter((b) => hit(box(s), b)).length;
    const spot = spots.reduce((best, s) => (clashes(s) < clashes(best) ? s : best));
    taken.push(box(spot));
    return { code: p.code, text, x: spot.x, y: spot.y, anchor: spot.anchor, mine };
  });
});
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="Your matched roles by forecast demand change and AI automation exposure">
    <!-- Quadrants -->
    <rect class="q risk" :x="L" :y="T" :width="sx(0) - L" :height="sy(RISK_SPLIT) - T" />
    <rect class="q transform" :x="sx(0)" :y="T" :width="W - R - sx(0)" :height="sy(RISK_SPLIT) - T" />
    <rect class="q niche" :x="L" :y="sy(RISK_SPLIT)" :width="sx(0) - L" :height="H - B - sy(RISK_SPLIT)" />
    <rect class="q proof" :x="sx(0)" :y="sy(RISK_SPLIT)" :width="W - R - sx(0)" :height="H - B - sy(RISK_SPLIT)" />
    <text class="ql risk" :x="L + 10" :y="T + 18">At risk</text>
    <text class="ql transform" :x="W - R - 10" :y="T + 18" text-anchor="end">Transform with AI</text>
    <text class="ql niche" :x="L + 10" :y="H - B - 10">Stable niche</text>
    <text class="ql proof" :x="W - R - 10" :y="H - B - 10" text-anchor="end">Growing, less exposed</text>

    <!-- Axes -->
    <line class="mid" :x1="sx(0)" :x2="sx(0)" :y1="T" :y2="H - B" />
    <line class="mid" :x1="L" :x2="W - R" :y1="sy(RISK_SPLIT)" :y2="sy(RISK_SPLIT)" />
    <text v-for="t in xTicks" :key="t" class="tick" :x="sx(t)" :y="H - B + 16" text-anchor="middle">{{ t > 0 ? '+' : '' }}{{ t }}%</text>
    <text class="tick" :x="L - 8" :y="T + 8" text-anchor="end">High</text>
    <text class="tick" :x="L - 8" :y="H - B" text-anchor="end">Low</text>
    <text class="axis" :x="(L + W - R) / 2" :y="H - 10" text-anchor="middle">Forecast change in job postings {{ byWhen }} →</text>
    <text class="axis" :transform="`translate(18 ${(T + H - B) / 2}) rotate(-90)`" text-anchor="middle">AI automation exposure →</text>

    <!-- Likely range for the selected role -->
    <g v-if="chosen" class="range">
      <line :x1="sx(chosen.o.range_low_pct)" :x2="sx(chosen.o.range_high_pct)" :y1="sy(chosen.y)" :y2="sy(chosen.y)" />
      <line :x1="sx(chosen.o.range_low_pct)" :x2="sx(chosen.o.range_low_pct)" :y1="sy(chosen.y) - 7" :y2="sy(chosen.y) + 7" />
      <line :x1="sx(chosen.o.range_high_pct)" :x2="sx(chosen.o.range_high_pct)" :y1="sy(chosen.y) - 7" :y2="sy(chosen.y) + 7" />
    </g>

    <!-- Dots: other jobs first so matched roles sit on top -->
    <circle v-for="p in others" :key="p.code" class="dot other" :cx="sx(p.x)" :cy="sy(p.y)" :r="p.r" />
    <circle
      v-for="p in mine"
      :key="p.code"
      class="dot mine"
      :class="{ on: p.code === selected }"
      :cx="sx(p.x)"
      :cy="sy(p.y)"
      :r="p.r"
      tabindex="0"
      role="button"
      :aria-label="`${p.title}: ${p.match}% match, ${p.x > 0 ? '+' : ''}${p.x}% postings`"
      @click="emit('select', p.code)"
      @keydown.enter="emit('select', p.code)"
    />
    <text v-for="l in labels" :key="'l' + l.code" class="label" :class="{ other: !l.mine }" :x="l.x" :y="l.y" :text-anchor="l.anchor">{{ l.text }}</text>
  </svg>
</template>

<style scoped>
svg { width: 100%; display: block; font-family: 'Nunito', sans-serif; }
.q.risk { fill: #fdf0e6; } .q.transform { fill: #fff8e1; } .q.niche { fill: #f5f4f1; } .q.proof { fill: #eaf5ee; }
.ql { font-size: 12px; font-weight: 900; }
.ql.risk { fill: #c2560f; } .ql.transform { fill: #a86b00; } .ql.niche { fill: #8a8782; } .ql.proof { fill: #2e7d4f; }
.mid { stroke: #c2bfba; stroke-width: 1.5; }
.tick { font-size: 10px; font-weight: 800; fill: #8a8782; }
.axis { font-size: 11px; font-weight: 800; fill: #5f5c57; }
.range line { stroke: var(--ink); stroke-width: 2; }
.dot.other { fill: #c2bfba; }
.dot.mine { fill: var(--orange); stroke: #fff; stroke-width: 2; cursor: pointer; outline: none; }
.dot.mine:hover, .dot.mine:focus-visible { fill: #e68900; }
.dot.mine.on { fill: var(--yellow); stroke: var(--ink); stroke-width: 3; }
.label { font-size: 11px; font-weight: 800; fill: var(--ink); pointer-events: none; }
.label.other { fill: #8a8782; font-weight: 700; }
</style>
