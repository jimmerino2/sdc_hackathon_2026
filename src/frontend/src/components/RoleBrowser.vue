<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
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
}>();
const emit = defineEmits<{ select: [code: string] }>();

const { state, scenario } = useFlow();
const { metrics, metricTarget, pct, ranked, rankColor } = useScenarioProbabilities();
/** The 3 AI-future scenarios, most likely first. */
const rankedScenarios = computed(() => ranked.value.map((k) => scenarios.find((s) => s.key === k)!));
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
  <div>
    <div class="bar">
      <div class="tabs">
        <button
          v-for="s in rankedScenarios"
          :key="s.key"
          :class="{ on: state.scenario === s.key }"
          :style="{ '--rc': rankColor(s.key) ?? 'var(--yellow)' }"
          @click="state.scenario = s.key"
        >
          <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
          <small v-if="pct(s.key) != null" class="tab-pct">{{ pct(s.key) }}%</small>
        </button>
      </div>
      <div v-if="!cardsOnly" class="view" role="group" aria-label="Layout">
        <button :class="{ on: state.rolesView === 'cards' }" :aria-pressed="state.rolesView === 'cards'" @click="state.rolesView = 'cards'">Cards</button>
        <button :class="{ on: view === 'chart' }" :aria-pressed="view === 'chart'" @click="state.rolesView = 'chart'">Chart</button>
      </div>
    </div>
    <template v-if="view === 'chart'">
      <h1>{{ heading }}</h1>
      <p class="chart-source">
        Chances of each future, from
        <select v-model="metricTarget" aria-label="Metric the chances are based on">
          <option v-for="m in metrics" :key="m.target" :value="m.target">{{ m.label }}</option>
        </select>
        forecasts, nearest-term.
      </p>
      <div class="card chart-card">
        <h2 class="chart-title">Demand vs AI automation exposure</h2>
        <PositionChart :jobs="jobs" :context="context" :scenario="backendScenario[state.scenario]" :selected="selected" @select="emit('select', $event)" />
        <p class="foot">
          Orange circles are your matches: bigger means a better fit. {{ chartHint ?? 'Tap one to see its forecast.' }} Grey circles are other jobs for comparison.
          The line through the selected role is its likely range. Exposure is how much AI is already used in a job’s work, weighted by how much of
          that use does the task (automation) rather than helps with it (augmentation), from the Anthropic Economic Index.
        </p>
      </div>
    </template>
    <div v-else class="list-wrap" :class="{ center: pick }">
      <h1 v-if="!cardsOnly">{{ heading }}</h1>
      <p class="chart-source">
        Chances of each future, from
        <select v-model="metricTarget" aria-label="Metric the chances are based on">
          <option v-for="m in metrics" :key="m.target" :value="m.target">{{ m.label }}</option>
        </select>
        forecasts, nearest-term.
      </p>
      <RoleList :jobs="jobs" :selected="pick ? selected : undefined" :roadmaps="roadmaps" @select="emit('select', $event)" />
    </div>
    <p v-if="note && view === 'chart'" class="note">{{ note }}</p>
  </div>
</template>

<style scoped>
.bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.tabs { display: flex; gap: 10px; flex-wrap: wrap; }
.view { margin-left: auto; display: flex; padding: 4px; border-radius: 14px; background: var(--line); }
.view button { padding: 8px 16px; border-radius: 10px; font-weight: 900; font-size: 13px; color: var(--muted); }
.view button.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30,30,30,.1); }
.chart-card { padding: 22px 24px; }
.chart-title { font-size: 17px; font-weight: 900; margin-bottom: 10px; }
.foot { margin-top: 12px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; }
.tabs button { display: flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: 14px; border: 2px solid var(--line-strong); background: #fff; box-shadow: 0 4px 0 rgba(30,30,30,.1); font-weight: 900; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; }
.tabs button { transition: transform .08s, box-shadow .08s; }
.tabs button:active { transform: translateY(3px); box-shadow: 0 1px 0 rgba(30,30,30,.1); translate: none; scale: 1; }
.tabs button.on:active { box-shadow: 0 1px 0 var(--rc); }
.tabs button.on { background: var(--rc); border-color: var(--rc); color: #fff; box-shadow: 0 4px 0 var(--rc); }
.tab-pct { font-weight: 900; opacity: .85; }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 10px; }
.chart-source { margin: 0 0 16px; font-size: 12px; font-weight: 600; color: var(--muted); }
.chart-source select { font: inherit; font-weight: 800; color: var(--ink); background: none; border: none; border-bottom: 2px solid var(--line-strong); padding: 0 2px 1px; cursor: pointer; }
.note { margin-top: 22px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; max-width: 760px; }
.list-wrap { max-width: 760px; }
.list-wrap.center { margin: 0 auto; }
</style>
