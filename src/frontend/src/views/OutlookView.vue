<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import Bubble from '../components/Bubble.vue';
import CapabilityChart from '../components/CapabilityChart.vue';
import CapabilityMethod from '../components/CapabilityMethod.vue';
import CapabilityTrend from '../components/CapabilityTrend.vue';
import Icon from '../components/Icon.vue';
import InfoDialog from '../components/InfoDialog.vue';
import RegimeExplainer from '../components/RegimeExplainer.vue';
import SuccessCurves from '../components/SuccessCurves.vue';
import {
  fetchAccuracy, fetchEngine, fetchOutlook, fetchRegime, fetchTargets, type EngineDetail, type RegimeExplained, type MethodScore, type OutlookRow,
  type TargetSummary, type UnitAccuracy,
} from '../api/outlook';
import { OCCUPATIONS, SECTORS } from '../data/outlookNames';

/** One card per forecast target. They measure different things and are never combined. */
interface Card {
  target: string;
  eyebrow: string;
  title: string;
  /** One line under the title; `blurb` (source, definitions) goes in the magnifier dialog. */
  short: string;
  blurb: string;
  names?: Record<string, string>;
  /** Unit code as the API reports it -> the key used in `names` (BTOS units carry their question wording). */
  key?: (unit: string) => string;
  defaultUnit: string;
  pickerLabel?: string;
  /** Plural of pickerLabel, for "all sectors" etc. */
  plural?: string;
  /** What one series is, in words, for the selected unit's name. */
  series?: (name: string) => string;
  minutes?: boolean;
}

const cards: Card[] = [
  {
    target: 'frontier_time_horizon', eyebrow: 'AI capability', title: 'How big a task can the best AI finish?',
    short: 'The longest task, in a skilled person’s working time, that the best AI model finishes half the time.',
    blurb: 'Task size is measured in human work: how long a skilled person needs for the task. The headline number is the biggest task the best measured AI model completes successfully half the time (not how long the AI takes). Mostly software tasks. Source: METR, via Epoch AI.',
    names: { 'v1.0': 'the best measured models (METR suite v1.0)', 'v1.1': 'the best measured models (METR suite v1.1)' },
    defaultUnit: 'v1.1', minutes: true,
  },
  {
    target: 'btos_ai_use_rate', eyebrow: 'Business adoption', title: 'How many US businesses use AI?',
    short: 'Share of US businesses that used AI in the last two weeks.',
    blurb: 'Share of US businesses that used AI in the last two weeks. Source: US Census Bureau survey.',
    names: SECTORS, key: (u) => u.split('|')[0], defaultUnit: 'US|new', pickerLabel: 'Sector', plural: 'sectors',
    series: (n) => `the share of businesses in “${n}” using AI, every two weeks`,
  },
  {
    target: 'worker_genai_use_rate', eyebrow: 'Worker adoption', title: 'How many workers use AI on the job?',
    short: 'Share of employed US adults using generative AI for their job.',
    blurb: 'Share of employed US adults using generative AI for their job. Source: Real-Time Population Survey.',
    names: OCCUPATIONS, defaultUnit: '00', pickerLabel: 'Occupation group', plural: 'occupation groups',
    series: (n) => `the share of workers in “${n}” using AI on the job, quarter by quarter`,
  },
];

const status = ref<'loading' | 'done' | 'error'>('loading');
const explain = ref(false);
/** Capability: past-test reliability of the faster / same / slower chances, per horizon. */
const regimes = ref<RegimeExplained[]>([]);
/** Capability: chart series, backtest scores and diagnostics from the forecasting engine. */
const engine = ref<EngineDetail | null>(null);
const regimeOf = (h: number) => regimes.value.find((r) => r.h === h);
const pace = (v: number) => `${v.toFixed(1)} doublings a year`;
function reliability(h: number) {
  const x = regimes.value.find((r) => r.h === h)?.reliability;
  if (!x || x.brier_model == null || x.brier_uniform == null) return null;
  return { model: x.brier_model.toFixed(2), uniform: x.brier_uniform.toFixed(2), better: x.brier_model < x.brier_uniform };
}
const summaries = ref<Record<string, TargetSummary>>({});
const rows = ref<Record<string, OutlookRow[]>>({});
const picked = reactive<Record<string, string>>(Object.fromEntries(cards.map((c) => [c.target, c.defaultUnit])));

async function load() {
  status.value = 'loading';
  try {
    const list = await fetchTargets();
    summaries.value = Object.fromEntries(list.map((t) => [t.target, t]));
    const got = await Promise.all(list.map((t) => fetchOutlook(t.target)));
    rows.value = Object.fromEntries(list.map((t, i) => [t.target, got[i]]));
    status.value = 'done';
  } catch {
    status.value = 'error';
  }
}
onMounted(async () => {
  await load();
  const cap = cards.find((c) => c.minutes);
  if (cap && rows.value[cap.target]?.length) {
    fetchRegime(cap.target, cap.defaultUnit).then((r) => { regimes.value = r; }).catch(() => {});
    fetchEngine(cap.target).then((e) => { engine.value = e?.units ? e : null; }).catch(() => {});
  }
  if (new URLSearchParams(location.search).has('explain')) explain.value = true;  // link straight to the explanation
});

const shown = computed(() => cards.filter((c) => rows.value[c.target]?.length));

function units(c: Card): string[] {
  return [...new Set((rows.value[c.target] ?? []).map((r) => r.unit))];
}
function unitName(c: Card, u: string): string {
  return c.names?.[c.key ? c.key(u) : u] ?? u;
}
function selectedUnit(c: Card): string | undefined {
  const all = rows.value[c.target] ?? [];
  return all.some((r) => r.unit === picked[c.target]) ? picked[c.target] : all[0]?.unit;
}
function selected(c: Card): OutlookRow[] {
  const u = selectedUnit(c);
  return (rows.value[c.target] ?? []).filter((r) => r.unit === u).sort((a, b) => a.h - b.h);
}

function fmt(c: Card, v: number | null): string {
  if (v == null) return '–';
  if (!c.minutes) return `${v.toFixed(1)}%`;
  if (v < 90) return `${Math.round(v)} min`;
  const h = v / 60;
  return `${h < 10 ? h.toFixed(1) : Math.round(h).toLocaleString('en')} hours`;
}
function horizon(r: OutlookRow): string {
  if (r.period_unit === 'fortnight') return `in about ${Math.round((r.h * 14) / 30.4)} months`;
  if (r.period_unit === 'quarter') return r.h === 1 ? 'next quarter' : `in ${r.h} quarters`;
  return r.h === 1 ? 'next month' : `in ${r.h} months`;
}
/** BTOS periods come as "202701 (ref 2027-01-03)": show the date only. */
function period(p: string): string {
  const m = p.match(/ref (\d{4}-\d{2}-\d{2})/);
  const d = m ? new Date(m[1]) : /^\d{4}-\d{2}$/.test(p) ? new Date(`${p}-01`) : null;
  if (d && !isNaN(+d)) return d.toLocaleDateString('en', m ? { day: 'numeric', month: 'short', year: 'numeric' } : { month: 'short', year: 'numeric' });
  const q = p.match(/^(\d{4})Q(\d)$/);
  return q ? `Q${q[2]} ${q[1]}` : p;
}

/** Plain names for the forecasting methods. */
const METHODS: Record<string, string> = {
  naive: '“No change”',
  drift: 'Continue last year’s trend',
  damped_drift: 'Trend, slowing down',
  pooled_mean: 'Average recent change across series',
  local_trend: 'Local trend model',
  ridge: 'Ridge regression',
  lightgbm: 'LightGBM',
  ensemble: 'Ensemble (mix of the approaches that passed testing)',
  damped_trend: 'Damped trend (simulated)',
  robust_local_trend: 'Robust local trend',
  jump_process: 'Jump model (new models arrive at random)',
  record_jump: 'Two-stage record model (will a record come, how big)',
};
const methodName = (m: string) => METHODS[m] ?? m;

/** Test results per card and selected unit, fetched when the selection changes. */
const accuracy = reactive<Record<string, UnitAccuracy[] | 'error'>>({});
const accKey = (c: Card, u: string) => `${c.target}::${u}`;
async function loadAccuracy(c: Card, u: string) {
  const k = accKey(c, u);
  if (accuracy[k]) return;
  try {
    accuracy[k] = await fetchAccuracy(c.target, u);
  } catch {
    accuracy[k] = 'error';
  }
}
watch([rows, () => ({ ...picked })], () => {
  for (const c of shown.value) {
    const u = selectedUnit(c);
    if (u) loadAccuracy(c, u);
  }
}, { deep: true });
function acc(c: Card, r: OutlookRow): UnitAccuracy | 'error' | undefined {
  const a = accuracy[accKey(c, r.unit)];
  return a === 'error' ? a : a?.find((x) => x.h === r.h);
}
/** An average error: pp for shares; for time horizons a typical "off by a factor of" (errors are in doublings). */
function err(c: Card, v: number | null | undefined): string {
  if (v == null) return '–';
  return c.minutes ? `×${(2 ** v).toFixed(2)}` : `${v.toFixed(2)} pp`;
}
/** Error relative to "no change": -23% means 23% smaller. */
function vsNaive(m: MethodScore, a: UnitAccuracy): string {
  const n = a.methods.find((x) => x.method === 'naive')?.mae;
  if (!n || m.method === 'naive') return '—';
  const d = Math.round((m.mae / n - 1) * 100);
  return `${d > 0 ? '+' : ''}${d}%`;
}
const pct0 = (v: number | undefined) => (v == null ? '–' : `${Math.round(v)}%`);
const accOf = (a: UnitAccuracy, m: string) => pct0(a.methods.find((x) => x.method === m)?.accuracy_pct);
const missOf = (c: Card, a: UnitAccuracy, m: string) => fmt(c, a.methods.find((x) => x.method === m)?.avg_miss ?? null);
const pooledAcc = (a: UnitAccuracy, m: string) => pct0(a.all_units.find((x) => x.method === m)?.accuracy_pct);
const best = (a: UnitAccuracy) => a.methods[0];

/** The pipeline's technical warnings, said plainly. Unknown ones are shown as they are. */
function friendly(w: string): string | null {
  if (w.startsWith('point forecast outside')) return null; // already said on the row itself
  if (w.startsWith('chosen model'))
    return 'Across all series, the method picked in earlier tests didn’t beat “no change” on recent months, so “no change” is shown.';
  if (w.startsWith('point-in-time basis: reconstructed') || w.startsWith('point-in-time basis: mixed'))
    return 'Part of the test history was rebuilt from later data, so the test scores are approximate.';
  if (w.startsWith('point-in-time basis: current_only'))
    return 'The test used today’s data rather than what was published at the time, so its scores may be optimistic.';
  if (w === 'insufficient history') return 'There isn’t much history yet, so treat this as a rough guide.';
  if (w === 'stale target data') return 'The source hasn’t published new data recently.';
  if (w.startsWith('short history')) return 'Only 9 survey readings exist so far, so this is a rough guide.';
  if (w.startsWith('few real vintages'))
    return 'Most of the test history for this measure was rebuilt from later releases, so test scores are approximate.';
  if (w.startsWith('pace chances prior-assisted'))
    return 'The faster / same / slower chances didn’t beat simple guesses in earlier tests, so they are partly pulled towards how often each happened before.';
  if (w.startsWith('historical pace basis: bridged'))
    return 'There is no full year of history on METR’s current task suite, so the past pace is estimated from its older suite.';
  if (w.startsWith('historical pace basis')) return 'The past year’s pace is estimated from the trend, not measured directly.';
  if (w.startsWith('current frontier is above'))
    return 'The best model’s result is near the top of METR’s task suite, so its own measurement is wide (that is why the range starts below today’s value).';
  return w;
}

/** One shared scale per card so the horizons compare at a glance; log for time horizons (they double). */
function scale(c: Card, rs: OutlookRow[]) {
  const vals = rs.flatMap((r) => [r.low ?? r.forecast, r.high ?? r.forecast, r.forecast, r.last_observed]);
  const f = (v: number) => (c.minutes ? Math.log2(v) : v);
  let lo = Math.min(...vals.map(f));
  let hi = Math.max(...vals.map(f));
  const pad = (hi - lo) * 0.06 || 1;
  lo -= pad;
  hi += pad;
  return (v: number | null) => (v == null ? 0 : ((f(v) - lo) / (hi - lo)) * 100);
}

function warnings(rs: OutlookRow[]): string[] {
  return [...new Set(rs.flatMap((r) => r.warnings).map(friendly).filter((w): w is string => !!w))];
}
function asOf(c: Card): string | null {
  const s = summaries.value[c.target];
  const h = s && Object.values(s.source_health)[0];
  return h?.last_available_at ? new Date(h.last_available_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' }) : null;
}
const REGIMES = [
  { key: 'p_acceleration', label: 'Faster than the past year', color: '#eb6834' },
  { key: 'p_stable', label: 'About the same pace', color: '#9e9a92' },
  { key: 'p_slowdown', label: 'Slower than the past year', color: '#2a78d6' },
] as const;
const pct = (v: number | null) => `${Math.round((v ?? 0) * 100)}%`;
/** Why the shown method is shown, in words: the choice is made on earlier months across every series of the card,
 *  and the held-back test can only send it back to "no change", never pick the test's winner. */
function whyShown(c: Card, r: OutlookRow, a: UnitAccuracy): string[] {
  const all = c.plural ? `all ${c.plural}` : 'every series';
  const pooled = (m: string) => err(c, a.all_units.find((x) => x.method === m)?.mae);
  const out: string[] = [];
  if (r.status === 'baseline_retained' && r.chosen_model) {
    out.push(`${methodName(r.chosen_model)} was picked using earlier months across ${all}. On the held-back test it did worse than “no change” across ${all} `
      + `(off by ${pooled(r.chosen_model)} vs ${pooled('naive')}), so “no change” is shown instead.`);
  } else if (a.served_model === 'naive') {
    out.push(`On the earlier months, across ${all}, no method beat “no change” by more than 2%, and the simplest method wins near-ties.`);
  } else {
    out.push(`${methodName(a.served_model)} was picked using earlier months across ${all}, then checked on the held-back test.`);
  }
  const b = best(a);
  if (b.method !== a.served_model) {
    out.push(`${methodName(b.method)} did best for ${unitName(c, r.unit)} in the test below, but the test only checks the pick; it never changes it. `
      + 'Choosing whichever method won the test would make the accuracy look better than it will be on future months.');
  }
  return out;
}
/** One-line test result for a row, e.g. "76% accurate in tests · “no change” 70%". */
function accLine(a: UnitAccuracy): string {
  return a.served_model !== 'naive'
    ? `${accOf(a, a.served_model)} accurate in tests · “no change” ${accOf(a, 'naive')}`
    : `“No change” forecast · ${accOf(a, 'naive')} accurate in tests`;
}
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">AI outlook</p>
      <h1>Where AI and jobs look to be heading</h1>
      <Bubble :size="56" class="intro">
        These are trend outlooks from public data, not promises. Hover a chart for exact values, and tap <b>Test details</b> or the magnifier to see how each forecast did on past months it hadn’t seen.
      </Bubble>

      <div v-if="status === 'loading'" class="grid" aria-busy="true" aria-label="Loading the outlook">
        <span v-for="n in 3" :key="n" class="skel card card-skel" />
      </div>

      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">Jobee couldn’t load the outlook just now. Try again in a moment.</Bubble>
        <button type="button" class="btn btn-secondary" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <div v-else class="grid">
        <section v-for="c in shown" :key="c.target" class="card outlook" :aria-labelledby="`h-${c.target}`">
          <header class="head">
            <div class="head-text">
              <p class="kicker">{{ c.eyebrow }}</p>
              <h2 :id="`h-${c.target}`">
                {{ c.title }}
                <InfoDialog :title="c.title">
                  <p>{{ c.blurb }}</p>
                  <p v-if="c.pickerLabel" class="muted">Pick a {{ c.pickerLabel.toLowerCase() }} to see its own forecast and how every method did on it.</p>
                </InfoDialog>
              </h2>
              <p class="blurb">{{ c.short }}</p>
            </div>
            <label v-if="c.pickerLabel && units(c).length > 1" class="picker">
              <span>{{ c.pickerLabel }}</span>
              <select v-model="picked[c.target]">
                <option v-for="u in units(c)" :key="u" :value="u">{{ unitName(c, u) }}</option>
              </select>
            </label>
          </header>

          <template v-for="rs in [selected(c)]" :key="'rs'">
            <div v-if="rs.length" class="now">
              <span class="now-val">{{ fmt(c, rs[0].last_observed) }}</span>
              <span class="now-lbl">{{ c.minutes ? 'of human work · ' : '' }}latest reading, {{ period(rs[0].last_observed_period) }}</span>
              <span v-if="asOf(c)" class="asof">Data as of {{ asOf(c) }}</span>
            </div>
            <CapabilityChart v-if="c.minutes && engine && selectedUnit(c) && engine.units[selectedUnit(c)!]"
                             :unit="engine.units[selectedUnit(c)!]" :saturation-hours="engine.config.saturation_hours"
                             :lag-months="engine.data.measurement_lag_months" />

            <div class="sec-head">
              <h3>Forecast</h3>
              <p class="key"><span class="sw-dot" /> forecast <span class="sw-band" /> likely range (80%) <span class="sw-tick" /> latest</p>
            </div>
            <ul class="rows">
              <li v-for="r in rs" :key="r.h" class="row">
                <div class="row-main">
                  <span class="when">{{ horizon(r) }}<small>{{ period(r.target_period) }}</small></span>
                  <div v-for="s in [scale(c, rs)]" :key="'s'" class="track"
                       :title="`${horizon(r)}: ${fmt(c, r.forecast)} (likely ${fmt(c, r.low)} to ${fmt(c, r.high)})`">
                    <span class="band" :style="{ left: `${s(r.low)}%`, width: `${Math.max(1, s(r.high) - s(r.low))}%` }" />
                    <span class="tick" :style="{ left: `${s(r.last_observed)}%` }" aria-hidden="true" />
                    <span class="dot" :style="{ left: `${s(r.forecast)}%` }" aria-hidden="true" />
                  </div>
                  <span class="val">{{ fmt(c, r.forecast) }}<small>likely {{ fmt(c, r.low) }} – {{ fmt(c, r.high) }}</small></span>
                </div>

                <div class="row-meta">
                  <template v-for="a in [acc(c, r)]" :key="'a'">
                    <span v-if="a === 'error'" class="muted">Test results couldn’t be loaded.</span>
                    <span v-else-if="!a" class="muted">Loading test results…</span>
                    <template v-else>
                      <span v-if="a.beats_naive !== null" class="verdict" :class="a.beats_naive ? 'yes' : 'no'">
                        <Icon :name="a.beats_naive ? 'check' : 'x'" :size="13" />
                        {{ a.beats_naive ? 'Beats “no change”' : 'Doesn’t beat “no change”' }}
                      </span>
                      <span v-else class="verdict same"><Icon name="scale" :size="13" /> “No change” shown</span>
                      <span class="acc">{{ accLine(a) }}<template v-if="a.n_test_points < 5"> · <b class="warn-t">only {{ a.n_test_points }} tests</b></template></span>
                      <InfoDialog :title="`How the forecast ${horizon(r)} did in tests`"
                                  :label="a.served_model === 'naive' && best(a).method !== 'naive' ? 'Why “no change”?' : 'Test details'" wide>
                        <div class="why">
                          <h3>Why {{ a.served_model === 'naive' ? '“no change”' : 'this method' }} is shown</h3>
                          <p v-for="t in whyShown(c, r, a)" :key="t">{{ t }}</p>
                        </div>
                        <p>
                          <b>Tested on {{ a.n_test_points }} past forecast{{ a.n_test_points === 1 ? '' : 's' }}</b> for {{ unitName(c, r.unit) }}.
                          <template v-if="a.served_model !== 'naive'">
                            The method shown ({{ methodName(a.served_model) }}) was <b>{{ accOf(a, a.served_model) }} accurate</b>
                            (off by {{ err(c, a.served_mae) }}{{ c.minutes ? `, about ${missOf(c, a, a.served_model)}` : '' }} on average);
                            “no change” was <b>{{ accOf(a, 'naive') }}</b> ({{ err(c, a.naive_mae) }}{{ c.minutes ? `, about ${missOf(c, a, 'naive')}` : '' }}).
                          </template>
                          <template v-else>
                            The forecast shown is “no change”: <b>{{ accOf(a, 'naive') }} accurate</b> (off by {{ err(c, a.naive_mae) }}{{ c.minutes ? `, about ${missOf(c, a, 'naive')}` : '' }} on average).
                            <template v-if="best(a).method !== 'naive'">The most accurate method here was {{ methodName(best(a).method) }}: {{ accOf(a, best(a).method) }} ({{ err(c, best(a).mae) }}).</template>
                          </template>
                        </p>
                        <p v-if="a.n_test_points < 5" class="warn-t">Only {{ a.n_test_points }} test points here, so this comparison can easily be luck.</p>
                        <h3>Every method tested for {{ unitName(c, r.unit) }} <span class="sub">held-back test, not used for choosing</span></h3>
                        <div class="scroll">
                          <table>
                            <thead>
                              <tr>
                                <th scope="col">Method</th><th scope="col">Accuracy</th><th scope="col">Avg error</th>
                                <th v-if="c.minutes" scope="col">Avg miss in time</th>
                                <th scope="col">vs “no change”</th>
                                <th v-if="c.pickerLabel" scope="col">Accuracy, all {{ c.plural }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="m in a.methods" :key="m.method" :class="{ shown: m.method === a.served_model }">
                                <td>{{ methodName(m.method) }}<span v-if="m.method === a.served_model" class="tag">shown</span></td>
                                <td>{{ Math.round(m.accuracy_pct) }}%</td>
                                <td>{{ err(c, m.mae) }}</td>
                                <td v-if="c.minutes">{{ fmt(c, m.avg_miss) }}</td>
                                <td>{{ vsNaive(m, a) }}</td>
                                <td v-if="c.pickerLabel">{{ pooledAcc(a, m.method) }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <h3>How to read this</h3>
                        <ul class="muted">
                          <li>Every method forecast months it hadn’t seen, then was compared with what actually happened.</li>
                          <li><b>Accuracy</b> = the smaller of forecast and actual divided by the larger, averaged (forecast 30, actual 40 → 75%).</li>
                          <li><b>Avg error</b> is {{ c.minutes ? 'a factor: ×1.30 means typically 30% too high or too low. Avg miss in time is the plain difference in working time, which recent (longer) tasks dominate' : 'in percentage points' }}.</li>
                          <li>A negative <b>vs “no change”</b> means a smaller error than simply assuming nothing changes.</li>
                          <li v-if="c.pickerLabel">A series is one line of numbers over time; here, {{ c.series?.(unitName(c, r.unit)) }}.
                            The last column averages a method over every series in this card ({{ units(c).length }} {{ c.plural }}).
                            One method is chosen for all of them together, so it can differ from the best method for this one.</li>
                        </ul>
                      </InfoDialog>
                    </template>
                  </template>
                </div>

                <p v-for="x in [c.minutes ? regimeOf(r.h) : undefined]" v-show="x?.p_no_new_record != null" :key="'nr'" class="norec">
                  Chance of <b>no new record</b> by then: <b>{{ pct(x?.p_no_new_record ?? null) }}</b>
                  <InfoDialog title="Chance of no new record">
                    <p>How likely it is that no AI model beats today’s best measured result before this date.</p>
                    <p class="muted">{{ x?.no_record_method === 'model'
                      ? 'Worked out by the two-stage record model: will a record come each month, and if so, how big.'
                      : 'How often past windows this long had no new record. The record model did worse than this in tests, so it isn’t used.' }}</p>
                  </InfoDialog>
                </p>
                <p v-if="r.low != null && r.high != null && (r.forecast < r.low || r.forecast > r.high)" class="skew">
                  <Icon name="shield-alert" :size="14" /> Forecasts like this have always come in too {{ r.forecast < r.low ? 'low' : 'high' }}, so the range is the better guide here.
                </p>

                <div v-if="r.p_acceleration != null" class="regime">
                  <p class="regime-q">
                    Will it grow faster {{ horizon(r) }} than over the past year?
                    <InfoDialog title="Faster, same pace or slower?">
                      <template v-for="x in [regimeOf(r.h)]" :key="'help'">
                        <p v-if="x">Over the past 12 months the best model’s task length grew <b>{{ pace(x.hist_pace) }}</b>.
                          Each of {{ x.n_sims.toLocaleString('en') }} simulated futures is counted as faster, about the same
                          (within ±{{ x.tolerance.toFixed(2) }} doublings a year) or slower over the next {{ r.h }} months.</p>
                        <p v-else>Compares growth over the next {{ r.h }} months with the pace of the past 12 months.</p>
                        <p v-if="x?.prior_assisted" class="muted">These chances are partly pulled towards past frequencies, because they didn’t beat simple guesses in earlier tests.</p>
                      </template>
                      <p v-for="rel in [reliability(r.h)]" v-show="rel" :key="'rel'">
                        In past tests these chances scored <b>{{ rel?.model }}</b> (Brier score, lower is better) vs {{ rel?.uniform }} for a plain
                        one-in-three guess: {{ rel?.better ? 'better than guessing.' : 'worse than guessing, so treat them with caution.' }}
                      </p>
                    </InfoDialog>
                    <span v-for="rel in [reliability(r.h)]" v-show="rel" :key="'relp'" class="verdict sm" :class="rel?.better ? 'yes' : 'no'">
                      {{ rel?.better ? 'Beat guessing in tests' : 'Worse than guessing in tests' }}
                    </span>
                  </p>
                  <div class="stack" role="img"
                       :aria-label="REGIMES.map((g) => `${g.label} ${pct(r[g.key])}`).join(', ')">
                    <span v-for="g in REGIMES" v-show="(r[g.key] ?? 0) > 0" :key="g.key" class="seg"
                          :style="{ flexGrow: r[g.key] ?? 0, background: g.color }" :title="`${g.label}: ${pct(r[g.key])}`" />
                  </div>
                  <ul class="legend">
                    <li v-for="g in REGIMES" :key="g.key"><span class="sw" :style="{ background: g.color }" />{{ g.label }} <b>{{ pct(r[g.key]) }}</b></li>
                  </ul>
                </div>
              </li>
            </ul>

            <button v-if="c.minutes && rs.some((r) => r.p_acceleration != null)" type="button" class="btn btn-secondary explain" @click="explain = true">
              <Icon name="search" :size="16" /> How are the faster / slower chances worked out?
            </button>

            <div v-if="c.minutes" class="deep">
              <CapabilityTrend v-if="engine && selectedUnit(c)" :detail="engine" :unit="selectedUnit(c)!" />
              <SuccessCurves />
              <CapabilityMethod v-if="engine && selectedUnit(c)" :detail="engine" :unit="selectedUnit(c)!" />
            </div>

            <details v-if="warnings(rs).length" class="notes">
              <summary><Icon name="shield-alert" :size="14" /> What to keep in mind ({{ warnings(rs).length }})</summary>
              <ul><li v-for="w in warnings(rs)" :key="w">{{ w }}</li></ul>
            </details>
            <RegimeExplainer v-if="c.minutes && selectedUnit(c)" v-model:open="explain" :target="c.target"
                             :unit="selectedUnit(c)!" :method-names="METHODS" />
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; min-width: 0; }
.eyebrow, .kicker { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
h1 { margin: 6px 0 14px; font-size: 28px; line-height: 1.15; }
.intro { margin-bottom: 22px; max-width: 720px; }
.grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; }
.card-skel { height: 420px; }
.outlook { padding: 24px 28px; display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.head-text { min-width: 0; flex: 1 1 360px; }
h2 { font-size: 20px; line-height: 1.25; display: flex; align-items: center; gap: 8px; margin: 2px 0 4px; }
.blurb { font-size: 13.5px; color: var(--muted); line-height: 1.45; font-weight: 600; }
.picker { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); flex: 0 1 300px; min-width: 0; }
.picker select { font: inherit; font-size: 14px; font-weight: 700; color: var(--ink); padding: 8px 10px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; width: 100%; }
.now { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; padding: 12px 16px; background: #faf9f6; border-radius: 14px; }
.now-val { font-size: 28px; font-weight: 900; }
.now-lbl { font-size: 12.5px; font-weight: 700; color: var(--muted); }
.asof { margin-left: auto; font-size: 11px; font-weight: 700; color: var(--muted); }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.sec-head h3 { font-size: 15px; }
.rows { list-style: none; display: flex; flex-direction: column; padding: 0; margin: 0; }
.rows .row { border-top: 2px solid var(--line); padding: 12px 0; display: flex; flex-direction: column; gap: 8px; }
.row-main { display: grid; grid-template-columns: 150px minmax(0, 1fr) 170px; align-items: center; gap: 14px; }
.when { font-size: 14px; font-weight: 800; display: flex; flex-direction: column; }
.when small, .val small { font-size: 11.5px; font-weight: 700; color: var(--muted); }
.val { font-size: 17px; font-weight: 900; text-align: right; display: flex; flex-direction: column; white-space: nowrap; }
.muted { color: var(--muted); font-weight: 700; }
.track { position: relative; height: 18px; }
.track::before { content: ''; position: absolute; left: 0; right: 0; top: 8px; height: 2px; background: var(--line); }
.band { position: absolute; top: 4px; height: 10px; border-radius: 4px; background: var(--cream); border: 2px solid var(--yellow); box-sizing: border-box; }
.dot { position: absolute; top: 3px; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; background: var(--ink); box-shadow: 0 0 0 2px #fff; }
.tick { position: absolute; top: 1px; width: 2px; height: 16px; margin-left: -1px; background: var(--muted); }
.row-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12.5px; }
.acc { font-weight: 700; color: var(--muted); }
.warn-t { color: var(--amber-ink); font-weight: 800; }
.norec { font-size: 12.5px; font-weight: 700; color: var(--ink); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.skew { font-size: 12.5px; font-weight: 700; color: var(--amber-ink); line-height: 1.4; display: flex; gap: 6px; align-items: flex-start; }
.verdict { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; white-space: nowrap; }
.verdict.sm { font-size: 11px; padding: 2px 8px; }
.verdict.yes { background: #e7f4ea; color: #1e5e30; }
.verdict.no { background: #fdecea; color: #a12a22; }
.verdict.same { background: #f0efec; color: var(--ink); }
.tag { margin-left: 6px; padding: 1px 6px; border-radius: 999px; background: var(--cream); color: var(--amber-ink); font-size: 10px; font-weight: 800; }
tr.shown td { font-weight: 800; background: #fffaf0; }
.why { background: #faf9f6; border-left: 3px solid var(--yellow); border-radius: 10px; padding: 10px 14px; display: flex; flex-direction: column; gap: 6px; }
.why h3 { margin: 0; }
.sub { font-size: 11px; font-weight: 700; color: var(--muted); margin-left: 6px; }
.regime { display: flex; flex-direction: column; gap: 6px; background: #faf9f6; border-radius: 12px; padding: 10px 12px; }
.regime-q { font-size: 13px; font-weight: 800; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.explain { align-self: flex-start; display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; font-size: 12px; }
.stack { display: flex; gap: 2px; height: 12px; }
.seg { border-radius: 4px; min-width: 4px; }
.legend { list-style: none; display: flex; flex-wrap: wrap; gap: 4px 14px; padding: 0; margin: 0; font-size: 12px; font-weight: 700; color: var(--muted); }
.legend b { color: var(--ink); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.key { font-size: 11px; font-weight: 700; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sw-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ink); }
.sw-band { width: 18px; height: 8px; border-radius: 3px; background: var(--cream); border: 2px solid var(--yellow); margin-left: 6px; }
.sw-tick { width: 2px; height: 12px; background: var(--muted); margin-left: 6px; }
.deep { display: flex; flex-direction: column; gap: 4px; margin-top: 4px; }
.notes { font-size: 12.5px; color: var(--muted); background: #fffaf0; border-radius: 12px; padding: 10px 14px; }
.notes summary { cursor: pointer; font-weight: 800; color: var(--amber-ink); display: flex; align-items: center; gap: 6px; }
.notes ul { margin: 8px 0 0 18px; display: flex; flex-direction: column; gap: 4px; line-height: 1.45; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 860px) {
  h1 { font-size: 23px; }
  .outlook { padding: 18px 16px; }
  .row-main { grid-template-columns: minmax(0, 1fr) auto; }
  .row-main .track { grid-column: 1 / -1; grid-row: 2; }
}
</style>
