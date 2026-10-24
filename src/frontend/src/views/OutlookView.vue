<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import Bubble from '../components/Bubble.vue';
import CapabilityChart from '../components/CapabilityChart.vue';
import CapabilityMethod from '../components/CapabilityMethod.vue';
import CapabilityTrend from '../components/CapabilityTrend.vue';
import Icon from '../components/Icon.vue';
import RegimeExplainer from '../components/RegimeExplainer.vue';
import SuccessCurves from '../components/SuccessCurves.vue';
import {
  fetchAccuracy, fetchEngine, fetchOutlook, fetchRegime, fetchTargets, type EngineDetail, type RegimeExplained, type MethodScore, type OutlookRow,
  type TargetSummary, type UnitAccuracy,
} from '../api/outlook';
import { COUNTRIES, OCCUPATIONS, SECTORS } from '../data/outlookNames';

/** One card per forecast target. They measure different things and are never combined. */
interface Card {
  target: string;
  eyebrow: string;
  title: string;
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
    blurb: 'Task size is measured in human work: how long a skilled person needs for the task. The headline number is the biggest task the best measured AI model completes successfully half the time (not how long the AI takes). Mostly software tasks. Source: METR, via Epoch AI.',
    names: { 'v1.0': 'the best measured models (METR suite v1.0)', 'v1.1': 'the best measured models (METR suite v1.1)' },
    defaultUnit: 'v1.1', minutes: true,
  },
  {
    target: 'ai_mention_share', eyebrow: 'Skill demand', title: 'How many job ads ask for AI?',
    blurb: 'Share of new job ads that mention AI. Source: Indeed Hiring Lab.',
    names: COUNTRIES, defaultUnit: 'US', pickerLabel: 'Country', plural: 'countries',
    series: (n) => `the share of job ads in ${n} that mention AI, month by month`,
  },
  {
    target: 'btos_ai_use_rate', eyebrow: 'Business adoption', title: 'How many US businesses use AI?',
    blurb: 'Share of US businesses that used AI in the last two weeks. Source: US Census Bureau survey.',
    names: SECTORS, key: (u) => u.split('|')[0], defaultUnit: 'US|new', pickerLabel: 'Sector', plural: 'sectors',
    series: (n) => `the share of businesses in “${n}” using AI, every two weeks`,
  },
  {
    target: 'worker_genai_use_rate', eyebrow: 'Worker adoption', title: 'How many workers use AI on the job?',
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
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">AI outlook</p>
      <h1>Where AI and jobs look to be heading</h1>
      <Bubble :size="56" class="intro">
        These are trend outlooks from public data, not promises. Under each forecast you can see how every method did on past months it hadn’t seen, for the exact country, sector or group you pick.
      </Bubble>

      <div v-if="status === 'loading'" class="grid" aria-busy="true" aria-label="Loading the outlook">
        <span v-for="n in 4" :key="n" class="skel card card-skel" />
      </div>

      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">Jobee couldn’t load the outlook just now. Try again in a moment.</Bubble>
        <button type="button" class="btn btn-secondary" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <div v-else class="grid">
        <section v-for="c in shown" :key="c.target" class="card outlook" :aria-labelledby="`h-${c.target}`">
          <p class="kicker">{{ c.eyebrow }}</p>
          <h2 :id="`h-${c.target}`">{{ c.title }}</h2>
          <p class="blurb">{{ c.blurb }}</p>

          <label v-if="c.pickerLabel && units(c).length > 1" class="picker">
            <span>{{ c.pickerLabel }}</span>
            <select v-model="picked[c.target]">
              <option v-for="u in units(c)" :key="u" :value="u">{{ unitName(c, u) }}</option>
            </select>
          </label>

          <template v-for="rs in [selected(c)]" :key="'rs'">
            <p v-if="rs.length" class="now">
              <span class="now-val">{{ fmt(c, rs[0].last_observed) }}</span>
              <span class="now-lbl">{{ c.minutes ? 'of human work, ' : '' }}latest, {{ period(rs[0].last_observed_period) }}</span>
            </p>
            <CapabilityChart v-if="c.minutes && engine && selectedUnit(c) && engine.units[selectedUnit(c)!]"
                             :unit="engine.units[selectedUnit(c)!]" :saturation-hours="engine.config.saturation_hours"
                             :lag-months="engine.data.measurement_lag_months" />

            <ul class="rows">
              <li v-for="r in rs" :key="r.h" class="row">
                <div class="row-head">
                  <span class="when">{{ horizon(r) }} <span class="muted">· {{ period(r.target_period) }}</span></span>
                  <span class="val">{{ fmt(c, r.forecast) }}</span>
                </div>
                <div v-for="s in [scale(c, rs)]" :key="'s'" class="track"
                     :title="`${horizon(r)}: ${fmt(c, r.forecast)} (likely ${fmt(c, r.low)} to ${fmt(c, r.high)})`">
                  <span class="band" :style="{ left: `${s(r.low)}%`, width: `${Math.max(1, s(r.high) - s(r.low))}%` }" />
                  <span class="tick now-tick" :style="{ left: `${s(r.last_observed)}%` }" aria-hidden="true" />
                  <span class="dot" :style="{ left: `${s(r.forecast)}%` }" aria-hidden="true" />
                </div>
                <p class="range">{{ c.minutes ? '80% range' : 'Likely range' }} {{ fmt(c, r.low) }} to {{ fmt(c, r.high) }}</p>
                <p v-for="x in [c.minutes ? regimeOf(r.h) : undefined]" v-show="x?.p_no_new_record != null" :key="'nr'" class="norec">
                  Chance of <b>no new record</b> by then: <b>{{ pct(x?.p_no_new_record ?? null) }}</b>{{ ' ' }}
                  <span class="muted">({{ x?.no_record_method === 'model' ? 'two-stage record model' : 'how often past windows this long had none; the record model did worse in tests' }})</span>
                </p>
                <p v-if="r.low != null && r.high != null && (r.forecast < r.low || r.forecast > r.high)" class="skew">
                  Forecasts like this have always come in too {{ r.forecast < r.low ? 'low' : 'high' }}, so the range is the better guide here.
                </p>
                <div v-for="a in [acc(c, r)]" :key="'a'" class="test">
                  <p v-if="a === 'error'" class="test-line">Test results couldn’t be loaded.</p>
                  <p v-else-if="!a" class="test-line muted">Loading test results…</p>
                  <template v-else>
                    <p class="test-line">
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
                    <span v-if="a.beats_naive !== null" class="verdict" :class="a.beats_naive ? 'yes' : 'no'">
                      <Icon :name="a.beats_naive ? 'check' : 'x'" :size="14" />
                      {{ a.beats_naive ? 'Beats “no change” here' : 'Does not beat “no change” here' }}
                    </span>
                    <span v-else class="verdict same"><Icon name="scale" :size="14" /> Shown forecast is “no change”</span>
                    <p v-if="a.n_test_points < 5" class="few">
                      Only {{ a.n_test_points }} test points here, so this comparison can easily be luck.
                    </p>
                    <div class="methods">
                      <p class="methods-h">Every method tested for {{ unitName(c, r.unit) }}</p>
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
                          <tr v-for="m in a.methods" :key="m.method" :class="{ shown: m.method === a.served_model, base: m.method === 'naive' }">
                            <td>{{ methodName(m.method) }}<span v-if="m.method === a.served_model" class="tag">shown</span></td>
                            <td>{{ Math.round(m.accuracy_pct) }}%</td>
                            <td>{{ err(c, m.mae) }}</td>
                            <td v-if="c.minutes">{{ fmt(c, m.avg_miss) }}</td>
                            <td>{{ vsNaive(m, a) }}</td>
                            <td v-if="c.pickerLabel">{{ pooledAcc(a, m.method) }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <p class="table-note">
                        Tested on months the methods hadn’t seen. Accuracy = the smaller of forecast and actual divided by the larger,
                        averaged (forecast 30, actual 40 → 75%).
                        Avg error is {{ c.minutes ? 'a factor (×1.30 = typically 30% too high or too low); avg miss in time is the plain difference in working time, which recent (longer) tasks dominate' : 'in percentage points' }};
                        a negative “vs no change” means a smaller error than “no change”.
                        <template v-if="c.pickerLabel">
                          A series is one line of numbers over time; here, {{ c.series?.(unitName(c, r.unit)) }}.
                          The last column averages a method over every series in this card ({{ units(c).length }} {{ c.plural }}).
                          That pooled score chose the method shown, so it can differ from the best method for this one.
                        </template>
                      </p>
                    </div>
                  </template>
                </div>

                <div v-if="r.p_acceleration != null" class="regime">
                  <p class="regime-q">{{ c.minutes ? "Will the measured frontier" : "Will task length" }} grow faster {{ horizon(r) }} than over the past year?</p>
                  <p v-for="x in [regimeOf(r.h)]" :key="'help'" class="regime-help">
                    <template v-if="x">
                      Over the past 12 months the best model’s task length grew {{ pace(x.hist_pace) }}. Each of {{ x.n_sims.toLocaleString('en') }} simulated futures
                      is counted as faster, about the same (within ±{{ x.tolerance.toFixed(2) }} doublings a year) or slower over the next {{ r.h }} months.
                      <template v-if="x.prior_assisted">These chances are partly pulled towards past frequencies, because they didn’t beat simple guesses in earlier tests.</template>
                    </template>
                    <template v-else>Compares growth over the next {{ r.h }} months with the pace of the past 12 months.</template>
                  </p>
                  <p v-for="rel in [reliability(r.h)]" v-show="rel" :key="'rel'" class="rel" :class="rel?.better ? 'ok' : 'bad'">
                    In past tests these chances scored {{ rel?.model }} (lower is better) vs {{ rel?.uniform }} for a plain
                    one-in-three guess: {{ rel?.better ? 'better than guessing.' : 'worse than guessing, so treat them with caution.' }}
                  </p>
                  <div class="stack" role="img"
                       :aria-label="REGIMES.map((g) => `${g.label} ${pct(r[g.key])}`).join(', ')">
                    <span v-for="g in REGIMES" v-show="(r[g.key] ?? 0) > 0" :key="g.key" class="seg"
                          :style="{ flexGrow: r[g.key] ?? 0, background: g.color }" :title="`${g.label}: ${pct(r[g.key])}`" />
                  </div>
                  <button v-if="c.minutes" type="button" class="btn btn-secondary explain" @click="explain = true">
                    <Icon name="search" :size="16" /> How is this worked out?
                  </button>
                  <ul class="legend">
                    <li v-for="g in REGIMES" :key="g.key"><span class="sw" :style="{ background: g.color }" />{{ g.label }} <b>{{ pct(r[g.key]) }}</b></li>
                  </ul>
                </div>
              </li>
            </ul>

            <CapabilityTrend v-if="c.minutes && engine && selectedUnit(c)" :detail="engine" :unit="selectedUnit(c)!" />
            <SuccessCurves v-if="c.minutes" />
            <CapabilityMethod v-if="c.minutes && engine && selectedUnit(c)" :detail="engine" :unit="selectedUnit(c)!" />
            <p class="key"><span class="sw-dot" /> forecast <span class="sw-band" /> likely range (80%) <span class="sw-tick" /> latest</p>

            <details v-if="warnings(rs).length" class="notes">
              <summary>What to keep in mind</summary>
              <ul><li v-for="w in warnings(rs)" :key="w">{{ w }}</li></ul>
            </details>
            <p v-if="asOf(c)" class="asof">Data as of {{ asOf(c) }}</p>
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
.outlook { padding: 24px 28px; display: flex; flex-direction: column; gap: 10px; }
h2 { font-size: 19px; line-height: 1.25; }
.blurb { font-size: 13px; color: var(--muted); line-height: 1.45; }
.picker { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); }
.picker select { font: inherit; font-size: 14px; font-weight: 700; color: var(--ink); padding: 8px 10px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; }
.now { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.now-val { font-size: 26px; font-weight: 900; }
.now-lbl { font-size: 12px; font-weight: 700; color: var(--muted); }
.rows { list-style: none; display: flex; flex-direction: column; gap: 14px; padding: 0; margin: 0; }
.rows .row { border-top: 2px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 6px; }
.row-head { display: flex; justify-content: space-between; gap: 8px; font-size: 14px; font-weight: 800; }
.muted { color: var(--muted); font-weight: 700; }
.val { font-size: 16px; font-weight: 900; white-space: nowrap; }
.track { position: relative; height: 18px; }
.track::before { content: ''; position: absolute; left: 0; right: 0; top: 8px; height: 2px; background: var(--line); }
.band { position: absolute; top: 4px; height: 10px; border-radius: 4px; background: var(--cream); border: 2px solid var(--yellow); box-sizing: border-box; }
.dot { position: absolute; top: 3px; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; background: var(--ink); box-shadow: 0 0 0 2px #fff; }
.tick { position: absolute; top: 1px; width: 2px; height: 16px; margin-left: -1px; background: var(--muted); }
.range { font-size: 12px; font-weight: 700; color: var(--muted); }
.norec { font-size: 12px; font-weight: 700; color: var(--ink); line-height: 1.4; }
.norec .muted { font-weight: 600; }
.skew { font-size: 12px; font-weight: 700; color: var(--amber-ink); line-height: 1.4; }
.test { display: flex; flex-direction: column; gap: 6px; }
.test-line { font-size: 12.5px; line-height: 1.5; color: var(--ink); }
.verdict { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.verdict.yes { background: #e7f4ea; color: #1e5e30; }
.verdict.no { background: #fdecea; color: #a12a22; }
.verdict.same { background: #f0efec; color: var(--ink); }
.few { font-size: 12px; font-weight: 700; color: var(--amber-ink); }
.methods { font-size: 12px; }
.methods-h { font-weight: 800; color: var(--ink); font-size: 12.5px; }
.methods table { width: 100%; border-collapse: collapse; margin-top: 8px; font-variant-numeric: tabular-nums; }
.methods th, .methods td { text-align: right; padding: 5px 6px; border-bottom: 1px solid var(--line); }
.methods th:first-child, .methods td:first-child { text-align: left; }
.methods th { font-weight: 800; color: var(--muted); font-size: 11px; }
.methods tr.shown td { font-weight: 800; }
.methods tr.base td { background: #faf9f6; }
.tag { margin-left: 6px; padding: 1px 6px; border-radius: 999px; background: var(--cream); color: var(--amber-ink); font-size: 10px; font-weight: 800; }
.table-note { margin-top: 6px; color: var(--muted); line-height: 1.45; }
.regime { margin-top: 4px; display: flex; flex-direction: column; gap: 6px; }
.regime-q { font-size: 13px; font-weight: 800; }
.regime-help { font-size: 11.5px; color: var(--muted); line-height: 1.45; }
.rel { font-size: 12px; font-weight: 700; line-height: 1.45; }
.rel.ok { color: #1e5e30; }
.rel.bad { color: #a12a22; }
.explain { align-self: flex-start; display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; font-size: 13px; }
.stack { display: flex; gap: 2px; height: 12px; }
.seg { border-radius: 4px; min-width: 4px; }
.legend { list-style: none; display: flex; flex-wrap: wrap; gap: 4px 14px; padding: 0; margin: 0; font-size: 12px; font-weight: 700; color: var(--muted); }
.legend b { color: var(--ink); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.key { font-size: 11px; font-weight: 700; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sw-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ink); }
.sw-band { width: 18px; height: 8px; border-radius: 3px; background: var(--cream); border: 2px solid var(--yellow); margin-left: 6px; }
.sw-tick { width: 2px; height: 12px; background: var(--muted); margin-left: 6px; }
.notes { font-size: 12px; color: var(--muted); }
.notes summary { cursor: pointer; font-weight: 800; color: var(--ink); }
.notes ul { margin: 6px 0 0 16px; display: flex; flex-direction: column; gap: 4px; line-height: 1.4; }
.asof { font-size: 11px; font-weight: 700; color: var(--muted); margin-top: auto; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 860px) {
  .grid { grid-template-columns: minmax(0, 1fr); }
  h1 { font-size: 23px; }
}
</style>
