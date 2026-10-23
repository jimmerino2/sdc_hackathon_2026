<script setup lang="ts">
import { onMounted, ref } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { fetchInterests, InterestsError, type Interest } from '../api/interests';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { state, key } = useFlow();
const interests = ref<Interest[]>([]);
const status = ref<'loading' | 'done' | 'error'>('loading');
const error = ref('');

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

function toggle(id: number) {
  const idx = state.value.interests.indexOf(id);
  if (idx >= 0) state.value.interests.splice(idx, 1);
  else state.value.interests.push(id);
}

onMounted(load);
</script>

<template>
  <FlowShell :progress="2" next="outcome" back="who" :mood="status === 'error' ? 'surprised' : 'thinking'" :next-disabled="!state.interests.length">
    <template #bubble>{{ status === 'error' ? error : personaCopy[key].interests }}</template>

    <div v-if="status === 'loading'" class="grid" aria-hidden="true">
      <span v-for="n in 8" :key="n" class="skel card tile-skel" />
    </div>

    <div v-else-if="status === 'error'" class="state">
      <button type="button" class="btn btn-secondary retry" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
    </div>

    <template v-else>
      <p id="interests-hint" class="hint">Pick any that fit</p>
      <div class="grid" role="group" aria-describedby="interests-hint">
        <button
          v-for="i in interests"
          :key="i.id"
          type="button"
          class="option tile"
          :class="{ selected: state.interests.includes(i.id) }"
          :aria-pressed="state.interests.includes(i.id)"
          @click="toggle(i.id)"
        >
          <span class="ic" aria-hidden="true"><Icon :name="i.icon" :size="22" /></span>
          <span class="txt">
            <h3>{{ i.interest }}</h3>
          </span>
          <span v-if="state.interests.includes(i.id)" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
        </button>
      </div>
    </template>
  </FlowShell>
</template>

<style scoped>
.hint { font-size: 13px; font-weight: 800; color: var(--muted); margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tile { position: relative; flex-direction: column; justify-content: center; min-height: 112px; padding: 14px 10px; gap: 10px; text-align: center; }
.ic { flex: none; width: 44px; height: 44px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.selected .ic { background: var(--yellow); }
.txt { min-width: 0; }
.tile h3 { font-size: 14px; line-height: 1.25; }
.tick { position: absolute; top: 8px; right: 8px; }
.tile-skel { height: 112px; border-radius: 16px; }
.state { display: flex; justify-content: center; padding: 24px 0; }
.retry { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 420px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
