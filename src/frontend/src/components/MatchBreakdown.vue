<script setup lang="ts">
import { computed } from 'vue';
import InfoDialog from './InfoDialog.vue';
import type { JobMatch, ScenarioOutlook, ScoreComponent } from '../api/jobs';
import { COMPONENT_LABELS, SCORE_TOOLTIP, formulaLine, matchSlices, partCaption } from '../data/matchExplain';

/** How a role's match is made up under one AI future: a pie of the parts in a dialog, so the card stays short. */
const props = defineProps<{ job: JobMatch; scenario: ScenarioOutlook['scenario']; stage?: string | null }>();

/** Each part keeps its colour whichever parts a role has. */
const COLORS: Record<ScoreComponent['key'], string> = { skills: '#d97a00', outlook: '#2b6cb0', interests: '#0fa37f', education: '#8e4bb5' };
const R = 42;
const CIRCUMFERENCE = 2 * Math.PI * R;
const GAP = 1; // percent of the ring left bare between slices

const outlook = computed(() => props.job.outlook.find((o) => o.scenario === props.scenario));
const breakdown = computed(() => outlook.value?.breakdown ?? null);
const slices = computed(() => (breakdown.value ? matchSlices(breakdown.value).filter((s) => s.points > 0) : []));
const arcs = computed(() => {
  let at = 0;
  return slices.value.map((s) => {
    const start = at;
    at += s.points;
    return { ...s, dash: `${(Math.max(s.points - GAP, 0.5) / 100) * CIRCUMFERENCE} ${CIRCUMFERENCE}`, offset: (-start / 100) * CIRCUMFERENCE };
  });
});
const rest = computed(() => 100 - slices.value.reduce((a, s) => a + s.points, 0));
const pieLabel = computed(() => `${breakdown.value?.match_percent}% match: ${slices.value.map((s) => `${COMPONENT_LABELS[s.key]} ${s.points}`).join(', ')}`);
</script>

<template>
  <p v-if="!breakdown" class="muted">Regenerate your roles to see why this role scored what it did.</p>
  <InfoDialog v-else title="How your match percentage is calculated">
    <div class="pie">
      <svg viewBox="0 0 100 100" role="img" :aria-label="pieLabel">
        <circle cx="50" cy="50" :r="R" class="track" />
        <circle
          v-for="a in arcs"
          :key="a.key"
          cx="50"
          cy="50"
          :r="R"
          class="arc"
          :stroke="COLORS[a.key]"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
          transform="rotate(-90 50 50)"
        ><title>{{ COMPONENT_LABELS[a.key] }}: {{ a.points }} points</title></circle>
        <text x="50" y="49" text-anchor="middle" class="big">{{ breakdown.match_percent }}%</text>
        <text x="50" y="60" text-anchor="middle" class="small">match</text>
      </svg>
      <ul class="legend">
        <li v-for="s in slices" :key="s.key">
          <i :style="{ background: COLORS[s.key] }" />
          <span><b>{{ COMPONENT_LABELS[s.key] }}</b><small>{{ partCaption(s.key, job, outlook, stage) }}</small></span>
          <em>{{ s.points }}</em>
        </li>
        <li v-if="rest > 0">
          <i class="none" />
          <span><b>Not matched yet</b></span>
          <em>{{ rest }}</em>
        </li>
      </ul>
    </div>
    <p>{{ SCORE_TOOLTIP }}</p>
    <p class="muted">{{ formulaLine(breakdown) }} The slices show each part’s share of that final score.</p>
    <p class="muted">Interests come from Jobee’s mapping of roles and interests to the UN goals. Demand is a forecast of US data, and career stage is the same for every role. This score hasn’t been validated as a measure of career suitability.</p>
  </InfoDialog>
</template>

<style scoped>
.muted { font-size: 14px; font-weight: 600; line-height: 1.45; color: var(--muted); }
.pie { display: grid; grid-template-columns: 190px minmax(0, 1fr); align-items: center; gap: 24px; margin: 4px 0 8px; }
.track { fill: none; stroke: var(--line); stroke-width: 13; }
.arc { fill: none; stroke-width: 13; }
.big { font-size: 17px; font-weight: 900; fill: var(--ink); }
.small { font-size: 7px; font-weight: 800; fill: var(--muted); }
.legend { list-style: none; margin: 0 !important; display: flex; flex-direction: column; gap: 10px !important; }
.legend li { display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.legend i { width: 14px; height: 14px; border-radius: 4px; }
.legend i.none { background: var(--line); }
.legend span { display: flex; flex-direction: column; line-height: 1.25; }
.legend b { font-weight: 800; }
.legend small { font-size: 14px; font-weight: 600; color: var(--muted); }
.legend em { font-style: normal; font-size: 18px; font-weight: 900; font-variant-numeric: tabular-nums; }
@media (max-width: 520px) { .pie { grid-template-columns: 1fr; } .pie svg { max-width: 180px; margin: 0 auto; } }
</style>
