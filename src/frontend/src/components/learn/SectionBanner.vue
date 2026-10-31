<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import JbButton from './JbButton.vue';

defineProps<{ eyebrow: string; title: string; meta?: string; guidebook?: RouteLocationRaw }>();
</script>

<template>
  <section class="jb jb-section">
    <div>
      <p class="jb-eyebrow">{{ eyebrow }}</p>
      <h2 class="jb-section__title">{{ title }}</h2>
      <p v-if="meta" class="jb-section__meta">{{ meta }} <slot /></p>
    </div>
    <JbButton v-if="guidebook" variant="ink" icon="book" :to="guidebook">Guidebook</JbButton>
  </section>
</template>
