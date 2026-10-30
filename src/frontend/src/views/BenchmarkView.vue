<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import {
  estimateRun, fetchBenchInfo, fetchCases, fetchRun, fetchRuns, resumeRun, startRun, stopRun,
  type BenchInfo, type BenchRequest, type Benchmark, type CaseRow, type Compared, type Estimate, type Mode,
  type RunDetail, type RunSummary,
} from '../api/llmBench';

/** LLM forecast benchmark: can an OpenRouter LLM forecast skill demand or AI capability better than the models we
 *  serve? An isolated experiment (src/backend/llm_bench): it reads the existing backtests and never changes them. */

const MODE_TEXT: Record<Mode, string> = {
  zero: 'Zero-shot', few: 'Few-shot', zero_named: 'Zero-shot, named', few_named: 'Few-shot, named',
};
const STATE_TEXT: Record<string, string> = {
  planned: 'Planned', running: 'Running', completed: 'Completed', stopped_budget: 'Stopped: budget reached',
  rate_limited: 'Paused: rate limit', auth_or_payment: 'Stopped: key or credit problem', too_many_failures: 'Stopped: repeated failures',
  stopped_by_user: 'Stopped by you', paused_request_limit: 'Paused: request limit', failed: 'Failed',
};

const status = ref<'loading' | 'done' | 'error'>('loading');
const info = ref<BenchInfo | null>(null);
const runs = ref<RunSummary[]>([]);

// ---- run settings ----
const benchmark = ref<Benchmark>('skills');
const horizons = ref<number[]>([3]);
const model = ref('');
const modes = ref<Mode[]>(['zero', 'few']);
const nSeries = ref(100);
const nOrigins = ref(4);
const batchSize = ref(10);
const maxSpend = ref(2);
const maxRequests = ref(0);
const dryRun = ref(false);

const bInfo = computed(() => info.value?.benchmarks[benchmark.value]);
const modelChoices = computed(() => {
  const s = info.value?.settings;
  return [...new Set([s?.model, s?.compare_model, ...(info.value?.free_models ?? [])].filter(Boolean) as string[])];
});
const modelInfo = (id: string) => info.value?.models[id];

function body(confirm = false): BenchRequest {
  return {
    benchmark: benchmark.value, horizons: [...horizons.value].sort((a, b) => a - b), n_series: nSeries.value, n_origins: nOrigins.value,
    modes: modes.value, model: model.value || undefined, batch_size: batchSize.value, max_spend_usd: maxSpend.value,
    few_shot_k: 4, max_examples: 10, max_requests: maxRequests.value, dry_run: dryRun.value, confirm,
  };
}

watch(benchmark, (b) => { horizons.value = [...(info.value?.benchmarks[b].default_horizons ?? [3])]; });
const toggle = <T,>(list: T[], x: T) => (list.includes(x) ? list.filter((y) => y !== x) : [...list, x]);

// ---- estimate and start ----
const est = ref<Estimate | null>(null);
const estFor = ref('');
const estBusy = ref(false);
const actionErr = ref('');
const confirmed = ref(false);
const estFresh = computed(() => est.value && estFor.value === JSON.stringify(body()));
watch(() => JSON.stringify(body()), () => { confirmed.value = false; });

async function estimate() {
  estBusy.value = true; actionErr.value = '';
  try {
    est.value = await estimateRun(body());
    estFor.value = JSON.stringify(body());
  } catch (e) {
    actionErr.value = String((e as Error).message ?? e);
  } finally {
    estBusy.value = false;
  }
}

async function start() {
  actionErr.value = '';
  try {
    const { run_id } = await startRun(body(!dryRun.value && confirmed.value));
    confirmed.value = false;
    await loadRuns();
    await openRun(run_id);
  } catch (e) {
    actionErr.value = String((e as Error).message ?? e);
  }
}

// ---- runs ----
const selected = ref('');
const detail = ref<RunDetail | null>(null);
const mode = ref<Mode>('zero');
let timer: number | undefined;

async function loadRuns() { runs.value = await fetchRuns(); }

async function openRun(id: string) {
  selected.value = id;
  detail.value = await fetchRun(id);
  if (!detail.value.config.modes.includes(mode.value)) mode.value = detail.value.config.modes[0];
  await loadCases();
  poll();
}

function poll() {
  window.clearTimeout(timer);
  if (!detail.value?.running) return;
  timer = window.setTimeout(async () => {
    if (!selected.value) return;
    detail.value = await fetchRun(selected.value);
    if (!detail.value.running) { await loadRuns(); await loadCases(); }
    poll();
  }, 2000);
}

async function stop() {
  if (selected.value) await stopRun(selected.value);
}
async function resume() {
  if (!detail.value) return;
  actionErr.value = '';
  try {
    await resumeRun(detail.value.run_id, !detail.value.config.dry_run);
    detail.value = await fetchRun(detail.value.run_id);
    poll();
  } catch (e) {
    actionErr.value = String((e as Error).message ?? e);
  }
}

const report = computed(() => detail.value?.report);
const isSkills = computed(() => report.value?.benchmark === 'skills');
const key = computed(() => (isSkills.value ? 'mae_pp' : 'mae_doublings'));
const modeResult = computed(() => report.value?.primary[mode.value] ?? report.value?.exploratory[mode.value]);
const exploratory = computed(() => mode.value.endsWith('_named'));
const progress = computed(() => (detail.value ? detail.value.status.done / Math.max(1, detail.value.status.total) : 0));
const terminal = computed(() => !detail.value?.running && detail.value?.status.state !== 'completed');

// ---- cases ----
const caseFilter = ref('');
const cases = ref<CaseRow[]>([]);
const casesN = ref(0);
async function loadCases() {
  if (!selected.value) return;
  const r = await fetchCases(selected.value, caseFilter.value ? mode.value : undefined, caseFilter.value || undefined);
  cases.value = r.rows; casesN.value = r.n;
}
watch([caseFilter, mode], loadCases);

// ---- formatting ----
const fmt = (x: number | null | undefined, d = 2) => (x === null || x === undefined ? '–' : x.toFixed(d));
const signed = (x: number | null | undefined, d = 2) => (x === null || x === undefined ? '–' : `${x > 0 ? '+' : ''}${x.toFixed(d)}`);
const pctv = (x: number | null | undefined) => (x === null || x === undefined ? '–' : `${(x * 100).toFixed(0)}%`);
const usd = (x: number | null | undefined) => (x === null || x === undefined ? '–' : x === 0 ? '$0' : x < 0.01 ? `$${x.toFixed(5)}` : `$${x.toFixed(3)}`);
const value = (x: unknown) => (typeof x !== 'number' ? '–' : isSkills.value ? `${(x * 100).toFixed(2)}%` : `${x.toFixed(1)} min`);
const err = (f: unknown, a: unknown) => {
  if (typeof f !== 'number' || typeof a !== 'number') return '–';
  return isSkills.value ? signed((f - a) * 100) + ' pp' : signed(Math.log2(f) - Math.log2(a)) + ' dbl';
};
const label = (r: CaseRow) => (r.series_key ? r.series_key.split('|').reverse().join(' · ') : `METR ${r.unit}`);

interface Row { name: string; s: Record<string, number | null>; llm?: boolean }
function rows(c: Compared | undefined, existingName: string): Row[] {
  if (!c || !('llm' in c)) return [];
  return [
    { name: `LLM · ${MODE_TEXT[mode.value]}`, s: c.llm, llm: true },
    { name: `Existing (${existingName})`, s: c.existing },
    { name: '“No change”', s: c.naive },
  ];
}
/** The served method per horizon, e.g. "mean12 at 3 months". */
const existingName = computed(() => {
  const d = detail.value;
  if (!d) return '';
  return d.config.horizons.map((h) => `${d.sample.served[String(h)] ?? '?'} at ${h} mo`).join(', ');
});
const groupTables = computed(() => {
  const m = modeResult.value;
  if (!m) return [];
  const t: { title: string; groups: Record<string, Compared> }[] = [{ title: 'By horizon (months)', groups: m.by_h }, { title: 'By forecast origin', groups: m.by_origin }];
  if (m.by_volume) t.push({ title: 'By ads in the 3 months before the origin', groups: m.by_volume });
  if (m.by_level) t.push({ title: 'By 12-month share at the origin', groups: m.by_level });
  return t;
});

onMounted(async () => {
  try {
    info.value = await fetchBenchInfo();
    model.value = info.value.settings.model;
    maxSpend.value = info.value.settings.max_spend_usd;
    batchSize.value = info.value.settings.batch_size;
    await loadRuns();
    status.value = 'done';
    const live = info.value.running?.run_id ?? runs.value[0]?.run_id;
    if (live) await openRun(live);
  } catch {
    status.value = 'error';
  }
});
onBeforeUnmount(() => window.clearTimeout(timer));
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">Forecast benchmark · experiment</p>
      <h1>Can an LLM forecast better than our models?</h1>
      <Bubble :size="56" class="intro">
        Asks an LLM (through OpenRouter) for the same past forecasts our skill-demand and AI-capability models were tested
        on, then scores both against what actually happened. The primary test hides every name, so the LLM can’t just
        remember the outcome. Nothing here changes the forecasts the app shows.
      </Bubble>

      <div v-if="status === 'loading'" class="skel card big-skel" aria-busy="true" aria-label="Loading" />
      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">Jobee couldn’t reach the benchmark API.</Bubble>
      </div>

      <template v-else-if="info">
        <!-- ================= NEW RUN ================= -->
        <section class="card pad">
          <h2><Icon name="sigma" :size="18" /> New run</h2>
          <p v-if="!info.key_configured" class="warn small"><Icon name="shield-alert" :size="14" /> No <code>OPENROUTER_BENCH_API_KEY</code> in <code>src/backend/.env</code>: only dry runs (mock replies, nothing sent) are possible.</p>
          <div class="filters">
            <label><span>Benchmark</span>
              <select v-model="benchmark"><option v-for="(b, id) in info.benchmarks" :key="id" :value="id">{{ b.label }}</option></select>
            </label>
            <label><span>Model</span>
              <select v-model="model">
                <option v-for="m in modelChoices" :key="m" :value="m">{{ m }}{{ m.endsWith(':free') || modelInfo(m)?.free ? ' · free' : '' }}</option>
              </select>
            </label>
            <label v-if="benchmark === 'skills'"><span>Skill series</span><input v-model.number="nSeries" type="number" min="1" max="1000" /></label>
            <label v-if="benchmark === 'skills'"><span>Origins per series</span><input v-model.number="nOrigins" type="number" min="1" max="12" /></label>
            <label><span>Cases per request</span><input v-model.number="batchSize" type="number" min="1" max="50" /></label>
            <label><span>Spend limit (USD)</span><input v-model.number="maxSpend" type="number" min="0" max="10" step="0.25" /></label>
            <label><span>Stop after requests</span><input v-model.number="maxRequests" type="number" min="0" title="0 = no limit; use a small number for a first test" /></label>
          </div>
          <div class="opts">
            <div><span class="lbl">Horizons</span>
              <div class="chips"><button v-for="x in bInfo?.horizons" :key="x" type="button" :class="{ on: horizons.includes(x) }" @click="horizons = toggle(horizons, x)">{{ x }} months</button></div>
            </div>
            <div><span class="lbl">Prompting</span>
              <div class="chips">
                <button v-for="m in info.modes.primary" :key="m" type="button" :class="{ on: modes.includes(m) }" @click="modes = toggle(modes, m)">{{ MODE_TEXT[m] }}</button>
                <button v-for="m in info.modes.exploratory" :key="m" type="button" :class="{ on: modes.includes(m) }" @click="modes = toggle(modes, m)">{{ MODE_TEXT[m] }} <span class="tag new">exploratory</span></button>
              </div>
            </div>
            <label class="inline"><input v-model="dryRun" type="checkbox" /> Dry run (mock replies, nothing sent)</label>
          </div>
          <p class="muted small">Target: {{ bInfo?.target }}. Cases: {{ bInfo?.origins }}. Named modes show real names and dates, so the LLM may recall what happened; they are reported apart and never pick a winner.</p>

          <div class="actions">
            <button type="button" class="btn btn-secondary" :disabled="estBusy || !horizons.length || !modes.length" @click="estimate">
              <Icon name="calculator" :size="18" /> {{ estBusy ? 'Building sample…' : 'Estimate cost' }}
            </button>
            <template v-if="estFresh && est">
              <label v-if="!dryRun" class="inline confirm"><input v-model="confirmed" type="checkbox" :disabled="!est.key_configured" /> I’ve read the estimate: send these {{ est.n_requests }} requests</label>
              <button type="button" class="btn btn-primary" :disabled="!!info.running || (!dryRun && (!confirmed || !est.key_configured))" @click="start">
                <Icon name="play" :size="18" /> {{ dryRun ? 'Start dry run' : 'Start live run' }}
              </button>
            </template>
          </div>
          <p v-if="actionErr" class="warn small"><Icon name="x" :size="14" /> {{ actionErr }}</p>

          <div v-if="est && estFresh" class="est">
            <div class="nums">
              <div><span>Cases</span><b>{{ est.n_cases }}</b><small>sample {{ est.sample_id }}</small></div>
              <div><span>Requests</span><b>{{ est.n_requests }}</b><small>~{{ est.est_prompt_tokens.toLocaleString('en') }} prompt tokens</small></div>
              <div><span>Expected cost</span><b>{{ est.model.free ? 'Free' : usd(est.expected_cost_usd) }}</b><small>at most {{ usd(est.max_cost_usd) }}</small></div>
              <div><span>Budget</span><b>{{ usd(est.budget_usd) }}</b><small :class="est.within_budget === false ? 'bad' : ''">{{ est.within_budget === false ? 'run stops at the limit' : 'fits' }}</small></div>
            </div>
            <p class="muted small">
              {{ est.model.id }}: {{ !est.model.listed ? 'not in OpenRouter’s list (price unknown)' : est.model.free ? 'free (rate-limited: about 20 requests a minute and a daily cap)' : `$${((est.model.prompt ?? 0) * 1e6).toFixed(3)} in / $${((est.model.completion ?? 0) * 1e6).toFixed(3)} out per million tokens` }}
              · {{ est.model.supported.includes('structured_outputs') ? 'strict JSON schema' : est.model.supported.includes('response_format') ? 'JSON mode' : 'no JSON mode: replies are parsed and checked' }}.
            </p>
          </div>
        </section>

        <!-- ================= RUNS ================= -->
        <section class="card pad">
          <h2><Icon name="clipboard-list" :size="18" /> Runs</h2>
          <p v-if="!runs.length" class="muted small">No runs yet.</p>
          <div v-else class="scroll">
            <table class="tbl click">
              <thead><tr><th>Run</th><th>Benchmark</th><th>Model</th><th>Modes</th><th>State</th><th>Requests</th><th>Spent</th></tr></thead>
              <tbody>
                <tr v-for="r in runs" :key="r.run_id" :class="{ on: r.run_id === selected }" @click="openRun(r.run_id)">
                  <td>{{ r.run_id }} <span v-if="r.dry_run" class="tag">dry run</span></td>
                  <td>{{ info.benchmarks[r.benchmark]?.label }} · h {{ r.horizons.join('/') }}</td>
                  <td>{{ r.model }}<span v-if="r.free" class="tag ok">free</span></td>
                  <td>{{ r.modes.map((m) => MODE_TEXT[m]).join(', ') }}</td>
                  <td>{{ STATE_TEXT[r.state ?? ''] ?? r.state }}</td>
                  <td>{{ r.done }}/{{ r.total }}</td>
                  <td>{{ usd(r.spent_usd) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ================= RESULT ================= -->
        <section v-if="detail && report" class="stack-col">
          <div class="card pad">
            <div class="detail-head">
              <div>
                <p class="kicker">{{ info.benchmarks[report.benchmark].label }} · {{ report.label }}</p>
                <h2>{{ STATE_TEXT[detail.status.state] ?? detail.status.state }}</h2>
                <p v-if="detail.status.stop_reason" class="small warn">{{ detail.status.stop_reason }}</p>
              </div>
              <div class="actions">
                <button v-if="detail.running" type="button" class="btn btn-secondary" @click="stop"><Icon name="x" :size="18" /> Stop</button>
                <button v-else-if="terminal" type="button" class="btn btn-secondary" :disabled="!!info.running" @click="resume"><Icon name="refresh" :size="18" /> Resume</button>
              </div>
            </div>
            <div class="bar-track"><div class="bar-fill" :style="{ width: `${progress * 100}%` }" /></div>
            <div class="nums">
              <div><span>Requests</span><b>{{ detail.status.done }}/{{ detail.status.total }}</b><small>{{ report.usage.retries ?? 0 }} retries</small></div>
              <div><span>Tokens</span><b>{{ ((report.usage.prompt_tokens ?? 0) + (report.usage.completion_tokens ?? 0)).toLocaleString('en') }}</b><small>{{ (report.usage.prompt_tokens ?? 0).toLocaleString('en') }} in · {{ (report.usage.completion_tokens ?? 0).toLocaleString('en') }} out</small></div>
              <div><span>Spent</span><b>{{ usd(detail.status.spent_usd) }}</b><small>of {{ usd(detail.status.budget_usd) }}<template v-for="(v, k) in report.usage.cost_by_source" :key="k"> · {{ k }} {{ usd(v) }}</template></small></div>
              <div v-if="report.usage.by_status"><span>Request outcomes</span><b>{{ report.usage.by_status.ok ?? 0 }} ok</b><small><template v-for="(v, k) in report.usage.by_status" :key="k"><template v-if="k !== 'ok'">{{ k }} {{ v }} · </template></template>{{ report.usage.requests_without_usage ?? 0 }} without usage data</small></div>
            </div>
            <p v-if="report.dry_run" class="warn small"><Icon name="shield-alert" :size="14" /> Dry run: the “LLM” numbers are each series’ last value, to check the pipeline. They are not an LLM’s forecasts.</p>
          </div>

          <nav class="seg" aria-label="Prompting mode">
            <button v-for="m in detail.config.modes" :key="m" type="button" :class="{ on: mode === m }" :aria-pressed="mode === m" @click="mode = m">
              {{ MODE_TEXT[m] }}<span v-if="m.endsWith('_named')" class="tag new">exploratory</span>
            </button>
          </nav>

          <div v-if="modeResult" class="card pad">
            <h2>{{ MODE_TEXT[mode] }}: accuracy on the same cases</h2>
            <p v-if="exploratory" class="warn small"><Icon name="shield-alert" :size="14" /> Exploratory: real names and dates were shown, so the LLM may know the outcome. Not comparable with the anonymous results.</p>
            <p class="small">
              Valid LLM forecasts for <b>{{ modeResult.n_valid }}</b> of {{ modeResult.n_cases }} cases
              <template v-if="report.modes[mode]"> (invalid or missing {{ pctv(report.modes[mode].invalid_rate) }}, request failed {{ pctv(report.modes[mode].request_failure_rate) }})</template>.
              All three are scored on those {{ modeResult.n_valid }} cases only.
            </p>
            <div v-if="'llm' in modeResult.overall" class="scroll">
              <table class="tbl">
                <thead v-if="isSkills"><tr><th>Method</th><th>n</th><th>Mean error (pp)</th><th>Bias (pp)</th><th>Direction right</th><th>Stable-skill error</th><th>Rising bias</th><th>Falling bias</th><th>vs “no change”</th></tr></thead>
                <thead v-else><tr><th>Method</th><th>n</th><th>Mean error (doublings)</th><th>Typical factor</th><th>Bias (doublings)</th><th>Median % error</th><th>Mean error (min)</th><th>vs “no change”</th></tr></thead>
                <tbody>
                  <tr v-for="r in rows(modeResult.overall as Compared, existingName)" :key="r.name" :class="{ shown: r.llm }">
                    <template v-if="isSkills">
                      <td>{{ r.name }}</td><td>{{ r.s.n }}</td><td>{{ fmt(r.s.mae_pp) }}</td><td>{{ signed(r.s.bias_pp) }}</td>
                      <td>{{ pctv(r.s.direction_acc) }}<small v-if="r.s.direction_acc === 0" class="muted"> (flat by design)</small></td>
                      <td>{{ fmt(r.s.stable_mae_pp) }}</td><td>{{ signed(r.s.rising_bias_pp) }}</td><td>{{ signed(r.s.falling_bias_pp) }}</td>
                      <td>{{ r.s.mae_ratio_vs_naive ? fmt(r.s.mae_ratio_vs_naive) + '×' : '–' }}</td>
                    </template>
                    <template v-else>
                      <td>{{ r.name }}</td><td>{{ r.s.n }}</td><td>{{ fmt(r.s.mae_doublings) }}</td><td>{{ fmt(r.s.typical_factor) }}×</td>
                      <td>{{ signed(r.s.bias_doublings) }}</td><td>{{ pctv(r.s.median_ape) }}</td><td>{{ fmt(r.s.mae_minutes, 0) }}</td>
                      <td>{{ r.s.mase_vs_naive ? fmt(r.s.mase_vs_naive) + '×' : '–' }}</td>
                    </template>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="modeResult.verdict" class="verdict-line">
              <span class="verdict" :class="modeResult.verdict.llm_lower_error ? 'yes' : 'no'">
                <Icon :name="modeResult.verdict.llm_lower_error ? 'check' : 'x'" :size="14" />
                {{ modeResult.verdict.llm_lower_error ? 'Lower error than the existing model here' : 'Not more accurate than the existing model here' }}
              </span>
              <span v-if="report.bootstrap[mode]" class="small muted">
                Gap {{ signed(report.bootstrap[mode]!.mean_diff, 3) }} {{ report.bootstrap[mode]!.units }}, 90% range {{ signed(report.bootstrap[mode]!.p05, 3) }} to {{ signed(report.bootstrap[mode]!.p95, 3) }}
                ({{ report.bootstrap[mode]!.p95 < 0 ? 'better beyond noise' : report.bootstrap[mode]!.p05 > 0 ? 'worse beyond noise' : 'within noise' }}; cases share origins, so this range is optimistic).
              </span>
            </p>
            <p class="muted small">Full sample ({{ report.full_sample.existing.n }} cases): existing {{ fmt(report.full_sample.existing[key]) }}, “no change” {{ fmt(report.full_sample.naive[key]) }} {{ isSkills ? 'pp' : 'doublings' }}.</p>

            <details v-for="t in groupTables" :key="t.title" class="notes">
              <summary>{{ t.title }}</summary>
              <table class="tbl">
                <thead><tr><th>Group</th><th>n</th><th>LLM</th><th>Existing</th><th>“No change”</th><th v-if="isSkills">LLM direction</th><th v-if="isSkills">Existing direction</th></tr></thead>
                <tbody>
                  <tr v-for="(g, name) in t.groups" :key="name">
                    <td>{{ name }}</td><td>{{ g.llm.n }}</td><td>{{ fmt(g.llm[key]) }}</td><td>{{ fmt(g.existing[key]) }}</td><td>{{ fmt(g.naive[key]) }}</td>
                    <td v-if="isSkills">{{ pctv(g.llm.direction_acc) }}</td><td v-if="isSkills">{{ pctv(g.existing.direction_acc) }}</td>
                  </tr>
                </tbody>
              </table>
            </details>
          </div>

          <div class="card pad">
            <div class="tbl-head">
              <h2>Forecasts side by side</h2>
              <label class="inline"><span class="small muted">Show</span>
                <select v-model="caseFilter">
                  <option value="">all cases</option>
                  <option value="failed">not valid ({{ MODE_TEXT[mode] }})</option>
                  <option value="invalid">invalid</option>
                  <option value="missing">missing</option>
                  <option value="unparseable">unparseable</option>
                  <option value="request_failed">request failed</option>
                  <option value="skipped_budget">skipped: budget</option>
                  <option value="not_attempted">not attempted</option>
                </select>
              </label>
            </div>
            <p class="muted small">{{ casesN }} cases. Real names are shown here for you; the primary prompts carried only the anonymous id.</p>
            <div class="scroll">
              <table class="tbl">
                <thead><tr><th>Series</th><th>Id sent</th><th>Origin</th><th>h</th><th>Existing</th><th>“No change”</th><th v-for="m in detail.config.modes" :key="m">{{ MODE_TEXT[m] }}</th><th>Actual</th><th>LLM miss</th></tr></thead>
                <tbody>
                  <tr v-for="r in cases" :key="r.case_id">
                    <td>{{ label(r) }}</td><td>{{ r.anon_id }}</td><td>{{ String(r.origin).slice(0, 10) }}</td><td>{{ r.h }}</td>
                    <td>{{ value(r.existing) }}</td><td>{{ value(r.naive) }}</td>
                    <td v-for="m in detail.config.modes" :key="m" :title="(r[`reason_${m}`] as string) ?? ''">
                      <template v-if="r[`status_${m}`] === 'ok'">{{ value(r[`llm_${m}`]) }}</template>
                      <span v-else class="bad small">{{ r[`status_${m}`] }}</span>
                    </td>
                    <td><b>{{ value(r.actual) }}</b></td><td>{{ err(r[`llm_${mode}`], r.actual) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; min-width: 0; }
.eyebrow, .kicker { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
h1 { margin: 6px 0 14px; font-size: 28px; line-height: 1.15; }
h2 { font-size: 18px; line-height: 1.25; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.intro { margin-bottom: 18px; max-width: 760px; }
.big-skel { height: 420px; }
.pad { padding: 20px 24px; }
.card + .card, .card + .stack-col { margin-top: 16px; }
.state { max-width: 560px; margin: 40px 0; }
.filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 10px 0; }
.filters label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); }
select, input[type='number'] { font: inherit; font-size: 13.5px; font-weight: 700; color: var(--ink); padding: 7px 9px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; min-width: 0; }
.opts { display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: flex-end; }
.lbl { font-size: 12px; font-weight: 800; color: var(--muted); }
.inline { display: flex; flex-direction: row; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; margin: 6px 0; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0; }
.chips button { font: inherit; font-size: 12px; font-weight: 800; padding: 5px 11px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; cursor: pointer; }
.chips button.on { background: var(--cream); border-color: var(--yellow); }
.actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
.confirm { color: var(--amber-ink); }
.est { margin-top: 14px; border-top: 2px solid var(--line); padding-top: 12px; }
.seg { display: flex; gap: 6px; flex-wrap: wrap; margin: 16px 0 0; }
.seg button { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 13px; font-weight: 800; padding: 8px 14px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; cursor: pointer; color: var(--ink); }
.seg button.on { background: var(--yellow); border-color: var(--orange); }
.stack-col { display: flex; flex-direction: column; gap: 16px; margin-top: 16px; }
.small { font-size: 12.5px; line-height: 1.5; }
.muted { color: var(--muted); }
.warn { color: var(--amber-ink); font-weight: 700; display: flex; gap: 6px; align-items: flex-start; }
.bad { color: #a12a22; font-weight: 800; }
.detail-head { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
.nums { display: flex; gap: 22px; flex-wrap: wrap; margin-top: 10px; }
.nums div { display: flex; flex-direction: column; } .nums span { font-size: 11px; font-weight: 800; color: var(--muted); }
.nums b { font-size: 20px; font-weight: 900; } .nums small { font-size: 11px; color: var(--muted); font-weight: 700; }
.bar-track { position: relative; height: 10px; background: #f0efec; border-radius: 6px; margin: 8px 0 4px; }
.bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: var(--yellow); border-radius: 6px; transition: width .3s; }
.verdict-line { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 10px 0 6px; }
.verdict { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.verdict.yes { background: #e7f4ea; color: #1e5e30; } .verdict.no { background: #fdecea; color: #a12a22; }
.tag { display: inline-block; margin-left: 6px; padding: 1px 7px; border-radius: 999px; background: #f0efec; color: var(--ink); font-size: 10px; font-weight: 800; vertical-align: 1px; }
.tag.ok { background: #e7f4ea; color: #1e5e30; } .tag.new { background: var(--cream); color: var(--amber-ink); }
.tbl-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; align-items: center; }
.scroll { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl th:first-child, .tbl td:first-child { text-align: left; white-space: normal; }
.tbl th { font-size: 11px; font-weight: 800; color: var(--muted); }
.tbl.click tbody tr { cursor: pointer; } .tbl.click tbody tr:hover, .tbl tr.on { background: #fffaf0; }
.tbl tr.shown td { font-weight: 800; }
.notes { margin-top: 10px; } .notes summary { cursor: pointer; font-weight: 800; font-size: 13px; }
code { font-size: 12px; background: #f6f4ef; padding: 1px 5px; border-radius: 6px; }
@media (max-width: 860px) {
  h1 { font-size: 23px; }
  .pad { padding: 16px; }
}
</style>
