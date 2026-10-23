<script setup lang="ts">
import Mascot, { type Mood } from '../Mascot.vue';
import { useFlash } from '../../composables/useFlash';

defineProps<{ message: string; mood?: Mood }>();
const { on: wiggle, trigger } = useFlash(700);
</script>

<template>
  <div class="jb jb-bee" :data-wiggle="wiggle ? 'true' : 'false'">
    <button type="button" class="jb-bee__btn" aria-label="Bee, your guide" @click="trigger"><Mascot :size="72" :mood="mood" /></button>
    <div v-if="message" :key="message" class="jb-bubble" role="status">{{ message }}</div>
  </div>
</template>
