<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import InfoDialog from './InfoDialog.vue';
import { fetchMethodology, type Methodology } from '../api/methodology';
import { day } from '../occupational/format';
import { useScenarioProbabilities } from '../composables/useScenarioProbabilities';

/** The "What the three AI futures mean" popup: the futures in plain words, and the source and date behind each measure the chances come from. */
const { metrics, metricTarget } = useScenarioProbabilities();
const methodology = ref<Methodology | null>(null);
const assumptions = computed(() => methodology.value?.scenarios ?? null);
onMounted(() => fetchMethodology().then((m) => { methodology.value = m; }).catch(() => {}));
/** What each future means for a role, in plain words (keyed by the backend's scenario name). */
const futureText: Record<string, string> = {
  'Rapid AI': 'AI spreads quickly. Roles where AI can do much of the work see slower job growth; the rest see more.',
  Baseline: 'AI keeps moving at about its recent pace. No extra push either way.',
  Slow: 'AI spreads slowly. Roles where AI can do much of the work hold up better.',
};
</script>

<template>
  <InfoDialog v-if="assumptions" title="What the three AI futures mean">
    <p>Nobody knows how fast AI will move, so we show three possible futures. They are what-ifs to plan around, not predictions.</p>
    <ul>
      <li v-for="f in assumptions.futures" :key="f.scenario"><b>{{ f.tab }}</b>: {{ futureText[f.scenario] }}</li>
    </ul>
    <h3>Where the chances come from</h3>
    <ul class="src-list">
      <li v-for="m in metrics" :key="m.target" class="src-item" :class="{ now: m.target === metricTarget }">
        <b>{{ m.label }}</b><span v-if="m.target === metricTarget" class="tag-now">in use</span>
        <span class="src-about">{{ m.about }}</span>
        <template v-if="methodology?.forecasts[m.target]">
          <span>Source: <a :href="methodology.forecasts[m.target]!.provenance.url ?? undefined" target="_blank" rel="noopener">{{ methodology.forecasts[m.target]!.provenance.source }}</a></span>
          <span>Data as of <b>{{ day(methodology.forecasts[m.target]!.provenance.last_updated) }}</b> · forecast made {{ day(methodology.forecasts[m.target]!.configuration.issued) }} · {{ methodology.forecasts[m.target]!.provenance.geography }}</span>
        </template>
        <span v-else class="muted">Source details are not available right now.</span>
      </li>
    </ul>
  </InfoDialog>
</template>

<style scoped>
.src-list { list-style: none; margin: 0 0 12px; padding: 0; display: grid; gap: 10px; }
.src-item { display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; border: 2px solid var(--line); border-radius: 14px; font-size: 15px; font-weight: 600; line-height: 1.45; }
.src-item.now { border-color: var(--yellow); background: var(--cream); }
.src-item b { font-weight: 900; }
.src-about { color: var(--muted); }
.src-item a { color: var(--ink); text-decoration: underline; }
.tag-now { align-self: flex-start; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--amber-ink); }
</style>
