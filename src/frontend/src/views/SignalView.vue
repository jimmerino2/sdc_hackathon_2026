<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import RoleDetail from '../components/RoleDetail.vue';
import { SOFTWARE_DEVELOPERS_ONET } from '../api/forecast';
import { loadSkillPlan, useFlow } from '../state';

const route = useRoute();
const router = useRouter();
const { state } = useFlow();
/** The role to show: ?role= from a link, else the chosen role, else Software Developers. */
const onetCode = computed(() => (route.query.role as string | undefined) ?? state.value.chosenRoleId ?? SOFTWARE_DEVELOPERS_ONET);
/** The quarters left out of the forecast (?skip=2020,2021,2026-Q3), kept in the address so a refresh or a shared link keeps them. */
const skip = computed(() => (typeof route.query.skip === 'string' ? route.query.skip : null));
function setSkip(next: string | null) {
  const { skip: _drop, ...rest } = route.query;
  void router.replace({ query: next ? { ...rest, skip: next } : rest });
}
/** This role's match from the roles page. Missing after a refresh. */
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === onetCode.value));

/** Leaving the forecast: lock in the role and start choosing its skills while the next page loads. */
function pickRole() {
  state.value.chosenRoleId = onetCode.value;
  void loadSkillPlan(state.value);
}
</script>

<template>
  <FlowShell next="gap" back="roles" gear="glasses" split @next="pickRole">
    <template #bubble>Here’s how demand for {{ job?.title ?? 'this role' }} could change over the next year.</template>
    <RoleDetail :onet-code="onetCode" :job="job" compact pick-quarter :skip="skip" @update:skip="setSkip" />
  </FlowShell>
</template>
