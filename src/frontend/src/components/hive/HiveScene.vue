<script setup lang="ts">
/**
 * The Protect the Hive backdrop: a tree branch with the hive hanging from it, in a sunny sky. Everything moves
 * (clouds drift, leaves sway and fall, pollen floats up). `storm` (0-1) darkens the sky into rain and lightning as
 * Robbee takes damage; `cracks` (0-5) splits the hive; `clear` shows a rainbow once he is beaten.
 * Draw order is bottom to top; the stage over it positions Robbee and the bees in HTML.
 */
defineProps<{ storm: number; cracks: number; clear?: boolean }>();

const motes = Array.from({ length: 16 }, (_, i) => ({ x: 70 + ((i * 97) % 1460), delay: -i * 0.9, dur: 7 + (i % 5) * 1.4, r: 3 + (i % 3) }));
const leaves = Array.from({ length: 7 }, (_, i) => ({ x: 110 + i * 215, delay: -i * 1.7, dur: 10 + (i % 3) * 2.6 }));
</script>

<template>
  <svg class="scene" viewBox="0 0 1600 760" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="hs-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#bfe6f8" /><stop offset=".55" stop-color="#e3f2f0" /><stop offset="1" stop-color="#fff2c9" />
      </linearGradient>
      <radialGradient id="hs-sun" cx=".5" cy=".5" r=".5">
        <stop offset="0" stop-color="#fff6c2" stop-opacity=".95" /><stop offset="1" stop-color="#fff6c2" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="hs-honey" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#e6a200" /><stop offset=".5" stop-color="#ffc21a" /><stop offset="1" stop-color="#e09a00" />
      </linearGradient>
      <linearGradient id="hs-rainbow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ff6b6b" /><stop offset=".2" stop-color="#ffb347" /><stop offset=".4" stop-color="#ffe66b" />
        <stop offset=".6" stop-color="#7bd88f" /><stop offset=".8" stop-color="#6bb8ff" /><stop offset="1" stop-color="#a98bff" />
      </linearGradient>
      <pattern id="hs-rain" width="26" height="70" patternUnits="userSpaceOnUse" patternTransform="rotate(12)">
        <line x1="13" y1="0" x2="13" y2="28" stroke="#d6e6ff" stroke-width="2.4" stroke-linecap="round" opacity=".75" />
      </pattern>
    </defs>

    <rect width="1600" height="760" fill="url(#hs-sky)" />
    <circle class="sun" cx="1290" cy="190" r="230" fill="url(#hs-sun)" />

    <!-- clouds -->
    <g class="cloud c1" fill="#fff" opacity=".92"><ellipse cx="260" cy="250" rx="90" ry="34" /><ellipse cx="320" cy="228" rx="64" ry="34" /><ellipse cx="205" cy="232" rx="54" ry="28" /></g>
    <g class="cloud c2" fill="#fff" opacity=".85"><ellipse cx="900" cy="330" rx="110" ry="36" /><ellipse cx="970" cy="306" rx="70" ry="34" /><ellipse cx="840" cy="312" rx="58" ry="28" /></g>
    <g class="cloud c3" fill="#fff" opacity=".8"><ellipse cx="1360" cy="290" rx="80" ry="30" /><ellipse cx="1410" cy="270" rx="54" ry="28" /></g>

    <!-- hills -->
    <path d="M0 700 Q220 610 470 668 T980 650 T1600 640 V760 H0 Z" fill="#9fd48f" />
    <path d="M0 735 Q300 680 640 724 T1250 706 T1600 722 V760 H0 Z" fill="#7cc274" />

    <!-- pollen drifting up -->
    <g fill="#ffd54a">
      <circle v-for="(m, i) in motes" :key="i" class="mote" :cx="m.x" cy="720" :r="m.r" :style="{ animationDelay: m.delay + 's', animationDuration: m.dur + 's' }" />
    </g>

    <!-- branch the hive hangs from -->
    <path d="M-20 130 Q400 96 800 128 T1620 104 V168 Q1200 190 800 176 T-20 190 Z" fill="#8b5a2b" />
    <path d="M-20 150 Q400 124 800 150 T1620 128" stroke="#a8743d" stroke-width="6" fill="none" opacity=".6" />
    <path d="M300 176 Q340 230 280 268 M1180 168 Q1230 226 1290 262" stroke="#8b5a2b" stroke-width="14" fill="none" stroke-linecap="round" />
    <ellipse cx="276" cy="270" rx="34" ry="16" fill="#7cc274" /><ellipse cx="1294" cy="264" rx="34" ry="16" fill="#7cc274" />

    <!-- canopy, swaying -->
    <g class="canopy" fill="#5aa85a">
      <circle cx="140" cy="50" r="130" /><circle cx="400" cy="30" r="110" fill="#7cc274" /><circle cx="650" cy="40" r="120" />
      <circle cx="930" cy="20" r="105" fill="#7cc274" /><circle cx="1180" cy="40" r="115" /><circle cx="1440" cy="30" r="125" fill="#7cc274" />
      <circle cx="1620" cy="80" r="110" />
    </g>

    <!-- the hive -->
    <g class="hive">
      <rect x="788" y="150" width="24" height="42" rx="8" fill="#6f4519" />
      <g stroke="#b87a00" stroke-width="5" fill="url(#hs-honey)">
        <rect x="725" y="118" width="150" height="116" rx="58" />
        <rect x="685" y="205" width="230" height="104" rx="50" />
        <rect x="655" y="290" width="290" height="104" rx="50" />
        <rect x="635" y="375" width="330" height="104" rx="50" />
        <rect x="625" y="460" width="350" height="104" rx="50" />
      </g>
      <g fill="none" stroke="#c98a00" stroke-width="3" opacity=".7">
        <path d="M760 240 l14 -8 l14 8 v16 l-14 8 l-14 -8 Z M788 240 l14 -8 l14 8 v16 l-14 8 l-14 -8 Z M774 264 l14 -8 l14 8 v16 l-14 8 l-14 -8 Z" />
      </g>
      <ellipse cx="800" cy="500" rx="74" ry="82" fill="#4a2c00" /><ellipse cx="800" cy="500" rx="74" ry="82" fill="none" stroke="#b87a00" stroke-width="6" />
      <g class="cracks" stroke="#3a2200" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path v-if="cracks >= 1" d="M840 140 L812 196 L846 214 L822 252" />
        <path v-if="cracks >= 2" d="M698 296 L736 318 L712 344 L748 372" />
        <path v-if="cracks >= 3" d="M902 298 L868 326 L896 350 L862 386" />
        <path v-if="cracks >= 4" d="M664 392 L700 414 L676 440 L708 468" />
        <path v-if="cracks >= 5" d="M938 388 L904 412 L930 440 L898 470" />
      </g>
    </g>

    <!-- falling leaves -->
    <g fill="#5aa85a">
      <ellipse v-for="(l, i) in leaves" :key="i" class="leaf" :cx="l.x" cy="60" rx="16" ry="8" :style="{ animationDelay: l.delay + 's', animationDuration: l.dur + 's' }" />
    </g>

    <!-- the rainbow once he is beaten -->
    <path class="rainbow" :class="{ on: clear }" d="M180 700 Q800 110 1420 700" fill="none" stroke="url(#hs-rainbow)" stroke-width="46" stroke-linecap="round" opacity="0" />

    <!-- the storm: darkness, rain and lightning grow as Robbee loses HP -->
    <rect width="1600" height="760" fill="#1d2440" :style="{ opacity: storm * 0.62 }" class="fade" />
    <rect class="rain fade" x="-100" y="-80" width="1800" height="920" fill="url(#hs-rain)" :style="{ opacity: Math.max(0, storm - 0.3) * 1.3 }" />
    <g class="fade" :style="{ opacity: storm > 0.55 ? 1 : 0 }">
      <rect class="flash" width="1600" height="760" fill="#fff" opacity="0" />
      <path class="bolt" d="M1180 0 L1120 150 L1170 150 L1090 330 L1220 130 L1168 130 Z" fill="#fff7b0" opacity="0" />
    </g>
  </svg>
</template>

<style scoped>
.scene { position: absolute; inset: 0; width: 100%; height: 100%; }
.fade { transition: opacity 1.4s ease; }
.sun { animation: sun-pulse 6s ease-in-out infinite; transform-origin: 1290px 190px; }
.cloud { animation: drift 60s linear infinite; }
.c2 { animation-duration: 85s; animation-delay: -30s; }
.c3 { animation-duration: 110s; animation-delay: -70s; }
.canopy { animation: sway 7s ease-in-out infinite; transform-origin: 800px -20px; }
.hive { animation: hive-sway 5.5s ease-in-out infinite; transform-origin: 800px 130px; }
.leaf { animation: leaf-fall 12s linear infinite; }
.mote { animation: mote-rise 9s ease-in infinite; opacity: 0; }
.rain { animation: rain 0.55s linear infinite; }
.flash { animation: flash 7s infinite; }
.bolt { animation: flash 7s infinite; }
.rainbow { transition: opacity 1.6s ease; }
.rainbow.on { opacity: .8; }

@keyframes drift { from { transform: translateX(-420px); } to { transform: translateX(1900px); } }
@keyframes sun-pulse { 0%, 100% { transform: scale(1); opacity: .9; } 50% { transform: scale(1.08); opacity: 1; } }
@keyframes sway { 0%, 100% { transform: rotate(-.6deg); } 50% { transform: rotate(.7deg); } }
@keyframes hive-sway { 0%, 100% { transform: rotate(-1deg); } 50% { transform: rotate(1.1deg); } }
@keyframes leaf-fall {
  0% { transform: translate(0, 0) rotate(0); opacity: 0; }
  8% { opacity: 1; }
  50% { transform: translate(60px, 380px) rotate(160deg); }
  92% { opacity: 1; }
  100% { transform: translate(-30px, 740px) rotate(340deg); opacity: 0; }
}
@keyframes mote-rise {
  0% { transform: translate(0, 0); opacity: 0; }
  15% { opacity: .85; }
  100% { transform: translate(28px, -520px); opacity: 0; }
}
@keyframes rain { from { transform: translateY(0); } to { transform: translateY(70px); } }
@keyframes flash { 0%, 90%, 100% { opacity: 0; } 92% { opacity: .75; } 94% { opacity: .1; } 96% { opacity: .55; } 98% { opacity: 0; } }

@media (prefers-reduced-motion: reduce) {
  .sun, .cloud, .canopy, .hive, .leaf, .mote, .rain, .flash, .bolt { animation: none; }
  .mote { opacity: .5; }
}
</style>
