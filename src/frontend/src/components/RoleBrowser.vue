<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import Icon from "./Icon.vue";
import InfoDialog from "./InfoDialog.vue";
import PositionChart from "./PositionChart.vue";
import RoleList from "./RoleList.vue";
import { scenarios } from "../data/flows";
import { backendScenario } from "../api/forecast";
import { fetchMethodology, type Methodology } from "../api/methodology";
import type { ContextRole, JobMatch } from "../api/jobs";
import type { RoadmapSummary } from "../api/roadmap";
import { useFlow } from "../state";
import { day } from "../occupational/format";
import { useScenarioProbabilities } from "../composables/useScenarioProbabilities";

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
/** Each future keeps its colour whatever its chance is: green speeds up, yellow holds steady, red slows down. */
const sColor = { accelerates: "#2e7d4f", steady: "var(--yellow)", slows: "#c62828" } as const;
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
const view = computed(() => (props.cardsOnly ? "cards" : state.value.rolesView));
const assumptions = ref<Methodology["scenarios"] | null>(null);
const methodology = ref<Methodology | null>(null);
onMounted(() =>
  fetchMethodology()
    .then((m) => {
      methodology.value = m;
      assumptions.value = m.scenarios;
    })
    .catch(() => {}),
);
/** What each future means for a role, in plain words (keyed by the backend's scenario name). */
const futureText: Record<string, string> = {
  "Rapid AI": "AI spreads quickly. Roles where AI can do much of the work see slower job growth; the rest see more.",
  Baseline: "AI keeps moving at about its recent pace. No extra push either way.",
  Slow: "AI spreads slowly. Roles where AI can do much of the work hold up better.",
};
/** The size of the assumed effect, e.g. "25" (the same for each end; it is applied in opposite directions). */
const assumedEffect = computed(() => {
  const e = assumptions.value?.futures.map((f) => Math.abs(f.effect_12m ?? 0)).find((v) => v > 0);
  return e == null ? "a fixed number of" : `±${Math.round(e * 100)}`;
});
const sIcon = { accelerates: "tup", steady: "arrow", slows: "tdown" } as const;

function outlook(job: JobMatch) {
  return job.outlook.find((o) => o.scenario === backendScenario[state.value.scenario]);
}
/** The heading follows what the forecast actually says for this tab, so it never promises growth that isn't there. */
const heading = computed(() => {
  const trends = props.jobs.map((j) => outlook(j)?.trend);
  const growing = trends.filter((t) => t === "growing").length;
  const shrinking = trends.filter((t) => t === "shrinking").length;
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
          v-for="s in scenarios"
          :key="s.key"
          :class="[`k-${s.key}`, { on: state.scenario === s.key }]"
          :style="{ '--rc': sColor[s.key] }"
          @click="state.scenario = s.key"
        >
          <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
          <small v-if="pct(s.key) != null" class="tab-pct">{{ pct(s.key) }}%</small>
        </button>
        <InfoDialog v-if="assumptions" title="What the three AI futures mean">
          <p>
            Nobody knows how fast AI will move, so we show three possible futures. They are what-ifs to plan around, not
            predictions.
          </p>
          <ul>
            <li v-for="f in assumptions.futures" :key="f.scenario">
              <b>{{ f.tab }}</b
              >: {{ futureText[f.scenario] }}
            </li>
          </ul>
          <h3>Where the chances come from</h3>
          <ul class="src-list">
            <li v-for="m in metrics" :key="m.target" class="src-item" :class="{ now: m.target === metricTarget }">
              <b>{{ m.label }}</b
              ><span v-if="m.target === metricTarget" class="tag-now">in use</span>
              <span class="src-about">{{ m.about }}</span>
              <template v-if="methodology?.forecasts[m.target]">
                <span
                  >Source:
                  <a
                    :href="methodology.forecasts[m.target]!.provenance.url ?? undefined"
                    target="_blank"
                    rel="noopener"
                    >{{ methodology.forecasts[m.target]!.provenance.source }}</a
                  ></span
                >
                <span
                  >Data as of <b>{{ day(methodology.forecasts[m.target]!.provenance.last_updated) }}</b> · forecast made
                  {{ day(methodology.forecasts[m.target]!.configuration.issued) }} ·
                  {{ methodology.forecasts[m.target]!.provenance.geography }}</span
                >
              </template>
              <span v-else class="muted">Source details are not available right now.</span>
            </li>
          </ul>
        </InfoDialog>
      </div>
      <div v-if="!cardsOnly" class="view" role="group" aria-label="Layout">
        <button
          :class="{ on: state.rolesView === 'cards' }"
          :aria-pressed="state.rolesView === 'cards'"
          @click="state.rolesView = 'cards'"
        >
          Cards
        </button>
        <button :class="{ on: view === 'chart' }" :aria-pressed="view === 'chart'" @click="state.rolesView = 'chart'">
          Chart
        </button>
      </div>
    </div>
    <template v-if="view === 'chart'">
      <h1>{{ heading }}</h1>
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
          >
            {{ m.label }}
          </button>
        </div>
      </div>
      <div class="card chart-card">
        <h2 class="chart-title">Demand vs AI automation exposure</h2>
        <PositionChart
          :jobs="jobs"
          :context="context"
          :scenario="backendScenario[state.scenario]"
          :selected="selected"
          @select="emit('select', $event)"
        />
        <p class="foot">
          Orange circles are your matches: bigger means a better fit.
          {{ chartHint ?? "Tap one to see its forecast." }} Grey circles are other jobs for comparison. The line through
          the selected role is its likely range. Exposure is how much AI is already used in a job’s work, weighted by
          how much of that use does the task (automation) rather than helps with it (augmentation), from the Anthropic
          Economic Index.
        </p>
      </div>
    </template>
    <div v-else class="list-wrap" :class="{ center: pick }">
      <h1 v-if="!cardsOnly">{{ heading }}</h1>
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
          >
            {{ m.label }}
          </button>
        </div>
      </div>
      <RoleList
        :jobs="jobs"
        :selected="pick ? selected : undefined"
        :roadmaps="roadmaps"
        :stage="stage"
        @select="emit('select', $event)"
      />
    </div>
    <p v-if="note && view === 'chart'" class="note">{{ note }}</p>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  align-items: center;
  flex: 1 1 auto;
  min-width: 0;
}
.view {
  margin-left: auto;
  display: flex;
  padding: 4px;
  border-radius: 14px;
  background: var(--line);
}
.view button {
  padding: 8px 16px;
  border-radius: 10px;
  font-weight: 900;
  font-size: 13px;
  color: var(--muted);
}
.view button.on {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 2px 0 rgba(30, 30, 30, 0.1);
}
.chart-card {
  padding: 22px 24px;
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
.tabs button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex: 1 1 0;
  min-width: 0;
  white-space: nowrap;
  padding: 9px 10px;
  border-radius: 12px;
  border: 2px solid var(--line-strong);
  background: #fff;
  box-shadow: 0 3px 0 rgba(30, 30, 30, 0.1);
  font-weight: 900;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.tabs button:not(.on) svg {
  color: var(--rc);
}
.tabs button.k-steady:not(.on) svg {
  color: var(--amber-ink);
}
.tabs button {
  transition:
    transform 0.08s,
    box-shadow 0.08s;
}
.tabs button:active {
  transform: translateY(3px);
  box-shadow: 0 1px 0 rgba(30, 30, 30, 0.1);
  translate: none;
  scale: 1;
}
.tabs button.on:active {
  box-shadow: 0 1px 0 var(--rc);
}
.tabs button.on {
  background: var(--rc);
  border-color: var(--rc);
  color: #fff;
  box-shadow: 0 3px 0 var(--rc);
}
.tabs button.k-steady.on {
  color: var(--ink);
}
@media (max-width: 520px) {
  .tabs button {
    padding: 8px 4px;
    font-size: 9.5px;
    letter-spacing: 0.02em;
    gap: 3px;
  }
  .tabs button svg {
    display: none;
  }
}
.src-list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: grid;
  gap: 10px;
}
.src-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  border: 2px solid var(--line);
  border-radius: 14px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.45;
}
.src-item.now {
  border-color: var(--yellow);
  background: var(--cream);
}
.src-item b {
  font-weight: 900;
}
.src-about {
  color: var(--muted);
}
.src-item a {
  color: var(--ink);
  text-decoration: underline;
}
.tag-now {
  align-self: flex-start;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--amber-ink);
}
.tab-pct {
  font-weight: 900;
  opacity: 0.85;
}
h1 {
  font-size: 30px;
  font-weight: 900;
  margin-bottom: 10px;
}
.metric-wrap {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.seg-label {
  font-size: 13px;
  font-weight: 900;
  color: var(--muted);
  white-space: nowrap;
}
.metric-seg {
  display: inline-flex;
  padding: 4px;
  border-radius: 14px;
  background: var(--line);
}
.metric-seg button {
  padding: 8px 16px;
  border-radius: 10px;
  font-weight: 900;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
  white-space: nowrap;
  transition:
    background 0.15s,
    color 0.15s;
}
.metric-seg button:hover {
  color: var(--ink);
}
.metric-seg button.on {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 2px 0 rgba(30, 30, 30, 0.1);
}
@media (max-width: 480px) {
  .metric-wrap {
    flex-wrap: wrap;
  }
  .metric-seg button {
    padding: 7px 10px;
    font-size: 11px;
  }
}
.note {
  margin-top: 22px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  line-height: 1.5;
  max-width: 760px;
}
.list-wrap {
  max-width: 760px;
}
.list-wrap.center {
  margin: 0 auto;
}
</style>
