<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import { levels } from '../data/flows';
import { useFlow } from '../state';

const { persona, state } = useFlow();
</script>

<template>
  <FlowShell :progress="3" next="resume">
    <h1>How comfortable are you with these?</h1>
    <Bubble class="b" :size="60">Be honest! I only use this to find your starting point.</Bubble>
    <div class="rows">
      <div v-for="(s, i) in persona.skills" :key="s.name" class="row">
        <span class="name">{{ s.name }}</span>
        <div class="lv">
          <button v-for="(l, li) in levels" :key="l" :class="{ on: state.levels[i] === li }" @click="state.levels[i] = li">{{ l }}</button>
        </div>
      </div>
    </div>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.rows { display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 10px 16px; flex-wrap: wrap; }
.name { font-weight: 800; font-size: 15px; }
.lv { display: flex; gap: 6px; }
.lv button { min-width: 60px; padding: 9px 8px; border-radius: 12px; border: 2px solid var(--line-strong); background: #fff; font-weight: 700; font-size: 11px; color: var(--muted); }
.lv button.on { background: var(--yellow); border-color: var(--yellow); box-shadow: 0 3px 0 var(--orange); color: var(--ink); font-weight: 900; }
</style>
