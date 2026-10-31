<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchSuccessCurves, type SuccessCurves, type SuccessModel } from '../api/outlook';
import ChartHover, { type HoverPoint } from './ChartHover.vue';

/** Task lengths each AI model completes at several success rates, plus one model's full success curve. */
const data = ref<SuccessCurves | null>(null);
const failed = ref(false);
const picked = ref('');
const showAll = ref(false);

onMounted(async () => {
  try {
    data.value = await fetchSuccessCurves();
    picked.value = data.value.models.find((m) => m.fitted)?.model ?? '';
  } catch {
    failed.value = true;
  }
});

const levels = computed(() => data.value?.levels ?? []);
const rows = computed(() => (showAll.value ? data.value?.models : data.value?.models.slice(0, 8)) ?? []);
const model = computed(() => data.value?.models.find((m) => m.model === picked.value));
const fitted = computed(() => data.value?.models.filter((m) => m.fitted) ?? []);

/** Human working time, short. */
function dur(min: number | null | undefined): string {
  if (min == null) return '–';
  if (min < 1) return `${Math.round(min * 60)} s`;
  if (min < 90) return `${Math.round(min)} min`;
  const h = min / 60;
  return h < 10 ? `${h.toFixed(1)} h` : `${Math.round(h).toLocaleString('en')} h`;
}
const beyond = (min: number | null | undefined) => min != null && data.value != null && min > data.value.longest_task_minutes;
const month = (d: string | null) => (d ? new Date(d).toLocaleDateString('en', { month: 'short', year: 'numeric' }) : '');
const label = (m: SuccessModel) => (m.epoch_model && !m.fitted ? m.epoch_model : m.model).replace(' (Inspect)', '');

/** Chart: success chance (0-100%) against task length (log scale), fitted curve and observed groups. */
const W = 680, H = 250, L = 44, R = 16, T = 14, B = 40;
const chart = computed(() => {
  const m = model.value;
  if (!m || m.intercept == null || m.slope == null || !data.value) return null;
  const lo = Math.log2(0.05), hi = Math.log2(Math.max(data.value.longest_task_minutes, 60) * 4);
  const sx = (min: number) => L + ((Math.log2(min) - lo) / (hi - lo)) * (W - L - R);
  const sy = (p: number) => T + (1 - p) * (H - T - B);
  const pts: string[] = [];
  for (let i = 0; i <= 120; i++) {
    const x = lo + ((hi - lo) * i) / 120;
    const p = 1 / (1 + Math.exp(-(m.intercept + m.slope * x)));
    pts.push(`${sx(2 ** x).toFixed(1)},${sy(p).toFixed(1)}`);
  }
  const ticks = [
    { min: 1 / 6, t: '10 s' }, { min: 1, t: '1 min' }, { min: 10, t: '10 min' }, { min: 60, t: '1 h' },
    { min: 480, t: '8 h' }, { min: 2400, t: '40 h' }, { min: 9600, t: '160 h' },
  ].filter((k) => Math.log2(k.min) >= lo && Math.log2(k.min) <= hi);
  const marks = [80, 50].map((p) => ({ p, min: m.horizons[String(p)] })).filter((k) => k.min != null) as { p: number; min: number }[];
  // hover: the fitted chance at evenly spaced task lengths, plus each observed task-length group
  const p = (min: number) => 1 / (1 + Math.exp(-(m.intercept! + m.slope! * Math.log2(min))));
  const hover: HoverPoint[] = [];
  for (let i = 0; i <= 40; i++) {
    const min = 2 ** (lo + ((hi - lo) * i) / 40);
    hover.push({
      x: sx(min), title: `Task of ${dur(min)}`,
      rows: [{ label: 'Chance of success (curve)', value: `${Math.round(p(min) * 100)}%`, color: '#2a78d6' },
        ...(beyond(min) ? [{ label: 'Beyond the longest task tested', value: '', muted: true }] : [])],
      dots: [{ y: sy(p(min)), color: '#2a78d6' }],
    });
  }
  for (const o of m.observed) {
    hover.push({
      x: sx(o.median_human_minutes), title: `${o.bin} tasks (median ${dur(o.median_human_minutes)})`,
      rows: [{ label: 'Observed success', value: `${Math.round(o.success_rate * 100)}%`, color: '#2a78d6' },
        { label: 'Attempts', value: String(o.attempts), muted: true },
        { label: 'Curve says', value: `${Math.round(p(o.median_human_minutes) * 100)}%`, muted: true }],
      dots: [{ y: sy(o.success_rate), color: '#2a78d6' }],
    });
  }
  return { sx, sy, line: pts.join(' '), ticks, marks, hover, xLongest: sx(data.value.longest_task_minutes) };
});
</script>

<template>
  <details class="sc">
    <summary><span class="sum-h">What about tasks it finishes more (or less) reliably?</span></summary>
    <p class="lead">
      The headline number is the task length the AI finishes <b>half</b> the time. The same AI finishes shorter tasks more
      reliably and longer ones less often. Read across a row to see how long a task each model handles at each success rate.
    </p>
    <p v-if="failed" class="muted">These numbers couldn’t be loaded.</p>
    <p v-else-if="!data" class="muted">Loading…</p>
    <template v-else>
      <div class="scroll">
        <table>
          <caption class="sr">Task length (a skilled person’s working time) each model completes at each success rate</caption>
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th v-for="p in levels" :key="p" scope="col" :class="{ hl: p === 50 }">{{ p }}%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in rows" :key="m.model">
              <th scope="row">
                <button v-if="m.fitted" type="button" class="link" :class="{ on: m.model === picked }" @click="picked = m.model">{{ label(m) }}</button>
                <span v-else>{{ label(m) }}</span>
                <span class="when">{{ month(m.release_date) }}</span>
              </th>
              <td v-for="p in levels" :key="p" :class="{ hl: p === 50, ext: beyond(m.horizons[String(p)]) }"
                  :title="beyond(m.horizons[String(p)]) ? 'Beyond the longest task METR tested: extrapolated' : undefined">
                {{ dur(m.horizons[String(p)]) }}<sup v-if="beyond(m.horizons[String(p)])">†</sup>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <button v-if="data.models.length > 8" type="button" class="more" @click="showAll = !showAll">
        {{ showAll ? 'Show fewer models' : `Show all ${data.models.length} models` }}
      </button>
      <p class="note">
        † Longer than the longest task METR tested ({{ dur(data.longest_task_minutes) }}): read off the curve beyond the data,
        so treat as a rough extrapolation. “–” = not published: METR has released only the 50% and 80% figures for the newest
        models. {{ data.note }}
      </p>

      <div v-if="chart && model" class="chart">
        <label class="pick">
          <span>Success curve for</span>
          <select v-model="picked">
            <option v-for="m in fitted" :key="m.model" :value="m.model">{{ label(m) }}</option>
          </select>
        </label>
        <ChartHover :w="W" :h="H" :top="T" :bottom="H - B" :points="chart.hover">
        <svg :viewBox="`0 0 ${W} ${H}`" role="img"
             :aria-label="`Chance that ${label(model)} completes a task, by task length; 50% at ${dur(model.horizons['50'])}, 80% at ${dur(model.horizons['80'])}`">
          <g v-for="p in [0, 0.25, 0.5, 0.75, 1]" :key="p">
            <line :x1="L" :x2="W - R" :y1="chart.sy(p)" :y2="chart.sy(p)" class="grid" />
            <text :x="L - 6" :y="chart.sy(p) + 4" text-anchor="end" class="tick">{{ p * 100 }}%</text>
          </g>
          <rect :x="chart.xLongest" :y="T" :width="W - R - chart.xLongest" :height="H - T - B" class="beyond" />
          <text :x="chart.xLongest - 6" :y="T + 14" text-anchor="end" class="tick">longest task tested →</text>
          <g v-for="t in chart.ticks" :key="t.t">
            <text :x="chart.sx(t.min)" :y="H - B + 16" text-anchor="middle" class="tick">{{ t.t }}</text>
          </g>
          <text :x="(L + W - R) / 2" :y="H - 6" text-anchor="middle" class="tick">task length (a skilled person’s working time, log scale)</text>
          <g v-for="k in chart.marks" :key="k.p">
            <line :x1="chart.sx(k.min)" :x2="chart.sx(k.min)" :y1="chart.sy(k.p / 100)" :y2="H - B" class="guide" />
            <text :x="chart.sx(k.min) + 5" :y="chart.sy(k.p / 100) - 6" class="mark">{{ k.p }}%: {{ dur(k.min) }}</text>
          </g>
          <polyline :points="chart.line" class="curve" />
          <circle v-for="o in model.observed" :key="o.bin" :cx="chart.sx(o.median_human_minutes)" :cy="chart.sy(o.success_rate)"
                  :r="4 + Math.min(6, Math.sqrt(o.attempts) / 4)" class="obs">
            <title>{{ o.bin }} tasks: succeeded {{ Math.round(o.success_rate * 100) }}% of {{ o.attempts }} attempts</title>
          </circle>
        </svg>
        </ChartHover>
        <p class="key"><span><i class="ln" /> fitted curve</span><span><i class="dt" /> observed success rate per task-length group (bigger = more attempts)</span></p>
      </div>
    </template>
  </details>
</template>

<style scoped>
.sc { border-top: 2px solid var(--line); padding-top: 12px; }
.sc > * + * { margin-top: 8px; }
.sc > summary { cursor: pointer; list-style: none; }
.sc > summary::-webkit-details-marker { display: none; }
.sum-h { font-size: 16px; font-weight: 800; }
.sum-h::before { content: '+ '; color: var(--orange); font-weight: 900; }
.sc[open] .sum-h::before { content: '− '; }
.more { display: block; }
.lead { font-size: 15px; line-height: 1.5; }
.muted { color: var(--muted); font-size: 15px; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }
th, td { padding: 6px 8px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }
thead th { font-size: 13px; color: var(--muted); font-weight: 800; }
tbody th { text-align: left; font-weight: 700; }
thead th:first-child { text-align: left; }
.hl { background: #fffaf0; font-weight: 800; }
.ext { color: var(--muted); font-style: italic; }
.when { margin-left: 6px; font-size: 13px; color: var(--muted); font-weight: 600; }
.link { border: 0; background: none; padding: 0; font: inherit; color: var(--ink); cursor: pointer; text-decoration: underline dotted; }
.link.on { text-decoration: underline; color: var(--amber-ink); }
.more { align-self: flex-start; border: 0; background: none; padding: 0; font: inherit; font-size: 14px; font-weight: 800; color: var(--amber-ink); cursor: pointer; }
.note { font-size: 14px; color: var(--muted); line-height: 1.45; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.chart { margin-top: 6px; }
.pick { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 800; color: var(--muted); }
.pick select { font: inherit; font-size: 15px; font-weight: 700; color: var(--ink); padding: 6px 8px; border: 2px solid var(--line-strong); border-radius: 10px; background: #fff; }
svg { width: 100%; height: auto; }
.chart :deep(.ch) { margin-top: 6px; }
.grid { stroke: var(--line); stroke-width: 1; }
.tick { font-size: 11px; fill: var(--muted); }
.beyond { fill: #f0efec; opacity: .6; }
.curve { fill: none; stroke: #2a78d6; stroke-width: 2; }
.obs { fill: #2a78d6; fill-opacity: .25; stroke: #2a78d6; stroke-width: 1.5; }
.guide { stroke: var(--ink); stroke-width: 1; stroke-dasharray: 3 3; }
.mark { font-size: 11px; font-weight: 800; fill: var(--ink); }
.key { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 14px; font-weight: 700; color: var(--muted); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.ln { display: inline-block; width: 18px; border-top: 2px solid #2a78d6; }
.dt { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: rgba(42, 120, 214, .25); border: 1.5px solid #2a78d6; }
</style>
