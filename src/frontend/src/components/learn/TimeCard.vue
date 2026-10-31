<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import InfoDialog from '../InfoDialog.vue';
import { DEFAULT_HOURS_PER_WEEK, formatMinutes, MAX_HOURS_PER_WEEK, MIN_HOURS_PER_WEEK, weeksFor } from '../../learn/time';

/** How long is left on the roadmap, and what that means at the learner's own pace. */
const props = defineProps<{ minutesLeft: number; statedSteps: number; estimatedSteps: number }>();

const KEY = 'jobee:hoursPerWeek';
function stored(): number {
  try {
    const n = Number(localStorage.getItem(KEY));
    return n >= MIN_HOURS_PER_WEEK && n <= MAX_HOURS_PER_WEEK ? n : DEFAULT_HOURS_PER_WEEK;
  } catch {
    return DEFAULT_HOURS_PER_WEEK;
  }
}
const hours = ref(stored());
watch(hours, (h) => {
  try {
    localStorage.setItem(KEY, String(h));
  } catch {
    // Not fatal: the pace just isn't remembered.
  }
});
const weeks = computed(() => weeksFor(props.minutesLeft, hours.value));
const step = (d: number) => { hours.value = Math.min(MAX_HOURS_PER_WEEK, Math.max(MIN_HOURS_PER_WEEK, hours.value + d)); };
</script>

<template>
  <section class="jb jb-card time">
    <div class="jb-card__head">
      <p class="jb-eyebrow">Time left</p>
      <InfoDialog title="How we estimate time">
        <p>Each step shows how long it should take. Some come straight from the course or video page, which states its own length. The rest use our own formula, so they are estimates.</p>
        <ul>
          <li><b>{{ statedSteps }} {{ statedSteps === 1 ? 'step' : 'steps' }}</b>: the length is stated by the first resource that gives one (at least an hour; a short clip doesn’t teach a skill).</li>
          <li><b>{{ estimatedSteps }} {{ estimatedSteps === 1 ? 'step' : 'steps' }}</b>: our formula, a base time for the kind of resource (build a project, take a course, watch a video, practise) × how deep the skill is for the role.</li>
        </ul>
        <p class="muted">Skills you already have count as done, so they add no time. The weeks depend on how many hours a week you choose.</p>
      </InfoDialog>
    </div>
    <h3 class="jb-card__title">{{ minutesLeft > 0 ? `About ${formatMinutes(minutesLeft)}` : 'Nothing left' }}</h3>
    <p v-if="minutesLeft > 0" class="jb-card__meta">
      About {{ weeks }} {{ weeks === 1 ? 'week' : 'weeks' }} at
      <span class="pace">
        <button type="button" class="pm" aria-label="Fewer hours a week" :disabled="hours <= MIN_HOURS_PER_WEEK" @click="step(-1)">−</button>
        <b>{{ hours }}</b> h
        <button type="button" class="pm" aria-label="More hours a week" :disabled="hours >= MAX_HOURS_PER_WEEK" @click="step(1)">+</button>
      </span>
      a week
    </p>
    <p class="jb-card__meta small">{{ statedSteps }} from course pages · {{ estimatedSteps }} our estimate</p>
  </section>
</template>

<style scoped>
.time .small { margin-top: 4px; font-size: 12px; opacity: .8; }
.pace { display: inline-flex; align-items: center; gap: 4px; margin: 0 2px; }
.pm { width: 22px; height: 22px; border-radius: 50%; border: 2px solid var(--line-strong); background: #fff; font-weight: 900; line-height: 1; }
.pm:disabled { opacity: .4; }
</style>
