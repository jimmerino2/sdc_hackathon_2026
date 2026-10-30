<script setup lang="ts">
/** A stinger, the currency challenges pay out: one per passed stage. */
withDefaults(defineProps<{ size?: number }>(), { size: 20 });
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
    <path d="M12 23 L8.2 11.5 A4.6 4.6 0 1 1 15.8 11.5 Z" />
  </svg>
</template>
