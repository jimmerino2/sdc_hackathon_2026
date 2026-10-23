<script setup lang="ts">
import Icon from '../Icon.vue';
import type { RouteLocationRaw } from 'vue-router';

withDefaults(defineProps<{ variant?: 'primary' | 'ink' | 'quiet'; icon?: string; to?: RouteLocationRaw; disabled?: boolean }>(), { variant: 'primary' });
</script>

<template>
  <RouterLink v-if="to" :to="to" class="jb jb-btn" :class="`jb-btn--${variant}`">
    <slot /><Icon v-if="icon" :name="icon" :size="18" />
  </RouterLink>
  <button v-else type="button" class="jb jb-btn" :class="`jb-btn--${variant}`" :disabled="disabled">
    <slot /><Icon v-if="icon" :name="icon" :size="18" />
  </button>
</template>
