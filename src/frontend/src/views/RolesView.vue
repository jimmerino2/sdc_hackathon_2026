<script setup lang="ts">
import { computed, onMounted } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import RoleBrowser from '../components/RoleBrowser.vue';
import { readProfileId } from '../api/profile';
import { loadJobs, useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { state, key } = useFlow();

const jobs = computed(() => state.value.jobs.data?.jobs ?? []);
const selected = computed(() => state.value.chosenRoleId ?? jobs.value[0]?.onet_code ?? null);
const loading = computed(() => state.value.jobs.status === 'loading' || state.value.jobs.status === 'idle');

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
      <RoleBrowser
        pick
        cards-only
        :jobs="jobs"
        :context="state.jobs.data?.context ?? []"
        :note="state.jobs.data?.note"
        :selected="selected"
        chart-hint="Tap one to pick it."
        @select="pick"
      />
    </template>
  </FlowShell>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 12px; }
.state { display: flex; justify-content: center; padding: 24px 0; }
.retry { display: inline-flex; align-items: center; gap: 8px; }
.seg-skel { height: 44px; margin-bottom: 4px; }
.row-skel { height: 76px; border-radius: 16px; }
</style>
