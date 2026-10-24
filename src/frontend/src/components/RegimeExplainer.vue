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
const x = (doublings: number) => { const g = 2 ** doublings; return `×${g < 10 ? g.toFixed(2) : g.toFixed(1)}`; };
const d1 = (v: number) => v.toFixed(1);
const pct = (v: number) => `${Math.round(v * 100)}%`;
const hours = (min: number) => (min < 90 ? `${Math.round(min)} min` : `${(min / 60).toFixed(min < 600 ? 1 : 0)} hours`);
const monthName = (p: string) => new Date(`${p}-01`).toLocaleDateString('en', { month: 'short', year: 'numeric' });
const months = (h: number) => `${h} month${h === 1 ? '' : 's'}`;
const name = (m: string) => props.methodNames[m] ?? m;
const BASIS: Record<string, string> = {
  observed_12m: 'measured directly on this task suite',
  bridged_12m: 'estimated through METR’s older task suite (no full year on the current one)',
  trend_prior: 'taken from the fitted trend (no 12-month history)',
  none: 'unknown',
};

const COLORS = { slower: '#2a78d6', same: '#9e9a92', faster: '#eb6834' };
type Band = keyof typeof COLORS;

/** Histogram of the simulated future paces, bars coloured by the band they fall in. */
const W = 680, PADX = 28, TOP = 30, PH = 120;
const plot = computed(() => {
  const d = r.value;
  if (!d) return null;
  const e = d.pace_histogram.edges, cnt = d.pace_histogram.counts;
  const lo = Math.min(e[0], d.same_band[0] - 0.5), hi = Math.max(e[e.length - 1], d.same_band[1] + 0.5);
  const sx = (v: number) => PADX + ((v - lo) / (hi - lo)) * (W - 2 * PADX);
  const top = Math.max(...cnt, 1);
  const BASE = TOP + PH;
  const bars = cnt.map((c, i) => {
    const mid = (e[i] + e[i + 1]) / 2;
    const band: Band = mid > d.same_band[1] ? 'faster' : mid < d.same_band[0] ? 'slower' : 'same';
    return { x: sx(e[i]) + 0.5, w: Math.max(sx(e[i + 1]) - sx(e[i]) - 1, 1), h: (c / top) * PH, band, c, lo: e[i], hi: e[i + 1] };
  });
  const ticks = [];
  for (let t = Math.ceil(lo); t <= Math.floor(hi); t++) ticks.push({ x: sx(t), label: String(t) });
  return { sx, bars, ticks, BASE, H: BASE + 36, x0: sx(d.same_band[0]), x1: sx(d.same_band[1]) };
});
const comps = computed(() => Object.entries(r.value?.components ?? {}));
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
      <p v-else-if="!data.length" class="muted">No explanation is available for this forecast.</p>
      <template v-else-if="r">
        <div class="tabs" role="tablist" aria-label="Horizon">
          <button v-for="(d, i) in data" :key="d.h" type="button" role="tab" :aria-selected="i === pick"
                  :class="{ on: i === pick }" @click="pick = i">Next {{ months(d.h) }}</button>
        </div>

        <ol class="steps">
          <li>
            <h3>Where things stand</h3>
            <p>The best AI model measured so far ({{ r.current_model }}; data complete through {{ monthName(r.last_observed_period) }}) succeeds half the time on
              tasks that take a skilled person about <b>{{ hours(r.last_observed) }}</b>.
              <template v-if="r.current_saturated">That is near the top of METR’s task suite, so the measurement itself is wide.</template></p>
            <p>Over the past 12 months that length grew <b>{{ x(r.hist_pace) }}</b>: <b>{{ d1(r.hist_pace) }} doublings a year</b>
              ({{ BASIS[r.pace_basis] ?? r.pace_basis }}). Allowing for how precisely each end was measured, the past pace was
              {{ d1(r.hist_pace_range[0]) }} to {{ d1(r.hist_pace_range[1]) }} doublings a year.</p>
          </li>
          <li>
            <h3>What “about the same pace” means</h3>
            <p>Within ±{{ r.tolerance.toFixed(2) }} doublings a year of the past pace, so between <b>{{ d1(r.same_band[0]) }}</b> and <b>{{ d1(r.same_band[1]) }}</b>
              doublings a year. Over the next {{ months(r.h) }} that is growth of {{ x(r.same_band[0] * r.h / 12) }} to {{ x(r.same_band[1] * r.h / 12) }}.
              More is “faster”, less is “slower” (still growing, just less quickly). The width is fixed in advance: the larger of 0.25 doublings a year
              and 20% of the past pace.</p>
          </li>
          <li>
            <h3>{{ r.n_sims.toLocaleString('en') }} simulated futures</h3>
            <p>Three approaches each simulate possible paths of the best measured model, and the forecast mixes them:</p>
            <table class="tbl">
              <thead><tr><th scope="col">Approach</th><th scope="col">Share</th><th scope="col">Median in {{ months(r.h) }}</th><th scope="col">Faster</th><th scope="col">Same</th><th scope="col">Slower</th></tr></thead>
              <tbody>
                <tr v-for="[k, v] in comps" :key="k">
                  <td>{{ name(k) }}</td><td>{{ v.weight != null ? pct(v.weight) : '–' }}</td><td>{{ hours(2 ** (v.q50) * 60) }}</td>
                  <td>{{ pct(v.p[0]) }}</td><td>{{ pct(v.p[1]) }}</td><td>{{ pct(v.p[2]) }}</td>
                </tr>
              </tbody>
            </table>
            <p class="note">The jump model treats new frontier-level models as arriving at random:
              <template v-if="r.p_no_new_record != null">in {{ pct(r.p_no_new_record) }} of its futures there is no new record within {{ months(r.h) }}.</template>
              Shares come from each approach’s past errors, held close to equal so a few lucky tests can’t dominate.</p>
          </li>
          <li>
            <h3>Where the simulated futures land</h3>
            <p>Each bar counts futures by their pace over the next {{ months(r.h) }}. 8 in 10 fall between
              {{ d1(r.future_pace_range[0]) }} and {{ d1(r.future_pace_range[1]) }} doublings a year; the median is {{ d1(r.future_pace_median) }}.</p>
            <svg v-if="plot" :viewBox="`0 0 ${W} ${plot.H}`" class="strip" role="img"
                 :aria-label="`Simulated paces: ${pct(r.p_simulated.faster)} faster, ${pct(r.p_simulated.same)} about the same, ${pct(r.p_simulated.slower)} slower`">
              <rect :x="plot.x0" :y="TOP - 18" :width="plot.x1 - plot.x0" :height="plot.BASE - TOP + 18" :fill="COLORS.same" fill-opacity=".12" />
              <text :x="(plot.x0 + plot.x1) / 2" :y="TOP - 6" text-anchor="middle" class="zone">about the same</text>
              <text :x="PADX + 2" :y="TOP - 6" class="zone">slower</text>
              <text :x="W - PADX - 2" :y="TOP - 6" text-anchor="end" class="zone">faster</text>
              <rect v-for="(b, i) in plot.bars" :key="i" :x="b.x" :y="plot.BASE - b.h" :width="b.w" :height="b.h" :fill="COLORS[b.band]">
                <title>{{ b.c }} futures at {{ d1(b.lo) }}–{{ d1(b.hi) }} doublings a year</title>
              </rect>
              <line :x1="plot.sx(r.hist_pace)" :x2="plot.sx(r.hist_pace)" :y1="TOP - 18" :y2="plot.BASE" class="pace" />
              <line :x1="PADX" :x2="W - PADX" :y1="plot.BASE" :y2="plot.BASE" class="axis" />
              <g v-for="t in plot.ticks" :key="t.label">
                <line :x1="t.x" :x2="t.x" :y1="plot.BASE" :y2="plot.BASE + 5" class="axis" />
                <text :x="t.x" :y="plot.BASE + 17" text-anchor="middle" class="tick">{{ t.label }}</text>
              </g>
              <text :x="W / 2" :y="plot.H - 3" text-anchor="middle" class="tick">pace over the next {{ months(r.h) }}, doublings a year</text>
            </svg>
            <p class="key">
              <span><i class="ln pace-k" /> past 12 months’ pace</span>
              <span><i class="dot" :style="{ background: COLORS.faster }" /> faster</span>
              <span><i class="dot" :style="{ background: COLORS.same }" /> about the same</span>
              <span><i class="dot" :style="{ background: COLORS.slower }" /> slower</span>
            </p>
          </li>
          <li>
            <h3>Result</h3>
            <table class="tbl result">
              <thead><tr><th scope="col">Outcome</th><th v-if="r.prior_assisted" scope="col">Simulated</th><th v-if="r.prior_assisted" scope="col">Past frequency</th><th scope="col">Chance</th></tr></thead>
              <tbody>
                <tr><td>Faster than the past year</td><td v-if="r.prior_assisted">{{ pct(r.p_simulated.faster) }}</td><td v-if="r.prior_assisted">{{ pct(r.base_rate.faster) }}</td><td><b>{{ pct(r.p_faster) }}</b></td></tr>
                <tr><td>About the same pace</td><td v-if="r.prior_assisted">{{ pct(r.p_simulated.same) }}</td><td v-if="r.prior_assisted">{{ pct(r.base_rate.same) }}</td><td><b>{{ pct(r.p_same) }}</b></td></tr>
                <tr><td>Slower than the past year</td><td v-if="r.prior_assisted">{{ pct(r.p_simulated.slower) }}</td><td v-if="r.prior_assisted">{{ pct(r.base_rate.slower) }}</td><td><b>{{ pct(r.p_slower) }}</b></td></tr>
              </tbody>
            </table>
            <p v-if="r.prior_assisted" class="note">These chances didn’t beat simple guesses in the earlier tests, so {{ pct(r.shrink) }} of each is the past frequency (set in advance).</p>
            <p v-if="r.probability_method === 'calibrated'" class="note">Calibrated: the simulated shares were softened or sharpened by one factor
              (temperature {{ r.temperature.toFixed(2) }}) fitted on earlier forecasts only, because that lowered the error in the earlier tests.</p>
            <p v-if="r.p_no_new_record != null" class="note">Separately, the chance that no new record appears at all within {{ months(r.h) }} is
              <b>{{ pct(r.p_no_new_record) }}</b>{{ r.no_record_method === 'model' ? ' (two-stage record model)' : ': how often past windows this long had none, because the record model did worse than that in tests' }}.</p>
            <h3 class="sub">Did chances like these work in past tests?</h3>
            <table class="tbl">
              <thead><tr><th scope="col">Tests</th><th scope="col">Cases</th><th scope="col">These chances</th><th scope="col">Past frequency</th><th scope="col">⅓ each</th></tr></thead>
              <tbody>
                <tr v-for="role in (['selection', 'holdout'] as const)" :key="role">
                  <td>{{ role === 'holdout' ? 'Recent (held back)' : 'Earlier' }}</td>
                  <td>{{ r.pace_scores[role]?.n ?? 0 }}</td>
                  <td><b>{{ r.pace_scores[role]?.brier_served?.toFixed(2) ?? '–' }}</b></td>
                  <td>{{ r.pace_scores[role]?.brier_climatology?.toFixed(2) ?? '–' }}</td>
                  <td>{{ r.pace_scores[role]?.brier_uniform?.toFixed(2) ?? '–' }}</td>
                </tr>
              </tbody>
            </table>
            <p class="note">Brier score: 0 = perfect, lower is better. What actually happened in the recent tests:
              {{ r.pace_scores.holdout?.class_counts?.faster ?? 0 }} faster, {{ r.pace_scores.holdout?.class_counts?.same ?? 0 }} about the same,
              {{ r.pace_scores.holdout?.class_counts?.slower ?? 0 }} slower. A past frequency does badly when that mix shifts, so the plain ⅓ guess is shown too.
              Few cases (especially at 12 months), most of them from rebuilt history, so treat small differences as luck.</p>
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
p + p { margin-top: 6px; }
.muted { color: var(--muted); }
.note { font-size: 12px; color: var(--muted); margin-top: 6px; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); }
.tbl th:first-child, .tbl td:first-child { text-align: left; }
.tbl th { font-size: 11px; color: var(--muted); font-weight: 800; }
.strip { width: 100%; height: auto; margin-top: 8px; }
.zone { font-size: 11px; font-weight: 800; fill: var(--muted); }
.tick { font-size: 11px; fill: var(--muted); }
.axis { stroke: var(--line-strong); stroke-width: 1; }
.pace { stroke: var(--ink); stroke-width: 2; stroke-dasharray: 4 4; }
.key { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; font-weight: 700; color: var(--muted); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.ln { display: inline-block; width: 18px; border-top: 2px solid var(--ink); }
.pace-k { border-top-style: dashed; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.result td:last-child { font-size: 15px; }
.sub { margin-top: 12px; }
</style>
