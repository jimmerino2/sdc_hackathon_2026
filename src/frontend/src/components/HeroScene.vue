<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import Icon from './Icon.vue';
import Mascot, { type Gear, type Mood } from './Mascot.vue';
import SkillLogo, { type LogoName } from './SkillLogo.vue';
import { BRAND_BEE } from '../bee';
import { useFit } from '../composables/useFit';

/**
 * The landing story, played once:
 *   the bee flies out of its hive, the hive vanishes, an AI computer pops up and hits the bee with ADVANCEMENTS IN AI,
 *   the bee puts on a suit and tie and fires honey carrying its skills back, and the scene freezes mid-attack.
 * Motion is a single CSS timeline (the delays below, in seconds); the bee's face and outfit follow it from the schedule.
 */
const W = 720;
const H = 380;
const SKILLS: LogoName[] = ['react', 'node', 'typescript', 'java', 'python', 'cpp'];
/** Where each honey glob stops, from the bee's hand: the first lands on the computer, the last has only just left. */
const GLOBS = [[220, -10, 14], [170, -45, -10], [135, 25, 20], [90, -30, -16], [60, 40, 8], [28, -6, -4]] as const;

const reduced = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
const mood = ref<Mood>(reduced ? 'serious' : 'idle');
const gear = ref<Gear>(reduced ? 'suit' : 'none');
const hurt = ref(reduced); // the computer has been hit
const suitedUp = ref(reduced); // fires the outfit-change flash

/** [seconds, what changes], matching the CSS delays. */
const SCHEDULE: [number, () => void][] = [
  [1.0, () => (mood.value = 'happy')],
  [2.8, () => (mood.value = 'wave')],
  [3.5, () => (mood.value = 'surprised')],
  [6.55, () => { gear.value = 'suit'; suitedUp.value = true; mood.value = 'serious'; }],
  [8.2, () => (hurt.value = true)],
];
const timers: number[] = [];
/** Changing the key rebuilds the scene, which restarts every CSS animation from the top. */
const play = ref(0);
const done = ref(reduced);
const END = 9.6; // seconds until the frozen frame and its caption are in place

function start() {
  timers.forEach((t) => window.clearTimeout(t));
  timers.length = 0;
  if (reduced) return;
  SCHEDULE.forEach(([s, f]) => timers.push(window.setTimeout(f, s * 1000)));
  timers.push(window.setTimeout(() => (done.value = true), END * 1000));
}
function replay() {
  mood.value = 'idle';
  gear.value = 'none';
  hurt.value = false;
  suitedUp.value = false;
  done.value = false;
  play.value++;
  start();
}
onMounted(start);
onBeforeUnmount(() => timers.forEach((t) => window.clearTimeout(t)));

const { el, scale } = useFit(W);
const frame = computed(() => ({ height: H * scale.value + 'px' }));
const hexes = [[3, 10, 30], [94, 6, 36], [90, 84, 24], [30, 88, 26], [60, 3, 18], [8, 62, 20]];
</script>

<template>
  <div class="wrap">
  <div ref="el" class="fit" :style="frame">
    <div :key="play" class="scene" :class="{ still: reduced }" :style="{ width: W + 'px', height: H + 'px', transform: `scale(${scale})` }" role="img" aria-label="The bee flies out of its hive, is attacked by an AI computer, puts on a suit and hits back with honey carrying skills: React, Node.js, TypeScript, Java, Python and C++.">
      <span v-for="(h, i) in hexes" :key="i" class="hex" :style="{ left: h[0] + '%', top: h[1] + '%', width: h[2] + 'px', height: h[2] * 1.15 + 'px', '--i': i }" />
      <span class="disc" />

      <!-- the hive the bee comes out of -->
      <div class="hive">
        <svg viewBox="0 0 110 130" width="110" height="130">
          <ellipse cx="55" cy="124" rx="46" ry="6" fill="rgba(0,0,0,.12)" />
          <path d="M18 118 C8 118 8 98 18 96 H92 C102 98 102 118 92 118 Z" fill="#f2a900" stroke="#1e1e1e" stroke-width="3" stroke-linejoin="round" />
          <path d="M24 96 C14 96 14 74 24 72 H86 C96 74 96 96 86 96 Z" fill="#ffc107" stroke="#1e1e1e" stroke-width="3" stroke-linejoin="round" />
          <path d="M30 72 C22 72 22 50 31 48 H79 C88 50 88 72 80 72 Z" fill="#f2a900" stroke="#1e1e1e" stroke-width="3" stroke-linejoin="round" />
          <path d="M36 48 C30 48 31 28 41 26 H69 C79 28 80 48 74 48 Z" fill="#ffc107" stroke="#1e1e1e" stroke-width="3" stroke-linejoin="round" />
          <path d="M47 26 C46 14 52 8 55 8 C58 8 64 14 63 26 Z" fill="#f2a900" stroke="#1e1e1e" stroke-width="3" stroke-linejoin="round" />
          <ellipse cx="55" cy="104" rx="15" ry="13" fill="#2b1b05" stroke="#1e1e1e" stroke-width="3" />
          <path d="M29 84 H81 M35 60 H75" stroke="#1e1e1e" stroke-width="2" opacity=".35" fill="none" />
        </svg>
        <span class="hive-puff p1" /><span class="hive-puff p2" /><span class="hive-puff p3" />
      </div>

      <!-- the bee -->
      <div class="bee">
        <div class="bee-fl">
          <div class="bee-re"><Mascot :size="150" :bee="BRAND_BEE" :mood="mood" :gear="gear" :look="false" wings /></div>
          <span class="poof" :class="{ on: suitedUp }"><i v-for="n in 8" :key="n" :style="{ '--a': n * 45 + 'deg' }" /></span>
        </div>
      </div>

      <!-- the AI computer -->
      <div class="pc">
        <div class="pc-fl"><div class="pc-re">
          <svg viewBox="0 0 150 150" width="150" height="150">
            <path class="cable" d="M75 120 C75 138 42 138 36 148" />
            <path class="antenna" d="M75 19 L75 6" /><circle class="ant-tip" cx="75" cy="5" r="4.5" />
            <rect class="arm" x="6" y="66" width="17" height="10" rx="5" /><rect class="arm" x="127" y="66" width="17" height="10" rx="5" />
            <rect class="shell" x="17" y="17" width="116" height="93" rx="15" />
            <rect class="screen" x="28" y="28" width="94" height="67" rx="9" />
            <g v-if="!hurt" class="face">
              <path class="brow" d="M40 43 L64 52" /><path class="brow" d="M110 43 L86 52" />
              <rect class="eye" x="45" y="56" width="15" height="11" rx="2" /><rect class="eye" x="90" y="56" width="15" height="11" rx="2" />
              <path class="mouth" d="M52 82 L60 75 L68 82 L76 75 L84 82 L92 75 L98 80" />
            </g>
            <g v-else class="face hurt-face">
              <path class="brow" d="M40 46 L64 46 M110 46 L86 46" />
              <path class="squint" d="M45 52 L60 60 L45 68 M105 52 L90 60 L105 68" />
              <path class="mouth" d="M58 84 Q75 74 92 84" />
            </g>
            <g class="drips" :class="{ on: hurt }">
              <path d="M30 28 H120 V40 C112 40 112 54 105 54 C98 54 99 40 90 40 C84 40 85 62 77 62 C69 62 70 40 60 40 C52 40 54 50 46 50 C38 50 40 40 30 40 Z" />
              <circle cx="46" cy="58" r="4" /><circle cx="77" cy="70" r="4.5" /><circle cx="105" cy="62" r="3.6" />
            </g>
            <text class="tag" x="75" y="104" text-anchor="middle">AI</text>
            <rect class="stand" x="62" y="110" width="26" height="10" /><rect class="base" x="45" y="118" width="60" height="9" rx="4" />
          </svg>
        </div></div>
      </div>

      <!-- the computer hits the bee: three shots land -->
      <span v-for="n in 3" :key="`s${n}`" class="shot" :style="{ '--n': n - 1 }">ADVANCEMENTS IN AI</span>
      <!-- and two more that the honey stops in mid-air -->
      <span class="held h1">ADVANCEMENTS IN AI</span>
      <span class="held h2">ADVANCEMENTS IN AI</span>

      <!-- the bee's answer: honey carrying skills -->
      <div v-for="(g, i) in GLOBS" :key="SKILLS[i]" class="glob" :style="{ '--tx': g[0] + 'px', '--ty': g[1] + 'px', '--r': g[2] + 'deg', '--i': i }">
        <svg viewBox="0 0 64 64" width="58" height="58">
          <defs><linearGradient :id="`hg${i}`" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd84d" /><stop offset="1" stop-color="#f19a00" /></linearGradient></defs>
          <path d="M32 3C48 3 60 14 60 30c0 10-6 16-12 22-2 4-2 10-7 9-5-1-3-5-7-4C20 62 4 50 4 32 4 14 18 3 32 3z" :fill="`url(#hg${i})`" stroke="#a85f00" stroke-width="2.6" stroke-linejoin="round" />
          <ellipse cx="20" cy="17" rx="7" ry="3.4" fill="#fff" opacity=".5" transform="rotate(-30 20 17)" />
          <circle cx="32" cy="30" r="19" fill="#fffdf5" stroke="#a85f00" stroke-width="1.6" />
          <svg x="18" y="16" width="28" height="28" viewBox="0 0 32 32"><SkillLogo :name="SKILLS[i]" /></svg>
        </svg>
      </div>
      <span class="clash c1" /><span class="clash c2" /><span class="clash c3" />
      <p class="caption">Skills beat the AI wave</p>
    </div>
  </div>
  <button v-if="!reduced" type="button" class="replay" :class="{ ready: done }" :disabled="!done" @click="replay"><Icon name="refresh" :size="15" />Replay</button>
  </div>
</template>

<style scoped>
.wrap { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.fit { position: relative; width: 100%; }
.scene { --ink: #1e1e1e; position: absolute; left: 0; top: 0; transform-origin: top left; }

.hex { position: absolute; background: var(--yellow); opacity: .5; clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); animation: drift 7s ease-in-out infinite; animation-delay: calc(var(--i) * -1.3s); }
.hex:nth-child(even) { background: var(--orange); opacity: .35; }
.disc { position: absolute; left: 50%; top: 50%; width: 360px; height: 360px; margin: -180px 0 0 -180px; border-radius: 50%; background: var(--cream); animation: breathe 6s ease-in-out infinite; }

.caption { position: absolute; left: 50%; bottom: 8px; margin: 0; padding: 7px 18px; transform: translateX(-50%); border-radius: 999px; background: var(--ink); color: var(--yellow); font: 900 13px 'Nunito', sans-serif; letter-spacing: .14em; text-transform: uppercase; white-space: nowrap; box-shadow: 0 4px 0 var(--orange); animation: caption .6s 9.5s cubic-bezier(.2, .9, .3, 1) both; }
.replay { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px; font: 800 12px 'Nunito', sans-serif; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); opacity: 0; pointer-events: none; transition: opacity .3s, color .15s, background .15s; }
.replay.ready { opacity: 1; pointer-events: auto; }
.replay.ready:hover { color: var(--ink); background: var(--cream); }
.replay:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }

/* ---- hive: pops in, then vanishes ---- */
.hive { position: absolute; left: 18px; top: 168px; width: 110px; height: 130px; animation: hive-in .5s both, hive-wobble .5s .5s, hive-out .6s 2.1s forwards; transform-origin: 50% 100%; }
.hive-puff { position: absolute; left: 35px; top: 55px; width: 40px; height: 40px; border-radius: 50%; background: #fff3cc; opacity: 0; }
.hive-puff.p2 { left: 10px; top: 80px; } .hive-puff.p3 { left: 62px; top: 78px; }
.hive-puff { animation: puff .8s 2.15s ease-out both; } .p2 { animation-delay: 2.25s; } .p3 { animation-delay: 2.35s; }

/* ---- bee: out of the hive door, then floating ---- */
.bee { position: absolute; left: 170px; top: 112px; width: 150px; animation: emerge 1.1s .9s cubic-bezier(.3, .8, .35, 1) both; }
.bee-fl { position: relative; animation: float 4.6s ease-in-out infinite; }
.bee-re { transform-origin: 50% 80%; animation: flinch .6s 4.9s, flinch .6s 5.6s, flinch .6s 6.3s, throw .5s 7.3s, throw .5s 7.52s, throw .5s 7.74s, throw .5s 7.96s, throw .5s 8.18s, throw .5s 8.4s; }
.poof { position: absolute; left: 50%; top: 50%; width: 0; height: 0; }
.poof i { position: absolute; left: -7px; top: -7px; width: 14px; height: 14px; background: #fff3a8; border: 2px solid var(--orange); clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%); opacity: 0; }
.poof.on i { animation: poof .8s ease-out both; }

/* ---- computer: appears out of nowhere, then holds its ground ---- */
.pc { position: absolute; left: 542px; top: 100px; width: 150px; height: 150px; animation: pc-pop .7s 3.3s both; }
.pc-fl { animation: hover 3.4s ease-in-out infinite; }
.pc-re { animation: recoil .4s 3.9s, recoil .4s 4.6s, recoil .4s 5.3s, recoil .4s 7.35s, recoil .4s 7.6s, hit .35s 8.2s, hit .35s 8.45s; }
.shell { fill: #353849; stroke: var(--ink); stroke-width: 3; }
.screen { fill: #0d1020; stroke: #1c2038; stroke-width: 2; }
.eye { fill: #ff3b30; filter: drop-shadow(0 0 4px #ff3b30); }
.brow, .squint { fill: none; stroke: #ff3b30; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }
.mouth { fill: none; stroke: #ff3b30; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.tag { font: 900 11px 'Nunito', sans-serif; fill: #ff8a80; letter-spacing: .1em; }
.stand { fill: #2a2c3a; } .base { fill: #2a2c3a; stroke: var(--ink); stroke-width: 2; }
.arm { fill: #353849; stroke: var(--ink); stroke-width: 2.5; } .antenna { stroke: var(--ink); stroke-width: 3; }
.ant-tip { fill: #ff3b30; filter: drop-shadow(0 0 5px #ff3b30); animation: blink 1s steps(2) infinite; }
.cable { fill: none; stroke: var(--ink); stroke-width: 3; stroke-linecap: round; }
.drips { fill: #ffb300; stroke: #a85f00; stroke-width: 1.5; opacity: 0; transform-origin: 75px 28px; }
.drips.on { animation: drip .9s ease-out both; }

/* ---- shots: ADVANCEMENTS IN AI ---- */
.shot, .held { position: absolute; padding: 5px 11px; border-radius: 8px; background: #ff3b30; color: #fff; border: 2px solid #8f1d15; font: 900 12px 'Nunito', sans-serif; letter-spacing: .08em; white-space: nowrap; box-shadow: 0 0 12px rgba(255, 59, 48, .6); }
.shot { left: 508px; top: 148px; opacity: 0; animation: shoot 1s calc(3.9s + var(--n) * .7s) ease-in forwards; }
.held { opacity: 0; }
.h1 { left: 378px; top: 236px; animation: held1 .8s 7.35s ease-out forwards; }
.h2 { left: 404px; top: 78px; animation: held2 .8s 7.6s ease-out forwards; }

/* ---- honey globs: launched one after another, stopping where the scene freezes ---- */
.glob { position: absolute; left: 298px; top: 158px; width: 58px; height: 58px; opacity: 0; filter: drop-shadow(0 3px 0 rgba(120, 70, 0, .35)); animation: toss .95s calc(7.3s + var(--i) * .22s) cubic-bezier(.25, .7, .3, 1) both; }
.clash { position: absolute; width: 22px; height: 22px; background: #fff7b0; border: 2px solid var(--orange); clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%); opacity: 0; animation: clash .5s ease-out both, twinkle 1.8s 9.2s ease-in-out infinite; }
.c1 { left: 420px; top: 168px; animation-delay: 7.9s, 9.2s; } .c2 { left: 372px; top: 214px; animation-delay: 8.0s, 9.5s; } .c3 { left: 468px; top: 104px; animation-delay: 8.1s, 9.8s; }

@keyframes caption { from { opacity: 0; transform: translate(-50%, 14px) scale(.9); } to { opacity: 1; transform: translate(-50%, 0) scale(1); } }
@keyframes drift { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-12px) rotate(14deg); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.04); } }
@keyframes float { 0%, 100% { transform: translate(0, 0) rotate(-2deg); } 50% { transform: translate(5px, -10px) rotate(2deg); } }
@keyframes hover { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes blink { 50% { opacity: .25; } }
@keyframes hive-in { from { opacity: 0; transform: scale(.2); } 70% { transform: scale(1.1); } to { opacity: 1; transform: scale(1); } }
@keyframes hive-wobble { 0%, 100% { transform: rotate(0); } 25% { transform: rotate(-4deg); } 75% { transform: rotate(4deg); } }
@keyframes hive-out { from { opacity: 1; transform: scale(1); } to { opacity: 0; transform: scale(.3); } }
@keyframes puff { 0% { opacity: .85; transform: scale(.3); } 100% { opacity: 0; transform: translateY(-26px) scale(1.7); } }
@keyframes emerge { 0% { opacity: 0; transform: translate(-182px, 96px) scale(.22); } 18% { opacity: 1; } 55% { transform: translate(-60px, -42px) scale(.8) rotate(-8deg); } 100% { opacity: 1; transform: none; } }
@keyframes pc-pop { 0% { opacity: 0; transform: scale(.5); } 15% { opacity: 1; transform: scale(1.12); } 28% { opacity: .15; } 42% { opacity: 1; transform: scale(.96) skewX(6deg); } 58% { opacity: .4; } 72% { opacity: 1; transform: skewX(-4deg); } 100% { opacity: 1; transform: none; } }
@keyframes recoil { 0%, 100% { transform: none; } 40% { transform: translateX(14px) rotate(3deg); } }
@keyframes hit { 0%, 100% { transform: none; filter: none; } 35% { transform: translateX(12px) rotate(4deg); filter: brightness(2); } 65% { transform: translateX(-4px) rotate(-2deg); } }
@keyframes shoot { 0% { opacity: 1; transform: translate(0, 0) scale(.6); } 88% { opacity: 1; transform: translate(-176px, 14px) scale(1); } 100% { opacity: 0; transform: translate(-190px, 14px) scale(1.4); } }
@keyframes held1 { 0% { opacity: 1; transform: translate(168px, -66px) scale(.6); } 100% { opacity: .96; transform: translate(0, 0) rotate(-7deg) scale(1); } }
@keyframes held2 { 0% { opacity: 1; transform: translate(140px, 78px) scale(.6); } 100% { opacity: .96; transform: translate(0, 0) rotate(6deg) scale(1); } }
@keyframes flinch { 0%, 100% { transform: none; filter: none; } 35% { transform: translateX(-16px) rotate(-8deg); filter: brightness(1.6) saturate(.5); } }
@keyframes throw { 0%, 100% { transform: none; } 35% { transform: translateX(-8px) rotate(-6deg); } 70% { transform: translateX(14px) rotate(6deg); } }
@keyframes poof { 0% { opacity: 1; transform: rotate(var(--a)) translateY(-10px) scale(.4); } 100% { opacity: 0; transform: rotate(var(--a)) translateY(-95px) scale(1.5); } }
@keyframes toss { 0% { opacity: 0; transform: translate(0, 0) scale(.3) rotate(-30deg); } 14% { opacity: 1; transform: translate(10px, -8px) scale(1) rotate(0); } 55% { opacity: 1; transform: translate(calc(var(--tx) * .5), calc(var(--ty) * .5 - 46px)) rotate(calc(var(--r) * -3)); } 100% { opacity: 1; transform: translate(var(--tx), var(--ty)) rotate(var(--r)); } }
@keyframes drip { 0% { opacity: 0; transform: scaleY(.1); } 100% { opacity: .95; transform: scaleY(1); } }
@keyframes clash { 0% { opacity: 0; transform: scale(.2) rotate(0); } 50% { opacity: 1; transform: scale(1.3) rotate(30deg); } 100% { opacity: .9; transform: scale(1) rotate(45deg); } }
@keyframes twinkle { 0%, 100% { transform: scale(1) rotate(45deg); opacity: .9; } 50% { transform: scale(1.35) rotate(60deg); opacity: 1; } }

/* Without motion, every animation lands on its last frame at once: the frozen scene, bee in its suit, computer hit. */
.still, .still * { animation-duration: .01ms !important; animation-delay: 0s !important; animation-iteration-count: 1 !important; }
.still .hex, .still .disc, .still .bee-fl, .still .pc-fl, .still .ant-tip { animation: none !important; }
.still .shot { display: none; }
</style>
