<script setup lang="ts">
import { onMounted, ref } from 'vue';
import Icon from './Icon.vue';
import { fetchBenchSummary, type Benchmark, type BenchSummary } from '../api/llmBench';

/** "We also tried LLMs": the LLM forecast benchmark's completed runs next to the served model, on the same past
 *  cases. Shown beside the forecasts it was compared with; hidden when no live run has completed. */
const props = defineProps<{ benchmark: Benchmark }>();

const s = ref<BenchSummary | null>(null);
onMounted(async () => {
  try {
    const r = await fetchBenchSummary(props.benchmark);
    s.value = r.rows.length ? r : null;
  } catch {
    s.value = null;
  }
});

const MODE: Record<string, string> = { zero: 'no examples', few: 'with past examples' };
const f = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2));
const times = (a: number | null, b: number | null | undefined) => (a == null || !b ? '–' : `${(a / b).toFixed(1)}×`);
const short = (m: string) => m.split('/').pop();
</script>

<template>
  <div v-if="s" class="card pad tried">
    <h2><Icon name="brain" :size="18" /> We also tried LLMs</h2>
    <p class="small">
      We asked LLMs for the same past forecasts this model was tested on, with names hidden so they couldn’t recall what
      happened, and scored both against the actual outcomes.
      <b v-if="!s.any_better">None of the {{ s.rows.length }} LLM setups beat the model shown here</b>
      <b v-else>Some LLM setups had lower error, which may be noise</b>
      <template v-if="benchmark === 'capability'">: they mostly forecast no further growth, while the record kept doubling.</template>
      <template v-else>: they mostly repeated the latest share.</template>
    </p>
    <div class="scroll">
      <table class="tbl">
        <thead><tr><th>Setup</th><th>Cases</th><th>Average error ({{ s.units }})</th><th>vs this model</th></tr></thead>
        <tbody>
          <tr class="shown"><td>This model (shown forecast)</td><td>{{ s.rows[0].n_cases }}</td><td>{{ f(s.full_sample.existing) }}</td><td>1.0×</td></tr>
          <tr><td>“No change”</td><td>{{ s.rows[0].n_cases }}</td><td>{{ f(s.full_sample.naive) }}</td><td>{{ times(s.full_sample.naive ?? null, s.full_sample.existing) }}</td></tr>
          <tr v-for="r in s.rows" :key="r.run_id + r.mode">
            <td>{{ short(r.model) }} · {{ r.reasoning === 'off' ? 'no thinking' : 'thinking' }} · {{ MODE[r.mode] ?? r.mode }}</td>
            <td>{{ r.n_valid }}</td><td>{{ f(r.llm) }}</td><td>{{ times(r.llm, r.existing) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="muted small">
      {{ benchmark === 'capability' ? 'Errors in doublings: 1 means off by a factor of 2.' : 'Errors in percentage points of share, 3 months ahead.' }}
      Total LLM cost ${{ s.total_cost_usd.toFixed(2) }}.
    </p>
  </div>
</template>

<style scoped>
.pad { padding: 20px 24px; }
.tried h2 { font-size: 20px; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.small { font-size: 14px; line-height: 1.5; }
.muted { color: var(--muted); }
.scroll { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 14px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl th:first-child, .tbl td:first-child { text-align: left; white-space: normal; }
.tbl th { font-size: 13px; font-weight: 800; color: var(--muted); }
.tbl tr.shown td { font-weight: 800; }
@media (max-width: 860px) { .pad { padding: 16px; } }
</style>
