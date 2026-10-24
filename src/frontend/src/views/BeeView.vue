<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import BeePicker from '../components/BeePicker.vue';
import { bee } from '../bee';
</script>

<template>
  <FlowShell :progress="0" next="name" back="landing" mood="wave">
    <template #bubble>Who should guide your career journey?</template>
    <BeePicker plain flowers @pick="bee = $event" />
  </FlowShell>
</template>
