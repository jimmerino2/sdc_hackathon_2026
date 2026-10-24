<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import Icon from './Icon.vue';
import { fetchRegime, type RegimeExplained } from '../api/outlook';

/** Step-by-step explanation of the "grow faster than the past year?" chances on the AI capability card. */
const props = defineProps<{ target: string; unit: string; methodNames: Record<string, string> }>();
const open = defineModel<boolean>('open', { default: false });

const dlg = ref<HTMLDialogElement>();
const data = ref<RegimeExplained[] | null>(null);
const failed = ref(false);
const pick = ref(0);

async function sync(v: boolean) {
  if (v) {
    dlg.value?.showModal();
    if (!data.value) {
      try {
        data.value = await fetchRegime(props.target, props.unit);
        pick.value = data.value.length - 1;
      } catch {
        failed.value = true;
      }
    }
  } else dlg.value?.close();
}
watch(open, sync);
onMounted(() => { if (open.value) sync(true); });  // opened before mounting (e.g. ?explain=1)

const r = computed(() => data.value?.[pick.value]);
const x = (v: number) => `×${v < 10 ? v.toFixed(2) : v.toFixed(1)}`;
const pct = (v: number) => `${Math.round(v * 100)}%`;
const hours = (min: number) => (min < 90 ? `${Math.round(min)} min` : `${(min / 60).toFixed(min < 600 ? 1 : 0)} hours`);
const monthName = (p: string) => new Date(`${p}-01`).toLocaleDateString('en', { month: 'short', year: 'numeric' });
const months = (h: number) => `${h} month${h === 1 ? '' : 's'}`;
const name = (m: string) => props.methodNames[m] ?? m;

const COLORS = { slower: '#2a78d6', same: '#9e9a92', faster: '#eb6834' };
type Band = keyof typeof COLORS;
const band = (g: number, d: RegimeExplained): Band => (g > d.band_high_growth ? 'faster' : g < d.band_low_growth ? 'slower' : 'same');

/** Dot strip: growth on a log scale, past-error outcomes stacked where they fall, the three bands behind them. */
const W = 680, PADX = 28, R = 5, TOP = 34;
const plot = computed(() => {
  const d = r.value;
  if (!d) return null;
  const gs = [...d.possible_outcomes.map((o) => o.growth), d.band_low_growth, d.band_high_growth, d.forecast_growth, 1];
  const lo = Math.log2(Math.min(...gs)) - 0.25, hi = Math.log2(Math.max(...gs)) + 0.25;
  const sx = (g: number) => PADX + ((Math.log2(g) - lo) / (hi - lo)) * (W - 2 * PADX);
  const cols = new Map<number, number>();
  const dots = [...d.possible_outcomes].sort((a, b) => a.growth - b.growth).map((o) => {
    const cx = sx(o.growth), col = Math.round(cx / (2 * R + 1));
    const k = cols.get(col) ?? 0;
    cols.set(col, k + 1);
    return { ...o, cx: col * (2 * R + 1), k, band: band(o.growth, d) };
  });
  const BASE = TOP + (Math.max(0, ...dots.map((p) => p.k)) + 1) * (2 * R + 1) + 6;  // grows with the tallest stack
  const H = BASE + 34;
  const placed = dots.map((p) => ({ ...p, cy: BASE - R - 2 - p.k * (2 * R + 1) }));
  const ticks = [];
  for (let e = Math.ceil(lo); e <= Math.floor(hi); e++) ticks.push({ x: sx(2 ** e), label: `×${2 ** e}` });
  return { sx, dots: placed, ticks, x0: sx(d.band_low_growth), x1: sx(d.band_high_growth), BASE, H };
});
</script>

<template>
  <dialog ref="dlg" class="dlg" aria-labelledby="regime-title" @close="open = false" @click.self="open = false">
    <div class="inner">
      <div class="top">
        <h2 id="regime-title">How the “faster / same pace / slower” chances are worked out</h2>
        <button type="button" class="close" aria-label="Close" @click="open = false"><Icon name="x" :size="20" /></button>
      </div>

      <p v-if="failed" class="muted">The explanation couldn’t be loaded.</p>
      <p v-else-if="!data" class="muted">Loading…</p>
      <template v-else-if="r">
        <div class="tabs" role="tablist" aria-label="Horizon">
          <button v-for="(d, i) in data" :key="d.h" type="button" role="tab" :aria-selected="i === pick"
                  :class="{ on: i === pick }" @click="pick = i">Next {{ months(d.h) }}</button>
        </div>

        <ol class="steps">
          <li>
            <h3>Where things stand</h3>
            <p>The best measured AI model (released by {{ monthName(r.last_observed_period) }}) completes tasks that take a skilled person
              about <b>{{ hours(r.last_observed) }}</b>, half the time. Over the past 12 months that length grew
              <b>{{ x(r.past_growth) }}</b>.</p>
          </li>
          <li>
            <h3>What “about the same pace” means for the next {{ months(r.h) }}</h3>
            <p>Growing at the past year’s pace for {{ months(r.h) }} would mean <b>{{ x(r.same_pace_growth) }}</b>.
              Pace is measured in doublings, and anything within ±{{ r.tolerance_pct }}% of that pace counts as
              “about the same”: growth between <b>{{ x(r.band_low_growth) }}</b> and <b>{{ x(r.band_high_growth) }}</b>.
              More than that is “faster”, less is “slower” (still growing, just less quickly).</p>
          </li>
          <li>
            <h3>Which forecasting method was used</h3>
            <p>Seven methods were each tested on past months they hadn’t seen. The one with the smallest typical miss in
              the earlier tests was chosen; it was then checked once on the most recent tests.</p>
            <table class="tbl">
              <thead><tr><th scope="col">Method</th><th scope="col">Typical miss, earlier tests</th><th scope="col">Typical miss, recent tests</th></tr></thead>
              <tbody>
                <tr v-for="m in r.methods" :key="m.method" :class="{ chosen: m.served }">
                  <td>{{ name(m.method) }}<span v-if="m.served" class="tag">chosen</span></td>
                  <td>{{ m.selection_typical_miss ? x(m.selection_typical_miss) : '–' }}</td>
                  <td>{{ m.holdout_typical_miss ? x(m.holdout_typical_miss) : '–' }}</td>
                </tr>
              </tbody>
            </table>
            <p class="note">A typical miss of ×2 means the forecast was typically twice or half the actual value.</p>
          </li>
          <li>
            <h3>Its forecast</h3>
            <p>{{ name(r.model) }} forecasts growth of <b>{{ x(r.forecast_growth) }}</b> over the next {{ months(r.h) }},
              to about <b>{{ hours(r.forecast) }}</b>. On its own that would be
              “{{ band(r.forecast_growth, r) === 'faster' ? 'faster' : band(r.forecast_growth, r) === 'slower' ? 'slower' : 'about the same pace' }}”.</p>
          </li>
          <li>
            <h3>How uncertain that is</h3>
            <p>The method has been wrong before. Each of its <b>{{ r.n }}</b> past errors is applied to today’s forecast,
              giving {{ r.n }} possible outcomes (the dots). The chances are simply how many dots land in each band.</p>
            <svg v-if="plot" :viewBox="`0 0 ${W} ${plot.H}`" class="strip" role="img"
                 :aria-label="`${r.n} possible outcomes: ${r.n_faster} faster, ${r.n - r.n_faster - r.n_slower} about the same, ${r.n_slower} slower`">
              <rect :x="PADX" y="10" :width="Math.max(0, plot.x0 - PADX)" :height="plot.BASE - 10" :fill="COLORS.slower" fill-opacity=".08" />
              <rect :x="plot.x0" y="10" :width="plot.x1 - plot.x0" :height="plot.BASE - 10" :fill="COLORS.same" fill-opacity=".14" />
              <rect :x="plot.x1" y="10" :width="Math.max(0, W - PADX - plot.x1)" :height="plot.BASE - 10" :fill="COLORS.faster" fill-opacity=".08" />
              <text :x="PADX + 4" y="24" class="zone">slower</text>
              <text :x="(plot.x0 + plot.x1) / 2" y="24" text-anchor="middle" class="zone">about the same pace</text>
              <text :x="W - PADX - 4" y="24" text-anchor="end" class="zone">faster</text>
              <line :x1="plot.sx(r.same_pace_growth)" :x2="plot.sx(r.same_pace_growth)" y1="30" :y2="plot.BASE" class="pace" />
              <line :x1="plot.sx(r.forecast_growth)" :x2="plot.sx(r.forecast_growth)" y1="30" :y2="plot.BASE" class="fc" />
              <circle v-for="(d, i) in plot.dots" :key="i" :cx="d.cx" :cy="d.cy" :r="R" :fill="COLORS[d.band]" stroke="#fff" stroke-width="2">
                <title>Possible outcome {{ x(d.growth) }} (forecast adjusted by the error made from {{ d.origin }}, {{ d.role === 'holdout' ? 'recent' : 'earlier' }} test)</title>
              </circle>
              <line :x1="PADX" :x2="W - PADX" :y1="plot.BASE" :y2="plot.BASE" class="axis" />
              <g v-for="t in plot.ticks" :key="t.label">
                <line :x1="t.x" :x2="t.x" :y1="plot.BASE" :y2="plot.BASE + 5" class="axis" />
                <text :x="t.x" :y="plot.BASE + 18" text-anchor="middle" class="tick">{{ t.label }}</text>
              </g>
              <text :x="W / 2" :y="plot.H - 4" text-anchor="middle" class="tick">growth over the next {{ months(r.h) }} (log scale)</text>
            </svg>
            <p class="key">
              <span><i class="ln pace-k" /> past year’s pace</span>
              <span><i class="ln fc-k" /> forecast</span>
              <span><i class="dot" :style="{ background: COLORS.faster }" /> faster</span>
              <span><i class="dot" :style="{ background: COLORS.same }" /> about the same</span>
              <span><i class="dot" :style="{ background: COLORS.slower }" /> slower</span>
            </p>
          </li>
          <li>
            <h3>Result</h3>
            <table class="tbl result">
              <thead><tr><th scope="col">Outcome</th><th scope="col">Dots</th><th scope="col">Chance</th></tr></thead>
              <tbody>
                <tr><td>Faster than the past year</td><td>{{ r.n_faster }} of {{ r.n }}</td><td><b>{{ pct(r.p_faster) }}</b></td></tr>
                <tr><td>About the same pace</td><td>{{ r.n - r.n_faster - r.n_slower }} of {{ r.n }}</td><td><b>{{ pct(r.p_same) }}</b></td></tr>
                <tr><td>Slower than the past year</td><td>{{ r.n_slower }} of {{ r.n }}</td><td><b>{{ pct(r.p_slower) }}</b></td></tr>
              </tbody>
            </table>
            <template v-if="r.reliability?.brier_model != null">
              <h3 class="sub">Did chances like these work in past tests?</h3>
              <p>On {{ r.reliability.n }} past forecasts whose outcome is now known, these chances scored
                <b>{{ r.reliability.brier_model.toFixed(2) }}</b> (Brier score: 0 = perfect, lower is better). A plain
                one-in-three guess scored <b>{{ r.reliability.brier_uniform?.toFixed(2) }}</b>.
                <b :class="r.reliability.brier_model < (r.reliability.brier_uniform ?? 0) ? 'ok' : 'bad'">
                  {{ r.reliability.brier_model < (r.reliability.brier_uniform ?? 0)
                    ? 'They did better than guessing.'
                    : 'They did worse than guessing, so treat these chances with caution.' }}
                </b></p>
            </template>
            <p class="note">With {{ r.n }} dots, a 0% only means none of the past errors pointed that way, not that it cannot happen.
              Most past errors come from rebuilt history (see “What to keep in mind” on the card).</p>
          </li>
        </ol>
      </template>
    </div>
  </dialog>
</template>

<style scoped>
.dlg { margin: auto; border: 0; border-radius: 20px; padding: 0; width: min(780px, calc(100vw - 32px)); max-height: calc(100vh - 48px); background: #fff; color: var(--ink); box-shadow: 0 20px 60px rgba(0, 0, 0, .25); }
.dlg::backdrop { background: rgba(30, 30, 30, .45); }
.inner { padding: 22px 24px 26px; }
.top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
h2 { font-size: 20px; line-height: 1.25; }
.close { border: 0; background: #f0efec; border-radius: 999px; width: 36px; height: 36px; display: grid; place-items: center; cursor: pointer; flex: none; }
.tabs { display: flex; gap: 8px; margin: 16px 0 6px; flex-wrap: wrap; }
.tabs button { border: 2px solid var(--line-strong); background: #fff; border-radius: 999px; padding: 6px 14px; font: inherit; font-size: 13px; font-weight: 800; cursor: pointer; }
.tabs button.on { background: var(--yellow); border-color: var(--orange); }
.steps { margin: 10px 0 0 20px; display: flex; flex-direction: column; gap: 18px; }
.steps li::marker { font-weight: 900; color: var(--orange); }
h3 { font-size: 15px; margin-bottom: 4px; }
p { font-size: 14px; line-height: 1.55; }
.muted { color: var(--muted); }
.note { font-size: 12px; color: var(--muted); margin-top: 6px; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); }
.tbl th:first-child, .tbl td:first-child { text-align: left; }
.tbl th { font-size: 11px; color: var(--muted); font-weight: 800; }
.tbl tr.chosen td { font-weight: 800; background: #fffaf0; }
.tag { margin-left: 6px; padding: 1px 6px; border-radius: 999px; background: var(--cream); color: var(--amber-ink); font-size: 10px; font-weight: 800; }
.strip { width: 100%; height: auto; margin-top: 8px; }
.zone { font-size: 11px; font-weight: 800; fill: var(--muted); }
.tick { font-size: 11px; fill: var(--muted); }
.axis { stroke: var(--line-strong); stroke-width: 1; }
.pace { stroke: var(--ink); stroke-width: 2; stroke-dasharray: 4 4; }
.fc { stroke: var(--ink); stroke-width: 2; }
.key { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; font-weight: 700; color: var(--muted); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.ln { display: inline-block; width: 18px; border-top: 2px solid var(--ink); }
.pace-k { border-top-style: dashed; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.result td:last-child { font-size: 15px; }
.sub { margin-top: 12px; }
.ok { color: #1e5e30; }
.bad { color: #a12a22; }
</style>
