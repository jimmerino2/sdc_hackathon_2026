<script setup lang="ts">
import Mascot from './Mascot.vue';
import Icon from './Icon.vue';
import { bee, BEES, beeInfo, type BeeName } from '../bee';

/** The four companion bees as a grid of cards. Shared by onboarding and the profile; the caller decides what a pick does. */
defineProps<{ columns?: number }>();
const emit = defineEmits<{ pick: [bee: BeeName] }>();
</script>

<template>
  <div class="grid" :style="{ gridTemplateColumns: `repeat(${columns ?? 2}, 1fr)` }">
    <button v-for="b in BEES" :key="b" type="button" class="option bee" :class="{ selected: bee === b }" :aria-pressed="bee === b" @click="emit('pick', b)">
      <Mascot :size="84" :bee="b" :mood="bee === b ? 'happy' : 'idle'" :look="false" class="m" />
      <h3>{{ b }}</h3>
      <p>{{ beeInfo[b].tagline }}</p>
      <small>{{ beeInfo[b].vibe }}</small>
      <span v-if="bee === b" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
    </button>
  </div>
</template>

<style scoped>
.grid { display: grid; gap: 14px; }
.bee { flex-direction: column; align-items: center; text-align: center; padding: 22px 14px 18px; gap: 4px; }
.bee .m { margin: 8px 0 14px; }
.bee small { font-size: 12px; color: var(--muted); font-weight: 600; line-height: 1.35; margin-top: 4px; }
.bee .tick { position: absolute; top: 12px; right: 12px; margin: 0; }
@media (max-width: 520px) { .grid { grid-template-columns: 1fr 1fr !important; } }
</style>
