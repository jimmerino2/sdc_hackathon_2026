<script setup lang="ts">
import { ref } from 'vue';
import Mascot from '../Mascot.vue';
import type { BeeName } from '../../bee';

/** A party member in the fight: the bee they picked, hovering with its wings going, and able to dive at Robbee. */
const props = withDefaults(defineProps<{ bee: string; name: string; stings: number; me?: boolean; delay?: number; size?: number }>(), { me: false, delay: 0, size: 88 });

const root = ref<HTMLElement | null>(null);

/** Dive at a point (dx, dy pixels from here) and back. */
function strike(dx: number, dy: number) {
  const el = root.value;
  if (!el) return;
  el.style.setProperty('--tx', `${dx}px`);
  el.style.setProperty('--ty', `${dy}px`);
  el.classList.remove('striking');
  void el.offsetWidth; // restart the animation if it is already running
  el.classList.add('striking');
}
defineExpose({ strike, el: root });
</script>

<template>
  <div ref="root" class="pb" @animationend.self="root?.classList.remove('striking')">
    <span class="pb__fly" :style="{ animationDelay: `${-props.delay}s` }">
      <Mascot :size="size" :bee="bee as BeeName" mood="serious" wings :look="false" />
    </span>
    <span class="pb__label">{{ me ? 'You' : name }} · {{ stings }} {{ stings === 1 ? 'stinger' : 'stingers' }}</span>
  </div>
</template>

<style scoped>
.pb { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.pb__fly { display: block; animation: pb-hover 3.4s ease-in-out infinite; }
.pb.striking { animation: pb-strike .75s cubic-bezier(.5, 0, .3, 1); z-index: 5; }
.pb__label { padding: 2px 10px; border-radius: 999px; background: rgba(255, 255, 255, .72); font-size: 16px; font-weight: 800; white-space: nowrap; color: #1b1b1b; }
@keyframes pb-hover {
  0%, 100% { transform: translate(0, 0) rotate(-3deg); }
  30% { transform: translate(8px, -12px) rotate(3deg); }
  65% { transform: translate(-7px, -5px) rotate(-2deg); }
}
@keyframes pb-strike {
  0% { transform: translate(0, 0) scale(1); }
  45% { transform: translate(var(--tx), var(--ty)) scale(1.25) rotate(8deg); }
  58% { transform: translate(calc(var(--tx) * .92), calc(var(--ty) * .92)) scale(1.15); }
  100% { transform: translate(0, 0) scale(1); }
}
@media (prefers-reduced-motion: reduce) { .pb__fly, .pb.striking { animation: none; } }
</style>
