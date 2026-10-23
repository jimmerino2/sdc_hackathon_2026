<script setup lang="ts">
import { computed } from 'vue';
import Icon from '../Icon.vue';
import { useCountUp } from '../../composables/useCountUp';

const props = defineProps<{ skills: string[]; owned?: number; total?: number; more?: number; eyebrow?: string }>();
const n = useCountUp(computed(() => props.owned ?? props.skills.length), 900);
</script>

<template>
  <section class="jb jb-owned">
    <span class="jb-owned__spark jb-owned__spark--a"><Icon name="sparkles" :size="22" /></span>
    <span class="jb-owned__spark jb-owned__spark--b"><Icon name="sparkles" :size="14" /></span>
    <p class="jb-eyebrow">{{ eyebrow ?? 'Already yours' }}</p>
    <h2 v-if="total" class="jb-owned__title">You already have <span class="jb-owned__n">{{ n }}</span> of {{ total }} key skills</h2>
    <h2 v-else class="jb-owned__title">Skills you already bring</h2>
    <ul class="jb-owned__chips">
      <li v-for="(s, i) in skills" :key="s" class="jb-chip" :style="{ '--i': i }">{{ s }}</li>
      <li v-if="more" class="jb-chip jb-chip--more" :style="{ '--i': skills.length }">+{{ more }}</li>
    </ul>
  </section>
</template>
