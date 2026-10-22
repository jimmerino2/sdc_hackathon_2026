<script setup lang="ts">
import Mascot from './Mascot.vue';
</script>

<template>
  <div class="cw">
    <div class="scene">
      <Mascot :size="64" gear="glasses" mood="idle" :gaze="[0.9, 0.1]" :look="false" />
      <svg viewBox="0 0 120 70" class="mini" aria-hidden="true">
        <rect x="1" y="1" width="118" height="68" rx="10" fill="#fff" stroke="#eceae5" stroke-width="2" />
        <g class="bars" fill="#ffe08a">
          <rect x="14" y="44" width="12" height="16" rx="2" /><rect x="34" y="38" width="12" height="22" rx="2" />
          <rect x="54" y="30" width="12" height="30" rx="2" /><rect x="74" y="22" width="12" height="38" rx="2" /><rect x="94" y="12" width="12" height="48" rx="2" fill="#ffc107" />
        </g>
        <polyline class="line" points="14,42 34,36 54,28 74,20 100,9" fill="none" stroke="#1e1e1e" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        <circle class="dot" cx="100" cy="9" r="4.5" fill="#ff9800" stroke="#1e1e1e" stroke-width="2" />
      </svg>
    </div>
    <p class="text"><slot /></p>
  </div>
</template>

<style scoped>
.cw { display: flex; flex-direction: column; gap: 10px; }
.scene { display: flex; align-items: center; gap: 12px; }
.mini { width: 150px; flex: none; }
.bars rect { transform-box: fill-box; transform-origin: 50% 100%; animation: grow 4s ease-out infinite; }
.bars rect:nth-child(2) { animation-delay: .15s; } .bars rect:nth-child(3) { animation-delay: .3s; } .bars rect:nth-child(4) { animation-delay: .45s; } .bars rect:nth-child(5) { animation-delay: .6s; }
.line { stroke-dasharray: 120; animation: draw 4s ease-out infinite; }
.dot { animation: blip 4s ease-out infinite; transform-box: fill-box; transform-origin: center; }
.text { background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 12px 16px; font-weight: 800; font-size: 14px; line-height: 1.35; }
@keyframes grow { 0% { transform: scaleY(0); } 30%, 100% { transform: scaleY(1); } }
@keyframes draw { 0% { stroke-dashoffset: 120; } 55%, 100% { stroke-dashoffset: 0; } }
@keyframes blip { 0%, 50% { transform: scale(0); } 65% { transform: scale(1.4); } 80%, 100% { transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .cw * { animation: none !important; } }
</style>
