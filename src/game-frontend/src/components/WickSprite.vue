<script setup lang="ts">
import type { Mood } from '@/content/dialogue'

withDefaults(defineProps<{ mood?: Mood; size?: number }>(), { mood: 'neutral', size: 64 })
</script>

<template>
  <svg
    class="wick"
    :class="`mood-${mood}`"
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    shape-rendering="crispEdges"
    aria-hidden="true"
  >
    <!-- handle -->
    <rect x="13" y="1" width="6" height="2" fill="#5a4636" />
    <rect x="12" y="2" width="2" height="3" fill="#5a4636" />
    <rect x="18" y="2" width="2" height="3" fill="#5a4636" />
    <!-- cap -->
    <rect x="9" y="5" width="14" height="3" fill="#ff9800" />
    <rect x="9" y="5" width="14" height="1" fill="#ffc107" />
    <!-- glass body -->
    <rect x="10" y="8" width="12" height="15" fill="#fff3c4" />
    <rect x="10" y="8" width="2" height="15" fill="#ffe08a" />
    <rect x="20" y="8" width="2" height="15" fill="#ffe08a" />
    <!-- flame -->
    <g class="flame">
      <rect x="14" y="11" width="4" height="7" fill="#ff9800" />
      <rect x="15" y="9" width="2" height="3" fill="#ffc107" />
      <rect x="15" y="13" width="2" height="4" fill="#fffdf5" />
    </g>
    <!-- face -->
    <g class="face">
      <template v-if="mood === 'happy' || mood === 'proud'">
        <rect x="12" y="15" width="2" height="1" fill="#2b2219" />
        <rect x="18" y="15" width="2" height="1" fill="#2b2219" />
        <rect x="14" y="19" width="4" height="1" fill="#2b2219" />
        <rect x="13" y="18" width="1" height="1" fill="#2b2219" />
        <rect x="18" y="18" width="1" height="1" fill="#2b2219" />
      </template>
      <template v-else-if="mood === 'worried'">
        <rect x="12" y="15" width="2" height="2" fill="#2b2219" />
        <rect x="18" y="15" width="2" height="2" fill="#2b2219" />
        <rect x="11" y="13" width="2" height="1" fill="#2b2219" />
        <rect x="19" y="13" width="2" height="1" fill="#2b2219" />
        <rect x="14" y="19" width="4" height="1" fill="#2b2219" />
      </template>
      <template v-else-if="mood === 'smug'">
        <rect x="12" y="16" width="2" height="1" fill="#2b2219" />
        <rect x="18" y="15" width="2" height="2" fill="#2b2219" />
        <rect x="15" y="19" width="4" height="1" fill="#2b2219" />
        <rect x="18" y="18" width="1" height="1" fill="#2b2219" />
      </template>
      <template v-else>
        <rect x="12" y="15" width="2" height="2" fill="#2b2219" />
        <rect x="18" y="15" width="2" height="2" fill="#2b2219" />
        <rect x="15" y="19" width="2" height="1" fill="#2b2219" />
      </template>
    </g>
    <!-- base -->
    <rect x="9" y="23" width="14" height="3" fill="#ff9800" />
    <rect x="9" y="25" width="14" height="1" fill="#c46f00" />
    <!-- little feet -->
    <rect x="11" y="26" width="3" height="2" fill="#5a4636" />
    <rect x="18" y="26" width="3" height="2" fill="#5a4636" />
    <g v-if="mood === 'proud'" class="sparkles">
      <rect x="3" y="9" width="2" height="2" fill="#ffc107" />
      <rect x="27" y="12" width="2" height="2" fill="#ffc107" />
      <rect x="5" y="20" width="1" height="1" fill="#ff9800" />
    </g>
  </svg>
</template>

<style scoped>
.wick {
  display: block;
  filter: drop-shadow(0 0 10px rgba(255, 193, 7, 0.45));
  animation: hover 3s ease-in-out infinite;
}

.flame {
  transform-origin: 16px 18px;
  animation: flicker 0.9s steps(3) infinite;
}

.mood-worried .flame {
  animation-duration: 0.4s;
}

.sparkles {
  animation: blink 0.8s steps(2) infinite;
}

@keyframes hover {
  50% {
    transform: translateY(-3px);
  }
}

@keyframes flicker {
  33% {
    transform: scaleY(1.12) scaleX(0.9);
  }
  66% {
    transform: scaleY(0.92);
  }
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
