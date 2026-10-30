<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import MatchBreakdown from './MatchBreakdown.vue';
import { matchPercent, type JobMatch, type ScenarioOutlook } from '../api/jobs';

/** The "Why 71%?" sub card tucked under a role's card. The slot goes beside "Why 71%?". */
const props = defineProps<{ job: JobMatch; scenario: ScenarioOutlook['scenario']; stage?: string | null }>();
const percent = computed(() => matchPercent(props.job, props.scenario));
</script>

<template>
  <details class="why">
    <summary>Why {{ percent }}%? <Icon name="chevron" :size="14" class="chev" /><slot /></summary>
    <MatchBreakdown :job="job" :scenario="scenario" :stage="stage" />
  </details>
</template>

<style scoped>
.why { margin: -6px 10px 0; padding: 14px 14px 8px; border: 2px solid var(--line); border-top: 0; border-radius: 0 0 14px 14px; background: #fff; }
.why summary { list-style: none; cursor: pointer; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12px; font-weight: 800; color: var(--muted); }
.why summary::-webkit-details-marker { display: none; }
.chev { transition: transform .15s; }
.why[open] .chev { transform: rotate(180deg); }
.why[open] summary { margin-bottom: 8px; }
.why :deep(.mb) { padding-bottom: 6px; }
</style>
