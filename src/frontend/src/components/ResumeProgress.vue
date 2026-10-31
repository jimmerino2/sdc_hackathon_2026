<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import { formatElapsed } from '../composables/useAnalysisClock';

const props = defineProps<{
  filename: string;
  sizeLabel: string;
  /** Null when the PDF couldn't be previewed or has no text layer. */
  stats: { chars: number; pages: number } | null;
  stage: number;
  /** Elapsed ms and the bar's 0-1 value. */
  elapsed: number;
  progress: number;
  slow: boolean;
  /** What the tray shows: skills the AI has confirmed, or keywords from the browser's scan while nothing is confirmed live. */
  tray: { title: string; items: string[]; allConfirmed: boolean };
  /** Words of reasoning the AI has done so far, when the server reports it. */
  thinkingWords: number | null;
  /** How many candidate skills the server picked to check, when known. */
  candidates: number | null;
  expectedSeconds: number;
  /** True once the response is in: the bar fills and every stage is checked. */
  finished: boolean;
}>();

const STEPS = ['Reading your PDF', 'Picking skills to check', 'Matching them against your resume', 'Ranking your strengths'];

const details = computed(() => [
  props.stats
    ? `Found ${props.stats.chars.toLocaleString()} characters on ${props.stats.pages} ${props.stats.pages === 1 ? 'page' : 'pages'}`
    : 'Pulling out the text',
  props.candidates ? `${props.candidates} skills from our library fit what you wrote` : 'Choosing which skills from our library fit',
  props.thinkingWords ? `The AI is working through your experience · ${props.thinkingWords.toLocaleString()} words of reasoning so far` : 'Weighing each one against what you actually did',
  'Ordering what shows up most strongly',
]);
const state = (i: number) => (props.finished || i < props.stage ? 'done' : i === props.stage ? 'active' : 'pending');
const pct = computed(() => Math.round((props.finished ? 1 : props.progress) * 100));
</script>

<template>
  <div class="card file in">
    <span v-if="!finished" class="spin" aria-hidden="true" />
    <div class="name">
      <b>{{ filename }}</b>
      <small>{{ sizeLabel }} · {{ finished ? 'done' : 'analysing' }}</small>
    </div>
  </div>

  <div class="card steps in" style="--i: 1" aria-live="polite">
    <ol>
      <li v-for="(title, i) in STEPS" :key="title" :data-s="state(i)">
        <span class="ico"><Icon name="check" :size="14" :stroke="3.4" /></span>
        <div>
          <b>{{ title }}</b>
          <small v-if="state(i) === 'active'">{{ details[i] }}</small>
          <small v-else-if="state(i) === 'done'">Done</small>
        </div>
      </li>
    </ol>
  </div>

  <div v-if="tray.items.length" class="card tray in" style="--i: 2">
    <p class="eyebrow">{{ tray.title }} <b>{{ tray.items.length }}</b></p>
    <ul>
      <li v-for="k in tray.items" :key="k" :class="{ ok: tray.allConfirmed }">{{ k }}</li>
    </ul>
  </div>

  <div class="card meter in" style="--i: 3">
    <div class="bar" :class="{ slow: slow && !finished }" role="progressbar" aria-label="Analysis progress" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="pct">
      <i :style="{ width: pct + '%' }" />
    </div>
    <div class="meta">
      <span>{{ formatElapsed(elapsed) }}</span>
      <span>{{ slow && !finished ? 'Taking a little longer than usual…' : `Usually about ${expectedSeconds} seconds` }}</span>
    </div>
  </div>
</template>

<style scoped>
.card { padding: 16px 22px; box-shadow: 0 8px 24px rgba(30, 30, 30, .08); margin-top: 14px; }
.card:first-child { margin-top: 0; }
.in { animation: rise .5s cubic-bezier(.22, 1, .36, 1) both; animation-delay: calc(var(--i, 0) * 90ms); }
.file { display: flex; align-items: center; gap: 12px; padding: 12px 16px; }
.name { flex: 1; min-width: 0; }
.name b { display: block; font-size: 16px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
small { display: block; font-size: 15px; line-height: 21px; font-weight: 700; color: var(--muted); }
.spin { flex: none; width: 20px; height: 20px; border-radius: 50%; border: 3px solid var(--line); border-top-color: var(--yellow); animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

ol { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
li[data-s] { display: flex; gap: 12px; align-items: flex-start; transition: opacity .26s; }
li[data-s='pending'] { opacity: .45; }
li b { display: block; font-size: 16px; line-height: 25px; font-weight: 800; }
li small { animation: swap .26s ease-out both; }
.ico { position: relative; flex: none; width: 24px; height: 24px; margin-top: 1px; border-radius: 50%; border: 3px solid var(--line-strong); display: grid; place-items: center; transition: background .26s, border-color .26s; }
.ico svg { display: none; }
[data-s='active'] .ico { border-color: var(--line); border-top-color: var(--yellow); animation: spin .8s linear infinite; }
[data-s='done'] .ico { background: var(--ink); border-color: var(--ink); color: var(--yellow); animation: pop .5s cubic-bezier(.34, 1.56, .64, 1); }
[data-s='done'] .ico svg { display: block; }

.eyebrow { margin: 0 0 10px; font-size: 13px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); display: flex; gap: 8px; align-items: baseline; }
.eyebrow b { color: var(--amber-ink); font-size: 16px; }
.tray ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; min-height: 36px; max-height: 190px; overflow: hidden; }
.tray li { padding: 7px 14px; border-radius: 999px; background: var(--ink); color: #fff; font-size: 15px; line-height: 18px; font-weight: 800; animation: fly .7s cubic-bezier(.34, 1.56, .64, 1) both; transition: background .26s, color .26s; }
.tray li.ok { background: var(--yellow); color: var(--ink); }

.meter { padding-bottom: 12px; }
.bar { height: 12px; border-radius: 999px; background: var(--line); overflow: hidden; }
.bar i { position: relative; display: block; height: 100%; min-width: 2%; border-radius: 999px; background: var(--yellow); overflow: hidden; transition: width .5s cubic-bezier(.22, 1, .36, 1); }
.bar i::after { content: ''; position: absolute; inset: 0; width: 60%; background: rgba(255, 255, 255, .55); animation: shimmer 1.8s ease-in-out infinite; }
.bar.slow i { animation: breathe 1.4s ease-in-out infinite; }
.meta { display: flex; justify-content: space-between; gap: 12px; margin-top: 8px; font-size: 14px; font-weight: 700; color: var(--muted); }

@keyframes rise { from { opacity: 0; transform: translateY(14px) scale(.96); } }
@keyframes swap { from { opacity: 0; transform: translateY(8px); } }
@keyframes pop { 0% { transform: scale(.4); } 60% { transform: scale(1.12); } }
@keyframes fly { 0% { opacity: 0; transform: translate(-120px, -20px) scale(.4) rotate(-12deg); } 70% { opacity: 1; } }
@keyframes shimmer { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
@keyframes breathe { 50% { opacity: .6; } }
@media (prefers-reduced-motion: reduce) { .spin, .ico, .bar i::after, .bar.slow i { animation: none !important; } }
</style>
