<script setup lang="ts">
import Mascot from './Mascot.vue';
withDefaults(defineProps<{ size?: number }>(), { size: 70 });
</script>

<template>
  <div class="row">
    <Mascot :size="size" />
    <p class="bubble"><slot /></p>
  </div>
</template>

<style scoped>
.row { display: flex; align-items: center; gap: 12px; }
.bubble {
  background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 12px 16px;
  font-weight: 800; font-size: 15px; line-height: 1.35; max-width: 390px;
}
</style>
