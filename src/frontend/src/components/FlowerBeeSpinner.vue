<script setup lang="ts">
import { computed } from 'vue';
import Mascot from './Mascot.vue';

/**
 * A flower in bloom with the learner's chosen bee flying laps around it. A spinner that fits the Jobee theme.
 * The bee follows the picked companion (see bee.ts) and stays upright while it circles.
 */
const props = withDefaults(defineProps<{ size?: number; petal?: string; edge?: string; core?: string }>(), {
  size: 170,
  petal: '#ffb3d1',
  edge: '#f27fae',
  core: '#ffd23f',
});

const PETALS = 8;
const beeSize = computed(() => Math.round(props.size * 0.27));
</script>

<template>
  <div class="fbs" :style="{ '--s': props.size + 'px', '--b': beeSize + 'px' }" aria-hidden="true">
    <svg class="ring" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r="43" fill="none" stroke="#ffd966" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="1 7" />
    </svg>

    <svg class="flower" viewBox="0 0 120 120">
      <g class="sway">
        <g v-for="n in PETALS" :key="n" :transform="`rotate(${(n - 1) * (360 / PETALS)} 60 60)`">
          <ellipse class="petal" cx="60" cy="38" rx="10" ry="19" :fill="petal" :stroke="edge" stroke-width="2" :style="{ animationDelay: `${(n - 1) * 45}ms` }" />
        </g>
        <circle class="core" cx="60" cy="60" r="12" :fill="core" :stroke="edge" stroke-width="2" />
      </g>
    </svg>

    <div class="orbit">
      <div class="fly">
        <div class="unspin">
          <div class="bob">
            <Mascot :size="beeSize" mood="happy" gear="none" wings :look="false" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fbs { --lap: 2.8s; position: relative; width: var(--s); height: var(--s); }
.fbs > * { position: absolute; inset: 0; width: 100%; height: 100%; }
.fbs > .flower { inset: 14%; width: 72%; height: 72%; overflow: visible; }

.ring { animation: spin 16s linear infinite reverse; opacity: .85; }

/* The flower blooms petal by petal, then sways gently. */
.flower .sway { transform-box: view-box; transform-origin: 60px 60px; animation: sway 3.2s ease-in-out infinite .6s; }
.petal { transform-box: view-box; transform-origin: 60px 60px; animation: bloom .5s cubic-bezier(.34, 1.56, .64, 1) both; }
.core { transform-box: view-box; transform-origin: 60px 60px; animation: bloom .4s cubic-bezier(.34, 1.56, .64, 1) .35s both, beat 1.6s ease-in-out 1s infinite; }

/* The bee flies a full lap. .orbit turns, .unspin turns back by the same amount so the bee stays upright. */
.orbit { animation: spin var(--lap) linear infinite; }
.fly { position: absolute; left: 50%; top: 50%; width: var(--b); height: var(--b); margin: calc(var(--b) / -2) 0 0 calc(var(--b) / -2); transform: translateX(calc(var(--s) * .36)); animation: drift 1.4s ease-in-out infinite; }
.unspin { width: 100%; height: 100%; animation: unspin var(--lap) linear infinite; }
.bob { width: 100%; height: 100%; animation: bob .5s ease-in-out infinite alternate; }
.fbs :deep(.shadow) { display: none; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes unspin { to { transform: rotate(-360deg); } }
@keyframes bloom { from { transform: scale(0) rotate(-40deg); opacity: 0; } to { transform: scale(1) rotate(0); opacity: 1; } }
@keyframes sway { 0%, 100% { transform: rotate(-5deg) scale(1); } 50% { transform: rotate(5deg) scale(1.04); } }
@keyframes beat { 50% { transform: scale(1.12); } }
@keyframes drift { 0%, 100% { transform: translateX(calc(var(--s) * .36)); } 50% { transform: translateX(calc(var(--s) * .31)); } }
@keyframes bob { from { transform: translateY(calc(var(--s) * -.018)) rotate(-6deg); } to { transform: translateY(calc(var(--s) * .018)) rotate(6deg); } }

/* Reduced motion: the bee still circles (it is the progress signal) but slowly; everything decorative stops. */
@media (prefers-reduced-motion: reduce) {
  .fbs { --lap: 8s; }
  .ring, .flower .sway, .petal, .core, .fly, .bob { animation: none; }
}
</style>
