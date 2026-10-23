<script setup lang="ts">
import { computed, onMounted } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { readProfileId } from '../api/profile';
import { backendScenario } from '../api/forecast';
import type { JobMatch } from '../api/jobs';
import { loadJobs, useFlow } from '../state';
import { scenarios } from '../data/flows';
import { skillLabel } from '../data/skills';
import { personaCopy } from '../data/personaCopy';

const CHIPS = 3; // skills shown per side in the open row

const { state, key } = useFlow();

const jobs = computed(() => state.value.jobs.data?.jobs ?? []);
const selected = computed(() => state.value.chosenRoleId ?? jobs.value[0]?.onet_code ?? null);
const loading = computed(() => state.value.jobs.status === 'loading' || state.value.jobs.status === 'idle');

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
  const o = jobs.value[0] && outlook(jobs.value[0]);
  if (!o) return '';
  const [y, m] = o.forecast_for.split('-');
  return `by ${months[Number(m) - 1]} ${y}`;
});

function pick(code: string) {
  state.value.chosenRoleId = code;
}

function retry() {
  state.value.profileId ??= readProfileId();
  loadJobs(state.value);
}

onMounted(() => {
  // Landing here directly (e.g. after a refresh) still works if this browser has a saved profile.
  if (state.value.jobs.status === 'idle') retry();
});
</script>

<template>
  <FlowShell
    :progress="5"
    next="signal"
    back="skills"
    :next-disabled="!selected || loading"
    :mood="state.jobs.status === 'error' ? 'surprised' : loading ? 'thinking' : 'happy'"
    @next="state.chosenRoleId = selected"
  >
    <template #bubble>
      <template v-if="loading">{{ personaCopy[key].rolesLoading }}</template>
      <template v-else-if="state.jobs.status === 'error'">{{ state.jobs.error }}</template>
      <template v-else>{{ personaCopy[key].roles }}</template>
    </template>

    <div v-if="loading" class="list" aria-hidden="true">
      <span class="skel seg-skel" />
      <span v-for="n in 4" :key="n" class="skel card row-skel" />
    </div>

    <div v-else-if="state.jobs.status === 'error'" class="state">
      <button type="button" class="btn btn-secondary retry" @click="retry"><Icon name="refresh" :size="18" /> Try again</button>
    </div>

    <template v-else>
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

      <div class="list" role="radiogroup" aria-label="Roles that fit you">
        <button
          v-for="j in jobs"
          :key="j.onet_code"
          type="button"
          role="radio"
          class="option role"
          :class="{ selected: selected === j.onet_code }"
          :aria-checked="selected === j.onet_code"
          @click="pick(j.onet_code)"
        >
          <span class="radio" aria-hidden="true"><Icon v-if="selected === j.onet_code" name="check" :size="14" :stroke="3.2" /></span>
          <span class="body">
            <span class="title-row">
              <h3>{{ j.title }}</h3>
              <em v-if="j.rank === 1" class="pill pill-dark">Best match</em>
            </span>
            <span class="sub">{{ j.match_percent }}% match · {{ j.skills_owned }} of {{ j.skills_total }} key skills</span>
            <span v-if="selected === j.onet_code" class="more">
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
        </button>
      </div>
      <p class="note">Percentages are the forecast change in job postings {{ by }}. Indicative, not a prediction.</p>
    </template>
  </FlowShell>
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
.body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.role h3 { font-size: 17px; }
.sub { font-size: 13px; font-weight: 700; color: var(--muted); }
.more { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; animation: open .2s ease both; }
.blurb { font-size: 13px; font-weight: 600; color: var(--muted); line-height: 1.45; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; padding: 5px 10px 5px 8px; }
.trend { display: inline-flex; align-items: center; gap: 4px; flex: none; margin-top: 1px; }
.trend b { font-size: 16px; font-weight: 900; }
.note { margin-top: 16px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; }
.state { display: flex; justify-content: center; padding: 24px 0; }
.retry { display: inline-flex; align-items: center; gap: 8px; }
.seg-skel { height: 44px; margin-bottom: 4px; }
.row-skel { height: 76px; border-radius: 16px; }
@keyframes open { from { opacity: 0; transform: translateY(-4px); } }
@media (max-width: 480px) {
  .seg button { font-size: 11px; }
  .seg-label { display: none; }
}
</style>
