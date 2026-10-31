<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import SourceStamp from './SourceStamp.vue';
import MatchWhy from './MatchWhy.vue';
import { backendScenario } from '../api/forecast';
import { matchPercent, type JobMatch } from '../api/jobs';
import type { RoadmapSummary } from '../api/roadmap';
import { roadmapStatus } from '../data/roadmapStatus';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';

/** The compact list of matched roles. Shared by the onboarding roles page and the logged-in one. */
const props = defineProps<{
  jobs: JobMatch[];
  /** The picked role, shown open. Leave it out when a row opens the role's page instead of picking it. */
  selected?: string | null;
  /** The profile's roadmaps by role. When given, each row shows its role's roadmap status. */
  roadmaps?: Record<string, RoadmapSummary>;
  /** The career stage behind the education part. */
  stage?: string | null;
}>();
const emit = defineEmits<{ select: [code: string] }>();

const { state } = useFlow();
const scenarioName = computed(() => backendScenario[state.value.scenario]);
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
const matchTooltip = 'Compatibility match based on your skills, interests, career stage, and job outlook. Does not reflect hiring chances.';
</script>

<template>
  <div>
    <div class="list" :role="picking ? 'radiogroup' : undefined" aria-label="Roles that fit you">
      <div v-for="(j, idx) in ordered" :key="j.onet_code" class="item">
      <button
        type="button"
        :role="picking ? 'radio' : undefined"
        class="option role"
        :class="{ selected: picking && selected === j.onet_code }"
        :aria-checked="picking ? selected === j.onet_code : undefined"
        @click="emit('select', j.onet_code)"
      >
        <span v-if="picking" class="radio" aria-hidden="true"><Icon v-if="selected === j.onet_code" name="check" :size="14" :stroke="3.2" /></span>
        <span
          class="score" 
          :class="{ best: idx === 0 }" 
          :style="{ '--p': matchPercent(j, scenarioName) }" 
          :title="matchTooltip"
          :aria-label="matchTooltip">
          <b>{{ matchPercent(j, scenarioName) }}<small>%</small></b>
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
        <span v-if="picking && selected === j.onet_code" class="more">
            <span class="chips">
              <span v-for="s in j.skills_you_have" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(s) }}</span>
              <span v-for="s in j.skills_to_learn" :key="s" class="chip chip-neutral">{{ skillLabel(s) }}</span>
          </span>
        </span>
      </button>
      <MatchWhy :job="j" :scenario="scenarioName" :stage="stage" />
      </div>
    </div>
    <p class="note">
      The arrow shows forecast demand {{ by }}.
    </p>
    <SourceStamp />
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 24px; }
/* drop-shadow follows the outline of the row and its sub card together, so the shadow steps in around the sub card. */
.item { display: flex; flex-direction: column; filter: drop-shadow(0 4px 0 var(--line-strong)); }
.item:has(.selected) { filter: drop-shadow(0 4px 0 var(--orange)); }
.item .role { z-index: 1; box-shadow: none; }
.role { align-items: flex-start; padding: 16px 18px; }
.role.selected { flex-wrap: wrap; }
/* Match ring: the filled arc is the match %. */
.score {
  flex: none; width: 58px; height: 58px; border-radius: 50%; display: grid; place-content: center; text-align: center;
  background: radial-gradient(closest-side, #fff 76%, transparent 78%), conic-gradient(var(--orange) calc(var(--p) * 1%), var(--line) 0);
}
.score.best { background: radial-gradient(closest-side, var(--yellow) 76%, transparent 78%), conic-gradient(var(--ink) calc(var(--p) * 1%), var(--line) 0); }
.score b { font-size: 20px; font-weight: 900; line-height: 1; color: var(--ink); }
.score b small { font-size: 13px; font-weight: 900; }
.score span { font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-top: 1px; }
.score.best span { color: var(--ink); }
.role:not(.selected) { align-items: center; }
.role:not(.selected) .trend, .role:not(.selected) .go, .role:not(.selected) .radio { margin-top: 0; }
.radio { width: 24px; height: 24px; margin-top: 1px; border-radius: 50%; border: 2px solid var(--line-strong); display: grid; place-items: center; flex: none; background: #fff; }
.selected .radio { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; text-align: left; }
.title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.role h3 { font-size: 19px; }
.sub { font-size: 15px; font-weight: 700; color: var(--muted); }
.rm { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 800; border: 2px solid var(--line-strong); color: var(--muted); background: #fff; }
.rm.ready { background: var(--cream); border-color: var(--yellow); color: var(--ink); }
.rm.started { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.rm.completed { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.more { flex: 0 0 100%; display: flex; flex-direction: column; gap: 12px; animation: open .2s ease both; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 14px; padding: 5px 10px; }
.chip-have { padding-left: 8px; }
.chip-neutral { padding: 3px 10px; }
.trend { display: inline-flex; align-items: center; gap: 4px; flex: none; margin-top: 1px; }
.trend b { font-size: 18px; font-weight: 900; }
.go { flex: none; margin-top: 2px; color: var(--muted); }
.note { margin-top: 16px; font-size: 14px; font-weight: 600; color: var(--muted); line-height: 1.5; }
@keyframes open { from { opacity: 0; transform: translateY(-4px); } }

</style>
