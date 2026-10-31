<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import { levels } from '../data/flows';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { state, key, checkSkills, levelOf } = useFlow();
</script>

<template>
  <FlowShell :progress="4" next="loading" next-label="Analyze my profile" back="resume" gear="glasses">
    <template #bubble>{{ personaCopy[key].skills }}</template>
    <div class="rows">
      <div v-for="(s, si) in checkSkills" :key="s" class="row">
        <span :id="`skill-${si}`" class="name">{{ skillLabel(s) }}</span>
        <div class="btn-group lv" role="radiogroup" :aria-labelledby="`skill-${si}`">
          <button
            v-for="(l, li) in levels"
            :key="l"
            type="button"
            role="radio"
            :aria-checked="levelOf(s) === li"
            :class="{ on: levelOf(s) === li }"
            @click="state.levels[s] = li"
          >{{ l }}</button>
        </div>
      </div>
    </div>
  </FlowShell>
</template>

<style scoped>
.rows { display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 10px 12px; background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 10px 12px 10px 16px; flex-wrap: wrap; }
.name { font-weight: 800; font-size: 16px; }
@media (max-width: 480px) { .lv { display: flex; width: 100%; } .lv button { flex: 1; } }
</style>
