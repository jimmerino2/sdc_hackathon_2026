<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import { bee, BEES, beeInfo, type BeeName } from '../bee';

function pick(b: BeeName) { bee.value = b; }
</script>

<template>
  <FlowShell :progress="0" next="who" back="landing">
    <h1>Pick your bee</h1>
    <Bubble class="b" mood="wave">Hi! I’ll be your companion from here on. Which bee should it be?</Bubble>
    <div class="grid">
      <button v-for="b in BEES" :key="b" type="button" class="option bee" :class="{ selected: bee === b }" @click="pick(b)">
        <Mascot :size="84" :bee="b" :mood="bee === b ? 'happy' : 'idle'" :look="false" class="m" />
        <h3>{{ b }}</h3>
        <p>{{ beeInfo[b].tagline }}</p>
        <small>{{ beeInfo[b].vibe }}</small>
        <span v-if="bee === b" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.bee { flex-direction: column; align-items: center; text-align: center; padding: 22px 14px 18px; gap: 4px; }
.bee .m { margin: 8px 0 14px; }
.bee small { font-size: 12px; color: var(--muted); font-weight: 600; line-height: 1.35; margin-top: 4px; }
.bee .tick { position: absolute; top: 12px; right: 12px; margin: 0; }
</style>
