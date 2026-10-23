<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { whoOptions } from '../data/flows';
import { useFlow } from '../state';

const { state } = useFlow();
</script>

<template>
  <FlowShell :progress="1" next="interests" back="name" gear="magnifier">
    <template #bubble>Where are you in your tech journey?</template>
    <div class="list" role="radiogroup" aria-label="Where you are right now">
      <button
        v-for="(o, i) in whoOptions"
        :key="o.title"
        type="button"
        role="radio"
        class="option"
        :class="{ selected: state.who === i }"
        :aria-checked="state.who === i"
        @click="state.who = i"
      >
        <span><h3>{{ o.title }}</h3></span>
        <span v-if="state.who === i" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
      </button>
    </div>
  </FlowShell>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 14px; }
.option { min-height: 72px; }
</style>
