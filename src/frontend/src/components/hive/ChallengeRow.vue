<script setup lang="ts">
import { computed } from "vue";
import Icon from "../Icon.vue";
import AiAssist from "./AiAssist.vue";
import ChallengeDetail from "./ChallengeDetail.vue";
import Stinger from "./Stinger.vue";
import type { RoadmapChallenge } from "../../api/roadmap";

/** One roadmap's challenge in the list: its stage tracker and next action; opens into the full brief and repo form. */
const base = import.meta.env.BASE_URL;
const props = defineProps<{ challenge: RoadmapChallenge; open: boolean; busy?: boolean; error?: string | null }>();
const emit = defineEmits<{ toggle: []; submit: [repoUrl: string]; advance: []; share: [] }>();

const c = computed(() => props.challenge);
const pts = (n: number | null | undefined) => (n == null ? null : Math.round(n));
const passed = computed(() => c.value.status === "passed" || c.value.status === "advancing");
/** Stage 2 passed. It stays complete through resubmits, even one that scores lower. */
const complete = computed(() => c.value.stage === 2 && !!c.value.completed_at);
/** Stage 1 passed and waiting for Robbee's rewrite. */
const twistDue = computed(() => c.value.stage === 1 && passed.value);

type Dot = { state: "current" | "done" | "hidden"; label: string };
const dots = computed<[Dot, Dot]>(() => {
  const last = pts(c.value.score);
  if (c.value.stage === 1) {
    const one: Dot = passed.value
      ? { state: "done", label: `Passed · ${last}` }
      : { state: "current", label: last != null ? `Last · ${last}` : "Stage 1" };
    return [one, { state: "hidden", label: "Hidden" }];
  }
  const first = pts(c.value.history[0]?.score);
  return [
    { state: "done", label: first != null ? `Passed · ${first}` : "Passed" },
    complete.value
      ? { state: "done", label: `${(last ?? 0) >= c.value.pass_score ? "Passed" : "Latest"} · ${last}` }
      : { state: "current", label: last != null ? `Last · ${last}` : "Robbee twist" },
  ];
});

const state = computed(() => (c.value.stage === 2 && !complete.value ? "twist" : complete.value ? "done" : "open"));
const meta = computed(() => `${c.value.role_title} · ${complete.value ? "Complete" : `Stage ${c.value.stage} of 2`}`);
</script>

<template>
  <section :id="`challenge-${c.challenge_id}`" class="crow" :data-state="state">
    <div class="crow__main">
      <button
        type="button"
        class="crow__head"
        :aria-expanded="open"
        :aria-controls="`challenge-body-${c.challenge_id}`"
        @click="emit('toggle')"
      >
        <span class="crow__disc"
          ><img
            :src="`${base}sdg/goal-${String(c.sdg).padStart(2, '0')}.jpg`"
            :alt="`UN Sustainable Development Goal ${c.sdg}: ${c.sdg_name}`"
            width="56"
            height="56"
        /></span>
        <span class="crow__label">
          <span class="crow__eyebrow">Challenge · SDG {{ c.sdg }} {{ c.sdg_name }}</span>
          <span class="crow__title">{{ c.title }}</span>
          <span class="crow__meta">{{ meta }}</span>
        </span>
      </button>

      <ol class="crow__track" aria-label="Stages">
        <li v-for="(d, i) in dots" :key="i" class="crow__stage" :data-dot="d.state">
          <span class="crow__dot">
            <Icon v-if="d.state === 'done'" name="check" :size="14" />
            <Icon v-else-if="d.state === 'hidden'" name="lock" :size="14" />
            <template v-else>{{ i + 1 }}</template>
          </span>
          <span class="crow__dlabel">{{ d.label }}</span>
        </li>
      </ol>

      <div class="crow__act">
        <button
          v-if="complete"
          type="button"
          class="crow__earned"
          :aria-expanded="open"
          :title="open ? 'Close' : 'Open to resubmit'"
          @click="emit('toggle')"
        >
          <Stinger :size="18" /><Stinger :size="18" /> 2 stingers
        </button>
        <button v-if="complete" type="button" class="crow__share" @click="emit('share')">Create LinkedIn post</button>
        <button v-else-if="twistDue" type="button" class="crow__btn crow__btn--alert" @click="emit('advance')">
          See round 2: add AI
        </button>
        <button
          v-else
          type="button"
          class="crow__fold"
          :class="{ open }"
          :aria-expanded="open"
          :aria-label="`${open ? 'Close' : 'Open'} ${c.title}`"
          @click="emit('toggle')"
        >
          <Icon name="chevron" :size="22" />
        </button>
      </div>
    </div>

    <div v-if="c.stage === 2 && !complete && c.twist" class="crow__twist">
      <Stinger :size="20" />
      <p>
        <b>Robbee changed the brief, you'll need to use AI to solve this.</b>{{ c.twist }} Score {{ c.pass_score }}+
        again to earn another stinger.
      </p>
    </div>

    <ChallengeDetail
      v-if="open"
      :id="`challenge-body-${c.challenge_id}`"
      :challenge="c"
      :busy="busy"
      :error="error"
      @submit="(u) => emit('submit', u)"
    />
    <AiAssist v-if="open" class="crow__assist" :challenge="c" />
  </section>
</template>

<style scoped>
.crow {
  overflow: hidden;
  border: 2px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface-raised);
  animation: jb-rise var(--dur-slow) var(--ease-out) both;
}
.crow[data-state="twist"] {
  border-color: var(--pop-orange);
}
.crow__main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 24px;
  padding: 18px 26px 18px 0;
}
.crow__head {
  display: flex;
  align-items: center;
  gap: 22px;
  min-width: 0;
  padding: 4px 0 4px 26px;
  border: 0;
  background: none;
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.crow__head:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: -3px;
  border-radius: var(--radius-md);
}
.crow__disc {
  flex: none;
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--honey);
  transition: transform var(--dur-fast) var(--ease-bounce);
}
.crow__disc img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.crow__head:hover .crow__disc {
  transform: rotate(-8deg);
}
.crow__label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.crow__eyebrow {
  font-size: 13px;
  line-height: 18px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--honey-deep);
}
.crow__title {
  font-size: 24px;
  line-height: 31px;
  font-weight: 900;
}
.crow__meta {
  font-size: 15px;
  line-height: 21px;
  font-weight: 600;
  color: var(--text-muted);
}

.crow__track {
  display: flex;
  align-items: flex-start;
  margin: 0;
  padding: 0;
  list-style: none;
}
.crow__stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 90px;
}
.crow__stage + .crow__stage::before {
  content: "";
  position: absolute;
  top: 14px;
  right: 60%;
  width: 76px;
  height: 3px;
  border-radius: 2px;
  background: var(--line);
}
.crow__stage[data-dot="done"] + .crow__stage[data-dot="done"]::before,
.crow__stage[data-dot="done"] + .crow__stage[data-dot="current"]::before {
  background: #2e7d4f;
}
.crow__dot {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 15px;
  font-weight: 900;
}
[data-dot="current"] .crow__dot {
  background: var(--honey);
  color: var(--on-honey);
}
[data-dot="done"] .crow__dot {
  background: #2e7d4f;
  color: #fff;
}
[data-dot="hidden"] .crow__dot {
  border: 2px solid var(--locked-edge);
  background: var(--surface-raised);
  color: var(--locked-icon);
}
.crow__dlabel {
  font-size: 14px;
  line-height: 18px;
  font-weight: 700;
  color: var(--text-muted);
  white-space: nowrap;
}

.crow__act {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.crow__share {
  width: 100%;
  padding: 9px 16px;
  border: 2px solid var(--line-strong);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  color: var(--text);
  font: inherit;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background var(--dur-fast);
}
.crow__share:hover {
  background: var(--honey-tint);
}
.crow__share:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.crow__fold {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text-muted);
  transition:
    color var(--dur-fast),
    background var(--dur-fast);
}
.crow__fold:hover {
  color: var(--text);
  background: var(--honey-tint);
}
.crow__fold svg {
  transition: transform var(--dur-base) var(--ease-out);
}
.crow__fold.open svg {
  transform: rotate(180deg);
}
.crow__fold:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.crow__btn {
  padding: 13px 18px;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--honey);
  color: var(--on-honey);
  font: inherit;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: 0 4px 0 var(--honey-deep);
  transition:
    transform var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}
.crow__btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 0 var(--honey-deep);
}
.crow__btn:active {
  transform: translateY(3px);
  box-shadow: 0 1px 0 var(--honey-deep);
}
.crow__btn:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.crow__btn--alert {
  background: #d32f2f;
  color: #fff;
  box-shadow: 0 4px 0 #8e1c1c;
  animation: crow-pulse 1.4s ease-in-out infinite;
}
.crow__btn--alert:hover {
  box-shadow: 0 6px 0 #8e1c1c;
}
.crow__earned {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  padding: 11px 16px;
  border: 2px solid var(--honey);
  border-radius: var(--radius-md);
  background: var(--honey-tint);
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.crow__earned {
  color: var(--text);
  font-family: inherit;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out);
}
.crow__earned:hover {
  background: #ffe39a;
}
.crow__earned:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.crow__earned :deep(svg:nth-of-type(2)) {
  margin-right: 6px;
}

.crow__twist {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 26px;
  border-top: 2px solid var(--pop-orange);
  background: #ffe7cc;
  color: var(--pop-orange);
}
.crow__twist p {
  margin: 0;
  color: var(--text);
  font-size: 16px;
  line-height: 23px;
  font-weight: 600;
}
.crow__twist b {
  display: block;
  color: #d9580a;
  font-size: 16px;
  font-weight: 900;
}
.crow :deep(.jb-quest__body) {
  border-top: 2px solid var(--line);
}
.crow__assist {
  margin: 0 22px 18px;
}

@keyframes crow-pulse {
  50% {
    filter: brightness(1.15);
  }
}
@media (prefers-reduced-motion: reduce) {
  .crow,
  .crow__btn--alert {
    animation: none;
  }
}
@media (max-width: 1100px) {
  .crow__main {
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 16px 18px 16px 0;
    row-gap: 14px;
  }
  .crow__act {
    align-items: flex-end;
  }
  .crow__head {
    padding-left: 18px;
    grid-column: 1 / -1;
  }
  .crow__track {
    padding-left: 18px;
  }
}
@media (max-width: 760px) {
  .crow__assist {
    margin: 0 16px 16px;
  }
}
@media (max-width: 560px) {
  .crow__main {
    grid-template-columns: 1fr;
  }
  .crow__head {
    gap: 14px;
  }
  .crow__disc {
    width: 44px;
    height: 44px;
  }
  .crow__title {
    font-size: 20px;
    line-height: 26px;
  }
  .crow__act {
    padding-left: 18px;
    align-items: flex-start;
  }
  .crow__twist {
    padding: 12px 18px;
  }
}
</style>
