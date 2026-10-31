<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import MatchWhy from '../components/MatchWhy.vue';
import RoleDetail from '../components/RoleDetail.vue';
import { fetchSuggested, matchPercent } from '../api/jobs';
import { backendScenario } from '../api/forecast';
import { readProfileId } from '../api/profile';
import { listRoadmaps, type RoadmapSummary } from '../api/roadmap';
import { roadmapStatus } from '../data/roadmapStatus';
import { openRoadmap, useFlow } from '../state';
import { go } from '../router';

const route = useRoute();
const router = useRouter();
const { state } = useFlow();

const code = computed(() => (route.query.role as string | undefined) ?? '');
const job = computed(() => state.value.suggested?.jobs.find((j) => j.onet_code === code.value));

/** Whether this role has a roadmap: unknown until checked, null once checked and there is none. */
const roadmap = ref<RoadmapSummary | null | undefined>(undefined);
const checkFailed = ref(false);
const status = computed(() => roadmapStatus(roadmap.value ?? undefined));
const checking = computed(() => roadmap.value === undefined && !checkFailed.value);

async function checkRoadmap() {
  const id = state.value.profileId ?? readProfileId();
  checkFailed.value = false;
  roadmap.value = undefined;
  if (!id) {
    checkFailed.value = true;
    return;
  }
  try {
    roadmap.value = (await listRoadmaps(id))[code.value] ?? null;
  } catch {
    checkFailed.value = true;
  }
}

function viewRoadmap() {
  openRoadmap(state.value, code.value);
  router.push(go('pathway'));
}

function generateRoadmap() {
  openRoadmap(state.value, code.value);
  router.push(go('generating'));
}

onMounted(async () => {
  checkRoadmap();
  // Landing here directly (e.g. after a refresh): the saved suggestions give the match and skill gap.
  const id = state.value.profileId ?? readProfileId();
  if (!state.value.suggested && id) {
    try {
      state.value.suggested = await fetchSuggested(id);
    } catch {
      // Not fatal: the outlook below still loads, it just won't show the skill gap.
    }
  }
});
</script>

<template>
  <div class="tab">
    <div class="page">
      <RouterLink :to="go('suggested')" class="back">← All roles</RouterLink>

      <div v-if="!code" class="state">
        <Bubble :size="64">Pick a role from your list to see its details.</Bubble>
        <RouterLink :to="go('suggested')" class="btn btn-secondary">Back to my roles</RouterLink>
      </div>

      <template v-else>
        <section class="head">
          <div class="card top">
          <div class="who">
            <span v-if="job" class="ic"><Icon :name="job.icon" :size="26" /></span>
            <div class="txt">
              <h1>{{ job?.title ?? 'Role details' }}</h1>
              <div class="meta">
                <span v-if="job" class="match"><b>{{ matchPercent(job, backendScenario[state.scenario]) }}%</b> match</span>
                <span v-if="!checkFailed && !checking" class="rm" :class="status.key">
                  <Icon v-if="status.key === 'completed'" name="check" :size="14" :stroke="3" /> {{ status.label }}
                </span>
              </div>
              <div v-if="roadmap && roadmap.total" class="progress"><i :style="{ width: (roadmap.completed / roadmap.total) * 100 + '%' }" /></div>
            </div>
          </div>

          </div>

          <MatchWhy v-if="job" :job="job" :scenario="backendScenario[state.scenario]" :stage="state.suggested?.stage">
            <RouterLink :to="{ ...go('suggested'), query: { view: 'simulate' } }" class="try"><Icon name="sparkles" :size="15" /> What if you learned a new skill?</RouterLink>
          </MatchWhy>
        </section>

        <RoleDetail :onet-code="code" :job="job">
          <template #actions>
            <div class="act">
              <button v-if="checking" type="button" class="btn btn-primary" disabled>Checking…</button>
              <button v-else-if="checkFailed" type="button" class="btn btn-secondary" @click="checkRoadmap"><Icon name="refresh" :size="18" /> Try again</button>
              <button v-else-if="roadmap" type="button" class="btn btn-primary" @click="viewRoadmap"><Icon name="route" :size="18" /> View roadmap</button>
              <button v-else type="button" class="btn btn-primary" @click="generateRoadmap"><Icon name="sparkles" :size="18" /> Generate roadmap</button>
              <small v-if="checkFailed">Couldn’t check your roadmaps.</small>
              <small v-else-if="!checking && !roadmap">Takes about 15 seconds.</small>
            </div>
          </template>
        </RoleDetail>
      </template>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; }
.back { display: inline-block; margin-bottom: 14px; font-size: 14px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.back:hover { color: var(--ink); }
.head { margin-bottom: 28px; }
.top { position: relative; z-index: 1; display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; padding: 20px 24px; }
.try { margin-left: 10px; display: inline-flex; align-items: center; gap: 6px; font-size: 15px; font-weight: 800; color: var(--amber-ink); text-decoration: underline; }
.who { display: flex; align-items: center; gap: 16px; min-width: 0; flex: 1; }
.ic { width: 52px; height: 52px; border-radius: 14px; background: var(--yellow); display: grid; place-items: center; flex: none; }
.txt { min-width: 0; flex: 1; }
.txt h1 { font-size: 30px; font-weight: 900; line-height: 1.15; margin: 0 0 8px; }
.meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.match { display: inline-flex; align-items: baseline; gap: 4px; background: var(--cream); border-radius: 12px; padding: 5px 12px; font-weight: 800; font-size: 14px; color: var(--muted); }
.match b { font-size: 18px; font-weight: 900; color: var(--ink); }
.rm { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 999px; font-size: 14px; font-weight: 800; border: 2px solid var(--line-strong); color: var(--muted); background: #fff; }
.rm.ready { background: var(--cream); border-color: var(--yellow); color: var(--ink); }
.rm.started { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.rm.completed { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.progress { height: 10px; margin-top: 12px; max-width: 320px; }
.act { display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
.act .btn { display: inline-flex; align-items: center; gap: 8px; }
.act small { font-size: 14px; font-weight: 700; color: var(--muted); text-align: center; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
</style>
