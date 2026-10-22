<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { whoOptions } from '../data/flows';
import { useFlow } from '../state';

const { persona, state } = useFlow();
</script>

<template>
  <FlowShell :progress="1" next="mind" back="name">
    <h1>Which one sounds like you?</h1>
    <Bubble class="b" gear="magnifier">{{ persona.mascotWelcome }}</Bubble>
    <div class="list">
      <button v-for="(o, i) in whoOptions" :key="o.title" class="option" :class="{ selected: state.who === i }" @click="state.who = i">
        <span class="ic"><Icon :name="o.icon" :size="22" /></span>
        <span><h3>{{ o.title }}</h3><p>{{ o.sub }}</p></span>
        <span v-if="state.who === i" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.list { display: flex; flex-direction: column; gap: 14px; }
</style>
