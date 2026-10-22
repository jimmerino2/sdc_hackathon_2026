<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import Icon from '../components/Icon.vue';
import Mascot from '../components/Mascot.vue';
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
</script>

<template>
  <div class="page">
    <div class="halo"><Mascot :size="100" class="m" mood="thinking" /></div>
    <h1>Building your roadmap…</h1>
    <p class="sub">Jobee is planning your path to {{ roleTitle }}. This can take up to half a minute.</p>
    <div class="progress"><i :style="{ width: Math.min(100, 12 + (stage * 88) / items.length) + '%' }" /></div>
    <ul class="card">
      <li v-for="(t, i) in items" :key="t" :class="{ done: i < stage, now: i === stage, wait: i > stage, bad: failed && i === stage }">
        <span class="dot"><Icon v-if="i <= stage" :name="i < stage ? 'check' : failed ? 'x' : 'sparkles'" :size="13" :stroke="3" /></span>
        {{ t }}
      </li>
    </ul>
    <div v-if="failed" class="fail" role="alert">
      <p>{{ state.roadmap.error }}</p>
      <button type="button" class="btn btn-secondary" @click="start"><Icon name="refresh" :size="18" /> Try again</button>
      <RouterLink :to="go(isOnboarded() ? 'suggested' : 'signal')" class="back">Back</RouterLink>
    </div>
    <div v-else class="know">
      <small>Did you know?</small>
      <p>Your roadmap starts with the skills everything else builds on, so each step unlocks the next.</p>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; max-width: 400px; margin: 0 auto; padding: 60px 20px; display: flex; flex-direction: column; align-items: center; }
.halo { width: 150px; height: 150px; border-radius: 50%; background: var(--cream); display: grid; place-items: center; margin-bottom: 28px; animation: float 2.4s ease-in-out infinite; }
@keyframes float { 50% { transform: translateY(-8px); } }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 8px; } .sub { color: var(--muted); font-weight: 600; font-size: 14px; margin-bottom: 24px; }
.progress { width: 100%; height: 12px; margin-bottom: 20px; }
ul { list-style: none; width: 100%; padding: 12px 20px; display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }
li { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 14px; }
.dot { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; flex: none; border: 2px solid var(--line-strong); }
.done .dot { background: var(--ink); color: var(--yellow); border-color: var(--ink); }
.now .dot { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.wait { color: var(--muted); }
.know { width: 100%; background: var(--cream); border-radius: 16px; padding: 14px 18px; }
.know small { font-size: 10px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.know p { font-weight: 800; font-size: 14px; line-height: 1.4; margin-top: 4px; }
.bad .dot { background: #fdecea; border-color: #b3261e; color: #b3261e; }
.fail { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 14px; }
.fail p { width: 100%; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; line-height: 1.4; }
.fail .btn { display: inline-flex; align-items: center; gap: 8px; }
.back { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.back:hover { color: var(--ink); }
</style>
