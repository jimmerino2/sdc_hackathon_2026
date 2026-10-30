<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchForecastSources, type DataSource } from '../api/forecast';
import { day, month } from '../occupational/format';

/** "Source: Indeed Job Postings Index (Indeed Hiring Lab) · data as of 9 Oct 2026". Names and dates come from the API, so a data refresh updates them. */
const props = defineProps<{
  /** Which sources to show, by id. Defaults to the role-trend source alone. */
  ids?: string[];
  /** A "Source Data" section with one small card per source, instead of a single line of text. */
  cards?: boolean;
}>();

const sources = ref<DataSource[]>([]);
onMounted(async () => {
  try {
    sources.value = await fetchForecastSources();
  } catch {
    // Not fatal: the page works without the stamp.
  }
});

const shown = computed(() => sources.value.filter((s) => (props.ids ?? ['indeed_postings']).includes(s.id)));
</script>

<template>
  <section v-if="cards && shown.length" class="src-section" aria-labelledby="src-title">
    <h2 id="src-title" class="src-title">Source Data</h2>
    <ul class="src-cards">
      <li v-for="s in shown" :key="s.id" class="card src-card">
        <a class="src-name" :href="s.url" target="_blank" rel="noopener">{{ s.name }}</a>
        <p class="src-by">{{ s.publisher }} · {{ s.license }}</p>
        <p class="src-use">{{ s.used_for }}</p>
        <p class="src-date">Data as of <b>{{ day(s.as_of) }}</b><template v-if="s.latest_month"> · latest month {{ month(s.latest_month) }}</template></p>
        <p v-if="s.is_proxy_for_malaysia" class="src-by">US data stands in for Malaysia</p>
      </li>
    </ul>
  </section>
  <p v-else-if="shown.length" class="stamp">
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
.src-title { font-size: 20px; font-weight: 900; margin: 4px 0 14px; line-height: 1.2; }
.src-cards { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.src-card { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.src-card p { margin: 0; font-size: 13px; font-weight: 700; color: var(--muted); line-height: 1.4; }
.src-name { font-size: 16px; font-weight: 900; color: var(--ink); text-decoration: underline; }
.src-use { color: var(--ink) !important; }
.src-date b { color: var(--ink); font-weight: 900; }
</style>
