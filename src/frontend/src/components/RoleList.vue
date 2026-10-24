<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import { backendScenario } from '../api/forecast';
import { matchPercent, type JobMatch } from '../api/jobs';
import type { RoadmapSummary } from '../api/roadmap';
import { scenarios } from '../data/flows';
import { roadmapStatus } from '../data/roadmapStatus';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { useScenarioProbabilities } from '../composables/useScenarioProbabilities';

/** The "If [AI future]" toggle and the compact list of matched roles. Shared by the onboarding roles page and the logged-in one. */
const props = defineProps<{
  jobs: JobMatch[];
  /** The picked role, shown open. Leave it out when a row opens the role's page instead of picking it. */
  selected?: string | null;
  /** The profile's roadmaps by role. When given, each row shows its role's roadmap status. */
  roadmaps?: Record<string, RoadmapSummary>;
}>();
const emit = defineEmits<{ select: [code: string] }>();

const CHIPS = 3; // skills shown per side in the open row

const { state } = useFlow();
const scenarioName = computed(() => backendScenario[state.value.scenario]);
const { metrics, metricTarget, pct, ranked, rankColor } = useScenarioProbabilities();
/** The 3 AI-future scenarios, most likely first. */
const rankedScenarios = computed(() => ranked.value.map((k) => scenarios.find((s) => s.key === k)!));
/** The roles, best match first under the chosen AI future, so the order and the Best match tag follow the tab. */
const ordered = computed(() => [...props.jobs].sort((a, b) => matchPercent(b, scenarioName.value) - matchPercent(a, scenarioName.value) || a.rank - b.rank));
/** Rows pick a role when a selection is tracked; otherwise they act as links. */
const picking = computed(() => props.selected !== undefined);

const trendIcon = { growing: 'tup', stable: 'arrow', shrinking: 'tdown' } as const;
const trendClass = { growing: 'trend-up', stable: 'trend-flat', shrinking: 'trend-down' } as const;
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function outlook(job: JobMatch) {
  return job.outlook.find((o) => o.scenario === backendScenario[state.value.scenario]);
}
function change(job: JobMatch) {
  const o = outlook(job);
  return o ? `${o.change_pct > 0 ? '+' : ''}${o.change_pct.toFixed(1)}%` : '–';
}
/** "by Sep 2027", from the first role's forecast; every role shares the same horizon. */
const by = computed(() => {
  const o = props.jobs[0] && outlook(props.jobs[0]);
  if (!o) return '';
  const [y, m] = o.forecast_for.split('-');
  return `by ${months[Number(m) - 1]} ${y}`;
});

const demandTooltip = 'Forecasted hiring demand: (+) means job openings are growing, (−) means openings are shrinking.';
</script>

<template>
  <div>
    <div v-if="pct('accelerates') != null" class="prob-graph">
      <p class="prob-title">Chances of each AI future, most likely first</p>
      <div class="prob-labels">
        <span v-for="s in rankedScenarios" :key="s.key" :style="{ width: pct(s.key) + '%', color: rankColor(s.key) ?? 'var(--muted)' }">{{ pct(s.key) }}%</span>
      </div>
      <div class="prob-bar" role="img" aria-label="Chances of each AI future">
        <span v-for="s in rankedScenarios" :key="s.key" class="prob-seg" :style="{ width: pct(s.key) + '%', background: rankColor(s.key) ?? '#c2bfba' }" />
      </div>
    </div>
    <div class="metric-wrap">
      <span class="seg-label">From</span>
      <div class="metric-seg" role="radiogroup" aria-label="Metric the chances are based on">
        <button
          v-for="m in metrics"
          :key="m.target"
          type="button"
          role="radio"
          :aria-checked="metricTarget === m.target"
          :class="{ on: metricTarget === m.target }"
          @click="metricTarget = m.target"
        >{{ m.label }}</button>
      </div>
    </div>
    <p class="seg-caption">Nearest-term forecast.</p>
    <div class="seg-wrap">
      <span class="seg-label">If</span>
      <div class="seg" role="radiogroup" aria-label="Possible AI future, most likely first">
        <button
          v-for="s in rankedScenarios"
          :key="s.key"
          type="button"
          role="radio"
          :aria-checked="state.scenario === s.key"
          :class="{ on: state.scenario === s.key }"
          :style="{ '--rc': rankColor(s.key) ?? 'var(--line-strong)' }"
          @click="state.scenario = s.key"
        >
          {{ s.label }}
          <small v-if="pct(s.key) != null" class="seg-pct">{{ pct(s.key) }}%</small>
        </button>
      </div>
    </div>

    <div class="list" :role="picking ? 'radiogroup' : undefined" aria-label="Roles that fit you">
      <button
        v-for="(j, idx) in ordered"
        :key="j.onet_code"
        type="button"
        :role="picking ? 'radio' : undefined"
        class="option role"
        :class="{ selected: picking && selected === j.onet_code }"
        :aria-checked="picking ? selected === j.onet_code : undefined"
        @click="emit('select', j.onet_code)"
      >
        <span v-if="picking" class="radio" aria-hidden="true"><Icon v-if="selected === j.onet_code" name="check" :size="14" :stroke="3.2" /></span>
        <span class="score" :class="{ best: idx === 0 }" :style="{ '--p': matchPercent(j, scenarioName) }">
          <b>{{ matchPercent(j, scenarioName) }}<small>%</small></b>
          <span>match</span>
        </span>
        <span class="body">
          <span class="title-row">
            <h3>{{ j.title }}</h3>
            <em v-if="idx === 0" class="pill pill-dark">Best match</em>
            <span v-if="roadmaps" class="rm" :class="roadmapStatus(roadmaps[j.onet_code]).key">
              <Icon v-if="roadmapStatus(roadmaps[j.onet_code]).key === 'completed'" name="check" :size="12" :stroke="3" />
              {{ roadmapStatus(roadmaps[j.onet_code]).label }}
            </span>
          </span>
          <span class="sub">{{ j.skills_owned }} of {{ j.skills_total }} key skills</span>
          <span v-if="picking && selected === j.onet_code" class="more">
            <span class="blurb">{{ j.description }}</span>
            <span class="chips">
              <span v-for="s in j.skills_you_have.slice(0, CHIPS)" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(s) }}</span>
              <span v-for="s in j.skills_to_learn.slice(0, CHIPS)" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="13" /> {{ skillLabel(s) }}</span>
            </span>
          </span>
        </span>
        <span
          class="trend"
          :class="trendClass[outlook(j)?.trend ?? 'stable']"
          :title="demandTooltip"
          :aria-label="demandTooltip"
        >
          <Icon :name="trendIcon[outlook(j)?.trend ?? 'stable']" :size="18" :stroke="2.6" />
          <b>{{ change(j) }}</b>
        </span>
        <Icon v-if="!picking" name="arrow" :size="18" class="go" />
      </button>
    </div>
    <p class="note">Percentages are the forecast change in job postings {{ by }}. Indicative, not a prediction.</p>
  </div>
</template>

<style scoped>
.prob-graph { margin-bottom: 14px; }
.prob-title { margin: 0 0 8px; font-size: 11px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.prob-labels { display: flex; gap: 2px; margin-bottom: 4px; }
.prob-labels span { display: block; min-width: 0; font-size: 11px; font-weight: 900; text-align: center; white-space: nowrap; overflow: visible; }
.prob-bar { display: flex; gap: 2px; height: 12px; border-radius: 6px; overflow: hidden; }
.prob-seg { display: block; height: 100%; min-width: 2px; }
.seg-wrap, .metric-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.seg-label { font-size: 13px; font-weight: 900; color: var(--muted); }
.seg, .metric-seg { flex: 1; display: grid; padding: 4px; border-radius: 14px; background: var(--line); }
.seg { grid-template-columns: repeat(3, 1fr); }
.metric-seg { grid-template-columns: repeat(4, 1fr); }
.seg button, .metric-seg button { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; padding: 8px 6px 6px; border-radius: 10px; font-weight: 900; font-size: 13px; color: var(--muted); text-align: center; line-height: 1.2; border-bottom: 3px solid var(--rc, transparent); transition: background .15s, color .15s, border-color .15s; }
.metric-seg button { font-size: 11px; padding: 7px 4px; border-bottom: none; }
.seg button:hover, .metric-seg button:hover { color: var(--ink); }
.seg button.on { background: #fff; color: var(--rc, var(--ink)); box-shadow: 0 2px 0 rgba(30, 30, 30, .1); }
.metric-seg button.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30, 30, 30, .1); }
.seg-pct { font-size: 11px; font-weight: 800; color: var(--muted); }
.seg button.on .seg-pct { color: var(--rc, var(--muted)); }
.seg-caption { margin: 0 0 16px; font-size: 12px; font-weight: 600; color: var(--muted); }

.list { display: flex; flex-direction: column; gap: 12px; }
.role { align-items: flex-start; padding: 16px 18px; }
/* Match ring: the filled arc is the match %. */
.score {
  flex: none; width: 58px; height: 58px; border-radius: 50%; display: grid; place-content: center; text-align: center;
  background: radial-gradient(closest-side, #fff 76%, transparent 78%), conic-gradient(var(--orange) calc(var(--p) * 1%), var(--line) 0);
}
.score.best { background: radial-gradient(closest-side, var(--yellow) 76%, transparent 78%), conic-gradient(var(--ink) calc(var(--p) * 1%), var(--line) 0); }
.score b { font-size: 18px; font-weight: 900; line-height: 1; color: var(--ink); }
.score b small { font-size: 11px; font-weight: 900; }
.score span { font-size: 9px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-top: 1px; }
.score.best span { color: var(--ink); }
.role:not(.selected) { align-items: center; }
.role:not(.selected) .trend, .role:not(.selected) .go, .role:not(.selected) .radio { margin-top: 0; }
.radio { width: 24px; height: 24px; margin-top: 1px; border-radius: 50%; border: 2px solid var(--line-strong); display: grid; place-items: center; flex: none; background: #fff; }
.selected .radio { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; text-align: left; }
.title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.role h3 { font-size: 17px; }
.sub { font-size: 13px; font-weight: 700; color: var(--muted); }
.rm { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 800; border: 2px solid var(--line-strong); color: var(--muted); background: #fff; }
.rm.ready { background: var(--cream); border-color: var(--yellow); color: var(--ink); }
.rm.started { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.rm.completed { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.more { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; animation: open .2s ease both; }
.blurb { font-size: 13px; font-weight: 600; color: var(--muted); line-height: 1.45; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; padding: 5px 10px 5px 8px; }
.trend { display: inline-flex; align-items: center; gap: 4px; flex: none; margin-top: 1px; }
.trend b { font-size: 16px; font-weight: 900; }
.go { flex: none; margin-top: 2px; color: var(--muted); }
.note { margin-top: 16px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; }
@keyframes open { from { opacity: 0; transform: translateY(-4px); } }
@media (max-width: 480px) {
  .seg button { font-size: 11px; }
  .seg-label { display: none; }
}
</style>
