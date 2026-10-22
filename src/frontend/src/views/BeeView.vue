<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import { bee, BEES, beeInfo, type BeeName } from '../bee';

function pick(b: BeeName) { bee.value = b; }
</script>

<template>
  <FlowShell :progress="0" next="name" back="landing" mood="wave">
    <template #bubble>Who should guide your career journey?</template>
    <div class="grid" role="group" aria-label="Choose your guide">
      <button v-for="b in BEES" :key="b" type="button" class="option bee" :class="{ selected: bee === b }" :aria-pressed="bee === b" @click="pick(b)">
        <Mascot :size="76" :bee="b" :mood="bee === b ? 'happy' : 'idle'" :look="false" class="m" />
        <h3>{{ b }}</h3>
        <span v-if="bee === b" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
  </FlowShell>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.bee { flex-direction: column; align-items: center; text-align: center; padding: 20px 12px 16px; gap: 2px; }
.bee .m { margin: 10px 0 14px; }
.bee p { font-size: 13px; }
.bee .tick { position: absolute; top: 12px; right: 12px; margin: 0; }
@media (max-width: 640px) { .grid { gap: 10px; } .bee { padding: 14px 8px 12px; } .bee .m { margin: 8px 0 10px; } }
</style>
