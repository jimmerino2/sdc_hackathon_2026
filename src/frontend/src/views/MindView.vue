<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { mindOptions } from '../data/flows';
import { useFlow } from '../state';

const { persona, state } = useFlow();
function toggle(i: number) {
  const idx = state.value.mind.indexOf(i);
  if (idx >= 0) state.value.mind.splice(idx, 1);
  else state.value.mind.push(i);
}
</script>

<template>
  <FlowShell :progress="2" next="skills">
    <h1>What’s been on your mind lately?</h1>
    <Bubble class="b">{{ persona.mindBubble }}</Bubble>
    <div class="grid">
      <button v-for="(o, i) in mindOptions" :key="o.title" class="option" :class="{ selected: state.mind.includes(i) }" @click="toggle(i)">
        <span class="ic"><Icon :name="o.icon" :size="22" /></span>
        <span><h3>{{ o.title }}</h3><p>{{ o.sub }}</p></span>
        <span v-if="state.mind.includes(i)" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
    <p class="hint">Pick as many as you like.</p>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.hint { margin-top: 24px; font-size: 12px; font-weight: 700; color: var(--muted); }
@media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
</style>
