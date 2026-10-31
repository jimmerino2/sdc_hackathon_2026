<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Bubble from '../components/Bubble.vue';
import CareerSimulator from '../components/CareerSimulator.vue';
import DataFreshness from '../components/DataFreshness.vue';
import Icon from '../components/Icon.vue';
import RoleBrowser from '../components/RoleBrowser.vue';
import { ForecastError, syncTrends, type TrendSync } from '../api/forecast';
import { fetchRecommendations, fetchSuggested, JobsError, type Recommendations } from '../api/jobs';
import { day, month } from '../occupational/format';
import { listRoadmaps, type RoadmapSummary } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { useFlow } from '../state';
import { go } from '../router';

const router = useRouter();
const route = useRoute();
/** The roles, or the What-If simulator on them; in the address so it can be linked to and survives a refresh. */
const simulating = computed(() => route.query.view === 'simulate');
const { state } = useFlow();
const suggested = ref<Recommendations | null>(state.value.suggested ?? null);
const status = ref<'loading' | 'done' | 'empty' | 'error'>(suggested.value ? 'done' : 'loading');
const error = ref('');
/** The profile's roadmaps by role, for the status on each card. Stays undefined if they can't be fetched, so cards show no status rather than a wrong "No roadmap yet". */
const roadmaps = ref<Record<string, RoadmapSummary>>();
/** Working out a fresh set. The current roles stay on screen until the new ones are ready. */
const regenerating = ref(false);
const regenError = ref('');
/** What the last Sync did to the trend data, to show under the header. */
const synced = ref<TrendSync | null>(null);
const syncNote = computed(() => {
  const s = synced.value;
  if (!s) return '';
  const names = (status: string) => s.ai.filter((a) => a.status === status).map((a) => a.name).join(', ');
  const ai = [
    names('updated') && ` New AI forecasts: ${names('updated')}.`,
    names('stale') && ` Not updated because the source is out of date: ${names('stale')}.`,
    names('failed') && ` Couldn’t update: ${names('failed')}.`,
  ].join('');
  if (s.manual_edits) return `Retrained on ${s.manual_edits} hand-edited ${s.manual_edits === 1 ? 'figure' : 'figures'}, forecasts from ${month(s.after.forecast_from)}. Press Sync again to go back to Indeed’s data.${ai}`;
  const source = s.pulled ? 'Pulled from Indeed' : 'Indeed couldn’t be reached, so this used the last saved copy';
  const data = s.before.as_of === s.after.as_of ? `data still as of ${day(s.after.as_of)}` : `data moved from ${day(s.before.as_of)} to ${day(s.after.as_of)}`;
  return `${source}: ${data}, forecasts retrained from ${month(s.after.forecast_from)}.${ai}`;
});

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
  if (!suggested.value) {
    status.value = 'loading';
  }
  try {
    const [saved, built] = await Promise.all([fetchSuggested(id), listRoadmaps(id).catch(() => null)]);
    suggested.value = saved;
    state.value.suggested = saved;
    if (built) roadmaps.value = built;
    status.value = saved ? 'done' : 'empty';
  } catch (e) {
    if (!suggested.value) {
      status.value = 'error';
      error.value = e instanceof JobsError ? e.message : 'Jobee couldn’t load your suggested roles. Try again in a moment.';
    }
  }
}

/** Pull the newest trend data where the server allows it, then match the profile's skills against the roles again. The result is saved, replacing the old set. */
async function regenerate() {
  const id = profileId();
  if (!id || regenerating.value) return;
  regenerating.value = true;
  regenError.value = '';
  synced.value = null;
  try {
    const trends = await syncTrends();
    suggested.value = await fetchRecommendations(id);
    state.value.suggested = suggested.value;
    status.value = 'done';
    synced.value = trends;
  } catch (e) {
    // Keep showing the roles we already have; only say the refresh didn't work.
    regenError.value = e instanceof JobsError || e instanceof ForecastError ? e.message : 'Jobee couldn’t refresh your roles just now. Try again in a moment.';
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
          <div v-if="updated" class="when">
            <span>Last updated {{ updated }}</span>
            <button type="button" class="sync" :disabled="regenerating" @click="regenerate">
              <Icon name="refresh" :size="14" :class="{ spin: regenerating }" /> {{ regenerating ? 'Syncing…' : 'Sync' }}
            </button>
            <DataFreshness :updated="updated" />
          </div>
        </div>
      </div>

      <div class="nav-bar">
        <div class="btn-group" role="group" aria-label="View">
          <RouterLink :to="{ ...go('suggested'), query: {} }" :class="{ on: !simulating }" :aria-current="!simulating ? 'page' : undefined">Your matches</RouterLink>
          <RouterLink :to="{ ...go('suggested'), query: { view: 'simulate' } }" :class="{ on: simulating }" :aria-current="simulating ? 'page' : undefined"><Icon name="lightbulb" :size="15" /> What-if simulator</RouterLink>
        </div>
      </div>

      <div v-if="regenerating" class="banner" role="status">
        <Bubble :size="48">Fetching the newest trend data, then working out your roles again. This takes a few seconds, or about 2.5 minutes if the AI data changed…</Bubble>
      </div>
      <p v-else-if="regenError" class="error" role="alert">{{ regenError }}</p>
      <p v-else-if="syncNote" class="synced" role="status">{{ syncNote }}</p>

      <div v-if="status === 'loading'" class="skel-wrap" aria-busy="true" aria-label="Loading your roles">
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
        :roadmaps="roadmaps"
        :stage="suggested.stage"
        :selected="state.chosenRoleId"
        @select="openRole"
      />
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.eyebrow { font-size: 13px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.when { margin-top: 6px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 14px; font-weight: 700; color: var(--muted); }
.sync { display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 999px; background: #fff; box-shadow: inset 0 0 0 2px var(--line-strong); color: var(--ink); font-size: 14px; font-weight: 800; }
.sync:hover { box-shadow: inset 0 0 0 2px var(--yellow); }
.sync:disabled { opacity: .6; cursor: default; }
.nav-bar { display: flex; align-items: center; margin-bottom: 20px; min-height: 44px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.banner { margin-bottom: 18px; }
.synced { margin-bottom: 18px; font-size: 14px; font-weight: 700; color: var(--muted); }
.error { margin-bottom: 18px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 16px; line-height: 1.4; }
.dim { opacity: .55; pointer-events: none; transition: opacity .2s; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
.skel-cards { display: flex; flex-direction: column; gap: 12px; }
.card-skel { height: 76px; border-radius: 16px; }
</style>
