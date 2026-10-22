<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { bee as currentBee, type BeeName } from '../bee';

export type Gear = 'none' | 'magnifier' | 'suit' | 'glasses';
export type Mood = 'idle' | 'serious' | 'wave' | 'happy' | 'thinking' | 'sleepy' | 'celebrate' | 'surprised';

const props = withDefaults(defineProps<{ size?: number; mood?: Mood; look?: boolean; wings?: boolean; bee?: BeeName; gear?: Gear; gaze?: [number, number] | null }>(), {
  size: 70,
  wings: false,
  bee: undefined,
  gear: 'none',
  gaze: null,
  mood: 'idle',
  look: true,
});

const root = ref<HTMLElement | null>(null);
const dx = ref(0);
const dy = ref(0);

function onMove(e: PointerEvent) {
  if (!root.value || !props.look || props.size < 56 || props.mood === 'sleepy') return;
  const r = root.value.getBoundingClientRect();
  const x = e.clientX - (r.left + r.width / 2);
  const y = e.clientY - (r.top + r.height / 2);
  const d = Math.hypot(x, y) || 1;
  const k = Math.min(1, d / 260);
  dx.value = (x / d) * k;
  dy.value = (y / d) * k;
}
onMounted(() => window.addEventListener('pointermove', onMove, { passive: true }));
onBeforeUnmount(() => window.removeEventListener('pointermove', onMove));

const who = computed<BeeName>(() => props.bee ?? currentBee.value);
const tired = computed(() => who.value === 'Barnabee' || who.value === 'Phoebee');
const gx = computed(() => (props.gaze ? props.gaze[0] : dx.value));
const gy = computed(() => (props.gaze ? props.gaze[1] : dy.value));

const confetti = [
  ['#ff9800', -60, -90], ['#1e1e1e', 55, -100], ['#ffc107', -90, -40], ['#ff9800', 90, -50], ['#1e1e1e', 10, -120], ['#ffc107', -30, -110],
] as const;
</script>

<template>
  <div ref="root" class="mascot" :class="[`m-${mood}`, `b-${who.toLowerCase()}`, { tired, suited: gear === 'suit' }]" :style="{ fontSize: size + 'px', '--dx': gx, '--dy': gy }" role="img" aria-label="Jobee the mascot">
    <div class="shadow" />
    <div class="jump">
      <template v-if="wings"><span class="wing l" /><span class="wing r" /></template>
      <span v-if="gear === 'suit'" class="hat"><i /></span>
      <span class="ant l" /><span class="ant r" />
      <div class="body">
        <svg class="marks" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <g class="stripes">
            <rect x="0" y="64" width="100" :height="who === 'Tobee' ? 9 : 7" />
            <rect x="0" y="80" width="100" :height="who === 'Tobee' ? 9 : 7" />
            <rect v-if="who === 'Tobee'" x="0" y="6" width="100" height="7" />
            <rect v-if="who === 'Tobee' || tired" x="0" y="95" width="100" height="5" />
          </g>
        </svg>
        <div class="face">
          <span class="cheek l" /><span class="cheek r" />
          <span class="eye l" /><span class="eye r" />
          <span class="mouth" />
          <template v-if="tired"><span class="bag l" /><span class="bag r" /><span class="lid l" /><span class="lid r" /></template>
          <template v-if="who === 'Phoebee'"><span class="lash l" /><span class="lash r" /></template>
          <template v-if="gear === 'glasses'"><span class="gl l" /><span class="gl r" /><span class="gl bridge" /></template>
        </div>
        <svg v-if="tired && gear !== 'suit'" class="lanyard" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M6 52 L50 78 M94 52 L50 78" stroke="#2f5fa8" stroke-width="3.5" fill="none" stroke-linecap="round" />
          <rect x="41" y="76" width="18" height="17" rx="3" fill="#fff" stroke="#1e1e1e" stroke-width="2" /><rect x="44" y="79" width="7" height="6" fill="#ff9800" />
        </svg>
        <span v-if="gear === 'suit'" class="suit"><b class="shirt" /><b class="tie l" /><b class="tie r" /><b class="knot" /></span>
      </div>
      <span v-if="gear === 'magnifier'" class="mag"><span class="lens" /><span class="handle" /></span>
      <span class="fx zzz">z<small>z</small></span>
      <span class="fx q">?</span>
      <span class="fx bang">!</span>
      <span v-for="(c, i) in confetti" :key="i" class="fx conf" :style="{ background: c[0], '--tx': c[1] / 100 + 'em', '--ty': c[2] / 100 + 'em', animationDelay: i * 0.07 + 's' }" />
    </div>
  </div>
</template>

<style scoped>
.mascot { position: relative; width: 1em; height: 1em; flex: none; display: block; }
.shadow { position: absolute; left: 12%; right: 12%; bottom: -6%; height: 8%; border-radius: 50%; background: rgba(30, 30, 30, .1); animation: shadow 3s ease-in-out infinite; }
.jump { position: absolute; inset: 0; transform-origin: 50% 100%; }
.body {
  position: absolute; inset: 0; background: var(--yellow); border-radius: .34em .34em .34em .06em;
  transform-origin: 50% 100%; animation: bob 3s ease-in-out infinite;
}
.face { position: absolute; inset: 0; transform: translate(calc(var(--dx) * .05em), calc(var(--dy) * .04em)); transition: transform .12s ease-out; }
.eye {
  position: absolute; top: 36%; width: .13em; height: .15em; border-radius: 50%; background: var(--ink);
  transform-origin: 50% 50%; animation: blink 4.5s infinite;
}
.eye.l { left: 28%; } .eye.r { right: 28%; }
.cheek { position: absolute; top: 55%; width: .1em; height: .06em; border-radius: 50%; background: var(--orange); opacity: .45; }
.cheek.l { left: 17%; } .cheek.r { right: 17%; }
.mouth { position: absolute; left: 50%; top: 58%; width: .1em; height: .05em; margin-left: -.05em; border-bottom: .022em solid var(--ink); border-radius: 0 0 .1em .1em; opacity: .9; transition: all .2s; }

/* wings */
.wing { position: absolute; top: .1em; width: .4em; height: .28em; background: #fff; border: .025em solid var(--orange); border-radius: 60% 40% 60% 40%; z-index: 0; animation: flap .22s ease-in-out infinite alternate; }
.wing.l { left: -.3em; transform-origin: 100% 70%; --r: -1; border-radius: 40% 60% 40% 60%; }
.wing.r { right: -.3em; transform-origin: 0 70%; --r: 1; }
.body { z-index: 1; }
@keyframes flap { from { transform: rotate(calc(var(--r) * -8deg)) scale(1, 1); } to { transform: rotate(calc(var(--r) * 28deg)) scale(.85, 1.05); } }

/* magnifier */
.mag { position: absolute; right: -.18em; bottom: .02em; width: .36em; height: .44em; z-index: 3; transform-origin: 30% 90%; animation: scan 2.6s ease-in-out infinite; }
.lens { position: absolute; top: -.04em; right: -.04em; width: .32em; height: .32em; border-radius: 50%; border: .035em solid var(--ink); background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.95) 0 14%, rgba(255,255,255,.4) 15% 100%); box-shadow: 0 .01em .02em rgba(0,0,0,.15); }
.handle { position: absolute; left: .02em; bottom: .0em; width: .04em; height: .2em; background: var(--orange); border-radius: .03em; transform: rotate(40deg); transform-origin: 50% 0; top: .22em; left: .08em; border: .01em solid var(--ink); }
@keyframes scan { 0%, 100% { transform: rotate(-12deg) translate(0, 0); } 50% { transform: rotate(14deg) translate(-.06em, -.05em); } }

/* suit + top hat */
.suit { position: absolute; left: 0; right: 0; bottom: 0; height: .3em; background: var(--ink); border-radius: 0 0 .34em .06em; overflow: hidden; }
.shirt { position: absolute; left: 50%; top: 0; width: .16em; height: .3em; margin-left: -.08em; background: #fff; clip-path: polygon(0 0, 100% 0, 50% 100%); }
.tie { position: absolute; top: .015em; width: .075em; height: .075em; background: var(--orange); }
.tie.l { left: 50%; margin-left: -.085em; clip-path: polygon(0 0, 100% 50%, 0 100%); }
.tie.r { left: 50%; margin-left: .01em; clip-path: polygon(100% 0, 0 50%, 100% 100%); }
.knot { position: absolute; top: .03em; left: 50%; margin-left: -.014em; width: .028em; height: .035em; background: #c76f00; border-radius: 1px; }
.hat { position: absolute; z-index: 2; left: 25%; top: -.22em; width: .5em; height: .27em; transform: rotate(-4deg); animation: bob 3s ease-in-out infinite; }
.hat::before { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: .06em; background: var(--ink); border-radius: .04em; }
.hat::after { content: ''; position: absolute; left: .08em; right: .08em; bottom: .05em; height: .2em; background: #2b2b2b; border-radius: .03em .03em 0 0; }
.hat i { position: absolute; z-index: 1; left: .08em; right: .08em; bottom: .06em; height: .04em; background: var(--orange); }

/* glasses */
.gl { position: absolute; top: .325em; width: .22em; height: .22em; border-radius: 50%; border: .025em solid var(--ink); background: rgba(255, 255, 255, .35); }
.gl.l { left: .235em; } .gl.r { right: .235em; }
.gl.bridge { top: .42em; left: 50%; width: .07em; height: 0; margin-left: -.035em; border: 0; border-top: .025em solid var(--ink); border-radius: 0; background: none; }

/* serious */
.m-serious .eye { animation: none; height: .075em; border-radius: .03em; top: 38%; }
.m-serious .eye::before { content: ''; position: absolute; left: -.015em; right: -.015em; top: -.06em; border-top: .028em solid var(--ink); }
.m-serious .eye.l::before { transform: rotate(8deg); } .m-serious .eye.r::before { transform: rotate(-8deg); }
.m-serious .mouth { width: .1em; height: 0; margin-left: -.05em; border-radius: 0; border-bottom: .025em solid var(--ink); }
.m-serious .cheek { opacity: .2; }

/* fx */
.fx { position: absolute; opacity: 0; font-weight: 900; color: var(--orange); pointer-events: none; }
.zzz { right: -.1em; top: -.1em; font-size: .28em; } .zzz small { font-size: .7em; margin-left: .05em; }
.q { right: -.08em; top: -.18em; font-size: .36em; } .bang { right: .05em; top: -.2em; font-size: .38em; color: var(--ink); }
.conf { left: 50%; top: 40%; width: .06em; height: .06em; border-radius: 1px; }

/* happy */
.m-happy .body, .m-celebrate .body { animation: squish 1.1s ease-in-out infinite; }
.m-happy .eye, .m-celebrate .eye { animation: none; height: .08em; width: .14em; background: transparent; border-top: .035em solid var(--ink); border-radius: .1em .1em 0 0; top: 38%; }
.m-happy .mouth, .m-celebrate .mouth { width: .17em; height: .09em; margin-left: -.085em; background: var(--ink); border: 0; border-radius: .02em .02em .1em .1em; top: 56%; }
.m-happy .cheek, .m-celebrate .cheek { opacity: .75; }

/* wave */
.m-wave .mouth { width: .13em; height: .07em; margin-left: -.065em; border-bottom-width: .025em; }

/* thinking */
.m-thinking .eye { animation: none; transform: translate(.03em, -.035em); }
.m-thinking .body { animation: tilt 2.4s ease-in-out infinite; }
.m-thinking .mouth { width: .06em; height: 0; margin-left: -.01em; border-bottom: .022em solid var(--ink); border-radius: 0; transform: rotate(-8deg); }
.m-thinking .q { opacity: 1; animation: pop 2.4s ease-in-out infinite; }

/* sleepy */
.m-sleepy .body { animation: breathe 3.6s ease-in-out infinite; }
.m-sleepy .eye { animation: none; height: .02em; border-radius: .1em; top: 42%; }
.m-sleepy .mouth { width: .05em; height: .05em; margin-left: -.025em; border: .02em solid var(--ink); border-radius: 50%; }
.m-sleepy .zzz { opacity: 1; animation: zzz 2.8s ease-out infinite; }

/* surprised */
.m-surprised .jump { animation: startle .6s ease-out 1; }
.m-surprised .eye { animation: none; width: .17em; height: .2em; top: 32%; }
.m-surprised .mouth { width: .07em; height: .09em; margin-left: -.035em; border: .025em solid var(--ink); border-radius: 50%; }
.m-surprised .bang { opacity: 1; }

/* celebrate */
.m-celebrate .jump { animation: hop 1.1s cubic-bezier(.3, .7, .4, 1) infinite; }
.m-celebrate .conf { animation: confetti 1.1s ease-out infinite; }

@keyframes bob { 0%, 100% { transform: translateY(0) scale(1, 1); } 50% { transform: translateY(-.025em) scale(1.015, .985); } }
@keyframes shadow { 0%, 100% { transform: scaleX(1); opacity: 1; } 50% { transform: scaleX(.92); opacity: .75; } }
@keyframes blink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(.1); } }
@keyframes squish { 0%, 100% { transform: scale(1, 1); } 25% { transform: scale(1.06, .92); } 55% { transform: scale(.96, 1.06); } }
@keyframes hop { 0%, 100% { transform: translateY(0); } 40% { transform: translateY(-.28em) rotate(-4deg); } 70% { transform: translateY(-.05em) rotate(3deg); } }
@keyframes tilt { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(-6deg); } }
@keyframes breathe { 0%, 100% { transform: scale(1, .96); } 50% { transform: scale(1.03, 1); } }
@keyframes zzz { 0% { opacity: 0; transform: translate(0, .1em) scale(.6); } 30% { opacity: 1; } 100% { opacity: 0; transform: translate(.12em, -.2em) scale(1.1); } }
@keyframes pop { 0%, 100% { transform: scale(.9) rotate(8deg); } 50% { transform: scale(1.1) rotate(-6deg); } }
@keyframes startle { 0% { transform: translateY(0) scale(1); } 25% { transform: translateY(-.12em) scale(.92, 1.1); } 100% { transform: translateY(0) scale(1); } }
@keyframes confetti { 0% { opacity: 1; transform: translate(0, 0) rotate(0); } 100% { opacity: 0; transform: translate(var(--tx), var(--ty)) rotate(280deg); } }

@media (prefers-reduced-motion: reduce) { .mascot * { animation: none !important; } }

/* ---- bee identity ---- */
.ant { position: absolute; top: -.13em; width: .03em; height: .16em; background: var(--ink); border-radius: .02em; z-index: 0; transform-origin: 50% 100%; }
.ant::after { content: ''; position: absolute; top: -.035em; left: -.02em; width: .07em; height: .07em; border-radius: 50%; background: var(--ink); }
.ant.l { left: 33%; transform: rotate(-18deg); } .ant.r { right: 33%; transform: rotate(18deg); }
.marks { position: absolute; inset: 0; width: 100%; height: 100%; border-radius: inherit; overflow: hidden; pointer-events: none; }
.marks { clip-path: inset(0 round .34em .34em .34em .06em); }
.stripes rect { fill: var(--orange); opacity: .45; }
.suited .marks { display: none; }
.b-libbee .stripes rect { fill: var(--orange); opacity: .4; }
.b-tobee .stripes rect { fill: var(--ink); opacity: .92; }
.b-tobee .body { inset: 0 -.025em 0 -.025em; }
.b-tobee .ant { height: .18em; }
.b-barnabee .stripes rect, .b-phoebee .stripes rect { fill: #2a2118; opacity: .9; }
.b-barnabee .body { border-radius: .38em .38em .36em .06em; inset: .05em -.07em 0 -.07em; }
.b-phoebee { transform: scale(.84); transform-origin: 50% 100%; }
.b-phoebee .body { border-radius: .36em; }
.lanyard { position: absolute; inset: 0; width: 100%; height: 100%; overflow: hidden; pointer-events: none; z-index: 1; }

/* tired manager face */
.tired .eye { background: #fff; width: .17em; height: .15em; top: 33%; border: .02em solid var(--ink); animation: none; overflow: hidden; }
.tired .eye::after { content: ''; position: absolute; left: .055em; top: .07em; width: .055em; height: .055em; border-radius: 50%; background: var(--ink); }
.tired .lid { position: absolute; top: 33%; width: .19em; height: .065em; background: var(--yellow); border-bottom: .022em solid var(--ink); z-index: 2; transform-origin: 50% 0; animation: droop 5s ease-in-out infinite; }
.tired .lid.l { left: calc(28% - .01em); } .tired .lid.r { right: calc(28% - .01em); }
.tired .eye.l { left: 28%; } .tired .eye.r { right: 28%; }
.tired .bag { position: absolute; top: 47%; width: .2em; height: .05em; border-radius: 0 0 .1em .1em; background: #8f6a7a; opacity: .55; z-index: 1; }
.tired .bag.l { left: calc(28% - .01em); } .tired .bag.r { right: calc(28% - .01em); }
.tired.m-idle .mouth, .tired.m-wave .mouth, .tired.m-serious .mouth { width: .12em; height: 0; margin-left: -.06em; border-bottom: .025em solid var(--ink); border-radius: 0; transform: rotate(-4deg) translateY(.01em); }
.tired .cheek { opacity: .2; }
.tired.m-happy .lid, .tired.m-celebrate .lid, .tired.m-surprised .lid { display: none; }
.tired.m-happy .eye, .tired.m-celebrate .eye { background: transparent; border: 0; border-top: .035em solid var(--ink); width: .14em; height: .08em; }
.tired.m-happy .eye::after, .tired.m-celebrate .eye::after, .tired.m-surprised .eye::after { display: none; }
.tired.m-surprised .eye { width: .17em; height: .2em; }
.tired.m-sleepy .lid, .tired.m-sleepy .eye::after { display: none; }
.tired.m-thinking .lid { top: 33%; }
.lash { position: absolute; top: 31%; width: .07em; height: .025em; border-top: .025em solid var(--ink); z-index: 3; }
.lash.l { left: calc(28% - .035em); transform: rotate(-30deg); } .lash.r { right: calc(28% - .035em); transform: rotate(30deg); }
@keyframes droop { 0%, 90%, 100% { transform: scaleY(1); } 94% { transform: scaleY(1.9); } }
</style>
