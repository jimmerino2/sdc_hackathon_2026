<script setup lang="ts">
import { computed, watch } from 'vue';
import Icon from './Icon.vue';
import ScenarioInfoDialog from './ScenarioInfoDialog.vue';
import PositionChart from './PositionChart.vue';
import RoleList from './RoleList.vue';
import { scenarios } from '../data/flows';
import { backendScenario } from '../api/forecast';
import type { ContextRole, JobMatch } from '../api/jobs';
import type { RoadmapSummary } from '../api/roadmap';
import { useFlow } from '../state';
import { useScenarioProbabilities } from '../composables/useScenarioProbabilities';

/** Suggested roles as a compact list ("cards") or the demand-vs-AI chart. Shared by the onboarding roles page and the sidebar one. */
const props = defineProps<{
  jobs: JobMatch[];
  context: ContextRole[];
  note?: string;
  /** The role shown as selected (outlined dot on the chart, open row in the list). */
  selected: string | null;
  /** Hint under the chart, since what a click does differs between pages. */
  chartHint?: string;
  /** Rows pick a role (shown open, with a radio) instead of opening it. */
  pick?: boolean;
  /** The profile's roadmaps by role. When given, each card shows its role's roadmap status. */
  roadmaps?: Record<string, RoadmapSummary>;
  /** Always the list: no Cards / Chart toggle. */
  cardsOnly?: boolean;
  /** The career stage behind the education part of each match. */
  stage?: string | null;
}>();
const emit = defineEmits<{ select: [code: string] }>();

const { state, scenario } = useFlow();
const { metrics, metricTarget, pct, ranked } = useScenarioProbabilities();
const activeMetricLabel = computed(() => metrics.find((m) => m.target === metricTarget.value)?.label ?? 'selected indicator');
const scenarioTooltip = computed(
  () => `Statistical likelihood of this AI scenario occurring, based on ${activeMetricLabel.value.toLowerCase()} forecasts. Does not reflect your job match.`
);
/** Each future keeps its place (accelerates, steady, slows) and its colour, whatever its chance is: green speeds up, yellow holds steady, red slows down. */
const sColor = { accelerates: '#2e7d4f', steady: 'var(--yellow)', slows: '#c62828' } as const;
/** Start on the most likely future once the chances arrive; after that the learner's own pick stands. */
let preselected = false;
watch(
  ranked,
  (order) => {
    if (preselected || pct(order[0]!) == null) return;
    preselected = true;
    state.value.scenario = order[0]!;
  },
  { immediate: true },
);
const view = computed(() => (props.cardsOnly ? 'cards' : state.value.rolesView));
const sIcon = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;

function outlook(job: JobMatch) {
  return job.outlook.find((o) => o.scenario === backendScenario[state.value.scenario]);
}
/** The heading follows what the forecast actually says for this tab, so it never promises growth that isn't there. */
const heading = computed(() => {
  const trends = props.jobs.map((j) => outlook(j)?.trend);
  const growing = trends.filter((t) => t === 'growing').length;
  const shrinking = trends.filter((t) => t === 'shrinking').length;
  const lead = `If ${scenario.value.title}`;
  if (growing >= trends.length / 2) return `${lead}, most of your best-fit roles grow.`;
  if (shrinking >= trends.length / 2) return `${lead}, demand dips for most of these roles, but your skills still fit.`;
  return `${lead}, these are your best-fit roles. Here’s how each one fares.`;
});
</script>

<template>
  <!-- Onboarding flow (inside FlowShell): clean single-column mode -->
  <div v-if="cardsOnly" class="cards-only-mode">
    <div class="bar">
      <div class="tabs">
        <button
          v-for="s in scenarios"
          :key="s.key"
          :class="[`k-${s.key}`, { on: state.scenario === s.key }]"
          :style="{ '--rc': sColor[s.key] }"
          @click="state.scenario = s.key"
        >
          <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
          <small
            v-if="pct(s.key) != null"
            class="tab-pct"
            :title="scenarioTooltip"
            :aria-label="scenarioTooltip"
          >{{ pct(s.key) }}%</small>
        </button>
        <ScenarioInfoDialog />
      </div>
    </div>
    <div class="list-wrap center">
      <div class="metric-wrap">
        <span class="seg-label">Chances from</span>
        <div class="metric-seg" role="radiogroup" aria-label="Metric the chances are based on">
          <button
            v-for="m in metrics"
            :key="m.target"
            type="button"
            role="radio"
            :aria-checked="metricTarget === m.target"
            :class="{ on: metricTarget === m.target }"
            @click="metricTarget = m.target"
          >{{ m.label }}</button>
        </div>
      </div>
      <RoleList :jobs="jobs" :selected="pick ? selected : undefined" :roadmaps="roadmaps" :stage="stage" @select="emit('select', $event)" />
    </div>
  </div>

  <!-- Full dashboard mode: Left content + Sticky right sidebar controls -->
  <div v-else class="browser-layout">
    <main class="main-col">
      <h1 class="headline">{{ heading }}</h1>

      <div v-if="view === 'chart'" class="content-panel">
        <div class="card chart-card">
          <h2 class="chart-title">Demand vs AI automation exposure</h2>
          <PositionChart :jobs="jobs" :context="context" :scenario="backendScenario[state.scenario]" :selected="selected" @select="emit('select', $event)" />
          <p class="foot">
            Orange circles are your matches: bigger means a better fit. {{ chartHint ?? 'Tap one to see its forecast.' }} Grey circles are other jobs for comparison.
            The line through the selected role is its likely range. Exposure is how much AI is already used in a job’s work, weighted by how much of
            that use does the task (automation) rather than helps with it (augmentation), from the Anthropic Economic Index.
          </p>
        </div>
        <p v-if="note" class="note">{{ note }}</p>
      </div>

      <div v-else class="content-panel">
        <RoleList :jobs="jobs" :selected="pick ? selected : undefined" :roadmaps="roadmaps" :stage="stage" @select="emit('select', $event)" />
      </div>
    </main>

    <aside class="sidebar" aria-label="Controls and scenarios">
      <div class="view-switch" role="group" aria-label="Layout">
        <button
          type="button"
          :class="{ on: state.rolesView === 'cards' }"
          :aria-pressed="state.rolesView === 'cards'"
          @click="state.rolesView = 'cards'"
        >
          <Icon name="layers" :size="15" /> Cards
        </button>
        <button
          type="button"
          :class="{ on: view === 'chart' }"
          :aria-pressed="view === 'chart'"
          @click="state.rolesView = 'chart'"
        >
          <Icon name="chart" :size="15" /> Chart
        </button>
      </div>

      <div class="panel-card">
        <div class="panel-head">
          <span class="panel-eyebrow">AI Scenario</span>
        <ScenarioInfoDialog />
        </div>

        <div class="scenario-list" role="radiogroup" aria-label="AI scenario">
          <button
            v-for="s in scenarios"
            :key="s.key"
            type="button"
            role="radio"
            :aria-checked="state.scenario === s.key"
            class="scenario-card"
            :class="[`k-${s.key}`, { on: state.scenario === s.key }]"
            :style="{ '--rc': sColor[s.key] }"
            @click="state.scenario = s.key"
          >
            <span class="scenario-bar" />
            <Icon :name="sIcon[s.key]" :size="16" class="scenario-icon" />
            <span class="scenario-label">{{ s.label }}</span>
            <span
              v-if="pct(s.key) != null"
              class="scenario-pct"
              :title="scenarioTooltip"
              :aria-label="scenarioTooltip"
            >{{ pct(s.key) }}%</span>
          </button>
        </div>

        <div class="metric-section">
          <span class="metric-eyebrow">Chances from</span>
          <div class="metric-seg-col" role="radiogroup" aria-label="Metric the chances are based on">
            <button
              v-for="m in metrics"
              :key="m.target"
              type="button"
              role="radio"
              :aria-checked="metricTarget === m.target"
              class="metric-btn"
              :class="{ on: metricTarget === m.target }"
              @click="metricTarget = m.target"
            >
              <span class="metric-dot" />
              <span>{{ m.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <slot name="sidebar-footer" />
    </aside>
  </div>
</template>

<style scoped>
/* Dashboard two-column layout */
.browser-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 32px;
  align-items: start;
}
.main-col {
  min-width: 0;
  max-width: 760px;
  width: 100%;
}
.headline {
  font-size: 28px;
  font-weight: 900;
  line-height: 1.25;
  margin-bottom: 20px;
  letter-spacing: -0.01em;
}
.content-panel {
  max-width: 760px;
  width: 100%;
}
.chart-card {
  padding: 22px 24px;
  max-width: 760px;
  width: 100%;
  box-sizing: border-box;
}
.chart-title {
  font-size: 17px;
  font-weight: 900;
  margin-bottom: 10px;
}
.foot {
  margin-top: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  line-height: 1.5;
}
.note {
  margin-top: 22px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  line-height: 1.5;
  max-width: 760px;
}

/* Sidebar Controls */
.sidebar {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.view-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4px;
  border-radius: 14px;
  background: var(--line);
  gap: 4px;
}
.view-switch button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 14px;
  border-radius: 10px;
  font-weight: 900;
  font-size: 13px;
  color: var(--muted);
  transition: all .12s ease;
}
.view-switch button:hover {
  color: var(--ink);
}
.view-switch button.on {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 2px 0 rgba(30,30,30,.1);
}
.panel-card {
  background: #fff;
  border: 2px solid var(--line-strong);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 4px 0 rgba(30, 30, 30, 0.05);
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-eyebrow {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
}
.scenario-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.scenario-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 12px;
  border: 2px solid var(--line);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: transform .08s ease, border-color .12s ease, background .12s ease, box-shadow .12s ease;
}
.scenario-card:hover {
  border-color: var(--line-strong);
  background: #faf9f6;
  transform: translateY(-1px);
}
.scenario-card:active {
  transform: translateY(2px);
}
.scenario-card.on {
  border-color: var(--rc);
  background: #fff;
  box-shadow: 0 3px 0 var(--rc);
}
.scenario-bar {
  width: 4px;
  height: 16px;
  border-radius: 4px;
  background: var(--line);
  flex: none;
  transition: background .12s ease;
}
.scenario-card.on .scenario-bar {
  background: var(--rc);
}
.scenario-icon {
  flex: none;
  color: var(--muted);
}
.scenario-card.on .scenario-icon {
  color: var(--rc);
}
.scenario-label {
  font-size: 11.5px;
  font-weight: 900;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--ink);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.scenario-pct {
  font-size: 12px;
  font-weight: 900;
  color: var(--muted);
  background: var(--line);
  padding: 2px 7px;
  border-radius: 999px;
  flex: none;
}
.scenario-card.k-steady.on .scenario-pct { color: var(--ink); }
.scenario-card.on .scenario-pct {
  background: var(--rc);
  color: #fff;
}
.metric-section {
  padding-top: 10px;
  border-top: 1.5px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.metric-eyebrow {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--muted);
}
.metric-seg-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
  background: var(--line);
  padding: 3px;
  border-radius: 12px;
}
.metric-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  text-align: left;
  transition: background .12s, color .12s;
}
.metric-btn:hover {
  color: var(--ink);
}
.metric-btn.on {
  background: #fff;
  color: var(--ink);
  font-weight: 900;
  box-shadow: 0 1px 2px rgba(30,30,30,.08);
}
.metric-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--line-strong);
  flex: none;
}
.metric-btn.on .metric-dot {
  background: var(--orange);
}

/* Onboarding (cards-only) styles */
.cards-only-mode .bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.cards-only-mode .tabs { display: flex; gap: 8px; flex-wrap: nowrap; align-items: center; flex: 1 1 auto; min-width: 0; }
.cards-only-mode .tabs button { display: flex; align-items: center; justify-content: center; gap: 6px; flex: 1 1 0; min-width: 0; white-space: nowrap; padding: 9px 10px; border-radius: 12px; border: 2px solid var(--line-strong); background: #fff; box-shadow: 0 3px 0 rgba(30,30,30,.1); font-weight: 900; font-size: 11px; letter-spacing: .05em; text-transform: uppercase; transition: transform .08s, box-shadow .08s; }
.cards-only-mode .tabs button:not(.on) svg { color: var(--rc); }
.cards-only-mode .tabs button.k-steady:not(.on) svg { color: var(--amber-ink); }
.cards-only-mode .tabs button:active { transform: translateY(3px); box-shadow: 0 1px 0 rgba(30,30,30,.1); translate: none; scale: 1; }
.cards-only-mode .tabs button.on:active { box-shadow: 0 1px 0 var(--rc); }
.cards-only-mode .tabs button.on { background: var(--rc); border-color: var(--rc); color: #fff; box-shadow: 0 3px 0 var(--rc); }
.cards-only-mode .tabs button.k-steady.on { color: var(--ink); }
.cards-only-mode .tabs button.k-steady.on .tab-pct { color: var(--ink); }
@media (max-width: 520px) {
  .cards-only-mode .tabs button { padding: 8px 4px; font-size: 9.5px; letter-spacing: .02em; gap: 3px; }
  .cards-only-mode .tabs button svg { display: none; }
}
.cards-only-mode .tab-pct { font-weight: 900; opacity: .85; }
.cards-only-mode .metric-wrap { display: inline-flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.cards-only-mode .seg-label { font-size: 13px; font-weight: 900; color: var(--muted); white-space: nowrap; }
.cards-only-mode .metric-seg { display: inline-flex; padding: 4px; border-radius: 14px; background: var(--line); }
.cards-only-mode .metric-seg button { padding: 8px 16px; border-radius: 10px; font-weight: 900; font-size: 12px; color: var(--muted); text-align: center; white-space: nowrap; transition: background .15s, color .15s; }
.cards-only-mode .metric-seg button:hover { color: var(--ink); }
.cards-only-mode .metric-seg button.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30, 30, 30, .1); }
.cards-only-mode .list-wrap { max-width: 760px; }
.cards-only-mode .list-wrap.center { margin: 0 auto; }

@media (max-width: 860px) {
  .browser-layout {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .sidebar {
    position: static;
    order: -1;
  }
}
@media (max-width: 480px) {
  .cards-only-mode .metric-wrap { flex-wrap: wrap; }
  .cards-only-mode .metric-seg button { padding: 7px 10px; font-size: 11px; }
}
</style>

