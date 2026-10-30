<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import Icon from '../components/Icon.vue';
import PollenField from '../components/PollenField.vue';
import { isOnboarded } from '../api/profile';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';
import { formatElapsed, progressAt, useAnalysisClock } from '../composables/useAnalysisClock';
import { pathwayFacts, roleStep, type PathwayStep } from '../data/pathwayFacts';

const EXPECTED_MS = 10_000;
/** When each of the six steps starts, as a fraction of the expected time. */
const STEP_STARTS = [0, 0.08, 0.26, 0.46, 0.64, 0.82];
/** The least time a step stays up once it is active, so a late response doesn't flash through the findings. */
const MIN_STEP_MS = 900;
const TITLES = ['Locked in your role', 'Ranking the skills', 'Grouping into sections and units', 'Setting the order you learn them in', 'Finding learning resources', 'Designing your first project'];

const { state } = useFlow();
const router = useRouter();
const clock = useAnalysisClock(EXPECTED_MS);

const cur = ref(0);
const finished = ref(false);
let lastStep = 0;
let leave: number | undefined;
const items = ref<HTMLElement[]>([]);

const failed = computed(() => state.value.roadmap.status === 'error');
const roadmap = computed(() => (state.value.roadmap.status === 'done' ? state.value.roadmap.data : null));
const roleTitle = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === state.value.chosenRoleId)?.title ?? 'your role');

/** Real once the roadmap is in; until then only the role is known. */
const steps = computed<PathwayStep[]>(() => {
  if (roadmap.value) return pathwayFacts(roadmap.value);
  return [roleStep(roleTitle.value, state.value.chosenRoleId ?? ''), ...TITLES.slice(1).map((title) => ({ title, what: '', why: '', found: [], summary: '' }))];
});
const known = (i: number) => i === 0 || !!roadmap.value;

const timeStep = computed(() => STEP_STARTS.reduce((s, start, i) => (clock.f.value >= start ? i : s), 0));
const stateOf = (i: number) => (finished.value || i < cur.value ? 'done' : i === cur.value ? 'active' : 'pending');
const pct = computed(() => Math.round((finished.value ? 1 : progressAt(clock.f.value, 2.6)) * 100));
const late = computed(() => clock.slow.value && !finished.value && !failed.value);

// Steps follow the clock, but past the first one they wait for the roadmap, since they show what is in it.
watch([clock.elapsed, roadmap], () => {
  if (finished.value || failed.value) return;
  const target = roadmap.value ? timeStep.value : 0;
  const now = Date.now();
  if (cur.value < target && now - lastStep >= MIN_STEP_MS) {
    cur.value++;
    lastStep = now;
    nextTick(() => items.value[cur.value]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }));
  } else if (roadmap.value && cur.value >= steps.value.length - 1 && now - lastStep >= MIN_STEP_MS) {
    finished.value = true;
    clock.stop();
    leave = window.setTimeout(() => router.push(go('pathway')), 900);
  }
});
watch(failed, (bad) => bad && clock.stop());

/** Builds the roadmap if it isn't there yet; the steps then play out from what comes back. */
function start() {
  clearTimeout(leave);
  cur.value = 0;
  finished.value = false;
  lastStep = Date.now();
  clock.start();
  loadRoadmap(state.value);
}

onMounted(start);
onBeforeUnmount(() => clearTimeout(leave));
</script>

<template>
  <div class="page">
    <div class="stack">
      <PollenField />
      <div class="progress" :class="{ bad: failed, slow: late }" role="progressbar" aria-label="Building your roadmap" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="pct">
        <i :style="{ width: pct + '%' }" />
      </div>
      <div class="meta">
        <span>{{ formatElapsed(clock.elapsed.value) }}</span>
        <span v-if="failed" class="bad" role="alert">{{ state.roadmap.error }}</span>
        <span v-else>{{ finished ? 'Done' : late ? 'Taking a little longer than usual…' : 'Usually about 10 seconds' }}</span>
      </div>

      <ol class="steps" aria-live="polite">
        <li v-for="(step, i) in steps" :key="step.title" :ref="(el) => (items[i] = el as HTMLElement)" class="card step" :data-s="failed && stateOf(i) === 'active' ? 'pending' : stateOf(i)">
          <span class="dot"><Icon name="check" :size="14" :stroke="3.4" /></span>
          <div>
            <h3>{{ step.title }}</h3>
            <p v-if="stateOf(i) === 'done' && known(i)" class="sum">{{ step.summary }}</p>
            <div v-else-if="stateOf(i) === 'active' && known(i)" class="det">
              <p>{{ step.what }}</p>
              <p class="why">{{ step.why }}</p>
              <ul>
                <li v-for="(f, k) in step.found.slice(0, 3)" :key="f" :style="{ '--i': k }">{{ f }}</li>
              </ul>
            </div>
          </div>
        </li>
      </ol>

      <div v-if="failed" class="actions">
        <button type="button" class="btn btn-secondary" @click="start"><Icon name="refresh" :size="18" /> Try again</button>
        <RouterLink :to="go(isOnboarded() ? 'suggested' : 'signal')" class="back">Back</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; padding: 32px 16px 48px; }
.stack { width: 100%; max-width: 680px; margin: auto 0; }
.stack :deep(.fpv) { margin-bottom: 14px; }
.progress { width: 100%; height: 14px; }
.progress.bad > i { background: #e8b4ae; }
.progress.slow > i { animation: breathe 1.4s ease-in-out infinite; }
.meta { display: flex; justify-content: space-between; gap: 12px; margin: 8px 0 16px; font-size: 12px; line-height: 16px; font-weight: 700; color: var(--muted); }
.meta .bad { color: #b3261e; text-align: right; }

.steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.step { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 12px; padding: 14px 16px; transition: opacity .26s, background .26s, border-color .26s; }
.step[data-s='pending'] { opacity: .55; }
.step[data-s='active'] { border-color: var(--yellow); background: #fff8e1; box-shadow: 0 8px 24px rgba(30, 30, 30, .08); }
h3 { margin: 0; font-size: 17px; line-height: 26px; font-weight: 900; }
.dot { position: relative; width: 24px; height: 24px; margin-top: 1px; border-radius: 50%; border: 3px solid var(--line-strong); display: grid; place-items: center; color: var(--yellow); transition: background .26s, border-color .26s; }
.dot svg { display: none; }
[data-s='active'] .dot { border-color: var(--line); border-top-color: var(--yellow); animation: spin .8s linear infinite; }
[data-s='done'] .dot { background: var(--ink); border-color: var(--ink); animation: pop .5s cubic-bezier(.34, 1.56, .64, 1); }
[data-s='done'] .dot svg { display: block; }

.sum { margin: 2px 0 0; font-size: 13px; line-height: 19px; font-weight: 700; color: var(--muted); animation: swap .4s ease-out both; }
.det { animation: swap .45s ease-out both; }
.det p { margin: 4px 0 0; font-size: 14px; line-height: 21px; font-weight: 600; }
.det .why { color: var(--muted); }
.det ul { margin: 12px 0 0; padding: 0; list-style: none; display: grid; gap: 7px; }
.det li { display: flex; gap: 9px; font-size: 13px; line-height: 19px; font-weight: 800; opacity: 0; animation: swap .45s ease-out forwards; animation-delay: calc(var(--i) * 700ms + 500ms); }
.det li::before { content: ''; flex: none; width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; background: var(--yellow); }

.actions { display: flex; flex-direction: column; align-items: center; gap: 14px; margin-top: 20px; }
.btn { gap: 8px; }
.back { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.back:hover { color: var(--ink); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pop { 0% { transform: scale(.4); } 60% { transform: scale(1.12); } }
@keyframes swap { from { opacity: 0; transform: translateY(8px); } }
@keyframes breathe { 50% { opacity: .6; } }
@media (prefers-reduced-motion: reduce) { .dot, .sum, .det, .det li, .progress.slow > i { animation: none !important; } .det li { opacity: 1; } }
</style>
