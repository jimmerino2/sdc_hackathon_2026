<script setup lang="ts">
import { computed } from 'vue';
import type { BacktestPoint, HistoryPoint, SkillRow } from '../../api/occupational';
import { addMonths, linear, methodName, month, monthsBetween, pct, ticks } from '../../occupational/format';
import ChartHover, { type HoverPoint } from '../ChartHover.vue';

const props = defineProps<{
  history: HistoryPoint[];
  forecast: SkillRow[];
  backtest: BacktestPoint[];
  from: string;
  h: number;
  label: string;
}>();

const W = 760, H = 320, L = 52, R = 18, T = 14, B = 64;
const VOL_H = 34; // ad-count bars under the axis

const hist = computed(() => props.history.filter((p) => !p.is_partial && p.month >= props.from));
const fc = computed(() => props.forecast);
const past = computed(() => props.backtest.filter((b) => b.h === props.h && b.target_month >= props.from));
const first = computed(() => hist.value[0]?.month ?? props.from);
const lastMonth = computed(() => fc.value.reduce((m, r) => (r.target_month > m ? r.target_month : m), hist.value.at(-1)?.month ?? props.from));
const span = computed(() => Math.max(1, monthsBetween(first.value, lastMonth.value)));
const x = (m: string) => L + (monthsBetween(first.value, m) / span.value) * (W - L - R);

const scale = computed(() => {
  const vals = [
    ...hist.value.map((p) => p.share_3m ?? 0),
    ...fc.value.flatMap((r) => [r.forecast, r.low ?? r.forecast, r.high ?? r.forecast]),
    ...past.value.flatMap((b) => [b.forecast, b.actual]),
  ];
  return linear(vals, H - B, T);
});
const y = (v: number) => scale.value[0](v);
const yTicks = computed(() => ticks(scale.value[1], scale.value[2]));
const maxAds = computed(() => Math.max(1, ...hist.value.map((p) => p.n_ads)));

const line = computed(() =>
  hist.value.filter((p) => p.share_3m != null).map((p, i) => `${i ? 'L' : 'M'}${x(p.month).toFixed(1)},${y(p.share_3m!).toFixed(1)}`).join(' '));
const lastObs = computed(() => [...hist.value].reverse().find((p) => p.share_3m != null));
const xTicks = computed(() => {
  const years: string[] = [];
  const y0 = Number(first.value.slice(0, 4));
  const y1 = Number(lastMonth.value.slice(0, 4));
  const step = Math.max(1, Math.ceil((y1 - y0 + 1) / 8));
  for (let yr = y0 + (first.value.endsWith('-01') ? 0 : 1); yr <= y1; yr += step) years.push(`${yr}-01`);
  return years;
});
/** One hover stop per month: the observed share and ads, earlier test forecasts for it, and new forecasts. */
const hover = computed<HoverPoint[]>(() => {
  const out: HoverPoint[] = [];
  for (const p of hist.value) {
    const tests = past.value.filter((b) => b.target_month === p.month);
    out.push({
      x: x(p.month), title: `${month(p.month)} (3 months to)`,
      rows: [
        ...(p.share_3m != null ? [{ label: 'Share of ads', value: pct(p.share_3m), color: 'var(--ink)' }] : []),
        { label: 'Ads that month', value: `${p.n_ads_skill} of ${p.n_ads} name it`, muted: true },
        ...tests.map((b) => ({ label: `Forecast made ${month(b.origin_month)}${b.method === 'persistence' ? ' (no change)' : ''}`, value: pct(b.forecast), color: b.method === 'persistence' ? '#9e9a92' : 'var(--orange)' })),
      ],
      dots: [...(p.share_3m != null ? [{ y: y(p.share_3m) }] : []), ...tests.map((b) => ({ y: y(b.forecast), color: 'var(--orange)' }))],
    });
  }
  for (const r of fc.value) {
    out.push({
      x: x(r.target_month), title: `${month(r.target_month)} · ${r.h}-month forecast`,
      rows: [{ label: 'Forecast', value: pct(r.forecast), color: 'var(--orange)' },
        { label: 'Historical error band', value: `${pct(r.low)}–${pct(r.high)}` },
        { label: 'Method', value: methodName(r.model), muted: true }],
      dots: [{ y: y(r.forecast), color: r.h === props.h ? 'var(--ink)' : 'var(--orange)' }],
    });
  }
  return out;
});
const nowX = computed(() => (lastObs.value ? x(addMonths(lastObs.value.month, 0)) : null));
</script>

<template>
  <ChartHover :w="W" :h="H" :top="T" :bottom="H - B" :points="hover">
  <svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="label">
    <g class="grid">
      <g v-for="t in yTicks" :key="t">
        <line :x1="L" :x2="W - R" :y1="y(t)" :y2="y(t)" />
        <text :x="L - 6" :y="y(t) + 3" text-anchor="end">{{ pct(t, 0) }}</text>
      </g>
      <text v-for="t in xTicks" :key="t" :x="x(t)" :y="H - B + 14" text-anchor="middle">{{ t.slice(0, 4) }}</text>
    </g>

    <!-- evidence: eligible ads per month in this country x occupation -->
    <g class="vol">
      <rect v-for="p in hist" :key="p.month" :x="x(p.month) - 1" :width="Math.max(1.5, (W - L - R) / span - 1)"
            :y="H - 6 - (p.n_ads / maxAds) * VOL_H" :height="(p.n_ads / maxAds) * VOL_H">
        <title>{{ month(p.month) }}: {{ p.n_ads }} ads, {{ p.n_ads_skill }} name it</title>
      </rect>
      <text :x="L - 6" :y="H - 8" text-anchor="end">ads</text>
    </g>

    <line v-if="nowX != null" class="now" :x1="nowX" :x2="nowX" :y1="T" :y2="H - B" />
    <path class="hist" :d="line" />

    <!-- earlier forecasts at this horizon (held-back test and validation periods) -->
    <g class="past">
      <circle v-for="b in past" :key="b.origin_month + b.method" :cx="x(b.target_month)" :cy="y(b.forecast)" r="3.2"
              :class="b.method === 'persistence' ? 'naive' : 'served'">
        <title>Forecast made {{ month(b.origin_month) }} for {{ month(b.target_month) }}: {{ pct(b.forecast) }} ({{ b.method }}); actual {{ pct(b.actual) }}</title>
      </circle>
    </g>

    <g v-if="lastObs" class="fc">
      <g v-for="r in fc" :key="r.h">
        <line class="dash" :x1="x(lastObs.month)" :y1="y(lastObs.share_3m!)" :x2="x(r.target_month)" :y2="y(r.forecast)" />
        <line v-if="r.low != null && r.high != null" class="bar" :x1="x(r.target_month)" :x2="x(r.target_month)" :y1="y(r.low)" :y2="y(r.high)" />
        <circle :cx="x(r.target_month)" :cy="y(r.forecast)" :r="r.h === h ? 5.5 : 4" :class="{ on: r.h === h }">
          <title>{{ month(r.target_month) }} ({{ r.h }} months ahead): {{ pct(r.forecast) }}, error band {{ pct(r.low) }} to {{ pct(r.high) }}</title>
        </circle>
      </g>
    </g>
  </svg>
  </ChartHover>
</template>

<style scoped>
svg { width: 100%; display: block; font-family: 'Nunito', sans-serif; }
.grid line { stroke: var(--line); stroke-width: 1; }
.grid text, .vol text { font-size: 10px; font-weight: 800; fill: #8a8782; }
.vol rect { fill: #e4e1da; }
.now { stroke: #c2bfba; stroke-dasharray: 3 3; }
.hist { fill: none; stroke: var(--ink); stroke-width: 2.2; stroke-linejoin: round; }
.past .served { fill: #fff; stroke: var(--orange); stroke-width: 1.6; }
.past .naive { fill: #fff; stroke: #9e9a92; stroke-width: 1.2; }
.fc .dash { stroke: var(--orange); stroke-width: 1.5; stroke-dasharray: 4 3; }
.fc .bar { stroke: var(--yellow); stroke-width: 6; stroke-linecap: round; opacity: .75; }
.fc circle { fill: var(--orange); stroke: #fff; stroke-width: 2; }
.fc circle.on { fill: var(--ink); }
</style>
