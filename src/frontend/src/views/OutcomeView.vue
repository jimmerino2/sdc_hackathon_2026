<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';

const { key } = useFlow();
</script>

<template>
  <FlowShell :progress="2.5" next="resume" back="interests" mood="celebrate">
    <template #bubble>{{ personaCopy[key].outcome.say }}</template>
    <ol class="path">
      <li v-for="(g, i) in personaCopy[key].outcome.goals" :key="g" class="stop" :style="{ '--d': i * 0.18 + 's' }">
        <div class="art" aria-hidden="true">
          <!-- roles that fit -->
          <div v-if="i === 0" class="cards">
            <span class="card c1"><b /><i /></span>
            <span class="card c2"><b /><i /><em><Icon name="check" :size="10" :stroke="3.5" /></em></span>
          </div>
          <!-- demand across three AI futures -->
          <svg v-else-if="i === 1" viewBox="0 0 64 44" class="trend">
            <polyline points="4,30 20,28 36,30 60,34" class="ln dim" />
            <polyline points="4,30 20,26 36,24 60,22" class="ln dim" />
            <polyline points="4,30 20,24 36,16 60,8" class="ln hot" />
            <circle cx="60" cy="8" r="3.5" class="dot" />
          </svg>
          <!-- step-by-step plan -->
          <div v-else class="plan">
            <span class="n" /><span class="bar" /><span class="n" /><span class="bar" /><span class="n goal" />
          </div>
        </div>
        <p>{{ g }}</p>
      </li>
    </ol>
  </FlowShell>
</template>

<style scoped>
.path { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; position: relative; }
.stop {
  display: flex; align-items: center; gap: 18px; background: #fff; border: 2px solid var(--line); border-radius: 18px;
  padding: 16px 20px; position: relative;
  animation: rise .5s var(--d) cubic-bezier(.2, .8, .3, 1.15) both;
}
.stop:not(:last-child)::after {
  content: ''; position: absolute; left: 51px; bottom: -16px; height: 16px; border-left: 3px dotted var(--yellow);
}
.stop p { font-size: 18px; font-weight: 800; line-height: 1.3; color: var(--ink); }
.art { flex: none; width: 64px; height: 52px; border-radius: 14px; background: var(--cream); display: grid; place-items: center; overflow: hidden; }

/* roles that fit */
.cards { position: relative; width: 44px; height: 34px; }
.card { position: absolute; width: 34px; height: 24px; border-radius: 6px; background: #fff; border: 2px solid var(--ink); }
.card b { position: absolute; left: 5px; top: 5px; width: 14px; height: 4px; border-radius: 2px; background: var(--ink); }
.card i { position: absolute; left: 5px; top: 12px; width: 20px; height: 3px; border-radius: 2px; background: #d8d3c8; }
.c1 { left: 0; top: 0; opacity: .6; }
.c2 { left: 10px; top: 10px; border-color: var(--orange); animation: slide .6s calc(var(--d) + .35s) cubic-bezier(.2, .8, .3, 1.3) both; }
.c2 em {
  position: absolute; right: -8px; top: -8px; width: 16px; height: 16px; border-radius: 50%; background: var(--orange); color: #fff;
  font-size: 10px; font-style: normal; font-weight: 900; display: grid; place-items: center;
  animation: pop .4s calc(var(--d) + .8s) cubic-bezier(.2, .8, .3, 1.6) both;
}

/* demand across futures */
.trend { width: 52px; height: 36px; }
.ln { fill: none; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 80; stroke-dashoffset: 80; animation: draw .9s calc(var(--d) + .3s) ease-out forwards; }
.dim { stroke: #c2bfba; stroke-width: 2.5; stroke-dasharray: 3 4; animation: none; stroke-dashoffset: 0; }
.hot { stroke: var(--orange); stroke-width: 4; }
.dot { fill: var(--ink); animation: pop .4s calc(var(--d) + 1.1s) cubic-bezier(.2, .8, .3, 1.6) both; transform-origin: 60px 8px; }

/* plan */
.plan { display: flex; align-items: center; }
.n { width: 10px; height: 10px; border-radius: 50%; background: var(--yellow); border: 2px solid var(--ink); animation: pop .35s both; }
.n:nth-child(1) { animation-delay: calc(var(--d) + .3s); }
.n:nth-child(3) { animation-delay: calc(var(--d) + .6s); }
.n.goal { width: 14px; height: 14px; background: var(--orange); animation-delay: calc(var(--d) + .9s); }
.bar { width: 10px; height: 3px; background: var(--ink); transform-origin: 0 50%; animation: grow .3s both; }
.bar:nth-child(2) { animation-delay: calc(var(--d) + .45s); }
.bar:nth-child(4) { animation-delay: calc(var(--d) + .75s); }

@keyframes rise { from { opacity: 0; transform: translateY(14px) scale(.98); } }
@keyframes slide { from { opacity: 0; transform: translate(10px, 8px); } }
@keyframes pop { from { opacity: 0; transform: scale(0); } }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes grow { from { transform: scaleX(0); } }

@media (max-width: 640px) {
  .stop { gap: 14px; padding: 14px 16px; }
  .stop:not(:last-child)::after { left: 47px; }
  .stop p { font-size: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .stop, .c2, .c2 em, .ln, .dot, .n, .bar { animation: none !important; stroke-dashoffset: 0; }
}
</style>
