<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import RoleBrowser from '../components/RoleBrowser.vue';
import { readProfileId } from '../api/profile';
import { loadJobs, useFlow } from '../state';
import { go } from '../router';
import { personaCopy } from '../data/personaCopy';

const router = useRouter();
const { state, key } = useFlow();

const jobs = computed(() => state.value.jobs.data?.jobs ?? []);
const selected = computed(() => state.value.chosenRoleId ?? jobs.value[0]?.onet_code ?? null);

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
  <FlowShell
    :progress="5"
    next="signal"
    next-label="Choose this role"
    back="skills"
    :next-disabled="!selected"
    wide
    :mood="state.jobs.status === 'error' ? 'surprised' : state.jobs.status === 'done' ? 'happy' : 'thinking'"
    @next="choose"
  >
    <template #bubble>
      <template v-if="state.jobs.status === 'loading' || state.jobs.status === 'idle'">{{ personaCopy[key].rolesLoading }}</template>
      <template v-else-if="state.jobs.status === 'error'">{{ state.jobs.error }}</template>
      <template v-else>{{ personaCopy[key].roles }}</template>
    </template>
    <div class="wrap">
      <div v-if="state.jobs.status === 'loading' || state.jobs.status === 'idle'" class="skel" aria-hidden="true">
        <span v-for="n in 3" :key="n" />
      </div>

      <div v-else-if="state.jobs.status === 'error'" class="state">
        <button type="button" class="btn btn-secondary retry" @click="retry"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <RoleBrowser
        v-else
        :jobs="jobs"
        :context="state.jobs.data?.context ?? []"
        :note="state.jobs.data?.note"
        :selected="selected"
        @select="openForecast"
      />
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { width: 100%; }
.wrap :deep(h1) { font-size: 24px; line-height: 1.25; margin-bottom: 18px; }
.skel { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.skel span { height: 300px; border-radius: 22px; background: linear-gradient(100deg, #fff 30%, var(--cream) 50%, #fff 70%) 0 0 / 300% 100%; border: 2px solid var(--line); animation: shimmer 1.6s linear infinite; }
@keyframes shimmer { to { background-position: -150% 0; } }
@media (max-width: 960px) { .skel { grid-template-columns: 1fr; } .skel span { height: 160px; } }
.state { display: flex; justify-content: center; padding: 24px 0; }
.retry { display: inline-flex; align-items: center; gap: 8px; }
</style>
