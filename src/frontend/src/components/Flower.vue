<script setup lang="ts">
/** A stalk, two leaves and an eight-petal head. Shared by the bee picker and the "where are you" screen. */
export type FlowerColors = { petal: string; edge: string; core: string };
defineProps<{ colors: FlowerColors }>();
</script>

<template>
  <svg class="flower" viewBox="0 0 120 120" width="140" height="140" aria-hidden="true">
    <path d="M60 58 C60 82 58 100 60 120" stroke="#4fa86a" stroke-width="5" fill="none" stroke-linecap="round" />
    <path d="M59 100 C42 98 34 88 32 80 C48 80 57 88 59 100Z" fill="#6cc283" />
    <path d="M61 92 C78 90 86 80 88 72 C72 72 63 80 61 92Z" fill="#6cc283" />
    <g class="head">
      <ellipse v-for="n in 8" :key="n" cx="60" cy="30" rx="12" ry="22" :fill="colors.petal" :stroke="colors.edge" stroke-width="2" :transform="`rotate(${(n - 1) * 45} 60 52)`" />
      <circle cx="60" cy="52" r="13" :fill="colors.core" :stroke="colors.edge" stroke-width="2" />
    </g>
  </svg>
</template>
