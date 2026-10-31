<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import ScenarioInfoDialog from './ScenarioInfoDialog.vue';
import { scenarioColor, scenarioIcon, scenarios, type ScenarioKey } from '../data/flows';
import { useFlow } from '../state';
import { useScenarioProbabilities } from '../composables/useScenarioProbabilities';

/** The AI future picker and the "Chances from" group. Shared by the roles list and a role's outlook, which also passes each future's demand. */
defineProps<{ demand?: Record<ScenarioKey, { text: string; trend: string }> }>();

const { state } = useFlow();
const { metrics, metricTarget, pct, loaded } = useScenarioProbabilities();
const activeMetricLabel = computed(() => metrics.find((m) => m.target === metricTarget.value)?.label ?? 'selected indicator');
const scenarioTooltip = computed(
  () => `Statistical likelihood of this AI scenario occurring, based on ${activeMetricLabel.value.toLowerCase()} forecasts. Does not reflect your job match.`,
);
</script>

<template>
  <div v-if="loaded" class="panel-card">
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
        :style="{ '--rc': scenarioColor[s.key] }"
        @click="state.scenario = s.key"
      >
        <span class="scenario-bar" />
        <Icon :name="scenarioIcon[s.key]" :size="16" class="scenario-icon" />
        <span class="scenario-text">
          <span class="scenario-label">{{ s.label }}</span>
          <small v-if="demand" class="scenario-demand" :class="demand[s.key].trend">{{ demand[s.key].text }}</small>
        </span>
        <span v-if="pct(s.key) != null" class="scenario-pct" :title="scenarioTooltip" :aria-label="scenarioTooltip">{{ pct(s.key) }}%</span>
      </button>
    </div>

    <div class="metric-section">
      <span class="panel-eyebrow">Chances from</span>
      <div class="btn-group btn-group--col" role="radiogroup" aria-label="Metric the chances are based on">
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
  </div>
</template>

<style scoped>
.panel-card { background: #fff; border: 2px solid var(--line-strong); border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 12px; box-shadow: 0 4px 0 rgba(30, 30, 30, .05); }
.panel-head { display: flex; justify-content: space-between; align-items: center; }
.panel-eyebrow { font-size: 13px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.scenario-list { display: flex; flex-direction: column; gap: 6px; }
.scenario-card { position: relative; display: flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 12px; border: 2px solid var(--line); background: #fff; cursor: pointer; text-align: left; transition: transform .08s ease, border-color .12s ease, background .12s ease, box-shadow .12s ease; }
.scenario-card:hover { border-color: var(--line-strong); background: #faf9f6; transform: translateY(-1px); }
.scenario-card:active { transform: translateY(2px); }
.scenario-card.on { border-color: var(--rc); background: #fff; box-shadow: 0 3px 0 var(--rc); }
.scenario-bar { width: 4px; align-self: stretch; min-height: 16px; border-radius: 4px; background: var(--line); flex: none; transition: background .12s ease; }
.scenario-card.on .scenario-bar { background: var(--rc); }
.scenario-icon { flex: none; color: var(--muted); }
.scenario-card.on .scenario-icon { color: var(--rc); }
.scenario-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.scenario-label { font-size: 14px; font-weight: 900; letter-spacing: .04em; text-transform: uppercase; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.scenario-demand { font-size: 14px; font-weight: 800; }
.scenario-pct { font-size: 14px; font-weight: 900; color: var(--muted); background: var(--line); padding: 2px 7px; border-radius: 999px; flex: none; }
.scenario-card.on .scenario-pct { background: var(--rc); color: #fff; }
.scenario-card.k-steady.on .scenario-pct { color: var(--ink); }
.metric-section { padding-top: 10px; border-top: 1.5px solid var(--line); display: flex; flex-direction: column; gap: 6px; }
</style>
