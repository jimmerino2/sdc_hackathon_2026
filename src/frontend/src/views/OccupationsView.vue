<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import ShareChart from '../components/occ/ShareChart.vue';
import {
  fetchAdoption, fetchEmerging, fetchOccEvaluation, fetchOccMeta, fetchSignals, fetchSkill, fetchSkills,
  type AdoptionResponse, type AsOfRow, type EmergingResponse, type OccEvaluation, type OccMeta, type SignalRow,
  type SignalsResponse, type SkillDetail, type SkillRow, type SkillsResponse,
} from '../api/occupational';
import { METHOD_NAMES, STATUS_TEXT, TAXONOMY_TEXT, growth, methodName, month, pct, pp, scenarioShare, trendOf } from '../occupational/format';

/** Occupational forecasting: skill demand, emerging skills and AI adoption per country x occupation.
 *  Separate from the AI outlook tab: its own pipeline (src/backend/occupational), data and models. */

type Tab = 'demand' | 'emerging' | 'signals' | 'adoption' | 'method';
const tab = ref<Tab>('demand');
const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: 'demand', label: 'Skill demand', icon: 'chart-bar' },
  { id: 'emerging', label: 'Emerging skills', icon: 'sparkles' },
  { id: 'signals', label: 'Emerging signals', icon: 'activity' },
  { id: 'adoption', label: 'AI adoption', icon: 'users' },
  { id: 'method', label: 'Method & data', icon: 'search' },
];

const status = ref<'loading' | 'done' | 'error' | 'missing'>('loading');
const meta = ref<OccMeta | null>(null);

// ---- filters ----
const sector = ref('');
const occupation = ref('software_engineer');
const country = ref('US');
const fromYear = ref('');
const h = ref(6);
const origin = ref(''); // '' = latest; else an earlier test-period origin

const sectors = computed(() => meta.value?.taxonomy.sectors ?? []);
const occupations = computed(() => sectors.value.find((s) => s.id === sector.value)?.occupations ?? []);
const occName = computed(() => occupations.value.find((o) => o.id === occupation.value)?.name ?? occupation.value);
const countryName = (c: string) => meta.value?.taxonomy.countries[c] ?? c;
const countries = computed(() =>
  (meta.value?.cells ?? []).filter((c) => c.occupation === occupation.value).sort((a, b) => b.ads_last_12m - a.ads_last_12m));
const years = computed(() => [...new Set((meta.value?.history_months ?? []).map((m) => m.slice(0, 4)))]);
const from = computed(() => `${fromYear.value || years.value[0] || '2014'}-01`);

async function loadMeta() {
  status.value = 'loading';
  try {
    meta.value = await fetchOccMeta();
    sector.value = meta.value.taxonomy.sectors[0]?.id ?? '';
    fromYear.value = String(Math.max(Number(years.value[0]), Number(meta.value.last_complete_month.slice(0, 4)) - 6));
    status.value = 'done';
  } catch (e) {
    status.value = String(e).includes('503') ? 'missing' : 'error';
  }
}

watch(occupation, () => {
  if (!countries.value.some((c) => c.country === country.value)) country.value = countries.value[0]?.country ?? 'US';
});

// ---- skill demand ----
const skills = ref<SkillsResponse | null>(null);
const skillsErr = ref(false);
const selected = ref<string | null>(null);
const detail = ref<SkillDetail | null>(null);
const category = ref('');
const search = ref('');
const minAds = ref(5);

async function loadSkills() {
  if (!meta.value) return;
  skillsErr.value = false;
  skills.value = null;
  try {
    skills.value = await fetchSkills(country.value, occupation.value, h.value, origin.value || undefined);
    const rows = skills.value.rows as { skill_id: string }[];
    if (!selected.value || !rows.some((r) => r.skill_id === selected.value)) selected.value = rows[0]?.skill_id ?? null;
  } catch {
    skillsErr.value = true;
  }
}
async function loadDetail() {
  detail.value = null;
  if (!selected.value) return;
  try {
    detail.value = await fetchSkill(selected.value, country.value, occupation.value);
  } catch {
    detail.value = null;
  }
}
watch([country, occupation, h, origin, () => meta.value], loadSkills);
watch([selected, country, occupation], loadDetail);

const latestRows = computed<SkillRow[]>(() => (skills.value?.mode === 'latest' ? skills.value.rows : []));
const asofRows = computed<AsOfRow[]>(() => (skills.value?.mode === 'asof' ? skills.value.rows : []));
const categories = computed(() => [...new Set(latestRows.value.map((r) => r.category).filter((c): c is string => !!c))].sort());
const shownRows = computed(() =>
  latestRows.value.filter((r) => (!category.value || r.category === category.value) &&
    (!search.value || r.skill_name.toLowerCase().includes(search.value.toLowerCase())) && r.count_12m >= minAds.value));
const rising = computed(() => latestRows.value.filter((r) => trendOf(r.growth_lb_pp, r.growth_ub_pp) === 'up')
  .sort((a, b) => (b.change_pp_recent_vs_base ?? 0) - (a.change_pp_recent_vs_base ?? 0)).slice(0, 8));
const falling = computed(() => latestRows.value.filter((r) => trendOf(r.growth_lb_pp, r.growth_ub_pp) === 'down')
  .sort((a, b) => (a.change_pp_recent_vs_base ?? 0) - (b.change_pp_recent_vs_base ?? 0)).slice(0, 8));
const cell = computed(() => skills.value?.cell);
const cellServed = computed(() => cell.value?.accuracy.find((a) => a.served));
const cellNaive = computed(() => cell.value?.accuracy.find((a) => a.method === 'persistence'));
const headline = computed(() => meta.value?.headline[String(h.value)]);
const asofMae = computed(() => {
  const r = asofRows.value;
  return r.length ? r.reduce((s, x) => s + Math.abs(x.forecast - x.actual), 0) / r.length * 100 : null;
});
const selRow = computed(() => latestRows.value.find((r) => r.skill_id === selected.value));
const servedBacktest = computed(() => detail.value?.backtest.filter((b) => b.role === 'test') ?? []);

// ---- emerging ----
const emerging = ref<EmergingResponse | null>(null);
const emFilter = ref<'growing' | 'not_onet' | 'discovered' | 'all'>('growing');
const openRow = ref<string | null>(null);
async function loadEmerging() {
  emerging.value = null;
  try {
    emerging.value = await fetchEmerging(country.value, occupation.value);
  } catch {
    emerging.value = null;
  }
}
const emRows = computed(() => (emerging.value?.rows ?? []).filter((r) => {
  if (emFilter.value === 'growing') return r.growth_lb_pp > 0;
  if (emFilter.value === 'not_onet') return !r.in_onet_for_occupation && r.k_recent > 0;
  if (emFilter.value === 'discovered') return r.origin === 'discovered';
  return true;
}).slice(0, 60));

// ---- adoption ----
const adoption = ref<AdoptionResponse | null>(null);
const adCountry = ref('ALL');
async function loadAdoption() {
  adoption.value = null;
  try {
    adoption.value = await fetchAdoption(occupation.value);
  } catch {
    adoption.value = null;
  }
}
const usageCountries = computed(() => [...new Set((adoption.value?.worker_usage ?? []).filter((w) => w.published_ok).map((w) => w.country))]);
const usage = computed(() => (adoption.value?.worker_usage ?? []).filter((w) => w.country === adCountry.value).sort((a, b) => a.year - b.year));
const rps = computed(() => (adoption.value?.worker_usage_context ?? []).filter((r) => r.group.startsWith('SOC 15')));
const signal = computed(() => (adoption.value?.employer_signal ?? []).filter((s) => s.country === country.value && s.share_3m != null));
function sparkPath(vals: number[], w: number, hgt: number) {
  const max = Math.max(0.01, ...vals);
  return vals.map((v, i) => `${i ? 'L' : 'M'}${((i / Math.max(1, vals.length - 1)) * w).toFixed(1)},${(hgt - (v / max) * hgt).toFixed(1)}`).join(' ');
}
const signalMax = computed(() => Math.max(0.01, ...signal.value.map((s) => s.share_3m ?? 0)));

// ---- method ----
const evaluation = ref<OccEvaluation | null>(null);
async function loadEvaluation() {
  if (evaluation.value) return;
  try {
    evaluation.value = await fetchOccEvaluation();
  } catch {
    evaluation.value = null;
  }
}

// ---- emerging signals (evidence outside the skill's own job-ad series; not a forecast) ----
const signals = ref<SignalsResponse | null>(null);
const sigFilter = ref<'accelerating' | 'adoption' | 'all'>('accelerating');
const sigOpen = ref<string | null>(null);
const passThrough = ref(50);  // scenario only: % of the evidence's recent growth assumed to reach hiring demand
async function loadSignals() {
  signals.value = null;
  try {
    signals.value = await fetchSignals(country.value, occupation.value);
  } catch {
    signals.value = { status: 'failed', rows: [] } as unknown as SignalsResponse;
  }
}
const SIGNAL_TEXT: Record<SignalRow['signal'], string> = {
  accelerating: 'Adoption and related demand both rising',
  some_acceleration: 'Some evidence rising',
  contradictory: 'Evidence points both ways',
  slowing: 'Adoption and related demand both falling',
  some_slowing: 'Some evidence falling',
  no_signal: 'No clear signal',
};
const sigRows = computed(() => (signals.value?.rows ?? []).filter((r) => {
  if (sigFilter.value === 'accelerating') return r.signal === 'accelerating' || r.signal === 'some_acceleration';
  if (sigFilter.value === 'adoption') return r.indicators.length > 0;
  return true;
}));
/** The growth a scenario carries forward: package adoption growth, else related-skill demand. */
function scenarioBasis(r: SignalRow): { g: number; label: string } | null {
  if (r.adoption_g6 != null) return { g: r.adoption_g6, label: 'package adoption (relative downloads)' };
  if (r.related_g6 != null) return { g: r.related_g6, label: 'related-skill job-ad demand' };
  return null;
}
/** Scenario bars: observed, forecast and scenario shares, scaled to the largest of them and the range. */
function scenarioBars(r: SignalRow, g: number) {
  const sc = scenarioShare(r.forecast, g, passThrough.value / 100);
  const bars = [
    { label: 'Last 3 months (observed)', v: r.baseline_share ?? 0, cls: 'obs' },
    { label: 'Job-ad forecast', v: r.forecast, cls: 'fc' },
    { label: 'Scenario (illustration)', v: sc, cls: 'sc' },
  ];
  const top = Math.max(r.high ?? 0, scenarioShare(r.forecast, Math.abs(g), 1), ...bars.map((b) => b.v), 0.01);
  return bars.map((b) => ({ ...b, w: Math.min(100, (b.v / top) * 100) }));
}
const relCorr = (k: string) => signals.value?.relationship.features[k]?.corr;

watch([tab, country, occupation, () => meta.value], () => {
  if (!meta.value) return;
  if (tab.value === 'emerging') loadEmerging();
  if (tab.value === 'signals') loadSignals();
  if (tab.value === 'adoption') loadAdoption();
  if (tab.value === 'method') loadEvaluation();
});
onMounted(() => {
  const t = new URLSearchParams(location.search).get('tab');  // link straight to a section
  if (tabs.some((x) => x.id === t)) tab.value = t as Tab;
  loadMeta();
});

const evidenceLabel = (e: string) => ({ high: 'Strong evidence', medium: 'Some evidence', low: 'Thin evidence' }[e] ?? e);
const confLabel = (c: string) => ({ high: 'High', medium: 'Medium', low: 'Low' }[c] ?? c);
const dirIcon = (d: string) => (d === 'rising' ? 'tup' : d === 'falling' ? 'tdown' : 'arrow');
const healthOk = (s?: string) => s === 'ok' || s === 'cache_only';
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">Occupational forecasting</p>
      <h1>What employers ask for, occupation by occupation</h1>
      <Bubble :size="56" class="intro">
        Skill demand measured from real job ads, per country and occupation, with forecasts that were tested on months the
        models had not seen. Kept separate from the AI outlook tab: its own data, models and tests.
      </Bubble>

      <div v-if="status === 'loading'" class="skel card big-skel" aria-busy="true" aria-label="Loading" />
      <div v-else-if="status === 'missing'" class="state">
        <Bubble :size="64">The occupational forecasts haven’t been built yet on this machine. Run <code>python -m occupational.run</code> in <code>src/backend</code>.</Bubble>
      </div>
      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">Jobee couldn’t load occupational forecasting just now.</Bubble>
        <button type="button" class="btn btn-secondary" @click="loadMeta"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <template v-else-if="meta">
        <!-- global filters: only options the data supports -->
        <section class="card filters" aria-label="Filters">
          <label><span>Country</span>
            <select v-model="country">
              <option v-for="c in countries" :key="c.country" :value="c.country">{{ countryName(c.country) }} · {{ c.ads_last_12m }} ads/yr</option>
            </select>
          </label>
          <label><span>Job sector</span>
            <select v-model="sector"><option v-for="s in sectors" :key="s.id" :value="s.id">{{ s.name }}</option></select>
          </label>
          <label><span>Occupation</span>
            <select v-model="occupation"><option v-for="o in occupations" :key="o.id" :value="o.id">{{ o.name }}</option></select>
          </label>
          <label><span>History from</span>
            <select v-model="fromYear"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select>
          </label>
          <label><span>Forecast horizon</span>
            <select v-model.number="h"><option v-for="x in meta.horizons" :key="x" :value="x">{{ x }} months</option></select>
          </label>
          <label><span>Latest observation</span>
            <select v-model="origin">
              <option value="">{{ month(meta.last_complete_month) }} (latest)</option>
              <option v-for="o in [...meta.asof_origins].reverse()" :key="o" :value="o">{{ month(o) }} (test: forecast vs actual)</option>
            </select>
          </label>
        </section>

        <nav class="seg" aria-label="Sections">
          <button v-for="t in tabs" :key="t.id" type="button" :aria-pressed="tab === t.id" :class="{ on: tab === t.id }" @click="tab = t.id">
            <Icon :name="t.icon" :size="16" /> {{ t.label }}
          </button>
        </nav>

        <!-- ================= SKILL DEMAND ================= -->
        <section v-if="tab === 'demand'" class="stack-col">
          <div v-if="skillsErr" class="card pad">Couldn’t load skills for this selection.</div>
          <div v-else-if="!skills" class="skel card mid-skel" />
          <template v-else>
            <div class="card pad summary">
              <div>
                <p class="kicker">{{ countryName(country) }} · {{ occName }}</p>
                <p class="big">{{ cell?.ads_last_12m.toLocaleString('en') }} <span>eligible job ads in the 12 months to {{ month(meta.last_complete_month) }}</span></p>
                <p class="muted small">Share = ads naming the skill ÷ eligible ads classified into this occupation and country (HN “Who is hiring?” posts; duplicates and posts without a description removed).</p>
                <p v-if="(cell?.ads_last_12m ?? 0) < 100" class="warn small"><Icon name="shield-alert" :size="14" /> Few ads here, so shares move a lot from month to month. Treat forecasts as rough.</p>
              </div>
              <div class="verdict-box">
                <p class="kicker">How the {{ h }}-month forecast tested</p>
                <template v-if="cellServed && cellNaive">
                  <p class="small">Here ({{ cellServed.n }} past forecasts): {{ methodName(cellServed.method) }} was off by <b>{{ cellServed.mae_pp.toFixed(2) }} pp</b> on average; “no change” by <b>{{ cellNaive.mae_pp.toFixed(2) }} pp</b>.</p>
                  <span class="verdict" :class="cellServed.mae_pp < cellNaive.mae_pp ? 'yes' : cellServed.method === 'persistence' ? 'same' : 'no'">
                    <Icon :name="cellServed.mae_pp < cellNaive.mae_pp ? 'check' : 'x'" :size="14" />
                    {{ cellServed.method === 'persistence' ? 'Shown forecast is “no change”' : cellServed.mae_pp < cellNaive.mae_pp ? 'Beats “no change” here' : 'Does not beat “no change” here' }}
                  </span>
                </template>
                <p v-else class="small warn">Too few ads in this country and occupation for tested forecasts (each test needs ≥ {{ meta.rules.min_target_ads }} ads in the target months). Forecasts below use the method chosen across all series.</p>
                <p v-if="headline" class="muted small">All series: {{ methodName(headline.served) }}, {{ headline.test_mae_pp?.toFixed(2) }} pp vs {{ headline.persistence_test_mae_pp?.toFixed(2) }} pp for “no change”; 80% ranges held {{ pct(headline.coverage_80, 0) }} of actual values.</p>
              </div>
            </div>

            <!-- as-of mode: what the model said then vs what happened -->
            <div v-if="skills.mode === 'asof'" class="card pad">
              <h2>Forecast made with data to {{ month(origin) }} vs what happened</h2>
              <p v-if="!asofRows.length" class="muted">No tested forecasts for this country and occupation at that date (too few ads in the target months).</p>
              <template v-else>
                <p class="small">Target: the 3 months ending {{ month(asofRows[0].target_month) }}. Average miss over {{ asofRows.length }} skills: <b>{{ asofMae?.toFixed(2) }} pp</b>.</p>
                <table class="tbl">
                  <thead><tr><th>Skill</th><th>12-month share then</th><th>Forecast</th><th>Actual</th><th>Miss</th></tr></thead>
                  <tbody>
                    <tr v-for="r in asofRows.slice(0, 40)" :key="r.skill_id">
                      <td>{{ r.skill_name }}</td><td>{{ pct(r.share_12m) }}</td><td>{{ pct(r.forecast) }}</td><td>{{ pct(r.actual) }}</td>
                      <td>{{ pp((r.forecast - r.actual) * 100) }}</td>
                    </tr>
                  </tbody>
                </table>
              </template>
            </div>

            <template v-else>
              <div class="two">
                <div class="card pad">
                  <h2><Icon name="tup" :size="18" /> Growing</h2>
                  <p class="muted small">Last 6 months vs the 12 before; listed only when the rise is clear of noise (80% band above zero).</p>
                  <ul class="movers">
                    <li v-for="r in rising" :key="r.skill_id"><button type="button" @click="selected = r.skill_id">{{ r.skill_name }}</button><b>{{ pp(r.change_pp_recent_vs_base) }}</b></li>
                    <li v-if="!rising.length" class="muted small">No skill rose clearly beyond noise.</li>
                  </ul>
                </div>
                <div class="card pad">
                  <h2><Icon name="tdown" :size="18" /> Declining</h2>
                  <p class="muted small">Same test, falling (80% band below zero).</p>
                  <ul class="movers">
                    <li v-for="r in falling" :key="r.skill_id"><button type="button" @click="selected = r.skill_id">{{ r.skill_name }}</button><b>{{ pp(r.change_pp_recent_vs_base) }}</b></li>
                    <li v-if="!falling.length" class="muted small">No skill fell clearly beyond noise.</li>
                  </ul>
                </div>
              </div>

              <!-- selected skill -->
              <div v-if="selRow" class="card pad detail">
                <div class="detail-head">
                  <div>
                    <p class="kicker">{{ selRow.category }} <span v-if="selRow.skill_status !== 'known'" class="tag">{{ TAXONOMY_TEXT[selRow.skill_status] ?? selRow.skill_status }}</span>
                      <span class="tag" :class="selRow.in_onet ? 'ok' : 'new'">{{ selRow.in_onet ? 'In O*NET tech list' : 'Not in O*NET tech list' }}</span></p>
                    <h2>{{ selRow.skill_name }}</h2>
                  </div>
                  <div class="nums">
                    <div><span>Last 12 months</span><b>{{ pct(selRow.share_12m) }}</b><small>{{ selRow.count_12m }} of {{ selRow.ads_12m }} ads</small></div>
                    <div><span>Last 3 months</span><b>{{ pct(selRow.last_share_3m) }}</b><small>{{ selRow.last_count_3m }} of {{ selRow.last_ads_3m }}</small></div>
                    <div><span>{{ month(selRow.target_month) }} forecast</span><b>{{ pct(selRow.forecast) }}</b><small>likely {{ pct(selRow.low) }}–{{ pct(selRow.high) }}</small></div>
                  </div>
                </div>
                <ShareChart v-if="detail" :history="detail.history" :forecast="detail.forecast" :backtest="servedBacktest"
                            :from="from" :h="h" :label="`${selRow.skill_name}: share of ${occName} ads in ${countryName(country)}, history and forecast`" />
                <div v-else class="skel chart-skel" />
                <p class="key"><span class="k-line" /> share of ads, 3-month window <span class="k-dot" /> forecast <span class="k-bar" /> likely range (80%)
                  <span class="k-ring" /> earlier test forecasts at {{ h }} months <span class="k-vol" /> ads per month</p>
                <p v-if="!selRow.backtested" class="warn small"><Icon name="shield-alert" :size="14" /> Found by the emerging-skill detector using today’s data, so it was not part of the backtest; its forecast uses the method chosen for all skills.</p>
                <p class="small muted">Method: {{ methodName(selRow.model) }}. {{ STATUS_TEXT[selRow.model_status] }}. {{ evidenceLabel(selRow.evidence) }} ({{ selRow.ads_12m }} ads in 12 months).</p>
                <div v-if="detail" class="detail-grid">
                  <div>
                    <h3>Recent ads naming it</h3>
                    <ul class="ex">
                      <li v-for="e in detail.examples" :key="e.url"><a :href="e.url" target="_blank" rel="noopener">{{ e.title_raw.slice(0, 90) }}</a> <span class="muted">· {{ e.source === 'adzuna' ? 'Adzuna' : 'HN' }} · {{ month(e.month) }}</span></li>
                      <li v-if="!detail.examples.length" class="muted small">None in this country and occupation.</li>
                    </ul>
                  </div>
                  <div>
                    <h3>Adzuna live-ad snapshot</h3>
                    <p class="muted small">Different population (job boards) and only a ~500-character snippet per ad, so shares run lower. Shown as a cross-check, never mixed into the series above.</p>
                    <ul class="ex">
                      <li v-for="a in detail.adzuna" :key="a.retrieved_at">{{ month(a.retrieved_at) }} ({{ a.retrieved_at }}): {{ pct(a.share) }} of {{ a.n_ads }} ads</li>
                      <li v-if="!detail.adzuna.length" class="muted small">No snapshot names it for this country and occupation.</li>
                    </ul>
                    <h3>Spellings seen</h3>
                    <p class="small">{{ detail.skill.aliases_seen.join(', ') || '—' }}</p>
                  </div>
                </div>
              </div>

              <!-- all skills -->
              <div class="card pad">
                <div class="tbl-head">
                  <h2>All tracked skills</h2>
                  <div class="tbl-filters">
                    <input v-model="search" type="search" placeholder="Find a skill" aria-label="Find a skill">
                    <select v-model="category" aria-label="Category"><option value="">All categories</option><option v-for="c in categories" :key="c" :value="c">{{ c }}</option></select>
                    <select v-model.number="minAds" aria-label="Minimum ads"><option :value="1">≥ 1 ad</option><option :value="5">≥ 5 ads</option><option :value="20">≥ 20 ads</option></select>
                  </div>
                </div>
                <div class="scroll">
                  <table class="tbl click">
                    <thead><tr><th>Skill</th><th>12-month share</th><th>Ads</th><th>Last 3 months</th><th>Forecast, {{ h }} mo</th><th>Likely range</th><th>Direction</th><th>Evidence</th></tr></thead>
                    <tbody>
                      <tr v-for="r in shownRows" :key="r.skill_id" :class="{ on: r.skill_id === selected }" tabindex="0"
                          @click="selected = r.skill_id" @keydown.enter="selected = r.skill_id">
                        <td>{{ r.skill_name }} <span v-if="r.skill_status !== 'known'" class="tag">{{ TAXONOMY_TEXT[r.skill_status] ?? r.skill_status }}</span><span v-if="!r.in_onet" class="tag new" title="Not among O*NET 31.0 technology skills (tools and software). Professional skills are rated separately in O*NET and are not checked here.">not in O*NET tech</span></td>
                        <td>{{ pct(r.share_12m) }}</td><td>{{ r.count_12m }}</td><td>{{ pct(r.last_share_3m) }}</td>
                        <td><b>{{ pct(r.forecast) }}</b></td><td>{{ pct(r.low) }}–{{ pct(r.high) }}</td>
                        <td><Icon :name="dirIcon(r.direction)" :size="14" /> {{ r.direction }}</td><td>{{ r.evidence }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p class="muted small">
                  Forecasts are for the 3 months ending {{ month(latestRows[0]?.target_month) }}.
                  Direction compares the forecast with the last 3 months’ share: rising or falling when it differs by at least {{ meta?.rules.direction_label_pp ?? 1 }} pp, otherwise flat (about stable).
                </p>
              </div>
            </template>
          </template>
        </section>

        <!-- ================= EMERGING ================= -->
        <section v-else-if="tab === 'emerging'" class="stack-col">
          <div v-if="!emerging" class="skel card mid-skel" />
          <template v-else>
            <div class="card pad">
              <h2>Which skills are gaining ground for {{ occName }} in {{ countryName(country) }}?</h2>
              <p class="small">Ranked by the <b>least</b> the share has plausibly grown (the 90% lower bound of last 6 months vs the 12 before), so a term going from 1 ad to 3 cannot top the list on percentage growth.
                New terms come from the ad text itself, not only from the vocabulary: a term is <b>newly detected</b> only with ≥ {{ (emerging.registry.thresholds.strong as any).recent_ads }} recent ads from ≥ {{ (emerging.registry.thresholds.strong as any).employers }} employers and a first appearance in the last {{ emerging.registry.thresholds.new_months }} months; weaker or older evidence stays <b>under review</b>.</p>
              <div class="chips">
                <button v-for="f in ([['growing', 'Clearly growing'], ['not_onet', 'Not in O*NET for this occupation'], ['discovered', 'Found in ad text'], ['all', 'All']] as const)" :key="f[0]"
                        type="button" :class="{ on: emFilter === f[0] }" @click="emFilter = f[0]">{{ f[1] }}</button>
              </div>
              <div class="scroll">
                <table class="tbl click">
                  <thead><tr><th>Skill</th><th>Status</th><th>O*NET</th><th>First seen</th><th>Ads: recent / before</th><th>Share now</th><th>Change</th><th>Growth, at least</th><th>Employers</th><th>Confidence</th></tr></thead>
                  <tbody>
                    <template v-for="r in emRows" :key="r.skill_id">
                      <tr tabindex="0" @click="openRow = openRow === r.skill_id ? null : r.skill_id" @keydown.enter="openRow = openRow === r.skill_id ? null : r.skill_id">
                        <td>{{ r.name }}</td><td><span class="tag">{{ TAXONOMY_TEXT[r.status] ?? r.status }}</span></td>
                        <td>{{ r.in_onet_for_occupation ? 'yes' : r.in_onet ? 'other occ.' : 'no' }}</td>
                        <td>{{ month(r.first_seen_any || r.first_seen) }}</td><td>{{ r.k_recent }} / {{ r.k_base }}</td>
                        <td>{{ pct(r.share_recent) }}</td><td>{{ pp(r.change_pp) }}</td><td>{{ pp(r.growth_lb_pp, 2) }}</td>
                        <td>{{ r.employers }}</td><td :class="'c-' + r.confidence">{{ confLabel(r.confidence) }}</td>
                      </tr>
                      <tr v-if="openRow === r.skill_id" class="more"><td colspan="10">
                        <p v-if="r.reason" class="small">{{ r.reason }}</p>
                        <p class="small muted">Recent window {{ r.recent_window }} ({{ r.n_recent }} ads); before {{ r.base_window }} ({{ r.n_base }} ads). Seen in {{ r.months_present }} of the last 6 months.</p>
                        <p v-if="r.aliases_seen.length" class="small">Spellings merged: {{ r.aliases_seen.join(', ') }}</p>
                        <ul v-if="r.evidence?.length" class="ex"><li v-for="e in r.evidence" :key="e.ad_id"><a :href="e.url" target="_blank" rel="noopener">{{ e.employer || 'ad' }}, {{ month(e.month) }}</a>: “{{ e.snippet }}”</li></ul>
                      </td></tr>
                    </template>
                    <tr v-if="!emRows.length"><td colspan="10" class="muted">Nothing here passes the evidence bar for this selection.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-if="emerging.backcheck" class="card pad">
              <h2>Would the detector have found recent skills in time?</h2>
              <p class="small">Test: {{ emerging.backcheck.skills.length }} recent skills were removed from the vocabulary and the detector was replayed every quarter from {{ month(emerging.backcheck.as_of_months[0]) }}, each time using only ads available then. Reference point: {{ emerging.backcheck.reference }}.</p>
              <div class="scroll">
                <table class="tbl">
                  <thead><tr><th>Withheld skill</th><th>First flagged</th><th>First “newly detected”</th><th>Plainly in demand (≥ 2%)</th><th>Lead</th></tr></thead>
                  <tbody>
                    <tr v-for="s in emerging.backcheck.skills" :key="s.skill_id">
                      <td>{{ s.name }}</td><td>{{ s.first_flagged ? month(s.first_flagged) : 'missed' }}</td>
                      <td>{{ s.first_newly_detected ? month(s.first_newly_detected) : '—' }}</td>
                      <td>{{ s.share_reached_2pct_us_swe ? month(s.share_reached_2pct_us_swe) : 'not yet' }}</td>
                      <td>{{ s.first_flagged && s.share_reached_2pct_us_swe ? (s.first_flagged <= s.share_reached_2pct_us_swe ? 'flagged first' : 'flagged after') : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="muted small">Misses are mostly lower-case phrases (“vector databases”, “prompt engineering”): the detector reads capitalised or tech-shaped terms only.</p>
            </div>
          </template>
        </section>

        <!-- ================= EMERGING SIGNALS ================= -->
        <section v-else-if="tab === 'signals'" class="stack-col">
          <div v-if="!signals" class="skel card mid-skel" />
          <div v-else-if="signals.status !== 'ok'" class="card pad">
            <h2>Emerging signals are not available</h2>
            <p class="small">The last pipeline run did not produce them<template v-if="signals.error"> ({{ signals.error }})</template>. The job-ad forecast on “Skill demand” is unaffected.</p>
          </div>
          <template v-else>
            <div class="card pad">
              <h2>Is the job-ad forecast missing an emerging skill?</h2>
              <p class="small">Big rises in hiring demand can start with little warning in a skill’s own job-ad history. This view puts evidence from outside that history next to the forecast:
                <b>package adoption</b> (PyPI and npm downloads relative to a skill-neutral basket of packages) and <b>related-skill demand</b> (job-ad share of skills in the same technology family, across every IT cell).
                Downloads include automated installs: they show ecosystem adoption, <b>not hiring</b>.</p>
              <div class="verdicts">
                <p class="small"><span class="tag" :class="signals.adjusted_forecast.validated ? 'ok' : 'new'">{{ signals.adjusted_forecast.validated ? 'validated' : 'not shown' }}</span>
                  <b>Signal-adjusted forecast.</b>
                  <template v-if="signals.adjusted_forecast.validated"> Passed its backtest; shown next to the job-ad forecast.</template>
                  <template v-else> A model adding this evidence to the job-ad forecast did not beat the job-ad forecast on held-back months
                    (test error {{ signals.test_summary.hybrid?.mae_pp.toFixed(2) }} pp vs {{ signals.test_summary.baseline?.mae_pp.toFixed(2) }} pp, {{ signals.test_summary.baseline?.n.toLocaleString('en') }} forecasts), so no adjusted number is shown.</template></p>
                <p class="small"><span class="tag" :class="signals.radar.validated ? 'ok' : 'new'">{{ signals.radar.validated ? 'validated' : 'not shown' }}</span>
                  <b>Rise alerts.</b>
                  <template v-if="signals.radar.validated"> Probability of a rise of ≥ {{ signals.radar.rise_pp }} pp in {{ signals.horizon }} months, tested on held-back months.</template>
                  <template v-else> On held-back months, alerts using this evidence caught {{ signals.radar_test.hybrid.true_alerts }} of {{ signals.radar_test.hybrid.positives }} real rises of ≥ {{ signals.radar.rise_pp }} pp with {{ signals.radar_test.hybrid.alerts - signals.radar_test.hybrid.true_alerts }} false alarms;
                    job-ad history alone caught {{ signals.radar_test.own.true_alerts }} with {{ signals.radar_test.own.alerts - signals.radar_test.own.true_alerts }} false alarms. Not reliably better, so no alert or probability is shown.</template></p>
                <p class="small muted">Historically (pooled across countries and occupations, {{ signals.relationship.period }}), 6-month package adoption growth correlated {{ relCorr('adoption_g6')?.toFixed(2) ?? '–' }} with the next {{ signals.horizon }} months’ change in a skill’s job-ad share, and related-skill demand {{ relCorr('related_g6')?.toFixed(2) ?? '–' }}: a weak link, too weak to move a forecast.</p>
              </div>
              <div class="chips">
                <button v-for="f in ([['accelerating', 'Rising evidence'], ['adoption', 'With package data'], ['all', 'All']] as const)" :key="f[0]"
                        type="button" :class="{ on: sigFilter === f[0] }" @click="sigFilter = f[0]">{{ f[1] }}</button>
              </div>
              <div class="scroll">
                <table class="tbl click">
                  <thead><tr><th>Skill</th><th>Last 3 months</th><th>Job-ad forecast, {{ signals.horizon }} mo</th><th>Change</th><th>Adoption, 6 mo</th><th>Related demand, 6 mo</th><th>Evidence</th><th>Job-ad data</th></tr></thead>
                  <tbody>
                    <template v-for="r in sigRows" :key="r.skill_id">
                      <tr tabindex="0" :class="{ on: sigOpen === r.skill_id }" @click="sigOpen = sigOpen === r.skill_id ? null : r.skill_id" @keydown.enter="sigOpen = sigOpen === r.skill_id ? null : r.skill_id">
                        <td>{{ r.skill_name }}</td><td>{{ pct(r.baseline_share) }}</td><td><b>{{ pct(r.forecast) }}</b></td>
                        <td><Icon :name="dirIcon(r.direction)" :size="13" /> {{ pp(r.change_pp) }}</td>
                        <td>{{ growth(r.adoption_g6) }}</td><td>{{ growth(r.related_g6) }}</td>
                        <td>{{ SIGNAL_TEXT[r.signal] }}</td>
                        <td :class="r.evidence_cell === 'large' ? 'c-high' : r.evidence_cell === 'medium' ? 'c-medium' : 'c-low'">{{ r.evidence_cell }} ({{ r.last_ads_3m }} ads)</td>
                      </tr>
                      <tr v-if="sigOpen === r.skill_id" class="more"><td colspan="8">
                        <div class="sig-detail">
                          <div>
                            <h3>Evidence</h3>
                            <p v-if="!r.indicators.length" class="small muted">No package is mapped to this skill (taxonomy/skill_signals.json); only related-skill demand applies.</p>
                            <table v-else class="tbl">
                              <thead><tr><th>Package</th><th>Latest month</th><th>Downloads, 3 mo</th><th>vs 6 mo before</th><th>vs 12 mo before</th><th>History</th><th>Quality</th></tr></thead>
                              <tbody>
                                <tr v-for="i in r.indicators" :key="i.source + i.package">
                                  <td><a :href="i.url" target="_blank" rel="noopener">{{ i.package }}</a> <span class="tag">{{ i.source }}</span></td>
                                  <td>{{ month(i.latest_month) }}<span v-if="!i.fresh" class="tag new">stale</span></td>
                                  <td>{{ i.downloads_3m != null ? Math.round(i.downloads_3m).toLocaleString('en') : 'too few' }}</td>
                                  <td>{{ growth(i.growth_vs_6m_before) }}</td><td>{{ growth(i.growth_vs_12m_before) }}</td>
                                  <td>{{ i.months_of_history }} mo</td>
                                  <td :class="i.quality === 'strong' ? 'c-high' : i.quality === 'moderate' ? 'c-medium' : 'c-low'">{{ i.quality }}</td>
                                </tr>
                              </tbody>
                            </table>
                            <p class="small muted"><template v-if="r.indicators.length">{{ r.indicators[0].window }}. Growth is relative to the reference basket, so ecosystem-wide growth does not count. </template>Related skills: {{ r.related_skills.join(', ') || 'its curated category' }} (their demand {{ growth(r.related_g6) }} over 6 months, {{ growth(r.related_g12) }} over 12).</p>
                          </div>
                          <div v-if="scenarioBasis(r)" class="scenario">
                            <h3>Scenario <span class="tag new">not a forecast</span></h3>
                            <p class="small">If <b>{{ passThrough }}%</b> of the recent growth in {{ scenarioBasis(r)!.label }} ({{ growth(scenarioBasis(r)!.g) }} over 6 months) carried into job-ad demand over the next {{ signals.horizon }} months:</p>
                            <input v-model.number="passThrough" type="range" min="0" max="100" step="10" aria-label="Share of the evidence's growth that reaches hiring demand" />
                            <div class="bars">
                              <div v-for="b in scenarioBars(r, scenarioBasis(r)!.g)" :key="b.label" class="bar-row">
                                <span>{{ b.label }}</span><i :class="b.cls" :style="{ width: b.w + '%' }" /><b>{{ pct(b.v) }}</b>
                              </div>
                            </div>
                            <p class="small muted">The pass-through is your assumption, not an estimate: historically this kind of evidence explained little of the next {{ signals.horizon }} months’ change. The job-ad forecast’s likely range is {{ pct(r.low) }}–{{ pct(r.high) }}.</p>
                          </div>
                        </div>
                      </td></tr>
                    </template>
                    <tr v-if="!sigRows.length"><td colspan="8" class="muted">No skill in this selection.</td></tr>
                  </tbody>
                </table>
              </div>
              <p class="muted small">Sources: <a :href="signals.sources.pypi.url" target="_blank" rel="noopener">{{ signals.sources.pypi.name }}</a>; <a :href="signals.sources.npm.url" target="_blank" rel="noopener">{{ signals.sources.npm.name }}</a>.
                Package data {{ month(signals.coverage.package_months.npm?.[0]) }} to {{ month(signals.coverage.package_months.npm?.[1] ?? signals.coverage.package_months.pypi?.[1]) }}<template v-if="signals.package_health?.status && signals.package_health.status !== 'ok'">; last refresh: {{ signals.package_health.status }}, showing cached observations</template>.</p>
            </div>
          </template>
        </section>

        <!-- ================= ADOPTION ================= -->
        <section v-else-if="tab === 'adoption'" class="stack-col">
          <div v-if="!adoption" class="skel card mid-skel" />
          <template v-else>
            <div class="card pad">
              <p class="kicker">A · Worker AI usage <span class="tag ok">measured</span></p>
              <h2>How many {{ occName }}s say they use AI tools at work?</h2>
              <label class="inline">Respondents in
                <select v-model="adCountry">
                  <option v-for="c in usageCountries" :key="c" :value="c">{{ c === 'ALL' ? 'all countries (survey population)' : countryName(c) }}</option>
                </select>
              </label>
              <div v-if="usage.length" class="bars">
                <div v-for="u in usage" :key="u.year" class="bar-row">
                  <span class="yr">{{ u.year }}</span>
                  <div class="bar-track">
                    <template v-if="u.published_ok && u.share_using != null">
                      <span class="bar-fill" :style="{ width: `${u.share_using * 100}%` }" />
                      <span class="ci" :style="{ left: `${(u.ci_low ?? 0) * 100}%`, width: `${((u.ci_high ?? 0) - (u.ci_low ?? 0)) * 100}%` }" />
                    </template>
                  </div>
                  <span class="val">{{ u.published_ok ? pct(u.share_using, 0) : `n=${u.n_respondents}, too few` }}</span>
                  <span class="muted small">n = {{ u.n_respondents.toLocaleString('en') }}</span>
                </div>
              </div>
              <p v-else class="muted">This occupation is not a category in the survey for this selection.</p>
              <p class="small muted">Stack Overflow Developer Survey, employed respondents whose main role is {{ usage[0]?.devtypes ?? '—' }}. Self-selected respondents, not a sample of all workers. Bars show the 95% range from sample size.</p>
              <p v-if="usage[0]?.comparability_note" class="warn small"><Icon name="shield-alert" :size="14" /> {{ usage[0].comparability_note }}</p>
              <p class="small muted">2025 split “Yes” into daily / weekly / monthly use; all count as using. {{ adoption.not_found.worker_usage_forecast }}</p>
              <details v-if="rps.length" class="notes">
                <summary>Context: all computer and mathematical workers, US (RPS)</summary>
                <p class="small">{{ rps[0].population }}; {{ rps[0].occupation_scope }}.</p>
                <p class="small">{{ rps.map((r) => `${r.quarter}: ${pct(r.share_using, 0)}`).join(' · ') }}</p>
              </details>
            </div>

            <div class="card pad">
              <p class="kicker">B · Employer deployment in this occupation’s work</p>
              <h2>Not measured directly</h2>
              <p class="small">{{ adoption.not_found.employer_deployment_by_occupation }}</p>
              <h3>Proxy <span class="tag new">proxy, not a deployment rate</span>: ads expecting the hire to use AI tools · {{ countryName(country) }}</h3>
              <svg v-if="signal.length > 2" viewBox="0 0 600 120" preserveAspectRatio="none" class="spark" role="img" aria-label="Share of ads expecting AI tool use over time">
                <path :d="sparkPath(signal.map((s) => s.share_3m ?? 0), 600, 110)" />
              </svg>
              <p v-if="signal.length" class="small">{{ month(signal[0].month) }}: {{ pct(signal[0].share_3m) }} → {{ month(signal.at(-1)!.month) }}: <b>{{ pct(signal.at(-1)!.share_3m) }}</b> of ads (3-month window; peak {{ pct(signalMax) }}).</p>
              <p v-else class="muted small">Not enough ads in this country and occupation.</p>
              <p class="muted small">{{ adoption.employer_signal[0]?.definition }}</p>
            </div>

            <div class="card pad">
              <p class="kicker">C · Task exposure <span class="tag">exposure, not adoption</span></p>
              <ul class="ex">
                <li v-for="e in adoption.task_exposure" :key="e.onet_code">{{ e.onet_title }} ({{ e.onet_code }}): <b>{{ Math.round(e.usage_percentile * 100) }}th percentile</b> of occupations by Claude work usage ({{ e.as_of }})</li>
                <li v-if="!adoption.task_exposure.length" class="muted small">No exposure figure for this occupation’s O*NET codes.</li>
              </ul>
              <p class="muted small">{{ adoption.task_exposure[0]?.definition }}</p>
            </div>

            <details class="card pad notes">
              <summary>Sources and what each one measures</summary>
              <div class="notes-scroll">
                <table class="tbl notes-tbl">
                  <thead>
                    <tr>
                      <th class="col-source">Source</th>
                      <th class="col-type">Type</th>
                      <th class="col-pop">Population</th>
                      <th class="col-def">Definition</th>
                      <th class="col-period">Period</th>
                      <th class="col-lim">Limitation</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="s in adoption.sources" :key="s.id">
                      <td class="col-source">{{ s.name }}</td>
                      <td class="col-type"><span class="tag">{{ s.measure_type }}</span></td>
                      <td class="col-pop">{{ s.population }}</td>
                      <td class="col-def">{{ s.definition }}</td>
                      <td class="col-period">{{ s.period }}</td>
                      <td class="col-lim">{{ s.limitation ?? '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </template>
        </section>

        <!-- ================= METHOD ================= -->
        <section v-else class="stack-col">
          <div class="card pad">
            <h2>Versions and dates</h2>
            <dl class="kv">
              <dt>Latest observation</dt><dd>{{ month(meta.last_complete_month) }} ({{ month(meta.partial_month) }} still collecting, not used)</dd>
              <dt>Forecast made</dt><dd>{{ new Date(meta.made_at).toLocaleString('en') }}</dd>
              <dt>History</dt><dd>from {{ month(meta.history_start) }}</dd>
              <dt>Run / model / data</dt><dd><code>{{ meta.run_id }}</code> · model <code>{{ meta.model_version }}</code> · data <code>{{ meta.data_version }}</code></dd>
              <dt>Taxonomy / registry</dt><dd>{{ meta.taxonomy_version }} · registry v{{ meta.registry_version }} · {{ meta.taxonomy.onet_release }}</dd>
              <dt>Ads</dt><dd>{{ meta.counts.ads.toLocaleString('en') }} read · {{ meta.counts.eligible.toLocaleString('en') }} eligible · {{ meta.counts.classified.toLocaleString('en') }} in a tracked occupation · {{ meta.counts.series.toLocaleString('en') }} skill series</dd>
              <dt>Target</dt><dd>{{ meta.target }}</dd>
              <dt>Split</dt><dd>train targets {{ meta.split.train_targets }} · validation {{ meta.split.validation_targets }} (chooses the method) · test {{ meta.split.test_targets }} (untouched until scoring)</dd>
            </dl>
          </div>
          <div class="card pad">
            <h2>Every method on held-back months</h2>
            <div v-if="!evaluation" class="skel line" />
            <template v-else>
              <div v-for="(v, hh) in evaluation.horizons" :key="hh" class="scroll">
                <h3>{{ hh }} months ahead · shown: {{ methodName(v.served) }} <span class="tag">{{ v.status.replace(/_/g, ' ') }}</span></h3>
                <table class="tbl">
                  <thead><tr><th>Method</th><th>Validation error</th><th>Test error</th><th>Test vs “no change”</th><th>Direction right*</th><th>80% range held</th><th>Range width</th></tr></thead>
                  <tbody>
                    <tr v-for="(s, m) in v.scores.test" :key="m" :class="{ shown: m === v.served }">
                      <td>{{ METHOD_NAMES[m] ?? m }}<span v-if="evaluation.post_hoc_methods.includes(String(m))" class="tag new">added after first test</span></td>
                      <td>{{ v.scores.validation[m]?.mae_pp.toFixed(2) }} pp</td><td>{{ s.mae_pp.toFixed(2) }} pp</td>
                      <td>{{ s.mae_ratio_vs_persistence != null ? `${Math.round((s.mae_ratio_vs_persistence - 1) * 100)}%` : '—' }}</td>
                      <td>{{ s.direction_acc != null ? pct(s.direction_acc, 0) : '—' }}</td>
                      <td>{{ pct(v.interval_test[m]?.coverage_80, 0) }}</td><td>{{ v.interval_test[m]?.mean_width_pp.toFixed(1) }} pp</td>
                    </tr>
                  </tbody>
                </table>
                <p class="muted small">{{ v.scores.test[v.served]?.n.toLocaleString('en') }} test forecasts (series × origin). Errors are the average absolute miss in share points.</p>
              </div>
              <p class="muted small">* Among forecasts where the share really moved ≥ {{ evaluation.rules.material_change_pp }} pp from its last-3-months share, by more than sampling noise: did the forecast land on the same side of that share? “No change” scores 0% by construction.</p>
            </template>
          </div>
          <div class="card pad">
            <h2>Sources</h2>
            <ul class="ex">
              <li v-for="(s, k) in meta.source_health" :key="k"><Icon :name="healthOk(s.status) ? 'check' : 'shield-alert'" :size="14" /> <b>{{ k }}</b>: {{ s.status }}</li>
            </ul>
            <h3>Known limitations</h3>
            <ul class="lim small">
              <li>Skill history comes from Hacker News “Who is hiring?” posts: tech companies, mostly US startups. It is a real, dated record, but not the whole labour market.</li>
              <li>A post hiring for several occupations counts for each; its skills are attributed to all of them.</li>
              <li>Data Analyst and Data Scientist have few HN ads per month, so their shares and forecasts are rough; the page says so where it applies.</li>
              <li>Adzuna (free tier) gives only current ads and snippets, so it is a dated cross-check that builds history from today, never back-filled.</li>
              <li>Comments are fetched today, so later edits or deletions are reflected (no point-in-time copies exist).</li>
              <li>Worker AI usage comes from a self-selected developer survey with three annual readings; no forecast is published for it.</li>
            </ul>
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
h3 { font-size: 13.5px; margin: 12px 0 6px; }
.intro { margin-bottom: 18px; max-width: 760px; }
.big-skel { height: 420px; } .mid-skel { height: 300px; } .chart-skel { height: 260px; }
.pad { padding: 20px 24px; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; padding: 16px 20px; }
.filters label, .inline { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); }
.inline { flex-direction: row; align-items: center; gap: 8px; margin: 6px 0 10px; }
select, input[type='search'] { font: inherit; font-size: 13.5px; font-weight: 700; color: var(--ink); padding: 7px 9px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; min-width: 0; }
.seg { display: flex; gap: 6px; flex-wrap: wrap; margin: 16px 0; }
.seg button { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 13px; font-weight: 800; padding: 8px 14px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; cursor: pointer; color: var(--ink); }
.seg button.on { background: var(--yellow); border-color: var(--orange); }
.stack-col { display: flex; flex-direction: column; gap: 16px; }
.summary { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 20px; }
.big { font-size: 26px; font-weight: 900; margin: 4px 0; } .big span { font-size: 13px; font-weight: 700; color: var(--muted); }
.small { font-size: 12.5px; line-height: 1.5; }
.muted { color: var(--muted); }
.warn { color: var(--amber-ink); font-weight: 700; display: flex; gap: 6px; align-items: flex-start; }
.verdict-box { display: flex; flex-direction: column; gap: 6px; border-left: 2px solid var(--line); padding-left: 18px; }
.verdict { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.verdict.yes { background: #e7f4ea; color: #1e5e30; } .verdict.no { background: #fdecea; color: #a12a22; } .verdict.same { background: #f0efec; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.movers { list-style: none; padding: 0; margin: 6px 0 0; display: flex; flex-direction: column; gap: 4px; }
.movers li { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; border-bottom: 1px solid var(--line); padding: 4px 0; }
.movers button { font: inherit; font-weight: 700; background: none; border: 0; padding: 0; cursor: pointer; color: var(--ink); text-align: left; }
.movers button:hover { text-decoration: underline; }
.detail-head { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
.nums { display: flex; gap: 18px; flex-wrap: wrap; }
.nums div { display: flex; flex-direction: column; } .nums span { font-size: 11px; font-weight: 800; color: var(--muted); }
.nums b { font-size: 20px; font-weight: 900; } .nums small { font-size: 11px; color: var(--muted); font-weight: 700; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 6px; }
.key { font-size: 11px; font-weight: 700; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: 4px 0 8px; }
.k-line { width: 16px; height: 2px; background: var(--ink); } .k-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--ink); margin-left: 6px; }
.k-bar { width: 6px; height: 14px; border-radius: 3px; background: var(--yellow); margin-left: 6px; }
.k-ring { width: 8px; height: 8px; border-radius: 50%; border: 2px solid var(--orange); margin-left: 6px; } .k-vol { width: 10px; height: 8px; background: #e4e1da; margin-left: 6px; }
.tag { display: inline-block; margin-left: 6px; padding: 1px 7px; border-radius: 999px; background: #f0efec; color: var(--ink); font-size: 10px; font-weight: 800; letter-spacing: 0; text-transform: none; vertical-align: 1px; }
.tag.ok { background: #e7f4ea; color: #1e5e30; } .tag.new { background: var(--cream); color: var(--amber-ink); }
.tbl-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; align-items: center; }
.tbl-filters { display: flex; gap: 8px; flex-wrap: wrap; }
.scroll { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl th:first-child, .tbl td:first-child { text-align: left; white-space: normal; }
.tbl th { font-size: 11px; font-weight: 800; color: var(--muted); }
.tbl.click tbody tr { cursor: pointer; } .tbl.click tbody tr:hover, .tbl tr.on { background: #fffaf0; }
.tbl tr.shown td { font-weight: 800; }
.tbl tr.more td { background: #faf9f6; white-space: normal; text-align: left; }
.c-high { color: #1e5e30; font-weight: 800; } .c-medium { color: var(--amber-ink); font-weight: 800; } .c-low { color: var(--muted); }
.verdicts { display: flex; flex-direction: column; gap: 6px; margin: 10px 0; }
.verdicts .tag { margin: 0 6px 0 0; }
.sig-detail { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 24px; padding: 6px 0; }
.sig-detail h3 { font-size: 13px; margin: 0 0 4px; }
.scenario input { width: 100%; }
.bar-row { display: grid; grid-template-columns: 150px 1fr 52px; gap: 8px; align-items: center; font-size: 12px; }
.bar-row i { display: block; height: 10px; border-radius: 3px; background: var(--line-strong); }
.bar-row i.fc { background: var(--yellow); }
.bar-row i.sc { background: repeating-linear-gradient(45deg, var(--amber-ink) 0 4px, transparent 4px 7px); border: 1px solid var(--amber-ink); }
@media (max-width: 760px) { .sig-detail { grid-template-columns: 1fr; } }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0; }
.chips button { font: inherit; font-size: 12px; font-weight: 800; padding: 5px 11px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; cursor: pointer; }
.chips button.on { background: var(--cream); border-color: var(--yellow); }
.ex { list-style: none; padding: 0; margin: 4px 0; display: flex; flex-direction: column; gap: 5px; font-size: 12.5px; line-height: 1.45; }
.ex a { color: var(--ink); font-weight: 700; }
.bars { display: flex; flex-direction: column; gap: 8px; margin: 8px 0; }
.bar-row { display: grid; grid-template-columns: 44px minmax(0, 1fr) 90px 90px; gap: 10px; align-items: center; font-size: 13px; font-weight: 800; }
.bar-track { position: relative; height: 16px; background: #f0efec; border-radius: 6px; }
.bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: var(--yellow); border-radius: 6px; }
.ci { position: absolute; top: 6px; height: 4px; background: var(--ink); opacity: .55; border-radius: 2px; }
.spark { width: 100%; height: 120px; display: block; margin: 6px 0; }
.spark path { fill: none; stroke: var(--orange); stroke-width: 2.2; vector-effect: non-scaling-stroke; }
.notes { max-width: 100%; overflow: hidden; }
.notes summary { cursor: pointer; font-weight: 800; }
.notes-scroll {
  margin-top: 12px;
  max-height: 420px;
  overflow-y: auto;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  -webkit-overflow-scrolling: touch;
}
.notes-tbl {
  width: 100%;
  min-width: 730px;
  border-collapse: collapse;
  font-size: 12.5px;
  line-height: 1.45;
  margin-top: 0;
}
.notes-tbl th,
.notes-tbl td {
  text-align: left;
  vertical-align: top;
  white-space: normal;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  word-break: break-word;
  overflow-wrap: break-word;
}
.notes-tbl thead th {
  position: sticky;
  top: 0;
  background: #faf9f6;
  z-index: 2;
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .06em;
  border-bottom: 2px solid var(--line);
}
.notes-tbl tbody tr:hover {
  background: #fffcf5;
}
.notes-tbl tbody tr:last-child td {
  border-bottom: none;
}
.notes-tbl .col-source { width: 20%; min-width: 140px; font-weight: 800; color: var(--ink); }
.notes-tbl .col-type { width: 10%; min-width: 80px; }
.notes-tbl .col-pop { width: 22%; min-width: 140px; }
.notes-tbl .col-def { width: 24%; min-width: 160px; }
.notes-tbl .col-period { width: 10%; min-width: 90px; }
.notes-tbl .col-lim { width: 14%; min-width: 120px; }
.notes-tbl .tag { margin-left: 0; }
.kv { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 6px 14px; font-size: 13px; }
.kv dt { font-weight: 800; color: var(--muted); }
.lim { margin: 4px 0 0 18px; display: flex; flex-direction: column; gap: 4px; }
code { font-size: 12px; background: #f6f4ef; padding: 1px 5px; border-radius: 6px; }
@media (max-width: 860px) {
  h1 { font-size: 23px; }
  .summary, .two, .detail-grid { grid-template-columns: minmax(0, 1fr); }
  .verdict-box { border-left: 0; padding-left: 0; }
  .kv { grid-template-columns: minmax(0, 1fr); }
  .bar-row { grid-template-columns: 40px minmax(0, 1fr) 70px; }
  .bar-row .small { display: none; }
}
</style>
