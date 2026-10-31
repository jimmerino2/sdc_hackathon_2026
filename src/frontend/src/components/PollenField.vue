<script setup lang="ts">
// First-person view: the camera is Jobee's eyes, flying over a flower field.
const flowers = [
  { x: 0, d: 0, c: '#ff9800' },
  { x: -170, d: 0.9, c: '#fff' },
  { x: 150, d: 1.8, c: '#ffc107' },
  { x: -60, d: 2.7, c: '#ff8a65' },
  { x: 230, d: 3.6, c: '#fff' },
  { x: -240, d: 4.5, c: '#ffc107' },
  { x: 60, d: 5.4, c: '#ff9800' },
  { x: -110, d: 6.3, c: '#fff' },
];
</script>

<template>
  <div class="fpv" role="img" aria-label="First-person view of Jobee flying through a flower field, collecting pollen">
    <div class="world">
      <div class="sun" />
      <div class="hills" />
      <div class="ground"><i v-for="n in 6" :key="n" :style="{ animationDelay: -n * 0.55 + 's' }" /></div>
      <div v-for="(f, i) in flowers" :key="i" class="fl" :style="{ '--x': f.x + 'px', animationDelay: f.d - 7.2 + 's' }">
        <span class="stem" />
        <span class="bloom" :style="{ '--petal': f.c }">
          <i v-for="p in 6" :key="p" :style="{ transform: `rotate(${p * 60}deg) translateY(-.5em)` }" />
          <b />
        </span>
        <span v-for="k in 5" :key="k" class="grain" :style="{ '--gx': (k - 3) * 36 + 'px', '--gy': -20 - (k % 3) * 18 + 'px', animationDelay: f.d - 7.2 + 's' }" />
      </div>
      <span v-for="k in 9" :key="'d' + k" class="dust" :style="{ left: 8 + k * 10 + '%', animationDelay: -k * 0.7 + 's' }" />
    </div>
    <div class="wing l" /><div class="wing r" />
    <div class="hud"><span>Pollen</span><b><i v-for="n in 4" :key="n" :style="{ animationDelay: n * 1.75 - 1.75 + 's' }" /></b></div>
    <span class="tag">Jobee’s view</span>
  </div>
</template>

<style scoped>
.fpv { position: relative; width: 100%; height: 230px; border-radius: 28px; overflow: hidden; margin-bottom: 24px; background: #ffe9a8; isolation: isolate; box-shadow: inset 0 0 0 3px rgba(30, 30, 30, .08); }
.world { position: absolute; inset: -6px; animation: cam 3.4s ease-in-out infinite; }
.world::before { content: ''; position: absolute; inset: 0 0 50% 0; background: linear-gradient(#ffdf80, #fff6d6); }
.sun { position: absolute; left: 62%; top: 12%; width: 36px; height: 36px; border-radius: 50%; background: var(--yellow); box-shadow: 0 0 0 10px rgba(255, 193, 7, .25); }
.hills { position: absolute; left: -10%; right: -10%; top: 33%; height: 70px; background: #bfdc93; border-radius: 50% 50% 0 0; }
.ground { position: absolute; left: 0; right: 0; top: 46%; bottom: 0; background: linear-gradient(#a8d27a, #7dbb55); overflow: hidden; }
.ground i { position: absolute; left: 50%; top: 0; width: 100%; height: 3px; background: rgba(255, 255, 255, .25); transform-origin: 50% 0; animation: stripe 3.3s linear infinite; }

.fl { position: absolute; left: 50%; top: 46%; width: 0; height: 0; font-size: 25px; transform-origin: 0 0; animation: approach 7.2s cubic-bezier(.5, 0, .9, .6) infinite; opacity: 0; }
.stem { position: absolute; left: -2px; top: 0; width: 4px; height: 70px; background: #4f9a39; border-radius: 2px; }
.bloom { position: absolute; left: 0; top: 0; width: 0; height: 0; }
.bloom i { position: absolute; left: -.42em; top: -.42em; width: .84em; height: .84em; border-radius: 50%; background: var(--petal); border: 2px solid rgba(30, 30, 30, .14); }
.bloom b { position: absolute; left: -.4em; top: -.4em; width: .8em; height: .8em; border-radius: 50%; background: var(--ink); z-index: 1; box-shadow: inset 0 0 0 3px var(--yellow); }
.grain { position: absolute; left: 0; top: 0; width: 6px; height: 6px; border-radius: 50%; background: var(--yellow); opacity: 0; animation: grab 7.2s ease-out infinite; }
.dust { position: absolute; top: 40%; width: 4px; height: 4px; border-radius: 50%; background: rgba(255, 193, 7, .8); animation: dust 6s linear infinite; }

.wing { position: absolute; bottom: -34px; width: 150px; height: 110px; background: #fff; border: 4px solid var(--orange); z-index: 3; }
.wing.l { left: -34px; border-radius: 10% 90% 20% 80%; transform-origin: 0 100%; animation: flapL .26s ease-in-out infinite alternate; }
.wing.r { right: -34px; border-radius: 90% 10% 80% 20%; transform-origin: 100% 100%; animation: flapR .26s ease-in-out infinite alternate; }
.hud { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); display: flex; align-items: center; gap: 10px; background: rgba(255, 255, 255, .92); border: 2px solid var(--line-strong); border-radius: 999px; padding: 6px 14px; z-index: 4; font-size: 13px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
.hud b { display: flex; gap: 5px; } .hud b i { width: 12px; height: 12px; border-radius: 50%; background: var(--line); animation: fill 7.2s infinite steps(1, end); }
.tag { position: absolute; left: 14px; top: 12px; z-index: 4; background: var(--ink); color: var(--yellow); font-size: 12px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; padding: 4px 10px; border-radius: 999px; }

@keyframes cam { 0%, 100% { transform: translate(-3px, 2px) rotate(-.6deg); } 50% { transform: translate(3px, -3px) rotate(.6deg); } }
@keyframes approach {
  0% { opacity: 0; transform: translate(0, 0) scale(.05); }
  6% { opacity: 1; }
  85% { opacity: 1; }
  100% { opacity: 0; transform: translate(var(--x), 150px) scale(2.2); }
}
@keyframes grab {
  0%, 70% { opacity: 0; transform: translate(0, 0) scale(.5); }
  76% { opacity: 1; }
  92% { opacity: 0; transform: translate(var(--gx), var(--gy)) scale(1.3); }
  100% { opacity: 0; }
}
@keyframes stripe { 0% { transform: translateY(0) scaleX(.05); opacity: 0; } 15% { opacity: 1; } 100% { transform: translateY(140px) scaleX(1); opacity: 0; } }
@keyframes dust { 0% { transform: translate(0, 0) scale(.4); opacity: 0; } 20% { opacity: 1; } 100% { transform: translate(var(--dx, 40px), 150px) scale(2); opacity: 0; } }
@keyframes flapL { from { transform: rotate(8deg); } to { transform: rotate(-26deg); } }
@keyframes flapR { from { transform: rotate(-8deg); } to { transform: rotate(26deg); } }
@keyframes fill { 0% { background: var(--line); } 25% { background: var(--yellow); } }
@media (prefers-reduced-motion: reduce) { .fpv * { animation: none !important; } }
</style>
