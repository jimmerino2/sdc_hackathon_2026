<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import CareerSimulator from '../components/CareerSimulator.vue';
import { allNodes } from '../learn/skillState';
import { useFlow } from '../state';
import { go } from '../router';

/**
 * The same page as the skill gap, now for the AI skills. The roadmap was built on the screen before this one, in one go from the
 * skills picked on the page before that, and its AI skills (one per section) are shown here next to those skills, so the learner sees
 * what they would add on top: today, with their skills, with AI skills too. Opening the roadmap comes after the email step.
 */
const { state } = useFlow();
const router = useRouter();

onMounted(() => {
  if (!state.value.roadmap.data) router.replace(go('gap')); // came here directly (or after a reload): there is no roadmap yet
});

const aiSkills = computed(() => allNodes(state.value.roadmap.data).filter((n) => n.kind === 'ai_guide').map((n) => ({ name: n.skill_name })));
</script>

<template>
  <FlowShell next="sync" next-label="Continue" back="gap" mood="happy" gear="glasses" wide>
    <template #bubble>
      <template v-if="aiSkills.length">These are the AI skills I’d add. They’re the purple part: see how much more you’d suit your roles.</template>
      <template v-else>This roadmap has no AI skills yet.</template>
    </template>
    <CareerSimulator v-if="aiSkills.length" embedded ai :ai-skills="aiSkills" />
    <p v-else class="note">You can go on and open your roadmap. Rebuild it later to get AI skills in it.</p>
  </FlowShell>
</template>

<style scoped>
.note { font-size: 17px; font-weight: 700; color: var(--muted); }
</style>
