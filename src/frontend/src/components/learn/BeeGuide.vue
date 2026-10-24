<script setup lang="ts">
import { RouterLink } from 'vue-router';
import Mascot, { type Mood } from '../Mascot.vue';
import { useFlash } from '../../composables/useFlash';

defineProps<{
  message: string;
  mood?: Mood;
  to?: unknown;
  actionText?: string;
}>();
const { on: wiggle, trigger } = useFlash(700);
</script>

<template>
  <div class="jb jb-bee" :data-wiggle="wiggle ? 'true' : 'false'">
    <button type="button" class="jb-bee__btn" aria-label="Bee, your guide" @click="trigger">
      <Mascot :size="42" :mood="mood" :look="false" />
    </button>
    <div v-if="message" :key="message" class="jb-bubble" role="status">
      <span>{{ message }}</span>
      <RouterLink v-if="to && actionText" :to="to as any" class="jb-bubble__link">{{ actionText }}</RouterLink>
    </div>
  </div>
</template>
