<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import RoleDetail from '../components/RoleDetail.vue';
import { fetchSuggested } from '../api/jobs';
import { readProfileId } from '../api/profile';
import { listRoadmaps, type RoadmapSummary } from '../api/roadmap';
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
        <RoleDetail :onet-code="code" :job="job">
          <template #actions>
            <div class="act">
              <button v-if="checking" type="button" class="btn btn-primary" disabled>Checking…</button>
              <button v-else-if="checkFailed" type="button" class="btn btn-secondary" @click="checkRoadmap"><Icon name="refresh" :size="18" /> Try again</button>
              <button v-else-if="roadmap" type="button" class="btn btn-primary" @click="viewRoadmap"><Icon name="route" :size="18" /> View roadmap</button>
              <button v-else type="button" class="btn btn-primary" @click="generateRoadmap">Generate roadmap <Icon name="arrow" :size="18" /></button>
              <small v-if="checkFailed">Couldn’t check your roadmaps.</small>
              <small v-else-if="!checking && !roadmap">Takes about 15 seconds.</small>
              <RouterLink :to="{ ...go('suggested'), query: { view: 'simulate' } }" class="try">What if you learned a new skill?</RouterLink>
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
.try { align-self: center; margin-top: 4px; display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 700; color: var(--muted); text-decoration: underline; }
.try:hover { color: var(--amber-ink); }
.act { display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
.act .btn { display: inline-flex; align-items: center; gap: 8px; }
.act small { font-size: 14px; font-weight: 700; color: var(--muted); text-align: center; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
</style>
