<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import RoleDetail from '../components/RoleDetail.vue';
import { SOFTWARE_DEVELOPERS_ONET } from '../api/forecast';
import { useFlow } from '../state';

const route = useRoute();
const { state } = useFlow();
/** The role to show: ?role= from the roles page, else the chosen role, else Software Developers. */
const onetCode = computed(() => (route.query.role as string | undefined) ?? state.value.chosenRoleId ?? SOFTWARE_DEVELOPERS_ONET);
/** This role's match from the roles page: skills the user has and still needs. Missing after a refresh. */
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === onetCode.value));
</script>

<template>
  <FlowShell :progress="5" next="sync" next-label="Build my pathway" back="roles" gear="glasses" wide @next="state.chosenRoleId = onetCode">
    <template #bubble>How could AI change demand for {{ job?.title ?? 'this role' }}?</template>
    <RoleDetail :onet-code="onetCode" :job="job" compact />
  </FlowShell>
</template>
