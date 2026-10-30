<script setup lang="ts">
import { computed } from 'vue';
import InfoDialog from './InfoDialog.vue';
import type { JobMatch, ScenarioOutlook } from '../api/jobs';
import { COMPONENT_LABELS, SCORE_TOOLTIP, formulaLine, partCaption } from '../data/matchExplain';

/** Why a role scored what it did under one AI future: a bar per part. The sums stay in the dialog. */
const props = defineProps<{ job: JobMatch; scenario: ScenarioOutlook['scenario']; stage?: string | null }>();

const outlook = computed(() => props.job.outlook.find((o) => o.scenario === props.scenario));
const breakdown = computed(() => outlook.value?.breakdown ?? null);
</script>

<template>
  <div class="mb">
    <p v-if="!breakdown" class="muted">Regenerate your roles to see why this role scored what it did.</p>
    <template v-else>
      <ul class="parts">
        <li v-for="c in breakdown.components" :key="c.key">
          <b>{{ COMPONENT_LABELS[c.key] }}</b>
          <span class="bar" role="img" :aria-label="`${COMPONENT_LABELS[c.key]}: ${Math.round(c.score * 100)} out of 100`"><i :style="{ width: `${c.score * 100}%` }" /></span>
          <small>{{ partCaption(c.key, job, outlook, stage) }}</small>
        </li>
      </ul>

      <InfoDialog title="How your match is calculated" label="How it’s calculated">
        <p>{{ SCORE_TOOLTIP }}</p>
        <table class="sums">
          <thead><tr><th>Part</th><th>Your score</th><th>Weight</th><th>Points</th></tr></thead>
          <tbody>
            <tr v-for="c in breakdown.components" :key="c.key">
              <td>{{ COMPONENT_LABELS[c.key] }}</td><td>{{ Math.round(c.score * 100) }}/100</td><td>{{ (c.share * 100).toFixed(1) }}%</td><td>+{{ (c.points * 100).toFixed(1) }}</td>
            </tr>
          </tbody>
        </table>
        <p>{{ formulaLine(breakdown) }}</p>
        <p class="muted">Interests come from Jobee’s mapping of roles and interests to the UN goals. Job ads are a forecast of US data, and career stage is the same for every role. This score hasn’t been validated as a measure of career suitability.</p>
      </InfoDialog>
    </template>
  </div>
</template>

<style scoped>
.mb { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; text-align: left; }
.parts { list-style: none; width: 100%; display: flex; flex-direction: column; gap: 9px; }
.parts li { display: grid; grid-template-columns: 96px minmax(50px, 1fr) minmax(0, 190px); align-items: center; gap: 10px; font-size: 13px; }
.parts b { font-weight: 800; }
.parts small { font-size: 12.5px; font-weight: 700; color: var(--muted); }
.bar { height: 9px; border-radius: 999px; background: var(--line); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: 999px; background: var(--orange); }
.muted { font-size: 12px; font-weight: 600; line-height: 1.45; color: var(--muted); }
.sums { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; font-variant-numeric: tabular-nums; }
.sums th, .sums td { padding: 6px 8px; text-align: right; border-bottom: 1px solid var(--line); }
.sums th:first-child, .sums td:first-child { text-align: left; }
.sums th { font-size: 11px; color: var(--muted); font-weight: 800; }
@media (max-width: 560px) {
  .parts li { grid-template-columns: 1fr auto; gap: 4px 10px; }
  .bar { grid-column: 1 / -1; grid-row: 2; }
}
</style>
