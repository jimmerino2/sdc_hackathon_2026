<script setup lang="ts">
import { computed, watch } from 'vue';
import { useCountUp } from '../../composables/useCountUp';
import { useFlash } from '../../composables/useFlash';

const props = defineProps<{ done: number; total: number; role: string; unit?: string }>();
const n = useCountUp(computed(() => props.done), 700);
const pct = computed(() => (props.total ? Math.round((props.done / props.total) * 100) : 0));
const { on: bump, trigger } = useFlash(620);
watch(() => props.done, trigger); // bump the bar whenever progress changes
</script>

<template>
  <section class="jb jb-card">
    <p class="jb-eyebrow">Target role</p>
    <h3 class="jb-card__title">{{ role }}</h3>
    <div class="jb-bar" role="progressbar" aria-label="Roadmap progress" :aria-valuemin="0" :aria-valuemax="total" :aria-valuenow="done">
      <div class="jb-bar__fill" :data-bump="bump ? 'true' : 'false'" :style="{ width: Math.max(pct, 3) + '%' }"><i class="jb-bar__shine" /></div>
    </div>
    <p class="jb-card__meta">{{ n }} of {{ total }} {{ unit ?? 'roadmap skills' }} done</p>
  </section>
</template>
