<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import BeePicker from '../components/BeePicker.vue';
import { bee } from '../bee';
</script>

<template>
  <FlowShell :progress="0" next="name" back="landing">
    <h1>Pick your bee</h1>
    <Bubble class="b" mood="wave">Hi! I’ll be your companion from here on. Which bee should it be?</Bubble>
    <BeePicker @pick="bee = $event" />
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
</style>
