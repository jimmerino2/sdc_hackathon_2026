<script setup lang="ts">
import { computed } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { scenarios } from '../data/flows';
import { useFlow } from '../state';

const { state } = useFlow();
const icons = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;
const hist = '0,150 60,140 130,120 200,95 260,70';
const lines = {
  accelerates: '260,70 340,35 420,0',
  steady: '260,70 340,68 420,64',
  slows: '260,70 340,85 420,108',
};
const active = computed(() => state.value.scenario);
</script>

<template>
  <FlowShell :progress="5" next="roles" next-label="See my future roles" skip-label="Compare all 3" skip-to="roles">
    <div class="wrap">
      <section class="left">
        <p class="eyebrow">Your AI signal</p>
        <h1>Here’s where AI is taking software work</h1>
        <div class="card chart">
          <small>AI adoption in software work</small>
          <h2>Three possible futures, 2026 → 2030</h2>
          <svg viewBox="0 0 440 190" role="img" aria-label="Three scenarios for AI adoption">
            <g stroke="#eceae5"><line v-for="y in [30, 80, 130, 175]" :key="y" x1="0" x2="440" :y1="y" :y2="y" /></g>
            <line x1="260" x2="260" y1="0" y2="180" stroke="#c2bfba" stroke-dasharray="3 4" />
            <polyline :points="hist" fill="none" stroke="#1e1e1e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
            <polygon points="260,70 420,0 420,108" fill="#fff3cc" opacity=".7" />
            <polyline :points="lines.steady" fill="none" stroke="#ffe08a" stroke-width="3" />
            <polyline :points="lines.slows" fill="none" stroke="#c2bfba" stroke-width="3" stroke-dasharray="2 5" stroke-linecap="round" />
            <polyline :points="lines.accelerates" fill="none" :stroke="active === 'accelerates' ? '#ff9800' : '#ffcf66'" stroke-width="5" stroke-linecap="round" />
            <polyline v-if="active === 'steady'" :points="lines.steady" fill="none" stroke="#ff9800" stroke-width="5" stroke-linecap="round" />
            <polyline v-if="active === 'slows'" :points="lines.slows" fill="none" stroke="#ff9800" stroke-width="5" stroke-linecap="round" />
            <circle cx="260" cy="70" r="12" fill="#fff3cc" stroke="#ffc107" stroke-width="2" /><circle cx="260" cy="70" r="6" fill="#1e1e1e" />
            <text x="425" y="-4" font-size="10" font-weight="900" text-anchor="end" fill="#1e1e1e" letter-spacing="1">ACCELERATES</text>
          </svg>
          <div class="axis"><span>2020</span><span>2023</span><span>2026 · today</span><span>2030</span></div>
          <p class="note">Blends Indeed job-posting trends, O*NET task exposure and AI-adoption research. Scenarios are illustrative, not predictions.</p>
        </div>
      </section>
      <section class="right">
        <Bubble :size="56" class="bub">Nobody knows the future for sure, so I plan for all three.</Bubble>
        <button v-for="s in scenarios" :key="s.key" class="option sc" :class="{ selected: state.scenario === s.key }" @click="state.scenario = s.key">
          <span class="ic"><Icon :name="icons[s.key]" :size="22" /></span>
          <span>
            <em class="pill" :class="{ 'pill-yellow': state.scenario === s.key }">{{ s.chance }}% likely</em>
            <h3>{{ s.title }}</h3><p>{{ s.blurb }}</p>
          </span>
          <span v-if="state.scenario === s.key" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
        </button>
        <p class="hint">Tap a future to see the roles that grow in it.</p>
      </section>
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; width: min(1180px, 94vw); margin-left: 50%; transform: translateX(-50%); padding-top: 0; }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
h1 { font-size: 30px; font-weight: 900; margin: 6px 0 22px; line-height: 1.15; }
.chart { padding: 22px 24px; }
.chart small { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.chart h2 { font-weight: 900; font-size: 20px; margin: 6px 0 14px; }
svg { width: 100%; overflow: visible; margin-top: 16px; }
.axis { display: flex; justify-content: space-between; font-size: 10px; font-weight: 900; color: var(--muted); letter-spacing: .05em; text-transform: uppercase; margin-top: 8px; }
.note { margin-top: 14px; font-size: 11px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.right { display: flex; flex-direction: column; gap: 14px; }
.bub { margin-bottom: 8px; flex-direction: row-reverse; }
.sc { align-items: flex-start; } .sc h3 { margin-top: 4px; font-size: 17px; }
.sc p { font-size: 13px; line-height: 1.35; }
.hint { font-size: 12px; font-weight: 700; color: var(--muted); }
@media (max-width: 900px) { .wrap { grid-template-columns: 1fr; } }
</style>
