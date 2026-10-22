<script setup lang="ts">
import { ref } from 'vue';
import Mascot, { type Mood } from '../components/Mascot.vue';
import { bee, BEES } from '../bee';

const moods: { id: Mood; label: string; note: string }[] = [
  { id: 'idle', label: 'Idle', note: 'Breathes, blinks, eyes follow your cursor' },
  { id: 'wave', label: 'Wave', note: 'Hello! Used on landing and welcome screens' },
  { id: 'happy', label: 'Happy', note: 'Squishy smile for good news' },
  { id: 'thinking', label: 'Thinking', note: 'Looks up, tilts, question mark pops' },
  { id: 'sleepy', label: 'Sleepy', note: 'Eyes closed, floating zzz' },
  { id: 'surprised', label: 'Surprised', note: 'Startled hop with wide eyes' },
  { id: 'celebrate', label: 'Celebrate', note: 'Jumps with confetti on milestones' },
];
const q = new URLSearchParams(location.search).get('bee');
if (q && (BEES as readonly string[]).includes(q)) bee.value = q as typeof bee.value;
const current = ref<Mood>('idle');
const replay = ref(0);
function pick(m: Mood) { current.value = m; replay.value++; }
</script>

<template>
  <main class="pg">
    <h1>Meet Jobee</h1>
    <p class="sub">Seven moods, four bees, all drawn in code.</p>
    <div class="bees"><button v-for="b in BEES" :key="b" class="pillbtn" :class="{ on: bee === b }" @click="bee = b">{{ b }}</button></div>
    <div class="stage"><Mascot :key="replay" :size="220" :mood="current" /></div>
    <div class="grid">
      <button v-for="m in moods" :key="m.id" class="tile" :class="{ on: current === m.id }" @click="pick(m.id)">
        <Mascot :size="64" :mood="m.id" :look="false" />
        <strong>{{ m.label }}</strong>
        <small>{{ m.note }}</small>
      </button>
    </div>
  </main>
</template>

<style scoped>
.bees { display: flex; gap: 10px; justify-content: center; margin: -20px 0 28px; }
.pillbtn { padding: 8px 16px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; font-weight: 900; font-size: 12px; letter-spacing: .06em; text-transform: uppercase; }
.pillbtn.on { background: var(--yellow); border-color: var(--yellow); }
.pg { max-width: 920px; margin: 0 auto; padding: 40px 20px 100px; text-align: center; }
h1 { font-size: 36px; font-weight: 900; }
.sub { color: var(--muted); font-weight: 600; margin: 6px 0 40px; }
.stage { display: grid; place-items: center; height: 340px; background: var(--cream); border-radius: 28px; margin-bottom: 28px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 14px; }
.tile { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 22px 14px; background: #fff; border: 2px solid var(--line-strong); border-radius: 18px; box-shadow: 0 4px 0 var(--line-strong); }
.tile.on { background: var(--cream); border-color: var(--yellow); box-shadow: 0 4px 0 var(--orange); }
.tile strong { font-weight: 900; } .tile small { font-size: 12px; color: var(--muted); font-weight: 600; }
</style>
