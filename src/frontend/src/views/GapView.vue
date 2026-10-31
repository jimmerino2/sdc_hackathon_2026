<script setup lang="ts">
import { computed, onMounted } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import CareerSimulator from '../components/CareerSimulator.vue';
import { loadSkillPlan, useFlow } from '../state';

/**
 * The last stop before the pathway. Jobee has already proposed a list of skills for the chosen role (started when the
 * learner left the forecast page); they start added here, so the matches show what they would do, and the learner can
 * add or remove any. Whatever is on the list at the end is what the roadmap is built from.
 */
const { state } = useFlow();
onMounted(() => loadSkillPlan(state.value)); // does nothing if it already started
const plan = computed(() => state.value.skillPlan);
/** Wait while the list is on its way; if it failed, carry on without one (the roadmap then chooses its own skills). */
const waiting = computed(() => plan.value.status === 'loading' || (plan.value.status === 'idle' && !!state.value.chosenRoleId));
</script>

<template>
  <FlowShell next="sync" next-label="Build my pathway" back="signal" mood="happy" gear="glasses" wide>
    <template #bubble>
      <template v-if="waiting">Choosing the skills worth learning for this role…</template>
      <template v-else-if="plan.status === 'done'">These are the skills I’d learn for this role. Add or remove any and watch your matches change.</template>
      <template v-else>What if you learned a new skill? Tap one and watch your matches change.</template>
    </template>
    <div v-if="waiting" class="wait skel card" aria-busy="true" aria-label="Choosing skills" />
    <CareerSimulator v-else embedded :preselect="plan.skills" />
  </FlowShell>
</template>

<style scoped>
.wait { height: 420px; }
</style>
