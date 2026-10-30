<script setup lang="ts">
import { computed } from 'vue';
import Icon from '../Icon.vue';
import type { RoadmapChallenge } from '../../api/roadmap';

/** The roadmap's challenge at the top of the Learn page. Details and submitting live on the Challenges page. */
const props = defineProps<{ challenge: RoadmapChallenge }>();

const c = computed(() => props.challenge);
const passed = computed(() => c.value.status === 'passed' || c.value.status === 'advancing');
const meta = computed(() => {
  if (c.value.stage === 2 && passed.value) return 'Complete · hive patched';
  if (c.value.stage === 1 && passed.value) return 'Passed! Robbee has something to say…';
  if (c.value.stage === 2) return c.value.twist ? `Robbee’s twist: ${c.value.twist}` : 'Robbee rewrote the brief';
  return c.value.score != null ? `Last score ${Math.round(c.value.score)} · ${c.value.pass_score}+ to pass` : `Build it, push it to GitHub, score ${c.value.pass_score}+ to pass`;
});
</script>

<template>
  <RouterLink :to="{ name: 'challenges', query: { open: c.challenge_id } }" class="jb jb-quest jb-quest--link">
    <span class="jb-quest__head">
      <span class="jb-quest__disc"><Icon name="trophy" :size="24" /></span>
      <span class="jb-quest__label">
        <span class="jb-eyebrow">Challenge · stage {{ c.stage }} of 2</span>
        <span class="jb-quest__title">{{ c.title }}</span>
        <span class="jb-quest__meta">{{ meta }}</span>
      </span>
      <Icon class="jb-quest__chev" name="arrow" :size="20" />
    </span>
  </RouterLink>
</template>
