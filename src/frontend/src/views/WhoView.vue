<script setup lang="ts">
import { ref } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Flower, { type FlowerColors } from '../components/Flower.vue';
import Icon from '../components/Icon.vue';
import Mascot from '../components/Mascot.vue';
import { whoOptions } from '../data/flows';
import { useFlow } from '../state';

const { state } = useFlow();

/** One flower per stage, three different shades (light blue, pink, deep pink), like the bee picker. */
const FLOWERS: FlowerColors[] = [
  { petal: '#7cc6ff', edge: '#3f9be8', core: '#fff1a8' },
  { petal: '#ffb3d1', edge: '#f27fae', core: '#ffd23f' },
  { petal: '#e8559a', edge: '#b82f73', core: '#ffe08a' },
];

/** True while the bee is mid-hop: wings out, then it settles on the flower. */
const hopping = ref(false);

function pick(i: number) {
  if (state.value.who === i) return;
  state.value.who = i;
  hopping.value = true;
}
</script>

<template>
  <FlowShell :progress="1" next="interests" back="name" gear="magnifier">
    <template #bubble>Where are you in your tech journey?</template>
    <div class="field">
      <div class="list" role="radiogroup" aria-label="Where you are right now">
        <button
          v-for="(o, i) in whoOptions"
          :key="o.title"
          type="button"
          role="radio"
          class="option stage"
          :class="{ selected: state.who === i }"
          :aria-checked="state.who === i"
          :aria-label="o.title"
          @click="pick(i)"
        >
          <span class="plot"><Flower :colors="FLOWERS[i]" /></span>
          <h3><Icon :name="o.icon" :size="20" :stroke="2.4" class="who-ic" />{{ o.short }}</h3>
          <span v-if="state.who === i" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
        </button>
      </div>
      <!-- One bee for the whole row: it slides to the picked flower and hops as it goes. -->
      <div class="rider" :style="{ '--i': state.who }" aria-hidden="true">
        <div :key="state.who" class="hop" @animationend="hopping = false">
          <Mascot :size="84" :wings="hopping" :mood="hopping ? 'surprised' : 'happy'" :look="false" />
        </div>
      </div>
    </div>
  </FlowShell>
</template>

<style scoped>
.field { --gap: 14px; position: relative; }
.list { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--gap); }
.stage { flex-direction: column; align-items: center; text-align: center; padding: 22px 12px 18px; gap: 4px; }
.stage h3 { font-size: 19px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.who-ic { color: var(--orange); }
.plot { display: block; width: 140px; height: 168px; margin-top: 2px; position: relative; }
.plot :deep(.flower) { position: absolute; left: 0; bottom: 0; }
.stage .tick { position: absolute; top: 12px; right: 12px; margin: 0; }

/* The bee sits on the flower head: centred over the picked column, 84px wide, the head ~46px below the card top. */
.rider {
  position: absolute; top: 46px; width: 84px; height: 84px; pointer-events: none;
  left: calc((100% - 2 * var(--gap)) / 3 * var(--i) + var(--gap) * var(--i) + (100% - 2 * var(--gap)) / 6 - 42px);
  transition: left .55s cubic-bezier(.45, 0, .25, 1);
}
.hop { animation: hop .55s cubic-bezier(.3, .7, .4, 1) both; transform-origin: 50% 100%; }
@keyframes hop {
  0% { transform: translateY(0) scale(1, 1); }
  15% { transform: translateY(2px) scale(1.08, .9); }
  50% { transform: translateY(-64px) scale(.96, 1.06) rotate(-6deg); }
  85% { transform: translateY(2px) scale(1.06, .94); }
  100% { transform: translateY(0) scale(1, 1); }
}
@media (prefers-reduced-motion: reduce) { .rider { transition: none; } .hop { animation: none; } }
@media (max-width: 560px) {
  .field { zoom: .68; }
}
</style>
