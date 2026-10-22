<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import RoleBrowser from '../components/RoleBrowser.vue';
import { readProfileId } from '../api/profile';
import { loadJobs, useFlow } from '../state';
import { go } from '../router';

const router = useRouter();
const { state } = useFlow();

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
  <FlowShell :progress="5" next="signal" next-label="Choose this role" back="skills" :next-disabled="!selected" @next="choose">
    <div class="wrap">
      <div v-if="state.jobs.status === 'loading' || state.jobs.status === 'idle'" class="state">
        <Bubble :size="70">Matching your skills against every role. This can take up to half a minute…</Bubble>
      </div>

      <div v-else-if="state.jobs.status === 'error'" class="state">
        <Bubble :size="70">{{ state.jobs.error }}</Bubble>
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
.wrap { width: min(1100px, 94vw); margin-left: 50%; transform: translateX(-50%); }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
.state { max-width: 560px; margin: 40px auto; display: flex; flex-direction: column; align-items: flex-start; gap: 18px; }
.retry { display: inline-flex; align-items: center; gap: 8px; margin-left: 82px; }
</style>
