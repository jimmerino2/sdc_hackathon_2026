<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import Icon from './Icon.vue';
import { fetchMethodology, type Methodology } from '../api/methodology';

/** The expandable "How this forecast works" panel. Everything shown comes from GET /methodology; a missing value says so. */
const props = defineProps<{ id: string }>();

const data = ref<Methodology | null>(null);
const failed = ref(false);
onMounted(async () => {
  try {
    data.value = await fetchMethodology();
  } catch {
    failed.value = true;
  }
});

const f = computed(() => data.value?.forecasts[props.id] ?? null);
const na = 'Not available';
const period = (h: number) => `${h} ${f.value?.configuration.horizon_unit}${h === 1 ? '' : 's'}`;
const num = (v: number | null | undefined) => (v == null ? na : v.toFixed(2));
const share = (v: number | null | undefined) => (v == null ? na : `${Math.round(v * 100)}%`);
const verdict = (v: boolean | null) => (v == null ? 'Baseline shown' : v ? 'Yes' : 'No');
const anyBaseline = computed(() => f.value?.configuration.horizons.some((h) => h.is_baseline) ?? false);
</script>

<template>
  <details class="fi">
    <summary><Icon name="search" :size="14" /> How this forecast works <Icon name="chevron" :size="14" class="chev" /></summary>
    <p v-if="failed" class="muted">The forecast information couldn’t be loaded just now.</p>
    <p v-else-if="!data" class="muted">Loading…</p>
    <p v-else-if="!f" class="muted">{{ na }}.</p>
    <div v-else class="body">
      <p v-for="h in f.configuration.horizons.filter((x) => x.is_baseline && x.status_text).slice(0, 1)" :key="h.h" class="base">
        <Icon name="scale" :size="14" /> {{ h.status_text }} This isn’t a failure: Jobee shows whichever method the evidence supports.
      </p>

      <section>
        <h4>Where the data comes from</h4>
        <dl>
          <dt>Source</dt><dd><a v-if="f.provenance.url" :href="f.provenance.url" target="_blank" rel="noopener">{{ f.provenance.source }}</a><template v-else>{{ f.provenance.source }}</template></dd>
          <dt>Geography</dt><dd>{{ f.provenance.geography }}</dd>
          <dt>Sample</dt><dd>{{ f.provenance.population }}</dd>
          <dt>Period</dt><dd>{{ f.provenance.period ?? na }}</dd>
          <dt>Last updated</dt><dd>{{ f.provenance.last_updated ?? na }}</dd>
          <template v-if="f.provenance.license"><dt>Licence</dt><dd>{{ f.provenance.license }}</dd></template>
          <template v-for="a in f.provenance.also_uses" :key="a.source">
            <dt>Also uses</dt><dd><a :href="a.url" target="_blank" rel="noopener">{{ a.source }}</a> for {{ a.used_for }} ({{ a.license }}, updated {{ a.last_updated ?? na }})</dd>
          </template>
        </dl>
        <ul v-if="f.provenance.coverage.length"><li v-for="c in f.provenance.coverage" :key="c">{{ c }}</li></ul>
      </section>

      <section>
        <h4>What is measured</h4>
        <dl>
          <dt>Metric</dt><dd>{{ f.measure.metric }}</dd>
          <dt>Unit</dt><dd>{{ f.measure.unit }}</dd>
          <dt>Out of</dt><dd>{{ f.measure.denominator }}</dd>
          <dt>Type</dt><dd>{{ f.measure.value_type }}</dd>
        </dl>
      </section>

      <section>
        <h4>Forecast setup</h4>
        <dl>
          <dt>Frequency</dt><dd>{{ f.configuration.frequency }}</dd>
          <dt>Last observation</dt><dd>{{ f.configuration.last_observation ?? na }}</dd>
          <dt>Issued</dt><dd>{{ f.configuration.issued ?? na }}</dd>
          <dt>Chosen by</dt><dd>{{ f.configuration.selection_rule ?? na }}</dd>
        </dl>
      </section>

      <section>
        <h4>How it held up in testing</h4>
        <p class="muted">{{ f.reliability.method }}. Test period: {{ f.reliability.window ?? na }}. Forecast dates tested: {{ f.reliability.origins ?? na }}.</p>
        <div class="scroll">
          <table>
            <thead><tr><th>Ahead</th><th>Shown</th><th>Avg error</th><th>{{ f.reliability.horizons[0]?.baseline }}</th><th>Beat it?</th><th>Band held</th><th>Tests</th></tr></thead>
            <tbody>
              <tr v-for="(t, i) in f.reliability.horizons" :key="t.h">
                <td>{{ period(t.h) }}</td><td>{{ f.configuration.horizons[i]?.model }}</td><td>{{ num(t.model_error) }}</td><td>{{ num(t.baseline_error) }}</td>
                <td>{{ verdict(t.outperformed) }}</td><td>{{ share(t.coverage_80) }}</td><td>{{ t.n ?? t.origins ?? na }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted">Errors are in {{ f.reliability.error_unit }}. “Band held” is how often the actual value fell inside the band.<template v-if="anyBaseline && f.reliability.horizons[0]?.machine_learning_error != null"> LightGBM’s error at {{ period(f.reliability.horizons[0].h) }} was {{ num(f.reliability.horizons[0].machine_learning_error) }}.</template></p>
      </section>

      <section>
        <h4>{{ f.uncertainty.label }}</h4>
        <p class="muted">{{ f.uncertainty.how }}</p>
      </section>

      <section>
        <h4>Keep in mind</h4>
        <ul><li v-for="l in f.limitations" :key="l">{{ l }}</li></ul>
        <p class="muted geo">{{ data.geography.note }} {{ data.geography.malaysia }}</p>
      </section>
    </div>
  </details>
</template>

<style scoped>
.fi { background: #faf9f6; border-radius: 12px; padding: 10px 14px; font-size: 12.5px; min-width: 0; max-width: 100%; }
.body, section { min-width: 0; }
.fi summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 6px; font-weight: 800; color: var(--ink); }
.fi summary::-webkit-details-marker { display: none; }
.chev { margin-left: auto; color: var(--muted); transition: transform .15s; }
.fi[open] .chev { transform: rotate(180deg); }
.body { display: flex; flex-direction: column; gap: 14px; margin-top: 12px; }
h4 { font-size: 13px; font-weight: 900; margin-bottom: 4px; }
.base { display: flex; gap: 6px; align-items: flex-start; padding: 8px 10px; border-radius: 10px; background: var(--cream); font-weight: 700; line-height: 1.4; }
.base svg { flex: none; margin-top: 2px; }
dl { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 3px 10px; line-height: 1.4; }
dt { color: var(--muted); font-weight: 700; }
dd { font-weight: 700; min-width: 0; overflow-wrap: anywhere; }
dd a { text-decoration: underline; }
ul { margin: 4px 0 0 16px; display: flex; flex-direction: column; gap: 3px; line-height: 1.4; font-weight: 600; color: var(--muted); }
.muted { color: var(--muted); font-weight: 600; line-height: 1.45; }
.geo { margin-top: 8px; }
.scroll { overflow-x: auto; margin: 6px 0; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: 5px 7px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
th { font-size: 11px; color: var(--muted); font-weight: 800; }
@media (max-width: 520px) { dl { grid-template-columns: 1fr; } dd { margin-bottom: 4px; } }
</style>
