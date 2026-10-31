<script setup lang="ts">
import { computed, watch } from 'vue';
import RoleList from './RoleList.vue';
import ScenarioPanel from './ScenarioPanel.vue';
import { backendScenario } from '../api/forecast';
import type { JobMatch } from '../api/jobs';
import type { RoadmapSummary } from '../api/roadmap';
import { useFlow } from '../state';
import { useScenarioProbabilities } from '../composables/useScenarioProbabilities';

/** Suggested roles as a compact list, with the AI future picker. Shared by the onboarding roles page and the sidebar one. */
const props = defineProps<{
  jobs: JobMatch[];
  /** The role shown as selected (open row in the list). */
  selected: string | null;
  /** Rows pick a role (shown open, with a radio) instead of opening it. */
  pick?: boolean;
  /** The profile's roadmaps by role. When given, each card shows its role's roadmap status. */
  roadmaps?: Record<string, RoadmapSummary>;
  /** The career stage behind the education part of each match. */
  stage?: string | null;
}>();
const emit = defineEmits<{ select: [code: string] }>();

const { state, scenario } = useFlow();
const { pct, ranked } = useScenarioProbabilities();
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
  <div class="browser-layout">
    <main class="main-col">
      <h1 v-if="!pick" class="headline">{{ heading }}</h1>
      <RoleList :jobs="jobs" :selected="pick ? selected : undefined" :roadmaps="roadmaps" :stage="stage" @select="emit('select', $event)" />
    </main>

    <aside class="sidebar" aria-label="Controls and scenarios">
      <ScenarioPanel />
    </aside>
  </div>
</template>

<style scoped>
/* Dashboard two-column layout */
.browser-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 32px;
  align-items: start;
}
.main-col {
  min-width: 0;
  max-width: 760px;
  width: 100%;
}
.headline {
  font-size: 32px;
  font-weight: 900;
  line-height: 1.25;
  margin-bottom: 20px;
  letter-spacing: -0.01em;
}
/* Sidebar Controls */
.sidebar {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

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
</style>

