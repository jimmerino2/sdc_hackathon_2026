<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import InfoDialog from './InfoDialog.vue';
import { fetchQuarters } from '../api/forecast';
import { fetchMethodology, type Methodology } from '../api/methodology';
import { day } from '../occupational/format';
import { SCENARIO_METRICS } from '../data/outlookScenarios';

/** The ? beside "Last updated": how often each kind of data behind the roles changes, and how recent Jobee's copy is. */
const props = defineProps<{ updated: string | null }>();

const methodology = ref<Methodology | null>(null);
/** Whether this server lets Sync pull new data; otherwise it only scores the roles again. */
const pulls = ref(false);
onMounted(() => {
  fetchMethodology().then((m) => { methodology.value = m; }).catch(() => {});
  fetchQuarters().then((q) => { pulls.value = q.refresh_enabled; }).catch(() => {});
});

const forecast = (id: string) => methodology.value?.forecasts[id] ?? null;
const rows = computed(() => [
  { name: 'Your role matches', how: 'When you press Sync', latest: props.updated },
  { name: 'Job demand', how: forecast('role_postings')?.configuration.frequency ?? 'Monthly', latest: day(forecast('role_postings')?.provenance.last_updated) },
  ...SCENARIO_METRICS.map((m) => ({ name: m.label, how: forecast(m.target)?.configuration.frequency ?? '–', latest: day(forecast(m.target)?.provenance.last_updated) })),
  { name: 'Skills for each role', how: 'Each new O*NET release', latest: null },
  { name: 'How much AI touches each job', how: 'Each new Anthropic Economic Index release', latest: null },
]);
</script>

<template>
  <InfoDialog title="How often this data updates">
    <p v-if="pulls">Sync pulls the newest Indeed data, retrains the job demand forecasts and scores your roles again. Worker adoption and business adoption are forecast again if their data changed. The other rows are refreshed separately.</p>
    <p v-else>Sync scores your roles again with the latest data Jobee holds.</p>
    <table>
      <thead><tr><th>Data</th><th>Updates</th><th>Latest</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.name"><td>{{ r.name }}</td><td>{{ r.how }}</td><td>{{ r.latest ?? '–' }}</td></tr>
      </tbody>
    </table>
    <p class="muted">“Updates” is how often the data changes at its source. Jobee’s copy changes when the team refreshes it, so it can trail the source for a while.</p>
  </InfoDialog>
</template>

<style scoped>
td:last-child { white-space: nowrap; }
</style>
