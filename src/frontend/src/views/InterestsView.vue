<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import InterestPicker from '../components/InterestPicker.vue';
import InterestSdgPanel from '../components/InterestSdgPanel.vue';
import { fetchInterests, InterestsError, MAX_INTERESTS, type Interest } from '../api/interests';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { state, key } = useFlow();
const interests = ref<Interest[]>([]);
const status = ref<'loading' | 'done' | 'error'>('loading');
const error = ref('');
const side = ref<HTMLElement | null>(null);

/** The latest pick, whose goals are on show. */
const latest = computed(() => interests.value.find((i) => i.id === state.value.interests.at(-1)) ?? null);

// The panel sits under the tiles on small screens, so bring it into view on a new pick
watch(() => state.value.interests.length, async (now, before) => {
  if (now <= before) return;
  await nextTick();
  const motion = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  side.value?.scrollIntoView({ block: 'nearest', behavior: motion });
});

async function load() {
  status.value = 'loading';
  try {
    interests.value = await fetchInterests();
    status.value = 'done';
  } catch (e) {
    error.value = e instanceof InterestsError ? e.message : 'Jobee couldn’t load the interests just now. Try again in a moment.';
    status.value = 'error';
  }
}

onMounted(() => {
  // Picks saved before the limit existed
  if (state.value.interests.length > MAX_INTERESTS) state.value.interests = state.value.interests.slice(0, MAX_INTERESTS);
  load();
});
</script>

<template>
  <FlowShell :progress="2" next="resume" back="who" wide :mood="status === 'error' ? 'surprised' : 'thinking'" :next-disabled="!state.interests.length">
    <template #bubble>{{ status === 'error' ? error : personaCopy[key].interests }}</template>

    <div v-if="status === 'loading'" class="grid" aria-hidden="true">
      <span v-for="n in 8" :key="n" class="skel card tile-skel" />
    </div>

    <div v-else-if="status === 'error'" class="state">
      <button type="button" class="btn btn-secondary retry" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
    </div>

    <div v-else class="layout">
      <div class="picks"><InterestPicker v-model="state.interests" :interests="interests" hint-id="interests-hint" /></div>
      <aside ref="side" class="side"><InterestSdgPanel :interest="latest" /></aside>
    </div>
  </FlowShell>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tile-skel { height: 112px; border-radius: 16px; }
.state { display: flex; justify-content: center; padding: 24px 0; }
.retry { display: inline-flex; align-items: center; gap: 8px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 520px); gap: 48px; align-items: start; }
.side { position: sticky; top: 0; scroll-margin: 16px; }
@media (max-width: 1040px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .side { position: static; }
}
@media (max-width: 420px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
