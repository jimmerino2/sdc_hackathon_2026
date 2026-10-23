<script setup lang="ts">
import { ref } from 'vue';
import Icon from '../Icon.vue';

defineProps<{ title: string; text?: string }>();
const drawKey = ref(0); // remounting the icon replays its draw-in animation
</script>

<template>
  <aside class="jb jb-signal" @mouseenter="drawKey++">
    <span class="jb-signal__icon"><Icon :key="drawKey" class="jb-draw" name="tup" :size="22" /></span>
    <div>
      <p class="jb-signal__title">{{ title }}</p>
      <p class="jb-signal__text">{{ text ?? 'Rechecked weekly against live job postings.' }}</p>
    </div>
    <span class="jb-signal__live" title="Live data" aria-hidden="true" />
  </aside>
</template>
