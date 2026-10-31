<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Mascot from '../Mascot.vue';
import type { BeeName } from '../../bee';
import Robbee from './Robbee.vue';
import Stinger from './Stinger.vue';

/**
 * The full-screen moments of a challenge, on a tilted hazard-taped band:
 * warning (Robbee attacks after a stage 1 pass) -> assessing (stage 2 is being written) -> rewritten (the new brief),
 * patched (stage 2 passed), and defeated (the party killed Robbee: one bee per party member, 1 to 4).
 */
export type HivePhase = 'warning' | 'assessing' | 'rewritten' | 'patched' | 'defeated';

/** awarded: this pass paid a stinger (false for a resubmitted, already-complete challenge). */
const props = defineProps<{
  phase: HivePhase; title: string; twist?: string | null; stingers: number; awarded?: boolean; error?: string | null;
  /** defeated: the party's bees, and the kill pollen the learner is paid (0 if they didn't sting). */
  party?: { name: string; bee: string }[]; reward?: number;
}>();

/** Where each bee of a party of 1 to 4 flies, as percentages of the crew box. */
const SPOTS: Record<number, [number, number][]> = {
  1: [[50, 24]],
  2: [[30, 24], [72, 34]],
  3: [[18, 34], [50, 14], [82, 34]],
  4: [[14, 38], [38, 14], [62, 14], [86, 38]],
};
const crew = computed(() => {
  const members = (props.party ?? []).slice(0, 4);
  const spots = SPOTS[members.length] ?? [];
  return members.map((m, i) => ({ ...m, x: spots[i][0], y: spots[i][1], delay: i * 0.18 }));
});
const emit = defineEmits<{ close: []; start: []; retry: []; share: [] }>();

const DAMAGE = ['Robbee is reading your repo…', 'Counting the dents in the hive…', 'Calling the client…', 'Rewriting your brief…'];
const line = ref(0);
let timer: number | undefined;
watch(() => props.phase, (p) => {
  clearInterval(timer);
  line.value = 0;
  if (p === 'assessing') timer = window.setInterval(() => (line.value = (line.value + 1) % DAMAGE.length), 2600);
}, { immediate: true });

/** Worried bees around the band while Robbee attacks. */
const bees = [
  { left: '10%', top: '10%', size: 84, delay: 0 },
  { left: '84%', top: '7%', size: 74, delay: 0.15 },
  { left: '4%', top: '78%', size: 80, delay: 0.3 },
  { left: '86%', top: '74%', size: 88, delay: 0.1 },
  { left: '47%', top: '86%', size: 64, delay: 0.25 },
];

const primary = ref<HTMLButtonElement | null>(null);
watch(() => [props.phase, props.error], () => nextTick(() => primary.value?.focus()));
const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') emit('close'); };
onMounted(() => { window.addEventListener('keydown', onKey); nextTick(() => primary.value?.focus()); });
onBeforeUnmount(() => { window.removeEventListener('keydown', onKey); clearInterval(timer); });

const nf = new Intl.NumberFormat('en');

const label = computed(() => ({
  warning: 'Warning: a boss has entered the hive',
  assessing: 'Assessing the damage',
  rewritten: `Project rewritten: ${props.title}`,
  patched: `Hive patched: ${props.title}`,
  defeated: 'Hive protected: Robbee was defeated',
})[props.phase]);
</script>

<template>
  <Teleport to="body">
    <div class="jb hive" :data-phase="phase" role="dialog" aria-modal="true" :aria-label="label">
      <div class="hive__dim" @click="emit('close')" />

      <template v-if="phase === 'warning'">
        <span v-for="(b, i) in bees" :key="i" class="hive__bee" :style="{ left: b.left, top: b.top, animationDelay: b.delay + 's' }">
          <Mascot :size="b.size" mood="surprised" bee="Libbee" :look="false" />
        </span>
      </template>

      <div class="hive__band" :key="phase">
        <!-- Robbee attacks -->
        <div v-if="phase === 'warning'" class="hive__warn" aria-live="assertive">
          <div class="hive__row">
            <svg class="hive__siren" viewBox="0 0 64 64" aria-hidden="true"><path d="M32 4v8M10 14l6 6M54 14l-6 6M2 34h8M62 34h-8" stroke="#ffc107" stroke-width="5" stroke-linecap="round" /><path d="M14 52V38a18 18 0 0 1 36 0v14Z" fill="#e53935" stroke="#7a0f0f" stroke-width="3" /><path d="M24 44V38a8 8 0 0 1 8-8" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" opacity=".8" /><rect x="8" y="52" width="48" height="9" rx="3" fill="#1e1e1e" /></svg>
            <span class="hive__word">Warning</span>
            <svg class="hive__siren" viewBox="0 0 64 64" aria-hidden="true"><path d="M32 4v8M10 14l6 6M54 14l-6 6M2 34h8M62 34h-8" stroke="#ffc107" stroke-width="5" stroke-linecap="round" /><path d="M14 52V38a18 18 0 0 1 36 0v14Z" fill="#e53935" stroke="#7a0f0f" stroke-width="3" /><path d="M24 44V38a8 8 0 0 1 8-8" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" opacity=".8" /><rect x="8" y="52" width="48" height="9" rx="3" fill="#1e1e1e" /></svg>
          </div>
          <span class="hive__word hive__word--gold">Warning</span>
          <span class="hive__sub">A boss has entered the hive</span>
        </div>

        <!-- stage 2 is being written -->
        <div v-else-if="phase === 'assessing'" class="hive__pair" aria-live="polite">
          <Robbee :size="170" />
          <div class="hive__copy">
            <span class="hive__tag hive__tag--gold">Damage report</span>
            <span class="hive__title hive__title--light">Assessing the damage</span>
            <template v-if="!error">
              <span class="hive__dots" aria-hidden="true"><i /><i /><i /></span>
              <span class="hive__lead hive__lead--light">{{ DAMAGE[line] }}</span>
            </template>
            <template v-else>
              <span class="hive__lead hive__lead--light" role="alert">{{ error }}</span>
              <span class="hive__acts">
                <button ref="primary" type="button" class="jb-btn jb-btn--primary hive__btn" @click="emit('retry')">Try again</button>
                <button type="button" class="hive__ghost" @click="emit('close')">Later</button>
              </span>
            </template>
          </div>
        </div>

        <!-- the new brief -->
        <div v-else-if="phase === 'rewritten'" class="hive__pair">
          <Robbee :size="190" />
          <div class="hive__copy">
            <span class="hive__tag">Project rewritten</span>
            <span class="hive__lead">Robbee rewrote the brief for</span>
            <span class="hive__title">{{ title }}</span>
            <span v-if="twist" class="hive__twist">“{{ twist }}”</span>
            <button ref="primary" type="button" class="jb-btn jb-btn--primary hive__btn" @click="emit('start')">Start stage 2</button>
          </div>
        </div>

        <!-- Robbee was killed: the whole party celebrates -->
        <div v-else-if="phase === 'defeated'" class="hive__pair hive__pair--crew">
          <div class="hive__crew" aria-hidden="true">
            <span v-for="(m, i) in crew" :key="i" class="hive__cb" :style="{ left: m.x + '%', top: m.y + '%', animationDelay: m.delay + 's' }">
              <i class="hive__trail" />
              <Mascot :size="82" mood="celebrate" :bee="m.bee as BeeName" wings :look="false" />
            </span>
            <span class="hive__fall"><Robbee :size="130" pose="defeated" :bob="false" /></span>
          </div>
          <div class="hive__copy">
            <span class="hive__tag hive__tag--green">Bankrupt &amp; unemployed</span>
            <span class="hive__title">Hive Protected!</span>
            <span class="hive__lead">Robbee is now bankrupt and unemployed, hooray!</span>
            <button ref="primary" type="button" class="jb-btn jb-btn--primary hive__btn" @click="emit('close')">
              {{ reward ? `Collect ${nf.format(reward)} pollen` : 'Nice teamwork' }}
            </button>
            <span v-if="!reward" class="hive__note">Sting Robbee next round to share the pollen.</span>
          </div>
        </div>

        <!-- stage 2 passed -->
        <div v-else class="hive__pair">
          <Mascot :size="150" mood="celebrate" :look="false" />
          <div class="hive__copy">
            <span class="hive__tag hive__tag--green">Hive patched</span>
            <span class="hive__lead">{{ awarded ? 'You held off Robbee. Challenge complete:' : 'You held off Robbee again:' }}</span>
            <span class="hive__title">{{ title }}</span>
            <span v-if="awarded" class="hive__earn"><Stinger :size="22" /> +1 stinger · {{ stingers }} total</span>
            <span v-else class="hive__earn"><Stinger :size="22" /> Stingers already earned · {{ stingers }} total</span>
            <button ref="primary" type="button" class="jb-btn jb-btn--primary hive__btn" @click="emit('close')">Back to challenges</button>
            <button type="button" class="jb-btn jb-btn--quiet hive__btn" @click="emit('share')">Create LinkedIn post</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.hive { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; overflow: hidden; font-family: var(--font-sans); }
.hive__dim { position: absolute; inset: 0; background: rgba(60, 56, 48, .55); backdrop-filter: grayscale(.7); animation: hive-fade .3s ease-out both; }

.hive__band {
  --tape: repeating-linear-gradient(-45deg, #1e1e1e 0 22px, #ffc107 22px 44px);
  position: relative; justify-self: start; width: 130vw; margin-left: -15vw; min-height: min(56vh, 520px); padding: 72px 12vw;
  display: grid; place-items: center; transform: rotate(-8deg);
  background: linear-gradient(110deg, #fff8e1 0%, #fff1c4 55%, #ffe39a 100%);
  box-shadow: 0 30px 80px rgba(0, 0, 0, .35);
  animation: hive-slam .5s cubic-bezier(.2, 1.4, .4, 1) both;
}
.hive__band::before, .hive__band::after { content: ''; position: absolute; left: 0; right: 0; height: 28px; background: var(--tape); }
.hive__band::before { top: 0; } .hive__band::after { bottom: 0; }
[data-phase="warning"] .hive__band { background: radial-gradient(ellipse at 50% 50%, #e8413c 0%, #c62828 55%, #a51c1c 100%); }
[data-phase="assessing"] .hive__band { background: radial-gradient(ellipse at 40% 50%, #3a2020 0%, #241414 70%); }

/* warning */
.hive__warn { display: flex; flex-direction: column; align-items: center; gap: 0; }
.hive__row { display: flex; align-items: center; gap: 24px; }
.hive__word {
  font-size: clamp(56px, 11vw, 150px); line-height: .95; font-weight: 900; letter-spacing: .02em; text-transform: uppercase;
  color: #fff; text-shadow: 0 6px 0 #6d0f0f, 0 10px 24px rgba(0, 0, 0, .25);
  animation: hive-pop .45s cubic-bezier(.2, 1.6, .4, 1) .1s both;
}
.hive__word--gold { color: #ffc107; margin-left: 4vw; animation-delay: .3s; }
.hive__sub { margin-top: 18px; color: #fff; font-size: clamp(14px, 1.8vw, 24px); font-weight: 900; letter-spacing: .14em; text-transform: uppercase; animation: hive-fade .4s ease-out .6s both; }
.hive__siren { width: clamp(48px, 7vw, 110px); height: auto; flex: none; animation: hive-flash .5s steps(2, end) infinite; }
.hive__bee { position: absolute; z-index: 2; animation: hive-shake .35s ease-in-out infinite alternate; }
.hive__bee::after { content: '!!'; position: absolute; right: -10px; top: -18px; color: #e53935; font-size: 30px; font-weight: 900; }

/* Robbee and copy, side by side */
.hive__pair { display: flex; align-items: center; gap: clamp(20px, 4vw, 56px); max-width: 1100px; }
.hive__pair > :first-child { flex: none; }
.hive__copy { display: flex; flex-direction: column; align-items: flex-start; gap: 10px; min-width: 0; }
.hive__tag { padding: 6px 14px; border-radius: 10px; background: #d32f2f; color: #fff; font-size: 16px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; transform: rotate(-3deg); }
.hive__tag--gold { background: #ffc107; color: #1e1e1e; }
.hive__tag--green { background: #2e7d4f; }
.hive__lead { color: #6b665a; font-size: clamp(18px, 2.4vw, 30px); font-weight: 800; }
.hive__lead--light { color: #f3e3c0; font-size: clamp(16px, 1.8vw, 22px); }
.hive__title { color: #1e1e1e; font-size: clamp(30px, 5vw, 64px); line-height: 1.05; font-weight: 900; overflow-wrap: anywhere; animation: hive-pop .45s cubic-bezier(.2, 1.6, .4, 1) .15s both; }
.hive__title--light { color: #ffc107; }
.hive__twist { max-width: 640px; color: #a85800; font-size: clamp(15px, 1.6vw, 20px); font-weight: 800; }
.hive__earn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px; background: #1e1e1e; color: #ffc107; font-size: 18px; font-weight: 900; }
.hive__btn { margin-top: 8px; padding: 14px 28px; font-size: 18px; letter-spacing: .08em; text-transform: uppercase; }
.hive__note { color: #6b665a; font-size: 16px; font-weight: 700; }
.hive__pair--crew { gap: clamp(8px, 2vw, 32px); }
.hive__crew { position: relative; flex: none; width: min(440px, 44vw); height: 330px; }
.hive__cb { position: absolute; transform: translate(-50%, 0); animation: hive-cheer 1.6s ease-in-out infinite; }
.hive__trail { position: absolute; left: 50%; top: 70%; width: 12px; height: 150px; margin-left: -6px; transform-origin: 50% 0; transform: rotate(32deg); background: radial-gradient(circle, #ffb90f 0 3.5px, transparent 4px) 0 0 / 12px 24px repeat-y; opacity: .75; z-index: -1; }
.hive__fall { position: absolute; left: 50%; bottom: -6px; margin-left: -70px; }
.hive__acts { display: flex; align-items: center; gap: 14px; }
.hive__ghost { border: 0; background: none; color: #f3e3c0; font: inherit; font-weight: 800; text-decoration: underline; cursor: pointer; }
.hive__dots { display: flex; gap: 8px; }
.hive__dots i { width: 12px; height: 12px; border-radius: 50%; background: #ffc107; animation: hive-dot 1s ease-in-out infinite; }
.hive__dots i:nth-child(2) { animation-delay: .15s; } .hive__dots i:nth-child(3) { animation-delay: .3s; }

@keyframes hive-fade { from { opacity: 0; } }
@keyframes hive-cheer { 0%, 100% { transform: translate(-50%, 0) rotate(-4deg); } 50% { transform: translate(-50%, -14px) rotate(4deg); } }
@keyframes hive-slam { from { opacity: 0; transform: rotate(-8deg) translateX(-30%) scaleX(.6); } }
@keyframes hive-pop { from { opacity: 0; transform: scale(1.6); } }
@keyframes hive-flash { 50% { filter: brightness(1.5) drop-shadow(0 0 12px #ff5252); } }
@keyframes hive-shake { from { transform: rotate(-6deg) translateX(-3px); } to { transform: rotate(6deg) translateX(3px); } }
@keyframes hive-dot { 0%, 100% { opacity: .35; transform: translateY(0); } 50% { opacity: 1; transform: translateY(-6px); } }
@media (prefers-reduced-motion: reduce) { .hive *, .hive__band { animation: none !important; } }

@media (max-width: 760px) {
  .hive__band { padding: 56px 16vw; min-height: 60vh; }
  .hive__pair { flex-direction: column; text-align: center; }
  .hive__pair :deep(svg.robbee) { width: 110px; height: auto; }
  .hive__copy { align-items: center; }
  .hive__bee { display: none; }
}
</style>
