<script setup lang="ts">
import MatchBreakdown from './MatchBreakdown.vue';
import type { JobMatch, ScenarioOutlook } from '../api/jobs';

/** The sub card tucked under a role's card: how its match is calculated. The slot goes beside the button. */
defineProps<{ job: JobMatch; scenario: ScenarioOutlook['scenario']; stage?: string | null }>();
</script>

<template>
  <div class="why">
    <MatchBreakdown :job="job" :scenario="scenario" :stage="stage" />
    <slot />
  </div>
</template>

<style scoped>
.why { margin: -6px 10px 0; padding: 14px 14px 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; border: 2px solid var(--line); border-top: 0; border-radius: 0 0 14px 14px; background: #fff; }
</style>
