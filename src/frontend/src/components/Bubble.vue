<script setup lang="ts">
import Mascot, { type Gear, type Mood } from './Mascot.vue';
withDefaults(defineProps<{ size?: number; mood?: Mood; gear?: Gear; wings?: boolean; thought?: boolean }>(), { size: 70, mood: 'idle', gear: 'none', wings: false, thought: false });
</script>

<template>
  <div class="row">
    <Mascot :size="size" :mood="mood" :gear="gear" :wings="wings" />
    <span v-if="thought" class="dots"><i /><i /></span>
    <p class="bubble" :class="{ cloud: thought }"><slot /></p>
  </div>
</template>

<style scoped>
.row { display: flex; align-items: center; gap: 12px; }
.bubble {
  background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 12px 16px;
  font-weight: 800; font-size: 15px; line-height: 1.35; max-width: 390px;
}
.cloud { border-radius: 28px; padding: 16px 22px; border-color: var(--line-strong); box-shadow: 0 4px 0 var(--line); animation: drift 3s ease-in-out infinite; }
.dots { display: flex; align-items: flex-end; gap: 5px; margin: 0 -6px 0 -4px; align-self: flex-start; padding-top: 6px; }
.dots i { display: block; background: #fff; border: 2px solid var(--line-strong); border-radius: 50%; animation: pulse 1.6s ease-in-out infinite; }
.dots i:nth-child(1) { width: 8px; height: 8px; }
.dots i:nth-child(2) { width: 14px; height: 14px; animation-delay: .25s; }
@keyframes pulse { 50% { transform: scale(1.25); } }
@keyframes drift { 50% { transform: translateY(-3px); } }
</style>
