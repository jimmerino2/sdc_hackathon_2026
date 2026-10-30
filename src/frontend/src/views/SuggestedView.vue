<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Bubble from '../components/Bubble.vue';
import CareerSimulator from '../components/CareerSimulator.vue';
import Icon from '../components/Icon.vue';
import RoleBrowser from '../components/RoleBrowser.vue';
import { fetchRecommendations, fetchSuggested, JobsError, type Recommendations } from '../api/jobs';
import { listRoadmaps, type RoadmapSummary } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { useFlow } from '../state';
import { go } from '../router';

const router = useRouter();
const route = useRoute();
/** The roles, or the What-If simulator on them; in the address so it can be linked to and survives a refresh. */
const simulating = computed(() => route.query.view === 'simulate');
const { state } = useFlow();
const status = ref<'loading' | 'done' | 'empty' | 'error'>('loading');
const error = ref('');
const suggested = ref<Recommendations | null>(null);
/** The profile's roadmaps by role, for the status on each card. Stays undefined if they can't be fetched, so cards show no status rather than a wrong "No roadmap yet". */
const roadmaps = ref<Record<string, RoadmapSummary>>();
/** Working out a fresh set. The current roles stay on screen until the new ones are ready. */
const regenerating = ref(false);
const regenError = ref('');

const profileId = () => state.value.profileId ?? readProfileId();

const updated = computed(() => {
  const at = suggested.value?.generated_at;
  if (!at) return null;
  return new Date(at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' });
});

async function load() {
  const id = profileId();
  if (!id) {
    status.value = 'error';
    error.value = 'Jobee couldn’t find your profile. Log in again to see your roles.';
    return;
  }
  status.value = 'loading';
  try {
    const [saved, built] = await Promise.all([fetchSuggested(id), listRoadmaps(id).catch(() => null)]);
    suggested.value = saved;
    state.value.suggested = saved;
    if (built) roadmaps.value = built;
    status.value = saved ? 'done' : 'empty';
  } catch (e) {
    status.value = 'error';
    error.value = e instanceof JobsError ? e.message : 'Jobee couldn’t load your suggested roles. Try again in a moment.';
  }
}

/** Match the profile's skills against the roles again, with today's forecasts. The result is saved, replacing the old set. */
async function regenerate() {
  const id = profileId();
  if (!id || regenerating.value) return;
  regenerating.value = true;
  regenError.value = '';
  try {
    suggested.value = await fetchRecommendations(id);
    state.value.suggested = suggested.value;
    status.value = 'done';
  } catch (e) {
    // Keep showing the roles we already have; only say the refresh didn't work.
    regenError.value = e instanceof JobsError ? e.message : 'Jobee couldn’t refresh your roles just now. Try again in a moment.';
  } finally {
    regenerating.value = false;
  }
}

/** Open a role's page: its outlook, skill gap and roadmap. */
function openRole(code: string) {
  router.push({ ...go('role'), query: { role: code } });
}

onMounted(load);
</script>

<template>
  <div class="tab">
    <div class="page">
      <div class="head">
        <div>
          <p class="eyebrow">Your roles</p>
          <p v-if="updated && status === 'done'" class="when">Last updated {{ updated }}</p>
        </div>
      </div>

      <div v-if="status === 'done'" class="nav-bar">
        <div class="switch" role="group" aria-label="View">
          <RouterLink :to="{ ...go('suggested'), query: {} }" :class="{ on: !simulating }" :aria-current="!simulating ? 'page' : undefined">Your matches</RouterLink>
          <RouterLink :to="{ ...go('suggested'), query: { view: 'simulate' } }" :class="{ on: simulating }" :aria-current="simulating ? 'page' : undefined"><Icon name="lightbulb" :size="15" /> What-if simulator</RouterLink>
        </div>
      </div>

      <div v-if="regenerating" class="banner" role="status">
        <Bubble :size="48">Working out your roles again with today’s forecasts. This can take up to half a minute…</Bubble>
      </div>
      <p v-else-if="regenError" class="error" role="alert">{{ regenError }}</p>

      <div v-if="status === 'loading'" class="skel-wrap" aria-busy="true" aria-label="Loading your roles">
        <span class="skel tab-skel" />
        <div class="skel-cards"><span v-for="n in 4" :key="n" class="skel card card-skel" /></div>
      </div>

      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">{{ error }}</Bubble>
        <button type="button" class="btn btn-secondary" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <div v-else-if="status === 'empty'" class="state">
        <Bubble :size="64">I haven’t saved any suggested roles for you yet. I can work them out now from the skills on your profile.</Bubble>
        <button type="button" class="btn btn-primary" :disabled="regenerating" @click="regenerate">
          {{ regenerating ? 'Working it out…' : 'Suggest roles for me' }}
        </button>
        <RouterLink :to="go('pathway')" class="btn btn-secondary">Back to my roadmap</RouterLink>
      </div>

      <CareerSimulator v-else-if="suggested && simulating" />

      <RoleBrowser
        v-else-if="suggested"
        :class="{ dim: regenerating }"
        :jobs="suggested.jobs"
        :context="suggested.context"
        :note="suggested.note"
        :roadmaps="roadmaps"
        :stage="suggested.stage"
        :selected="state.chosenRoleId"
        chart-hint="Tap one to open it."
        @select="openRole"
      >
        <template #sidebar-footer>
          <button
            type="button"
            class="btn btn-secondary regen-sidebar"
            :disabled="regenerating"
            @click="regenerate"
          >
            <Icon name="refresh" :size="16" :class="{ spin: regenerating }" />
            {{ regenerating ? 'Regenerating…' : 'Regenerate roles' }}
          </button>
        </template>
      </RoleBrowser>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.eyebrow { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.when { margin-top: 4px; font-size: 12px; font-weight: 700; color: var(--muted); }
.nav-bar { display: flex; align-items: center; margin-bottom: 20px; min-height: 44px; }
.switch { display: inline-flex; padding: 4px; border-radius: 14px; background: var(--line); max-width: 100%; }
.switch a { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 10px; font-weight: 900; font-size: 13px; color: var(--muted); transition: background .15s ease, color .15s ease, box-shadow .15s ease; }
.switch a.on { background: #fff; color: var(--ink); box-shadow: 0 2px 0 rgba(30, 30, 30, .1); }
.regen-sidebar {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 900;
  background: #fff;
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.banner { margin-bottom: 18px; }
.error { margin-bottom: 18px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; line-height: 1.4; }
.dim { opacity: .55; pointer-events: none; transition: opacity .2s; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
.tab-skel { display: block; height: 44px; margin-bottom: 16px; }
.skel-cards { display: flex; flex-direction: column; gap: 12px; }
.card-skel { height: 76px; border-radius: 16px; }
</style>
