<script setup lang="ts">
import { computed } from 'vue';
import type { Interest } from '../api/interests';
import { INTEREST_SDGS, SDG_GOALS } from '../data/interestSdgs';

/** The SDGs behind one interest: icon, title and targets, each in the goal's own colour. */
const props = defineProps<{ interest: Interest | null }>();
const base = import.meta.env.BASE_URL;

// An interest with no written targets still shows the goals it's tied to
const goals = computed(() => {
  const i = props.interest;
  if (!i) return [];
  return (INTEREST_SDGS[i.interest] ?? i.sdg.map((w) => ({ sdg: w.sdg, targets: [] })))
    .filter((g) => SDG_GOALS[g.sdg])
    .map((g) => ({ ...g, ...SDG_GOALS[g.sdg] }));
});
</script>

<template>
  <section class="panel card" aria-live="polite">
    <template v-if="interest">
      <h2>{{ interest.interest }}</h2>
      <ul class="goals">
        <li v-for="g in goals" :key="g.sdg" class="goal" :style="{ color: g.color }">
          <img :src="`${base}sdg/goal-${String(g.sdg).padStart(2, '0')}.jpg`" :alt="`UN Sustainable Development Goal ${g.sdg}: ${g.title}`" width="64" height="64" loading="lazy" />
          <div class="body">
            <h3>SDG {{ g.sdg }}: {{ g.title }}</h3>
            <ul v-if="g.targets.length" class="targets">
              <li v-for="t in g.targets" :key="t.code"><b>{{ t.code }}</b> {{ t.text }}</li>
            </ul>
          </div>
        </li>
      </ul>
    </template>
    <p v-else class="empty">Pick an interest to see the global goals it connects to.</p>
  </section>
</template>

<style scoped>
.panel { padding: 24px; }
h2 { font-size: 26px; font-weight: 900; line-height: 1.2; margin-bottom: 14px; }
.goals, .targets { list-style: none; }
.goals { display: flex; flex-direction: column; gap: 16px; }
.goal { display: flex; align-items: flex-start; gap: 12px; }
.goal img { flex: none; width: 64px; height: 64px; border-radius: 10px; }
.body { min-width: 0; }
h3 { font-size: 21px; font-weight: 800; line-height: 1.25; }
.targets { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; font-size: 18px; font-weight: 600; line-height: 1.35; }
.targets b { font-weight: 800; }
.empty { font-size: 20px; font-weight: 700; line-height: 1.3; color: var(--muted); text-align: center; padding: 28px 8px; }
</style>
