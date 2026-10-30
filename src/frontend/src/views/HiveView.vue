<script setup lang="ts">
import '../learn.css';
import { onMounted, ref } from 'vue';
import HiveSwitch from '../components/hive/HiveSwitch.vue';
import Robbee from '../components/hive/Robbee.vue';
import Stinger from '../components/hive/Stinger.vue';
import { fetchChallenges } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { useFlow } from '../state';
import { go } from '../router';

/** Protect the Hive: the boss fight where stingers get spent. A placeholder until the fight is specced. */
const { state } = useFlow();
const stingers = ref<number | null>(null);

onMounted(async () => {
  const id = state.value.profileId ?? readProfileId();
  if (!id) return;
  try {
    stingers.value = (await fetchChallenges(id)).stingers;
  } catch {
    // The count is a nicety here; the page stands without it.
  }
});
</script>

<template>
  <div class="tab jb hivepage">
    <header class="hivepage__head">
      <div>
        <h1>Protect the Hive!</h1>
        <p>Team up and spend your stingers to drive Robbee off.</p>
      </div>
      <HiveSwitch current="hive" />
    </header>

    <section class="soon">
      <Robbee :size="200" />
      <div class="soon__copy">
        <span class="soon__tag">Coming soon</span>
        <h2>Robbee is circling the hive</h2>
        <p>The boss fight opens soon. Until then, pass challenge stages to stock up: every pass lands a stinger.</p>
        <span v-if="stingers != null" class="soon__count"><Stinger :size="20" /> {{ stingers }} {{ stingers === 1 ? 'stinger' : 'stingers' }} ready</span>
        <RouterLink :to="go('challenges')" class="soon__cta">Go to challenges</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hivepage { display: flex; flex-direction: column; gap: 24px; max-width: 1600px; }
.hivepage__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.hivepage__head h1 { margin: 0; font-size: 40px; line-height: 48px; font-weight: 900; }
.hivepage__head p { margin: 4px 0 0; color: var(--text-muted); font-size: 16px; font-weight: 600; }
.soon { display: flex; align-items: center; gap: 48px; padding: 48px; border: 2px dashed var(--honey); border-radius: 28px; background: repeating-linear-gradient(-45deg, #fffaf0 0 18px, #fff4d9 18px 36px); }
.soon__copy { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; max-width: 560px; }
.soon__tag { padding: 5px 12px; border-radius: 10px; background: #d32f2f; color: #fff; font-size: 13px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; transform: rotate(-3deg); }
.soon h2 { margin: 0; font-size: 32px; line-height: 38px; font-weight: 900; }
.soon p { margin: 0; color: var(--text-muted); font-size: 16px; line-height: 24px; font-weight: 600; }
.soon__count { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px; background: #1e1e1e; color: #ffc107; font-weight: 900; }
.soon__cta { padding: 14px 24px; border-radius: var(--radius-md); background: var(--honey); color: var(--on-honey); text-decoration: none; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; box-shadow: 0 4px 0 var(--honey-deep); }
@media (max-width: 760px) {
  .soon { flex-direction: column; padding: 28px 20px; gap: 20px; text-align: center; }
  .soon__copy { align-items: center; }
}
</style>
