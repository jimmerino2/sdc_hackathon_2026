<script setup lang="ts">
import { go } from '../../router';

/** Switches between the challenge list and the Protect the Hive page. */
defineProps<{ current: 'challenges' | 'hive' }>();
</script>

<template>
  <nav class="hswitch" aria-label="Challenges">
    <RouterLink :to="go('challenges')" class="hswitch__opt" :class="{ on: current === 'challenges' }" :aria-current="current === 'challenges' ? 'page' : undefined">Challenges</RouterLink>
    <RouterLink :to="go('hive')" class="hswitch__opt" :class="{ on: current === 'hive' }" :aria-current="current === 'hive' ? 'page' : undefined">Protect the Hive!</RouterLink>
  </nav>
</template>

<style scoped>
.hswitch { display: inline-flex; flex: none; padding: 5px; border-radius: var(--radius-pill); background: #f1ece0; }
.hswitch__opt { padding: 9px 20px; border-radius: var(--radius-pill); color: var(--text-muted); font-size: 14px; font-weight: 800; text-decoration: none; transition: background var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out); }
.hswitch__opt:hover { color: var(--text); }
.hswitch__opt.on { background: var(--honey); color: var(--on-honey); box-shadow: 0 3px 0 var(--honey-deep); }
.hswitch__opt:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
</style>
