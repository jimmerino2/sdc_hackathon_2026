<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchForecastSources, type DataSource } from '../api/forecast';
import { day, month } from '../occupational/format';

/** "Source: Indeed Job Postings Index (Indeed Hiring Lab) · data as of 9 Oct 2026". Names and dates come from the API, so a data refresh updates them. */
const sources = ref<DataSource[]>([]);
onMounted(async () => {
  try {
    sources.value = await fetchForecastSources();
  } catch {
    // Not fatal: the page works without the stamp.
  }
});

const shown = computed(() => sources.value.filter((s) => s.id === 'indeed_postings'));
</script>

<template>
  <p v-if="shown.length" class="stamp">
    <span v-for="s in shown" :key="s.id" class="src">
      Source: <a :href="s.url" target="_blank" rel="noopener">{{ s.name }}</a>, {{ s.publisher }}
      · data as of <b>{{ day(s.as_of) }}</b><template v-if="s.latest_month"> · latest month {{ month(s.latest_month) }}</template>
      <template v-if="s.is_proxy_for_malaysia"> · US data stands in for Malaysia</template>
    </span>
  </p>
</template>

<style scoped>
.stamp { margin: 8px 0 0; font-size: 12px; font-weight: 700; line-height: 1.5; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }
.stamp b { color: var(--ink); font-weight: 900; }
.stamp a { color: inherit; text-decoration: underline; }
</style>
