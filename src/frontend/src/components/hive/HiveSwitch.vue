<script setup lang="ts">
import { go } from '../../router';

/** Switches between the challenge list and the Protect the Hive page. */
defineProps<{ current: 'challenges' | 'hive' }>();
</script>

<template>
  <nav class="btn-group" aria-label="Challenges">
    <RouterLink :to="go('challenges')" :class="{ on: current === 'challenges' }" :aria-current="current === 'challenges' ? 'page' : undefined">Challenges</RouterLink>
    <RouterLink :to="go('hive')" :class="{ on: current === 'hive' }" :aria-current="current === 'hive' ? 'page' : undefined">Protect the Hive!</RouterLink>
  </nav>
</template>

