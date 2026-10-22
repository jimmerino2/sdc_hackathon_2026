<script setup lang="ts">
import { computed } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { useFlow } from '../state';

const { chosenRole, persona } = useFlow();
const gaps = computed(() => chosenRole.value.gap.map((g, i) => ({ name: g, need: 3 - (i % 2), now: 0 })));
</script>

<template>
  <FlowShell :progress="5" next="pathway" next-label="Build my pathway" skip-label="Back to roles" skip-to="roles">
    <p class="eyebrow">Your skill gap</p>
    <h1>Here’s how close you are to {{ chosenRole.title }}</h1>
    <Bubble class="b" :size="60">You already have {{ chosenRole.haveCount }} of {{ chosenRole.total }} skills. Let’s close the rest, {{ persona.name.split(',')[0] }}.</Bubble>

    <div class="card block">
      <div class="head"><h2>Already yours</h2><span class="pill pill-dark">{{ chosenRole.have.length }} skills</span></div>
      <div class="chips"><span v-for="s in chosenRole.have" :key="s" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ s }}</span></div>
    </div>

    <div class="card block">
      <div class="head"><h2>Close your gap</h2><span class="pill">{{ gaps.length }} to build</span></div>
      <div v-for="g in gaps" :key="g.name" class="gap">
        <span class="chip chip-gap"><Icon name="sparkles" :size="14" /> {{ g.name }}</span>
        <div class="bar"><div class="progress"><i :style="{ width: (g.now / g.need) * 100 + '%' }" /></div><small>Level 0 → {{ g.need }}</small></div>
      </div>
      <p class="est">About {{ persona.weeksToGo }} weeks at {{ persona.minutesPerDay }} min a day.</p>
    </div>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin: 6px 0 22px; line-height: 1.15; }
.b { margin-bottom: 22px; }
.block { padding: 20px 22px; margin-bottom: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
h2 { font-weight: 900; font-size: 17px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.gap { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px 0; border-top: 2px solid var(--line); }
.gap:first-of-type { border-top: 0; }
.bar { width: 45%; display: flex; flex-direction: column; gap: 4px; } .bar small { font-size: 11px; font-weight: 700; color: var(--muted); }
.est { margin-top: 10px; font-size: 13px; font-weight: 700; color: var(--muted); }
</style>
