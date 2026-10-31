<script setup lang="ts">
import { ref, watch } from 'vue';
import Icon from '../Icon.vue';
import { useFlash } from '../../composables/useFlash';
import type { SkillState } from '../../learn/skillState';

const props = defineProps<{ name: string; kind?: string; state: SkillState; selected?: boolean; tag?: string | null; busy?: boolean; /** Orb above its label, for the graph layout. */ stack?: boolean; /** The skill group's icon and yellow shade (0 lightest): they mark the orb. */ icon?: string; shade?: number; /** Set when a demand forecast matched this skill; shows a trend badge the learner can click to select it. */ forecastDirection?: 'rising' | 'falling' | 'flat' | null ; /** A section's AI study guide: drawn purple and 1.5x the size. */ ai?: boolean }>();
const emit = defineEmits<{ select: [] }>();

const { on: shaking, trigger: shake } = useFlash(480);
const burstKey = ref(0);
// A node that becomes done throws confetti from its centre.
watch(() => props.state, (now, was) => { if (was !== 'done' && now === 'done') burstKey.value++; });

const BURST_COLORS = ['var(--honey)', 'var(--pop-orange)', 'var(--pop-sky)', 'var(--text)'];
const particles = Array.from({ length: 14 }, (_, i) => {
  const a = (i / 14) * Math.PI * 2;
  const r = i % 2 ? 62 : 44;
  return { '--dx': `${Math.round(Math.cos(a) * r)}px`, '--dy': `${Math.round(Math.sin(a) * r)}px`, '--c': BURST_COLORS[i % 4]! };
});

const status = { done: 'completed', locked: 'locked', ready: 'ready to learn' } as const;
const dirIcon = { rising: 'tup', falling: 'tdown' } as const;

function click() {
  if (props.state === 'locked') shake();
  emit('select');
}

/** The forecast badge selects the node too (same side panel, just a second way in). */
function clickForecast(e: MouseEvent) {
  e.stopPropagation();
  emit('select');
}
</script>

<template>
  <div class="jb jb-node" :data-ai="ai ? 'true' : undefined" :data-layout="stack ? 'stack' : undefined" :data-grouped="shade !== undefined ? 'true' : undefined" :style="shade !== undefined ? { '--gs': shade } : undefined" :data-state="state" :data-selected="selected ? 'true' : 'false'" :data-shaking="shaking ? 'true' : 'false'">
    <span v-if="tag" class="jb-node__tag">{{ tag }}</span>
    <div class="jb-node__discwrap">
      <button type="button" class="jb-node__disc" :aria-label="`${name}, ${status[state]}`" :aria-pressed="!!selected" :aria-busy="busy || undefined" @click="click">
        <Icon v-if="state === 'done'" class="jb-draw" name="check" :size="30" :stroke="3" />
        <Icon v-else :name="icon ?? (state === 'locked' ? 'lock' : 'star')" :size="state === 'locked' ? 26 : 30" />
      </button>
      <span v-if="state === 'locked' && icon" class="jb-node__lock" aria-hidden="true"><Icon name="lock" :size="13" :stroke="2.8" /></span>
      <button v-if="forecastDirection === 'rising' || forecastDirection === 'falling'" type="button" class="jb-node__forecast" :data-direction="forecastDirection" :aria-label="`${name} demand forecast: ${forecastDirection}`" @click="clickForecast">
        <Icon :name="dirIcon[forecastDirection]" :size="13" :stroke="2.8" />
      </button>
      <span v-if="burstKey > 0" :key="burstKey" class="jb-burst" aria-hidden="true"><i v-for="(p, i) in particles" :key="i" :style="p" /></span>
    </div>
    <div class="jb-node__label" @click="click">
      <strong class="jb-node__name">{{ name }}</strong>
      <span v-if="kind" class="jb-node__kind">{{ kind }}</span>
    </div>
  </div>
</template>
