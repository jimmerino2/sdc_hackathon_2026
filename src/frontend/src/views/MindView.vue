<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { mindOptions } from '../data/flows';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { state, key } = useFlow();
function toggle(i: number) {
  const idx = state.value.mind.indexOf(i);
  if (idx >= 0) state.value.mind.splice(idx, 1);
  else state.value.mind.push(i);
}
</script>

<template>
  <FlowShell :progress="2" next="outcome" back="who" mood="thinking" :next-disabled="!state.mind.length">
    <template #bubble>{{ personaCopy[key].mind }}</template>
    <p id="mind-hint" class="hint">Pick any that fit</p>
    <div class="grid" role="group" aria-describedby="mind-hint">
      <button
        v-for="(o, i) in mindOptions"
        :key="o.title"
        type="button"
        class="option"
        :class="{ selected: state.mind.includes(i) }"
        :aria-pressed="state.mind.includes(i)"
        @click="toggle(i)"
      >
        <h3>{{ o.title }}</h3>
        <span v-if="state.mind.includes(i)" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
  </FlowShell>
</template>

<style scoped>
.hint { font-size: 13px; font-weight: 800; color: var(--muted); margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.option { min-height: 76px; }
.option h3 { font-size: 16px; }
@media (max-width: 560px) { .grid { grid-template-columns: 1fr; } .option { min-height: 60px; } }
</style>
