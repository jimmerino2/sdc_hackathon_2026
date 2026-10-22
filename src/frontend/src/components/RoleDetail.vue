<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import Bubble from './Bubble.vue';
import ChartWatcher from './ChartWatcher.vue';
import Icon from './Icon.vue';
import { scenarios, type ScenarioKey } from '../data/flows';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';
import { backendScenario, fetchJobForecasts, type JobForecast } from '../api/forecast';
import type { JobMatch } from '../api/jobs';

/** A role's AI outlook (the three-futures chart) and skill gap. Shared by the onboarding forecast page and the role page. */
const props = defineProps<{
  onetCode: string;
  job?: JobMatch;
  /** Onboarding: Jobee already asks the question in the header, so drop the big headings and extra bubbles. */
  compact?: boolean;
}>();

const { state, key } = useFlow();
const icons = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;
const active = computed(() => state.value.scenario);

const forecasts = ref<JobForecast[]>([]);
const status = ref<'loading' | 'ready' | 'error'>('loading');

async function load() {
  status.value = 'loading';
  try {
    forecasts.value = await fetchJobForecasts(props.onetCode);
    status.value = forecasts.value.length ? 'ready' : 'error';
  } catch {
    status.value = 'error';
  }
}
onMounted(load);
watch(() => props.onetCode, load);

const byScenario = computed(() => {
  const out = {} as Record<ScenarioKey, JobForecast | undefined>;
  for (const s of scenarios) out[s.key] = forecasts.value.find((f) => f.scenario === backendScenario[s.key]);
  return out;
});

/** Postings change (%) at months 0, 3, 6, 9, 12 for one scenario: the same figure the role cards show. */
function series(k: ScenarioKey): { m: number; v: number }[] {
  const f = byScenario.value[k];
  if (!f) return [];
  return [{ m: 0, v: 0 }, ...f.outlook.map((o) => ({ m: o.horizon_months, v: o.change_pct }))];
}

// Chart geometry: x = months ahead, y = % change in postings.
const X0 = 34, X1 = 420, Y0 = 8, Y1 = 172;
const band = computed(() => byScenario.value[active.value]?.outlook ?? []);
const yRange = computed(() => {
  const vals = [0, ...scenarios.flatMap((s) => series(s.key).map((p) => p.v))];
  for (const o of band.value) vals.push(o.range.low, o.range.high);
  return { lo: Math.floor(Math.min(...vals) / 10) * 10, hi: Math.ceil(Math.max(...vals) / 10) * 10 };
});
const sx = (m: number) => X0 + (m / 12) * (X1 - X0);
const sy = (v: number) => Y1 - ((v - yRange.value.lo) / (yRange.value.hi - yRange.value.lo)) * (Y1 - Y0);
const ticks = computed(() => {
  const out: number[] = [];
  for (let t = yRange.value.lo; t <= yRange.value.hi; t += 10) out.push(t);
  return out;
});
const pts = (k: ScenarioKey) => series(k).map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
const rangePoly = computed(() => {
  const o = band.value;
  if (!o.length) return '';
  const up = [{ m: 0, v: 0 }, ...o.map((h) => ({ m: h.horizon_months, v: h.range.high }))];
  const dn = [{ m: 0, v: 0 }, ...o.map((h) => ({ m: h.horizon_months, v: h.range.low }))].reverse();
  return [...up, ...dn].map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
});
const endLabel = computed(() => {
  const s = series(active.value);
  const last = s[s.length - 1];
  return last ? `${last.v > 0 ? '+' : ''}${last.v}%` : '';
});
const axis = computed(() => {
  const f = forecasts.value[0];
  return f ? [`${f.forecast_from} · today`, ...f.outlook.map((o) => o.forecast_for)] : [];
});
const meta = computed(() => forecasts.value[0]);
/** This role's 12-month postings change under one scenario, e.g. "−3.2% by Sep 2027". */
function outcome(k: ScenarioKey) {
  const last = byScenario.value[k]?.outlook.at(-1);
  if (!last) return 'No forecast yet';
  const [y, m] = last.forecast_for.split('-');
  const month = new Date(Number(y), Number(m) - 1).toLocaleString('en', { month: 'short' });
  return `${last.change_pct > 0 ? '+' : ''}${last.change_pct}% postings by ${month} ${y}`;
}
const title = computed(() => meta.value?.title ?? 'This role');
const firstName = computed(() => state.value.name.trim().split(/\s+/)[0] ?? '');
</script>

<template>
  <div class="wrap" :class="{ compact }">
      <section class="left">
        <p class="eyebrow">Your AI signal</p>
        <h1 v-if="!compact">Here’s the AI outlook for {{ title }}</h1>
        <p v-else class="signal-note">{{ personaCopy[key].signalNote }}</p>
        <div class="card chart">
          <small>{{ title }} · postings outlook</small>
          <h2>Three possible futures, next 12 months</h2>
          <p v-if="status === 'loading'" class="state">Loading the LightGBM forecast…</p>
          <p v-else-if="status === 'error'" class="state">Couldn’t reach the forecast service. Make sure the backend is running on port 8000.</p>
          <template v-else>
            <svg viewBox="0 0 440 190" role="img" :aria-label="`Forecast of ${title} job postings under three AI scenarios`">
              <g stroke="#eceae5"><line v-for="t in ticks" :key="t" :x1="X0" :x2="X1" :y1="sy(t)" :y2="sy(t)" :stroke="t === 0 ? '#c2bfba' : '#eceae5'" /></g>
              <text v-for="t in ticks" :key="'l' + t" :x="X0 - 6" :y="sy(t) + 3" font-size="9" font-weight="800" text-anchor="end" fill="#8a8782">{{ t > 0 ? '+' : '' }}{{ t }}%</text>
              <polygon :points="rangePoly" fill="#fff3cc" opacity=".7" />
              <polyline v-for="s in scenarios.filter((x) => x.key !== active)" :key="s.key" :points="pts(s.key)" fill="none" stroke="#c2bfba" stroke-width="3" stroke-dasharray="2 5" stroke-linecap="round" />
              <polyline :points="pts(active)" fill="none" stroke="#ff9800" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
              <circle v-for="p in series(active)" :key="p.m" :cx="sx(p.m)" :cy="sy(p.v)" r="4" fill="#1e1e1e" />
              <text :x="X1" :y="sy(series(active).at(-1)?.v ?? 0) - 10" font-size="11" font-weight="900" text-anchor="end" fill="#1e1e1e">{{ endLabel }}</text>
            </svg>
            <div class="axis"><span v-for="a in axis" :key="a">{{ a }}</span></div>
            <p class="note">
              Change in {{ title }} job postings vs today: the sector’s recent pace, shifted by how AI-exposed this role is under each scenario. Shaded band is the likely range for the selected future.
              {{ meta?.is_proxy_for_malaysia ? 'Uses US postings data as a stand-in for Malaysia. ' : '' }}Indicative, not a prediction.
            </p>
          </template>
        </div>
      </section>
      <section class="right">
        <ChartWatcher v-if="!compact" class="bub">Nobody knows the future for sure, so I plan for all three.</ChartWatcher>
        <button v-for="s in scenarios" :key="s.key" class="option sc" :class="{ selected: state.scenario === s.key }" @click="state.scenario = s.key">
          <span class="ic"><Icon :name="icons[s.key]" :size="22" /></span>
          <span>
            <em class="pill" :class="{ 'pill-yellow': state.scenario === s.key }">{{ outcome(s.key) }}</em>
            <h3>{{ s.title }}</h3><p>{{ s.blurb }}</p>
          </span>
          <span v-if="state.scenario === s.key" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
        </button>
        <p v-if="!compact" class="hint">Tap a future to see how {{ title }} fares in it.</p>
      </section>

      <section class="gap-row">
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
    </div>
</template>

<style scoped>
.wrap { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; }
h1 { font-size: 30px; font-weight: 900; margin: 6px 0 22px; line-height: 1.15; }

.compact .eyebrow { margin-bottom: 10px; }
.signal-note { font-size: 14px; font-weight: 700; color: var(--muted); line-height: 1.4; margin: -6px 0 14px; }
.gap-title { font-size: 22px; font-weight: 900; margin: 4px 0 16px; line-height: 1.2; }
.chart { padding: 22px 24px; }
.chart small { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.chart h2 { font-weight: 900; font-size: 20px; margin: 6px 0 14px; }
svg { width: 100%; overflow: visible; margin-top: 16px; }
.state { margin: 18px 0 6px; font-size: 13px; font-weight: 700; color: var(--muted); }
.axis { display: flex; justify-content: space-between; font-size: 10px; font-weight: 900; color: var(--muted); letter-spacing: .05em; text-transform: uppercase; margin-top: 8px; }
.note { margin-top: 14px; font-size: 11px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.right { display: flex; flex-direction: column; gap: 14px; }
.bub { margin-bottom: 8px; flex-direction: row-reverse; }
.sc { align-items: flex-start; } .sc h3 { margin-top: 4px; font-size: 17px; }
.sc p { font-size: 13px; line-height: 1.35; }
.hint { font-size: 12px; font-weight: 700; color: var(--muted); }
.gap-row { grid-column: 1 / -1; margin-top: 12px; }
.gap-row .b { margin-bottom: 18px; }
.gap-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.block { padding: 20px 22px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.head h2 { font-weight: 900; font-size: 17px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.empty { font-size: 13px; font-weight: 700; color: var(--muted); }
@media (max-width: 900px) { .wrap, .gap-cards { grid-template-columns: 1fr; } }
</style>
