<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import PositionChart from '../components/PositionChart.vue';
import { scenarios } from '../data/flows';
import { skillLabel } from '../data/skills';
import { backendScenario } from '../api/forecast';
import { readProfileId } from '../api/profile';
import type { JobMatch } from '../api/jobs';
import { loadJobs, useFlow } from '../state';
import { go } from '../router';

const CHIPS = 3; // skills shown per side on a card

const router = useRouter();
const { state, scenario } = useFlow();
const sIcon = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;
const trendIcon = { growing: 'tup', stable: 'arrow', shrinking: 'tdown' } as const;
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const jobs = computed(() => state.value.jobs.data?.jobs ?? []);
const selected = computed(() => state.value.chosenRoleId ?? jobs.value[0]?.onet_code ?? null);

function outlook(job: JobMatch) {
  return job.outlook.find((o) => o.scenario === backendScenario[state.value.scenario]);
}
function changeText(job: JobMatch) {
  const o = outlook(job);
  return o ? `${o.change_pct > 0 ? '+' : ''}${o.change_pct.toFixed(1)}%` : '–';
}
function byText(job: JobMatch) {
  const o = outlook(job);
  if (!o) return 'no forecast yet';
  const [y, m] = o.forecast_for.split('-');
  return `postings by ${months[Number(m) - 1]} ${y}`;
}

/** The heading follows what the forecast actually says for this tab, so it never promises growth that isn't there. */
const heading = computed(() => {
  const trends = jobs.value.map((j) => outlook(j)?.trend);
  const growing = trends.filter((t) => t === 'growing').length;
  const shrinking = trends.filter((t) => t === 'shrinking').length;
  const lead = `If ${scenario.value.title}`;
  if (growing >= trends.length / 2) return `${lead}, most of your best-fit roles grow.`;
  if (shrinking >= trends.length / 2) return `${lead}, demand dips for most of these roles, but your skills still fit.`;
  return `${lead}, these are your best-fit roles. Here’s how each one fares.`;
});

/** Open the forecast page for this role. */
function openForecast(code: string) {
  state.value.chosenRoleId = code;
  router.push({ ...go('signal'), query: { role: code } });
}

function choose() {
  state.value.chosenRoleId = selected.value;
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
  <FlowShell :progress="5" next="signal" next-label="Choose this role" skip-label="Save for later" skip-to="resources" :next-disabled="!selected" @next="choose">
    <div class="wrap">
      <div v-if="state.jobs.status === 'loading' || state.jobs.status === 'idle'" class="state">
        <Bubble :size="70">Matching your skills against every role. This can take up to half a minute…</Bubble>
      </div>

      <div v-else-if="state.jobs.status === 'error'" class="state">
        <Bubble :size="70">{{ state.jobs.error }}</Bubble>
        <button type="button" class="btn btn-secondary retry" @click="retry"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <template v-else>
        <div class="bar">
          <div class="tabs">
            <button v-for="s in scenarios" :key="s.key" :class="{ on: state.scenario === s.key }" @click="state.scenario = s.key">
              <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
            </button>
          </div>
          <div class="view" role="group" aria-label="Layout">
            <button :class="{ on: state.rolesView === 'cards' }" :aria-pressed="state.rolesView === 'cards'" @click="state.rolesView = 'cards'">Cards</button>
            <button :class="{ on: state.rolesView === 'chart' }" :aria-pressed="state.rolesView === 'chart'" @click="state.rolesView = 'chart'">Chart</button>
          </div>
        </div>
        <h1>{{ heading }}</h1>
        <div v-if="state.rolesView === 'chart'" class="card chart-card">
          <h2 class="chart-title">Demand vs AI automation exposure</h2>
          <PositionChart
            :jobs="jobs"
            :context="state.jobs.data?.context ?? []"
            :scenario="backendScenario[state.scenario]"
            :selected="selected"
            @select="openForecast"
          />
          <p class="foot">
            Orange circles are your matches: bigger means a better fit. Tap one to see its forecast. Grey circles are other jobs for comparison.
            The line through the selected role is its likely range. Exposure is how much AI is already used in a job’s work, weighted by how much of
            that use does the task (automation) rather than helps with it (augmentation), from the Anthropic Economic Index.
          </p>
        </div>
        <div v-else class="cards">
          <button v-for="j in jobs" :key="j.onet_code" class="rc" :class="{ on: selected === j.onet_code }" @click="openForecast(j.onet_code)">
            <div class="top">
              <span class="ic"><Icon :name="j.icon" :size="22" /></span>
              <span class="match"><b>{{ j.match_percent }}%</b> match</span>
            </div>
            <em v-if="j.rank === 1" class="pill pill-dark best">Best match</em>
            <h2>{{ j.title }}</h2>
            <div class="big" :class="outlook(j)?.trend">
              <Icon :name="trendIcon[outlook(j)?.trend ?? 'stable']" :size="26" :stroke="2.6" />
              <b>{{ changeText(j) }}</b><span>{{ byText(j) }}</span>
            </div>
            <div class="progress"><i :style="{ width: (j.skills_owned / j.skills_total) * 100 + '%' }" /></div>
            <p class="small">{{ j.skills_owned }} of {{ j.skills_total }} key skills already yours</p>
            <p class="blurb">{{ j.description }}</p>
            <div class="chips">
              <span v-for="s in j.skills_you_have.slice(0, CHIPS)" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(s) }}</span>
              <span v-for="s in j.skills_to_learn.slice(0, CHIPS)" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="13" /> {{ skillLabel(s) }}</span>
            </div>
          </button>
        </div>
        <p class="note">{{ state.jobs.data?.note }}</p>
      </template>
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { width: min(1100px, 94vw); margin-left: 50%; transform: translateX(-50%); }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
.bar { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; }
.tabs { display: flex; gap: 10px; flex-wrap: wrap; }
.view { display: flex; padding: 4px; border-radius: 14px; background: var(--line); }
.view button { padding: 8px 16px; border-radius: 10px; font-weight: 900; font-size: 13px; color: var(--muted); }
.view button.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30,30,30,.1); }
.chart-card { padding: 22px 24px; }
.chart-title { font-size: 17px; font-weight: 900; margin-bottom: 10px; }
.foot { margin-top: 12px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; }
.tabs button { display: flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: 14px; border: 2px solid var(--line-strong); background: #fff; box-shadow: 0 4px 0 rgba(30,30,30,.1); font-weight: 900; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; }
.tabs button.on { background: var(--yellow); border-color: var(--yellow); box-shadow: 0 4px 0 var(--orange); }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 22px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.rc { text-align: left; background: #fff; border: 2px solid var(--line-strong); border-radius: 22px; padding: 22px; box-shadow: 0 5px 0 var(--line); display: flex; flex-direction: column; gap: 10px; transition: transform .12s; }
.rc:hover { transform: translateY(-2px); }
.rc.on { border: 3px solid var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.top { display: flex; justify-content: space-between; align-items: center; }
.ic { width: 42px; height: 42px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.on .ic { background: var(--yellow); }
h2 { font-size: 21px; font-weight: 800; margin-top: 6px; }
.big { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 8px; } .big b { font-size: 44px; font-weight: 900; line-height: 1; } .big span { font-size: 13px; color: var(--muted); font-weight: 700; }
.small { font-size: 12px; font-weight: 700; color: var(--muted); }
.match { display: inline-flex; align-items: baseline; gap: 4px; background: var(--cream); border-radius: 12px; padding: 6px 12px; font-weight: 800; font-size: 12px; color: var(--muted); }
.match b { font-size: 18px; font-weight: 900; color: var(--ink); }
.on .match { background: var(--yellow); color: var(--ink); }
.best { align-self: flex-start; }
.big svg { color: var(--orange); align-self: center; flex: none; }
.big.shrinking b, .big.shrinking svg { color: var(--muted); }
.state { max-width: 560px; margin: 40px auto; display: flex; flex-direction: column; align-items: flex-start; gap: 18px; }
.retry { display: inline-flex; align-items: center; gap: 8px; margin-left: 82px; }
.note { margin-top: 22px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; max-width: 760px; }
.blurb { font-size: 13px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; padding: 6px 11px 6px 9px; }
@media (max-width: 960px) { .cards { grid-template-columns: 1fr; } }
</style>
