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
        <div class="lv" role="radiogroup" :aria-labelledby="`skill-${si}`">
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
.name { font-weight: 800; font-size: 15px; }
.lv { display: flex; gap: 6px; }
.lv button {
  min-width: 60px; padding: 9px 8px; border-radius: 12px; border: 2px solid var(--line-strong); background: #fff;
  font-weight: 800; font-size: 12px; color: var(--muted); transition: background .12s, border-color .12s, transform .08s;
}
.lv button:hover { border-color: var(--yellow); color: var(--ink); }
.lv button:active { transform: translateY(2px); }
.lv button.on { background: var(--yellow); border-color: var(--yellow); box-shadow: 0 3px 0 var(--orange); color: var(--ink); font-weight: 900; }
@media (max-width: 480px) { .lv { width: 100%; } .lv button { flex: 1; min-width: 0; } }
</style>
