<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Bubble from './Bubble.vue';
import ChartWatcher from './ChartWatcher.vue';
import ForecastInfo from './ForecastInfo.vue';
import Icon from './Icon.vue';
import QuarterPicker from './QuarterPicker.vue';
import ScenarioPanel from './ScenarioPanel.vue';
import { scenarios, type ScenarioKey } from '../data/flows';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';
import { month } from '../occupational/format';
import { formatSkip, parseSkip } from '../data/quarterPick';
import { backendScenario, fetchJobForecasts, fetchQuarters, refreshForecastData, retrainForecast, type JobForecast, type JobHorizon, type Quarters, type Retrained } from '../api/forecast';
import { fetchInterestReasons, type InterestReason, type JobMatch } from '../api/jobs';
import { readProfileId } from '../api/profile';
import { fetchRoleSdg, type RoleSdg, type SdgTargetNote } from '../api/sdg';
import { SDG_GOALS } from '../data/interestSdgs';

/** A role's AI outlook (the three-futures chart) and skill gap. Shared by the onboarding forecast page and the role page. */
const props = defineProps<{
  onetCode: string;
  job?: JobMatch;
  /** Onboarding: Jobee already asks the question in the header, so drop the big headings and extra bubbles. */
  compact?: boolean;
  /** Show the quarter picker: the learner can leave years or quarters out and see the forecast the model would make without them. */
  pickQuarter?: boolean;
  /** The quarters left out, as kept in the address ("2020,2021,2026-Q3"); null or missing = none. */
  skip?: string | null;
}>();
const emit = defineEmits<{ 'update:skip': [skip: string | null] }>();

const { state, key } = useFlow();
const base = import.meta.env.BASE_URL;
/** The role's SDGs that one of the learner's interests points at. */
const fromInterests = computed(() => props.job?.sdg_reasons?.filter((r) => r.interests.length) ?? []);
const active = computed(() => state.value.scenario);

/** The LLM's sentence for each interest card, by "sdg:interest". Only fetched on the role page, not in onboarding. */
const reasons = ref<Record<string, string>>({});
const reasonsStatus = ref<'idle' | 'loading' | 'done'>('idle');
async function loadReasons() {
  const id = state.value.profileId ?? readProfileId();
  if (props.compact || !id || !fromInterests.value.length || reasonsStatus.value !== 'idle') return;
  reasonsStatus.value = 'loading';
  try {
    const list: InterestReason[] = await fetchInterestReasons(id, props.onetCode);
    reasons.value = Object.fromEntries(list.map((r) => [`${r.sdg}:${r.interest}`, r.reason]));
  } catch {
    // Not fatal: the cards still show which interests point at each goal.
  }
  reasonsStatus.value = 'done';
}
// The job can arrive after mounting (the saved suggestions load on a refresh).
watch(fromInterests, loadReasons, { immediate: true });
watch(() => props.onetCode, () => {
  reasons.value = {};
  reasonsStatus.value = 'idle';
  loadReasons();
});

/** The SDG targets the role and its skills serve (onet_roles_sdg / onet_skills_sdg). Null until loaded or if none. */
const roleSdg = ref<RoleSdg | null>(null);
async function loadSdg() {
  const code = props.onetCode;
  roleSdg.value = null;
  try {
    const r = await fetchRoleSdg(code);
    if (code === props.onetCode) roleSdg.value = r;
  } catch {
    // Not fatal: the page works without the targets.
  }
}
watch(() => props.onetCode, loadSdg, { immediate: true });
/** The role's targets under one goal. */
const targetsFor = (sdg: number): SdgTargetNote[] => roleSdg.value?.targets.filter((t) => t.sdg === sdg) ?? [];
/**
 * Every goal the role serves, main first, each with its targets and the learner's interests that point at it. From the
 * SDG targets, or the match's goals if those didn't load. An interest can point at a goal of the match's weights that
 * the targets don't list, so that goal is kept.
 */
const goals = computed(() => {
  const r = roleSdg.value;
  const list = r ? [r.main, ...r.relevant] : (props.job?.sdg_reasons ?? []).map((g) => ({ sdg: g.sdg, name: g.name }));
  for (const g of fromInterests.value) if (!list.some((x) => x.sdg === g.sdg)) list.push({ sdg: g.sdg, name: g.name });
  return list.map((g) => ({ ...g, targets: targetsFor(g.sdg), interests: props.job?.sdg_reasons?.find((x) => x.sdg === g.sdg)?.interests ?? [] }));
});
const goalGroups = computed(() => [
  { label: 'Main SDG', goals: goals.value.slice(0, 1) },
  { label: 'Relevant SDGs', goals: goals.value.slice(1) },
].filter((g) => g.goals.length));

/** The skill whose targets are showing (hover, focus or tap), and how far its card moves left to stay on screen. */
const tip = ref<string | null>(null);
const tipShift = ref(0);
async function showTip(id: string) {
  if (tip.value === id) return;
  tip.value = id;
  tipShift.value = 0;
  await nextTick();
  const r = document.getElementById(`tip-${id}`)?.getBoundingClientRect();
  if (!r) return;
  const over = r.right - (window.innerWidth - 16);
  tipShift.value = over > 0 ? -Math.min(over, r.left - 16) : 0;
}
function hideTip(id: string) {
  if (tip.value === id) tip.value = null;
}
const sdgTile = (sdg: number) => `${base}sdg/goal-${String(sdg).padStart(2, '0')}.jpg`;
const sdgColor = (sdg: number) => SDG_GOALS[sdg]?.color ?? 'var(--ink)';
/** The role's key skills (the gap cards' chips) with the goal and targets each serves; skills to build first. */
const skillSdgs = computed(() => {
  const all = roleSdg.value?.skills ?? [];
  const names = props.job ? [...props.job.skills_to_learn, ...props.job.skills_you_have] : [];
  return names.flatMap((n) => {
    const s = all.find((x) => x.skill_name === n);
    return s ? [{ ...s, have: props.job!.skills_you_have.includes(n) }] : [];
  });
});

/** What is shown: the stored forecast, or the retrained one for the quarters picked. */
const forecasts = ref<JobForecast[]>([]);
/** The stored forecast with every quarter; stays as the faint comparison line when a retrained one is shown. */
const stored = ref<JobForecast[]>([]);
const status = ref<'loading' | 'ready' | 'error'>('loading');
const quarters = ref<Quarters | null>(null);
const retrained = ref<Retrained | null>(null);
const busy = ref(false);
const pickError = ref<string | null>(null);
let pending: AbortController | undefined;
let wait: number | undefined;

/** The quarters left out; can only be read once the quarters are known. */
const excluded = computed(() => parseSkip(props.skip, quarters.value?.quarters ?? []));
const DEBOUNCE_MS = 350;

/** Retrains without the quarters (none = all the data). A newer pick cancels an older one still running, so a stale answer can't land. */
async function retrain(left: string[]) {
  pending?.abort();
  const mine = (pending = new AbortController());
  busy.value = true;
  pickError.value = null;
  try {
    const r = await retrainForecast(props.onetCode, left, mine.signal);
    retrained.value = r;
    forecasts.value = r.forecasts;
  } catch (e) {
    if ((e as Error).name === 'AbortError') return;
    pickError.value = e instanceof Error ? e.message : 'The forecast couldn’t be retrained just now. Try again.';
  } finally {
    if (pending === mine) busy.value = false;
  }
}

async function load() {
  status.value = 'loading';
  clearTimeout(wait);
  pending?.abort();
  busy.value = false;
  retrained.value = null;
  pickError.value = null;
  try {
    stored.value = forecasts.value = await fetchJobForecasts(props.onetCode);
    status.value = forecasts.value.length ? 'ready' : 'error';
  } catch {
    status.value = 'error';
    return;
  }
  if (props.pickQuarter) fetchQuarters().then((q) => (quarters.value = q)).catch(() => {}); // the chart still works without the picker
}
onMounted(load);
watch(() => props.onetCode, load);

// Follow the choice: wait a moment so several taps in a row make one retrain, then show it. Nothing left out shows the stored forecast.
watch([() => [...excluded.value].sort().join(','), status], ([key]) => {
  clearTimeout(wait);
  if (!props.pickQuarter || status.value !== 'ready' || !quarters.value) return;
  if (!key) {
    if (!retrained.value && !busy.value) return;
    pending?.abort();
    busy.value = false;
    pickError.value = null;
    retrained.value = null;
    forecasts.value = stored.value;
    return;
  }
  pending?.abort(); // an older request still running must not land (or un-dim the chart) over this choice
  pending = undefined;
  busy.value = true; // dim the chart at once; the request follows after the pause
  wait = window.setTimeout(() => retrain(key.split(',')), DEBOUNCE_MS);
});
onBeforeUnmount(() => { clearTimeout(wait); pending?.abort(); });

function pick(next: Set<string>) {
  emit('update:skip', quarters.value ? formatSkip(next, quarters.value.quarters) : null);
}

/** Makes the server re-read the stored data, then retrains so a changed row shows. */
async function refresh() {
  try {
    await refreshForecastData();
    quarters.value = await fetchQuarters();
  } catch (e) {
    pickError.value = e instanceof Error ? e.message : 'Couldn’t refresh.';
    return;
  }
  clearTimeout(wait);
  await retrain([...excluded.value].sort());
}

const byScenario = computed(() => {
  const out = {} as Record<ScenarioKey, JobForecast | undefined>;
  for (const s of scenarios) out[s.key] = forecasts.value.find((f) => f.scenario === backendScenario[s.key]);
  return out;
});

/**
 * Where the numbers on the chart and the futures come from. With the quarter picker the machine-learning model is shown,
 * since it is what retraining changes; the role page keeps the sector's recent pace ("last year's pace repeats").
 */
const useModel = computed(() => !!props.pickQuarter);
function figure(o: JobHorizon): { pct: number; range: { low: number; high: number } } {
  return useModel.value ? { pct: o.model_change_pct, range: o.model_range } : { pct: o.change_pct, range: o.range };
}
/** The model's own track record at 12 months, in words. */
const modelCheck = computed(() => {
  const status = retrained.value?.model_status ?? forecasts.value[0]?.outlook.at(-1)?.reliability.status;
  return status === 'validated'
    ? 'In past tests this model beat the simple baselines, so it is a fair guide.'
    : 'In past tests this model did not beat the simple baselines, so treat it as a rough guide.';
});

/** The same scenario's forecast with every quarter, drawn faintly behind a retrained one so the change shows. */
const ghost = computed(() => {
  if (!retrained.value) return [];
  const f = stored.value.find((x) => x.scenario === backendScenario[active.value]);
  return f ? [{ m: 0, v: 0 }, ...f.outlook.map((o) => ({ m: o.horizon_months, v: figure(o).pct }))] : [];
});

/** Postings change (%) at months 0, 3, 6, 9, 12 for one scenario: the same figure the role cards show. */
function series(k: ScenarioKey): { m: number; v: number }[] {
  const f = byScenario.value[k];
  if (!f) return [];
  return [{ m: 0, v: 0 }, ...f.outlook.map((o) => ({ m: o.horizon_months, v: figure(o).pct }))];
}

/** The past months (m = -n..0, 0 = today), same for every scenario since they only differ in the future. */
const history = computed(() => {
  const h = byScenario.value[active.value]?.history ?? forecasts.value[0]?.history ?? [];
  return h.map((p, i) => ({ m: i - (h.length - 1), v: p.change_pct, month: p.month }));
});
/** Months of history on the chart; fixed so the chart keeps its shape even if a role has less. */
const PAST = 12;

// Chart geometry: x = months from today (negative = past), y = % change in postings vs today.
const X0 = 34, X1 = 420, Y0 = 8, Y1 = 172;
const band = computed(() => byScenario.value[active.value]?.outlook ?? []);
const yRange = computed(() => {
  const vals = [0, ...history.value.map((p) => p.v), ...scenarios.flatMap((s) => series(s.key).map((p) => p.v)), ...ghost.value.map((p) => p.v)];
  for (const o of band.value) vals.push(figure(o).range.low, figure(o).range.high);
  return { lo: Math.floor(Math.min(...vals) / 10) * 10, hi: Math.ceil(Math.max(...vals) / 10) * 10 };
});
const sx = (m: number) => X0 + ((m + PAST) / (PAST + 12)) * (X1 - X0);
const sy = (v: number) => Y1 - ((v - yRange.value.lo) / (yRange.value.hi - yRange.value.lo)) * (Y1 - Y0);
const ticks = computed(() => {
  const out: number[] = [];
  for (let t = yRange.value.lo; t <= yRange.value.hi; t += 10) out.push(t);
  return out;
});
const histPts = computed(() => history.value.map((p) => `${sx(p.m)},${sy(p.v)}`).join(' '));
const ghostPts = computed(() => ghost.value.map((p) => `${sx(p.m)},${sy(p.v)}`).join(' '));
const pts = (k: ScenarioKey) => series(k).map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
const rangePoly = computed(() => {
  const o = band.value;
  if (!o.length) return '';
  const up = [{ m: 0, v: 0 }, ...o.map((h) => ({ m: h.horizon_months, v: figure(h).range.high }))];
  const dn = [{ m: 0, v: 0 }, ...o.map((h) => ({ m: h.horizon_months, v: figure(h).range.low }))].reverse();
  return [...up, ...dn].map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
});
const endLabel = computed(() => {
  const s = series(active.value);
  const last = s[s.length - 1];
  return last ? `${last.v > 0 ? '+' : ''}${last.v}%` : '';
});
/** Month labels under the chart: one year back, six months back, today, and the forecast's halfway and end points. */
const axis = computed(() => {
  const f = forecasts.value[0];
  if (!f) return [];
  const at = (h: number) => f.outlook.find((o) => o.horizon_months === h)?.forecast_for;
  const past = (m: number) => history.value.find((p) => p.m === m)?.month;
  return [
    { m: -PAST, label: past(-PAST) },
    { m: -6, label: past(-6) },
    { m: 0, label: f.forecast_from },
    { m: 6, label: at(6) },
    { m: 12, label: at(12) },
  ].filter((a) => a.label).map((a) => ({ x: sx(a.m), label: month(a.label), today: a.m === 0 }));
});
const meta = computed(() => forecasts.value[0]);
/** This role's 12-month demand change under one scenario, e.g. "−3.2% demand by Sep 2027". */
function outcome(k: ScenarioKey) {
  const last = byScenario.value[k]?.outlook.at(-1);
  if (!last) return 'No forecast yet';
  const [y, m] = last.forecast_for.split('-');
  const month = new Date(Number(y), Number(m) - 1).toLocaleString('en', { month: 'short' });
  const pct = figure(last).pct;
  return `${pct > 0 ? '+' : ''}${pct}% demand by ${month} ${y}`;
}
/** Which way demand heads under one scenario, so the eye goes to ups (green) and downs (red). */
function trendOf(k: ScenarioKey) {
  const last = byScenario.value[k]?.outlook.at(-1);
  const v = last ? figure(last).pct : 0;
  return v >= 0.5 ? 'trend-up' : v <= -0.5 ? 'trend-down' : 'trend-flat';
}
/** Each future's demand for the picker, once the forecast has loaded. */
const demand = computed(() =>
  status.value === 'ready' ? (Object.fromEntries(scenarios.map((s) => [s.key, { text: outcome(s.key), trend: trendOf(s.key) }])) as Record<ScenarioKey, { text: string; trend: string }>) : undefined,
);
const title = computed(() => meta.value?.title ?? 'This role');
const firstName = computed(() => state.value.name.trim().split(/\s+/)[0] ?? '');
</script>

<template>
  <div class="wrap" :class="{ compact, split: pickQuarter && quarters }">
      <section class="left">
        <h1 v-if="!compact">Here’s the AI outlook for {{ title }}</h1>
        <div class="card chart">
          <small>{{ title }} · {{ useModel ? 'machine-learning forecast' : 'demand outlook' }}</small>
          <h2>Three possible futures, next 12 months</h2>
          <div v-if="status === 'loading'" class="chart-skel" aria-hidden="true"><span class="skel" /><span class="skel line" /></div>
          <p v-else-if="status === 'error'" class="state">Couldn’t reach the forecast service. Make sure the backend is running on port 8000.</p>
          <template v-else>
            <svg :class="{ busy }" viewBox="0 0 440 190" role="img" :aria-label="`Forecast of ${title} demand under three AI scenarios`">
              <g stroke="#eceae5"><line v-for="t in ticks" :key="t" :x1="X0" :x2="X1" :y1="sy(t)" :y2="sy(t)" :stroke="t === 0 ? '#c2bfba' : '#eceae5'" /></g>
              <text v-for="t in ticks" :key="'l' + t" :x="X0 - 6" :y="sy(t) + 3" font-size="9" font-weight="800" text-anchor="end" fill="#8a8782">{{ t > 0 ? '+' : '' }}{{ t }}%</text>
              <polygon :points="rangePoly" fill="#fff3cc" opacity=".7" />
              <polyline v-if="histPts" :points="histPts" fill="none" stroke="#1e1e1e" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
              <line :x1="sx(0)" :x2="sx(0)" :y1="Y0" :y2="Y1" stroke="#1e1e1e" stroke-width="2" stroke-dasharray="1 5" stroke-linecap="round" />
              <text :x="sx(0) - 5" :y="Y0 + 8" font-size="9" font-weight="900" text-anchor="end" fill="#8a8782">PAST</text>
              <text :x="sx(0) + 5" :y="Y0 + 8" font-size="9" font-weight="900" text-anchor="start" fill="#8a8782">FORECAST</text>
              <polyline v-for="s in scenarios.filter((x) => x.key !== active)" :key="s.key" :points="pts(s.key)" fill="none" stroke="#c2bfba" stroke-width="3" stroke-dasharray="2 5" stroke-linecap="round" />
              <polyline v-if="ghostPts" :points="ghostPts" fill="none" stroke="#1e1e1e" stroke-opacity=".28" stroke-width="3" stroke-dasharray="1 6" stroke-linecap="round" />
              <polyline :points="pts(active)" fill="none" stroke="#ff9800" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
              <circle v-for="p in series(active)" :key="p.m" :cx="sx(p.m)" :cy="sy(p.v)" r="4" fill="#1e1e1e" />
              <text :x="X1" :y="sy(series(active).at(-1)?.v ?? 0) - 10" font-size="11" font-weight="900" text-anchor="end" fill="#1e1e1e">{{ endLabel }}</text>
            </svg>
            <svg class="axis" viewBox="0 0 440 16" aria-hidden="true">
              <text v-for="a in axis" :key="a.x" :x="a.x" y="11" font-size="9" font-weight="900" text-anchor="middle" :fill="a.today ? '#1e1e1e' : '#8a8782'">{{ a.today ? `TODAY · ${a.label}` : a.label }}</text>
            </svg>
            <ul class="key" aria-label="Chart legend">
              <li><i class="k-past" />Past demand</li>
              <li><i class="k-picked" />Selected future</li>
              <li><i class="k-other" />Other futures</li>
              <li><i class="k-band" />How far past forecasts missed</li>
            </ul>
            <p class="note">
              <template v-if="useModel">
                Change in {{ title }} demand vs today, forecast by a machine-learning model (LightGBM) trained on the sector’s monthly postings, then shifted by how AI-exposed this role is under each scenario. Shaded band is how far the model’s past forecasts missed, not a confidence interval. {{ modelCheck }}
              </template>
              <template v-else>
                Change in {{ title }} demand vs today: the sector’s recent pace, shifted by how AI-exposed this role is under each scenario. Shaded band is the historical error band for the selected future: how far past forecasts missed, not a confidence interval.
              </template>
              {{ meta?.is_proxy_for_malaysia ? 'Uses US postings data as a stand-in for Malaysia. ' : '' }}Indicative, not a prediction.
              <template v-if="meta"> Issued {{ meta.data_as_of ?? 'date not available' }}; last observation {{ meta.forecast_from }}.</template>
              <template v-if="retrained"> Faint dotted line: {{ useModel ? 'the model’s forecast' : 'the forecast' }} with every quarter.</template>
            </p>
            <!-- Its text says the sector's pace is what is shown, which isn't true while the model is. -->
            <ForecastInfo v-if="!useModel" id="role_postings" class="fi-gap" />
          </template>
        </div>
      </section>
      <section class="right">
        <ChartWatcher v-if="!compact" class="bub">Nobody knows the future for sure, so I plan for all three.</ChartWatcher>
        <ScenarioPanel :demand="demand" />
        <slot name="actions" />
      </section>

      <section v-if="!compact" class="gap-row">
        <p class="eyebrow">Your skill gap</p>
        <h1 v-if="!compact">Here’s how close you are to {{ title }}</h1>
        <template v-if="job">
          <h2 v-if="compact" class="gap-title">{{ job.skills_owned }} of {{ job.skills_total }} key skills already yours</h2>
          <Bubble v-else class="b" :size="60">
            You already have {{ job.skills_owned }} of {{ job.skills_total }} key skills.
            Let’s close the rest{{ firstName ? `, ${firstName}` : '' }}.
          </Bubble>
          <div class="gap-cards">
            <div class="card block">
              <div class="head"><h2>{{ compact ? personaCopy[key].haveTitle : 'Already yours' }}</h2><span class="pill pill-dark">{{ job.skills_you_have.length }} skills</span></div>
              <div v-if="job.skills_you_have.length" class="chips">
                <span v-for="s in job.skills_you_have" :key="s" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s) }}</span>
              </div>
              <p v-else class="empty">None of this role’s key skills yet. Everyone starts somewhere.</p>
            </div>
            <div class="card block">
              <div class="head"><h2>{{ compact ? personaCopy[key].gapTitle : 'Close your gap' }}</h2><span class="pill">{{ job.skills_to_learn.length }} to build</span></div>
              <div v-if="job.skills_to_learn.length" class="chips">
                <span v-for="s in job.skills_to_learn" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="14" /> {{ skillLabel(s) }}</span>
              </div>
              <p v-else class="empty">You already cover every key skill for this role.</p>
            </div>
          </div>
        </template>
        <p v-else class="empty">Pick this role from your matches to see which skills you already have and which to build.</p>
      </section>

      <aside v-if="pickQuarter && quarters" class="aside" aria-label="Choose the data the forecast is trained on">
        <QuarterPicker
          :quarters="quarters.quarters"
          :excluded="excluded"
          :busy="busy"
          :error="pickError"
          :result="retrained"
          :can-refresh="quarters.refresh_enabled"
          @apply="pick"
          @refresh="refresh"
        />
      </aside>

      <section v-if="goals.length" class="sdg-row impact" aria-labelledby="impact-title">
        <p class="eyebrow">Global goals</p>
        <h2 id="impact-title" class="sdg-title">How {{ job?.title ?? title }} serves the SDGs</h2>
        <div class="impact-goals">
          <div v-for="grp in goalGroups" :key="grp.label" class="impact-group">
            <span class="impact-label">{{ grp.label }}</span>
            <ul class="sdg-list">
              <li v-for="g in grp.goals" :key="g.sdg" class="sdg-card why">
                <img class="sdg-tile" :src="sdgTile(g.sdg)" :alt="`UN Sustainable Development Goal ${g.sdg}: ${g.name}`" width="148" height="148" loading="lazy" />
                <div class="sdg-from">
                  <template v-for="i in g.interests" :key="i">
                    <span class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> <span>{{ i }}</span></span>
                    <p v-if="reasons[`${g.sdg}:${i}`]" class="sdg-why">{{ reasons[`${g.sdg}:${i}`] }}</p>
                    <span v-else-if="reasonsStatus === 'loading'" class="skel sdg-why-skel" aria-hidden="true" />
                  </template>
                  <ul v-if="g.targets.length" class="sdg-targets" :aria-label="`SDG ${g.sdg} targets`">
                    <li v-for="t in g.targets" :key="t.code"><b :style="{ color: sdgColor(t.sdg) }">{{ t.code }}</b> {{ t.text }}</li>
                  </ul>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <template v-if="skillSdgs.length">
          <h3 class="impact-sub">Your key skills and the goals they serve</h3>
          <p class="impact-hint">Hover or tap a skill to see the targets it serves.</p>
          <ul class="skill-sdgs">
            <li v-for="s in skillSdgs" :key="s.skill_id" class="skill-sdg" @mouseenter="showTip(s.skill_id)" @mouseleave="hideTip(s.skill_id)">
              <button
                type="button"
                class="chip"
                :class="s.have ? 'chip-have' : 'chip-gap'"
                :aria-expanded="tip === s.skill_id"
                :aria-describedby="tip === s.skill_id ? `tip-${s.skill_id}` : undefined"
                @focus="showTip(s.skill_id)"
                @blur="hideTip(s.skill_id)"
                @click="showTip(s.skill_id)"
                @keydown.esc="tip = null"
              >
                <Icon :name="s.have ? 'check' : 'sparkles'" :size="13" :stroke="s.have ? 3 : 2" />
                <span>{{ skillLabel(s.skill_name) }}</span>
                <span class="skill-sdg-goals" aria-hidden="true">
                  <img v-for="g in [s.main, ...s.relevant]" :key="g.sdg" :src="sdgTile(g.sdg)" alt="" width="22" height="22" loading="lazy" />
                </span>
              </button>
              <div v-if="tip === s.skill_id" :id="`tip-${s.skill_id}`" class="skill-tip" role="tooltip" :style="{ left: `${tipShift}px` }">
                <p class="skill-tip-goals">
                  <span v-for="g in [s.main, ...s.relevant]" :key="g.sdg" :style="{ color: sdgColor(g.sdg) }">SDG {{ g.sdg }}: {{ g.name }}</span>
                </p>
                <ul class="sdg-targets">
                  <li v-for="t in s.targets" :key="t.code"><b :style="{ color: sdgColor(t.sdg) }">{{ t.code }}</b> {{ t.text }}</li>
                </ul>
              </div>
            </li>
          </ul>
        </template>
        <p class="sdg-credit">SDG icons: United Nations. The UN has not approved this app.</p>
      </section>
    </div>
</template>

<style scoped>
.wrap { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; }
h1 { font-size: 34px; font-weight: 900; margin: 6px 0 22px; line-height: 1.15; }

.compact { gap: 24px; }
.chart-skel { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.chart-skel .skel:first-child { height: 170px; }
.chart-skel .line { width: 60%; }
.gap-title { font-size: 25px; font-weight: 900; margin: 4px 0 16px; line-height: 1.2; }
.chart { padding: 22px 24px; }
.chart small { font-size: 13px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.chart h2 { font-weight: 900; font-size: 23px; margin: 6px 0 14px; }
.chart > svg { width: 100%; overflow: visible; margin-top: 16px; transition: opacity .2s; }
.chart > svg.busy { opacity: .45; }
.state { margin: 18px 0 6px; font-size: 15px; font-weight: 700; color: var(--muted); }
.chart > svg.axis { margin-top: 4px; }
.note { margin-top: 14px; font-size: 13px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.key { list-style: none; display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 12px; font-size: 14px; font-weight: 700; color: var(--muted); }
.key li { display: inline-flex; align-items: center; gap: 7px; }
.key i { flex: none; width: 20px; }
.k-past { border-top: 3px solid #1e1e1e; }
.k-picked { border-top: 5px solid #ff9800; border-radius: 3px; }
.k-other { border-top: 3px dotted #c2bfba; }
.k-band { height: 12px; border-radius: 3px; background: #fff3cc; box-shadow: inset 0 0 0 1px #e8d9a0; }
.left, .chart { min-width: 0; }
.fi-gap { margin-top: 12px; }
.right { display: flex; flex-direction: column; gap: 14px; }
.bub { margin-bottom: 8px; flex-direction: row-reverse; }
.sdg-row { grid-column: 1 / -1; margin-top: 12px; }
.sdg-title { font-size: 23px; font-weight: 900; margin: 4px 0 14px; line-height: 1.2; }
.sdg-list { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 18px; }
.sdg-card { width: 148px; display: flex; flex-direction: column; gap: 10px; }
.sdg-tile { display: block; width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 0 rgba(30, 30, 30, .12); }
.sdg-from { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.sdg-from .chip { max-width: 100%; white-space: normal; text-align: left; line-height: 1.25; border-radius: 14px; }
.sdg-from .chip svg { flex: none; }
.sdg-card.why { width: 230px; }
.sdg-card.why .sdg-tile { width: 148px; }
.sdg-why { font-size: 15px; font-weight: 600; line-height: 1.4; color: var(--muted); margin: 0 0 6px 4px; }
.sdg-why-skel { display: block; width: 100%; height: 36px; border-radius: 10px; margin-bottom: 6px; }
.sdg-credit { margin-top: 14px; font-size: 13px; font-weight: 600; color: var(--muted); }
.sdg-targets { list-style: none; margin: 0; padding: 0 0 0 4px; display: flex; flex-direction: column; gap: 4px; font-size: 14px; font-weight: 600; line-height: 1.35; color: var(--muted); }
.sdg-targets b { font-weight: 900; margin-right: 2px; }
.impact-goals { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 18px 28px; }
.impact-group { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }
.impact-label { padding: 6px 14px; border-radius: 10px; background: var(--ink); color: #fff; font-size: 15px; font-weight: 900; }
.impact-sub { font-size: 19px; font-weight: 900; margin: 26px 0 4px; }
.impact-hint { font-size: 14px; font-weight: 600; color: var(--muted); margin: 0 0 12px; }
.skill-sdgs { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 10px; }
.skill-sdg { position: relative; }
.skill-sdg .chip { cursor: help; font: inherit; font-size: 15px; font-weight: 700; line-height: 1.25; white-space: normal; text-align: left; }
.skill-sdg .chip-have { border: 2px solid var(--ink); }
.skill-sdg .chip:focus-visible { outline: 3px solid var(--orange); outline-offset: 2px; }
.skill-sdg-goals { display: inline-flex; flex: none; gap: 3px; margin-left: 2px; }
.skill-sdg-goals img { width: 22px; height: 22px; border-radius: 4px; }
.skill-tip { position: absolute; top: calc(100% + 8px); z-index: 20; width: min(340px, calc(100vw - 32px)); padding: 14px 16px; border-radius: 14px; background: #fff; border: 2px solid var(--line-strong, #e6e2da); box-shadow: 0 10px 24px rgba(30, 30, 30, .14); display: flex; flex-direction: column; gap: 8px; }
.skill-tip-goals { display: flex; flex-direction: column; gap: 2px; margin: 0; font-size: 13px; font-weight: 900; line-height: 1.3; }
.skill-tip .sdg-targets { padding-left: 0; }
@media (max-width: 560px) { .sdg-card.why { width: 100%; } }
.gap-row { grid-column: 1 / -1; margin-top: 12px; }
.gap-row .b { margin-bottom: 18px; }
.gap-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.block { padding: 20px 22px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.head h2 { font-weight: 900; font-size: 19px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.empty { font-size: 15px; font-weight: 700; color: var(--muted); }
@media (max-width: 900px) { .wrap, .gap-cards { grid-template-columns: 1fr; } .bub { display: none; } }

/* The chart and the futures on the left, the data panel beside them; on a narrow screen the panel sits between the two. */
.wrap.split { grid-template-columns: minmax(0, 1fr) 320px; grid-template-areas: 'left aside' 'right aside'; align-items: start; column-gap: 24px; }
.split .left { grid-area: left; }
.split .right { grid-area: right; }
.aside { grid-area: aside; position: sticky; top: 0; }
@media (max-width: 900px) {
  .wrap.split { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'left' 'aside' 'right'; }
  .aside { position: static; }
}
</style>
