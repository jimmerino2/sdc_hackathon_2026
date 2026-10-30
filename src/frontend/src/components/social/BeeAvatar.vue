<script setup lang="ts">
import Mascot from '../Mascot.vue';
import type { BeeName } from '../../bee';

/** A person's picture: their companion bee, animated, in a honey ring. */
withDefaults(defineProps<{ bee: string; size?: number; me?: boolean }>(), { size: 44, me: false });
</script>

<template>
  <span class="avatar" :class="{ me }" :style="{ width: size + 'px', height: size + 'px' }">
    <Mascot :size="size * 0.62" :bee="bee as BeeName" :look="false" />
  </span>
</template>

<style scoped>
.avatar { flex: none; display: grid; place-items: center; border: 2px solid var(--honey); border-radius: 50%; background: var(--surface-raised); }
.avatar.me { background: var(--honey-tint); }
</style>
