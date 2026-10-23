<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import { backendScenario } from '../api/forecast';
import type { JobMatch } from '../api/jobs';
import type { RoadmapSummary } from '../api/roadmap';
import { scenarios } from '../data/flows';
import { roadmapStatus } from '../data/roadmapStatus';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';

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
</script>

<template>
  <div>
    <div class="seg-wrap">
      <span class="seg-label">If</span>
      <div class="seg" role="radiogroup" aria-label="Possible AI future">
        <button
          v-for="s in scenarios"
          :key="s.key"
          type="button"
          role="radio"
          :aria-checked="state.scenario === s.key"
          :class="{ on: state.scenario === s.key }"
          @click="state.scenario = s.key"
        >{{ s.label }}</button>
      </div>
    </div>

    <div class="list" :role="picking ? 'radiogroup' : undefined" aria-label="Roles that fit you">
      <button
        v-for="j in jobs"
        :key="j.onet_code"
        type="button"
        :role="picking ? 'radio' : undefined"
        class="option role"
        :class="{ selected: picking && selected === j.onet_code }"
        :aria-checked="picking ? selected === j.onet_code : undefined"
        @click="emit('select', j.onet_code)"
      >
        <span v-if="picking" class="radio" aria-hidden="true"><Icon v-if="selected === j.onet_code" name="check" :size="14" :stroke="3.2" /></span>
        <span class="body">
          <span class="title-row">
            <h3>{{ j.title }}</h3>
            <em v-if="j.rank === 1" class="pill pill-dark">Best match</em>
            <span v-if="roadmaps" class="rm" :class="roadmapStatus(roadmaps[j.onet_code]).key">
              <Icon v-if="roadmapStatus(roadmaps[j.onet_code]).key === 'completed'" name="check" :size="12" :stroke="3" />
              {{ roadmapStatus(roadmaps[j.onet_code]).label }}
            </span>
          </span>
          <span class="sub">{{ j.match_percent }}% match · {{ j.skills_owned }} of {{ j.skills_total }} key skills</span>
          <span v-if="picking && selected === j.onet_code" class="more">
            <span class="blurb">{{ j.description }}</span>
            <span class="chips">
              <span v-for="s in j.skills_you_have.slice(0, CHIPS)" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(s) }}</span>
              <span v-for="s in j.skills_to_learn.slice(0, CHIPS)" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="13" /> {{ skillLabel(s) }}</span>
            </span>
          </span>
        </span>
        <span class="trend" :class="trendClass[outlook(j)?.trend ?? 'stable']">
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
.seg-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.seg-label { font-size: 13px; font-weight: 900; color: var(--muted); }
.seg { flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); padding: 4px; border-radius: 14px; background: var(--line); }
.seg button { padding: 9px 6px; border-radius: 10px; font-weight: 900; font-size: 13px; color: var(--muted); transition: background .15s, color .15s; }
.seg button:hover { color: var(--ink); }
.seg button.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30, 30, 30, .1); }

.list { display: flex; flex-direction: column; gap: 12px; }
.role { align-items: flex-start; padding: 16px 18px; }
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
