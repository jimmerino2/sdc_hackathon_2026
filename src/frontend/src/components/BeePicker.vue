<script setup lang="ts">
import { reactive } from 'vue';
import Mascot from './Mascot.vue';
import Icon from './Icon.vue';
import { bee, BEES, beeInfo, type BeeName } from '../bee';

/** The four companion bees as a grid of cards. Shared by onboarding and the profile; the caller decides what a pick does. */
defineProps<{ columns?: number; /** Names only, no taglines (onboarding). */ plain?: boolean; /** Each bee flies in and lands on its own flower (onboarding). */ flowers?: boolean }>();
const emit = defineEmits<{ pick: [bee: BeeName] }>();

/** Petal, heart and leaf colours per bee: Libbee and Phoebee pink, Tobee and Barnabee blue, four different shades. */
const FLOWER: Record<BeeName, { petal: string; edge: string; core: string }> = {
  Libbee: { petal: '#ffb3d1', edge: '#f27fae', core: '#ffd23f' },
  Tobee: { petal: '#7cc6ff', edge: '#3f9be8', core: '#fff1a8' },
  Barnabee: { petal: '#5b7fe0', edge: '#3a55b8', core: '#ffc83d' },
  Phoebee: { petal: '#e8559a', edge: '#b82f73', core: '#ffe08a' },
};
const landed = reactive<Record<string, boolean>>({});
</script>

<template>
  <div class="grid" :style="{ gridTemplateColumns: `repeat(${columns ?? 2}, 1fr)` }">
    <button v-for="b in BEES" :key="b" type="button" class="option bee" :class="{ selected: bee === b }" :aria-pressed="bee === b" @click="emit('pick', b)">
      <div v-if="flowers" class="stage" :class="{ landed: landed[b] }" :style="{ '--d': BEES.indexOf(b) * 0.35 + 's', '--side': BEES.indexOf(b) % 2 ? 1 : -1 }">
        <svg class="flower" viewBox="0 0 120 120" width="140" height="140" aria-hidden="true">
          <path d="M60 58 C60 82 58 100 60 120" stroke="#4fa86a" stroke-width="5" fill="none" stroke-linecap="round" />
          <path d="M59 100 C42 98 34 88 32 80 C48 80 57 88 59 100Z" fill="#6cc283" />
          <path d="M61 92 C78 90 86 80 88 72 C72 72 63 80 61 92Z" fill="#6cc283" />
          <g class="head">
            <ellipse v-for="n in 8" :key="n" cx="60" cy="30" rx="12" ry="22" :fill="FLOWER[b].petal" :stroke="FLOWER[b].edge" stroke-width="2" :transform="`rotate(${(n - 1) * 45} 60 52)`" />
            <circle cx="60" cy="52" r="13" :fill="FLOWER[b].core" :stroke="FLOWER[b].edge" stroke-width="2" />
          </g>
        </svg>
        <Mascot class="fly" :size="84" :bee="b" :wings="!landed[b]" :mood="landed[b] ? (bee === b ? 'happy' : 'idle') : 'surprised'" :look="false" @animationend.self="landed[b] = true" />
      </div>
      <Mascot v-else :size="84" :bee="b" :mood="bee === b ? 'happy' : 'idle'" :look="false" class="m" />
      <h3>{{ b }}</h3>
      <template v-if="!plain">
        <p>{{ beeInfo[b].tagline }}</p>
        <small>{{ beeInfo[b].vibe }}</small>
      </template>
      <span v-if="bee === b" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
    </button>
  </div>
</template>

<style scoped>
.grid { display: grid; gap: 14px; }
.bee { flex-direction: column; align-items: center; text-align: center; padding: 22px 14px 18px; gap: 4px; }
.bee .m { margin: 8px 0 14px; }
.bee small { font-size: 12px; color: var(--muted); font-weight: 600; line-height: 1.35; margin-top: 4px; }
.bee .tick { position: absolute; top: 12px; right: 12px; margin: 0; }

/* The flower's head sits at the stage's lower middle; the bee lands on it. */
.stage { position: relative; width: 160px; height: 168px; margin-top: 2px; }
.flower { position: absolute; left: 50%; bottom: 0; margin-left: -70px; transform-origin: 50% 100%; }
.stage.landed .flower { animation: dip .7s ease-out; }
.stage.landed .head { animation: none; }
.stage .fly { position: absolute; left: 50%; bottom: 62px; margin-left: -42px; animation: land 1.5s var(--d) cubic-bezier(.3, .7, .3, 1) both; }
@keyframes land {
  0% { transform: translate(calc(var(--side) * 140px), -150px) rotate(calc(var(--side) * 14deg)); opacity: 0; }
  12% { opacity: 1; }
  55% { transform: translate(calc(var(--side) * -34px), -48px) rotate(calc(var(--side) * -10deg)); }
  80% { transform: translate(calc(var(--side) * 8px), -14px) rotate(calc(var(--side) * 4deg)); }
  100% { transform: translate(0, 0) rotate(0); }
}
@keyframes dip { 0% { transform: rotate(0) scaleY(1); } 30% { transform: rotate(calc(var(--side) * 5deg)) scaleY(.94); } 65% { transform: rotate(calc(var(--side) * -2deg)); } 100% { transform: rotate(0) scaleY(1); } }
@media (prefers-reduced-motion: reduce) { .fly, .stage.landed .flower { animation: none; } }
@media (max-width: 520px) { .grid { grid-template-columns: 1fr 1fr !important; } }
</style>
