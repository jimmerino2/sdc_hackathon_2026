<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 70 });
</script>

<template>
  <div
    class="mascot"
    :style="{ width: size + 'px', height: size + 'px', borderRadius: `${size * 0.34}px ${size * 0.34}px ${size * 0.34}px ${size * 0.06}px` }"
  >
    <i :style="{ width: size * 0.13 + 'px', height: size * 0.13 + 'px' }" />
    <i :style="{ width: size * 0.13 + 'px', height: size * 0.13 + 'px' }" />
  </div>
</template>

<style scoped>
.mascot { background: var(--yellow); display: flex; align-items: center; justify-content: center; gap: 22%; flex: none; }
.mascot i { background: var(--ink); border-radius: 50%; display: block; }
</style>
