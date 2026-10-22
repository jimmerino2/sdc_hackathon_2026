<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import Icon from '../components/Icon.vue';
import PollenField from '../components/PollenField.vue';
import { isOnboarded } from '../api/profile';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state } = useFlow();
const router = useRouter();
const stage = ref(0);
let timer: number | undefined;

const roleTitle = computed(
  () => state.value.jobs.data?.jobs.find((j) => j.onet_code === state.value.chosenRoleId)?.title ?? 'your role',
);
const items = computed(() => [
  state.value.email ? `Synced ${state.value.email}` : 'Saved your profile',
  `Locked in ${roleTitle.value}`,
  'Grouping the key skills into sections and units',
  'Setting the order you’ll learn them in',
]);
const failed = computed(() => state.value.roadmap.status === 'error');

/** The last step waits on the real work (building the roadmap), so the pathway opens ready. */
function start() {
  stage.value = 0;
  clearInterval(timer);
  timer = window.setInterval(() => {
    if (stage.value < items.value.length - 1) stage.value++;
    else if (state.value.roadmap.status === 'done') {
      clearInterval(timer);
      stage.value = items.value.length;
      router.push(go('pathway'));
    } else if (failed.value) clearInterval(timer);
  }, 1400);
  loadRoadmap(state.value);
}

onMounted(start);
onBeforeUnmount(() => clearInterval(timer));

const pct = computed(() => Math.round(Math.min(100, 12 + (stage.value * 88) / items.value.length)));
const status = computed(() => (failed.value ? state.value.roadmap.error : items.value[Math.min(stage.value, items.value.length - 1)]));
</script>

<template>
  <div class="page">
    <div class="stack">
      <PollenField />
      <div class="progress" :class="{ bad: failed }" role="progressbar" aria-label="Building your roadmap" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="pct"><i :style="{ width: pct + '%' }" /></div>
      <p class="status" :class="{ bad: failed }" :role="failed ? 'alert' : 'status'" aria-live="polite">
        <Transition name="swap" mode="out-in"><span :key="status ?? ''">{{ status }}</span></Transition>
      </p>
      <button v-if="failed" type="button" class="btn btn-secondary" @click="start"><Icon name="refresh" :size="18" /> Try again</button>
      <RouterLink v-if="failed" :to="go(isOnboarded() ? 'suggested' : 'signal')" class="back">Back</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px 20px; }
.stack { width: 100%; max-width: 440px; display: flex; flex-direction: column; align-items: center; }
.stack :deep(.fpv) { margin-bottom: 28px; }
.progress { width: 100%; height: 14px; margin-bottom: 18px; }
.progress.bad > i { background: #e8b4ae; }
.status { min-height: 2.8em; text-align: center; font-weight: 800; font-size: 17px; line-height: 1.4; color: var(--ink); }
.status.bad { color: #b3261e; margin-bottom: 16px; }
.btn { gap: 8px; }
.swap-enter-active, .swap-leave-active { transition: opacity .2s ease, transform .2s ease; }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }
.back { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.back:hover { color: var(--ink); }
</style>
