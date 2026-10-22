<script setup lang="ts">
import Mascot from './Mascot.vue';
import { go, type Step } from '../router';

withDefaults(defineProps<{ to?: Step }>(), { to: 'landing' });
</script>

<template>
  <RouterLink :to="go(to)" class="logo">
    <Mascot :size="30" />
    <span>jobee</span>
  </RouterLink>
</template>

<style scoped>
.logo { display: inline-flex; align-items: center; gap: 8px; font-weight: 900; font-size: 28px; letter-spacing: -.02em; }
</style>
