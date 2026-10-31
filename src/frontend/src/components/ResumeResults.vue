<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import Icon from './Icon.vue';
import { prefersReducedMotion, useCountUp } from '../composables/useCountUp';

export interface SkillRow {
  /** The API's name, which is what the rest of the app knows the skill by. */
  name: string;
  label: string;
  score: number;
  /** Mentions in the resume text: 0 means inferred from context, null means we couldn't look. */
  n: number | null;
}

const props = defineProps<{
  filename: string;
  sizeLabel: string;
  rows: SkillRow[];
  pages: number;
  /** Throw the confetti: a fresh result, not coming back to the page. */
  celebrate?: boolean;
}>();
const emit = defineEmits<{ focus: [label: string | null]; remove: [row: SkillRow] }>();

const SHOWN_CHIPS = 12;
const top = computed(() => props.rows.slice(0, 5));
const rest = computed(() => props.rows.filter((r) => !top.value.includes(r)));
const expanded = ref(false);
const chips = computed(() => (expanded.value ? rest.value : rest.value.slice(0, SHOWN_CHIPS)));
const anyInferred = computed(() => props.rows.some((r) => r.n === 0));
const total = useCountUp(computed(() => props.rows.length), 900);

const leaving = ref<string | null>(null);
function remove(row: SkillRow) {
  emit('focus', null);
  leaving.value = row.name;
  window.setTimeout(() => {
    leaving.value = null;
    emit('remove', row);
  }, prefersReducedMotion() ? 0 : 280);
}

const filled = ref(false);
const burst = ref(false);
onMounted(() => {
  window.setTimeout(() => (filled.value = true), 50);
  if (!props.celebrate || prefersReducedMotion()) return;
  burst.value = true;
  window.setTimeout(() => (burst.value = false), 1200);
});
const pieces = Array.from({ length: 22 }, (_, i) => {
  const a = (i / 22) * Math.PI * 2;
  const r = 70 + (i % 3) * 30;
  return { dx: Math.round(Math.cos(a) * r), dy: Math.round(Math.sin(a) * r * 0.8), c: ['var(--yellow)', 'var(--orange)', '#2f9bff', 'var(--ink)'][i % 4] };
});
const mention = (n: number | null) => (n === null ? '' : n ? `${n}×` : 'inferred');
</script>

<template>
  <div v-if="burst" class="burst" aria-hidden="true"><i v-for="(p, i) in pieces" :key="i" :style="{ '--dx': p.dx + 'px', '--dy': p.dy + 'px', '--c': p.c }" /></div>

  <div class="card file in">
    <div class="name">
      <b>{{ filename }}</b>
      <small>{{ sizeLabel }} · {{ pages }} {{ pages === 1 ? 'page' : 'pages' }}</small>
    </div>
    <span class="read"><Icon name="check" :size="14" :stroke="3" /> Read</span>
  </div>

  <section class="sum in" style="--i: 1">
    <h2>We found <span class="count">{{ total }}</span> {{ rows.length === 1 ? 'skill' : 'skills' }}</h2>
  </section>

  <template v-if="top.length">
    <h3>Your strongest</h3>
    <ol class="top5">
      <li
        v-for="(r, i) in top"
        :key="r.name"
        tabindex="0"
        :style="{ '--i': i }"
        @mouseenter="emit('focus', r.label)"
        @mouseleave="emit('focus', null)"
        @focus="emit('focus', r.label)"
        @blur="emit('focus', null)"
      >
        <span class="rank">{{ i + 1 }}</span>
        <div>
          <b>{{ r.label }} <small v-if="r.n !== null">{{ r.n ? `mentioned ${r.n}×` : 'inferred from context' }}</small></b>
          <div class="meter"><i :style="{ '--i': i, width: filled ? Math.round(r.score * 100) + '%' : '0' }" /></div>
        </div>
        <span class="pct">{{ Math.round(r.score * 100) }}%</span>
      </li>
    </ol>
  </template>

  <h3>{{ top.length ? 'Also in your resume' : 'Your skills' }}</h3>
  <ul class="chips">
    <li
      v-for="(r, i) in chips"
      :key="r.name"
      class="sk"
      :class="{ inf: r.n === 0, out: leaving === r.name }"
      :style="{ '--i': i }"
      @mouseenter="emit('focus', r.label)"
      @mouseleave="emit('focus', null)"
    >
      <span>{{ r.label }}</span>
      <em v-if="mention(r.n)">{{ mention(r.n) }}</em>
      <button type="button" :aria-label="`Remove ${r.label}`" @focus="emit('focus', r.label)" @blur="emit('focus', null)" @click="remove(r)"><Icon name="x" :size="13" :stroke="3" /></button>
    </li>
    <li v-if="!expanded && rest.length > SHOWN_CHIPS"><button type="button" class="pill" @click="expanded = true">+ {{ rest.length - SHOWN_CHIPS }} more</button></li>
  </ul>
  <ul class="key">
    <li><i class="solid" />Named in your resume</li>
    <li v-if="anyInferred"><i class="dashed" />Not named, so the AI inferred it from context</li>
  </ul>
  <p class="help">Tap ✕ to remove a skill that isn’t right.</p>
</template>

<style scoped>
.card { padding: 12px 16px; box-shadow: 0 8px 24px rgba(30, 30, 30, .08); }
.in { animation: rise .5s cubic-bezier(.22, 1, .36, 1) both; animation-delay: calc(var(--i, 0) * 90ms); }
.file { display: flex; align-items: center; gap: 12px; }
.name { flex: 1; min-width: 0; }
.name b { display: block; font-size: 16px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
small { font-size: 14px; font-weight: 700; color: var(--muted); }
.read { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px 4px 10px; border-radius: 999px; background: var(--ink); color: var(--yellow); font-size: 14px; font-weight: 800; flex: none; }

.sum { position: relative; margin-top: 14px; padding: 14px 24px; border-radius: 20px; background: var(--ink); color: #fff; }
.sum h2 { margin: 0; font-size: 25px; line-height: 32px; font-weight: 900; color: #fff; }
.sum .count { display: inline-block; min-width: .6em; color: var(--yellow); }

h3 { margin: 22px 0 12px; font-size: 18px; line-height: 23px; font-weight: 800; }

.top5 { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.top5 li { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto; align-items: center; gap: 14px; padding: 12px 16px; border-radius: 16px; background: #fff; border: 2px solid var(--line); animation: fly .7s cubic-bezier(.34, 1.56, .64, 1) both; animation-delay: calc(var(--i) * 120ms + 200ms); transition: transform .26s cubic-bezier(.34, 1.56, .64, 1), border-color .26s; }
.top5 li:hover, .top5 li:focus-visible { transform: translateX(6px); border-color: var(--yellow); }
.rank { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: var(--yellow); box-shadow: 0 3px 0 var(--orange); font-size: 16px; font-weight: 900; }
.top5 b { display: flex; gap: 8px; align-items: baseline; margin-bottom: 6px; font-size: 16px; line-height: 23px; font-weight: 800; }
.meter { height: 8px; border-radius: 999px; background: var(--line); overflow: hidden; }
.meter i { display: block; height: 100%; border-radius: 999px; background: var(--yellow); transition: width 1s cubic-bezier(.34, 1.56, .64, 1) calc(var(--i, 0) * 120ms + 600ms); }.pct { min-width: 3ch; text-align: right; font-size: 16px; font-weight: 900; }

.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.sk { display: inline-flex; align-items: center; gap: 8px; padding: 7px 8px 7px 14px; border-radius: 999px; background: var(--ink); color: #fff; font-size: 15px; line-height: 18px; font-weight: 800; animation: pop .5s cubic-bezier(.34, 1.56, .64, 1) both; animation-delay: calc(var(--i) * 45ms + 900ms); transition: transform .14s cubic-bezier(.34, 1.56, .64, 1); }
.sk:hover { transform: translateY(-3px) rotate(-2deg); }
.sk em { font-style: normal; font-size: 13px; font-weight: 700; opacity: .8; }
.sk button { display: grid; place-items: center; width: 22px; height: 22px; border: 0; border-radius: 50%; background: transparent; color: inherit; opacity: .6; cursor: pointer; transition: opacity .14s, background .14s, transform .14s cubic-bezier(.34, 1.56, .64, 1); }
.sk button:hover, .sk button:focus-visible { opacity: 1; background: rgba(255, 193, 7, .35); transform: rotate(90deg); }
.sk.inf { background: transparent; color: var(--ink); border: 2px dashed var(--line-strong); padding: 5px 6px 5px 12px; }
.sk.inf button:hover, .sk.inf button:focus-visible { background: var(--line); }
.sk.out { animation: out .3s cubic-bezier(.22, 1, .36, 1) forwards; }
.pill { padding: 7px 14px; border-radius: 999px; border: 0; background: #fff; color: var(--ink); font: inherit; font-size: 15px; font-weight: 800; box-shadow: inset 0 0 0 2px var(--line-strong); cursor: pointer; animation: pop .5s cubic-bezier(.34, 1.56, .64, 1) both; animation-delay: 1.6s; transition: transform .14s cubic-bezier(.34, 1.56, .64, 1); }
.pill:hover { transform: translateY(-2px); }
.key { list-style: none; margin: 14px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 15px; line-height: 21px; font-weight: 700; color: var(--muted); }
.key li { display: inline-flex; align-items: center; gap: 8px; }
.key i { flex: none; width: 26px; height: 16px; border-radius: 999px; }
.key .solid { background: var(--ink); }
.key .dashed { border: 2px dashed var(--line-strong); }
.help { margin: 6px 0 0; font-size: 15px; line-height: 21px; font-weight: 600; color: var(--muted); }

.burst { position: fixed; left: 50%; top: 110px; width: 0; height: 0; z-index: 9; pointer-events: none; }
.burst i { position: absolute; left: 0; top: 0; width: 9px; height: 9px; border-radius: 50%; background: var(--c); animation: burst .85s cubic-bezier(.22, 1, .36, 1) forwards; }

@keyframes rise { from { opacity: 0; transform: translateY(14px) scale(.96); } }
@keyframes pop { 0% { opacity: 0; transform: scale(.4); } 60% { opacity: 1; transform: scale(1.12); } }
@keyframes fly { 0% { opacity: 0; transform: translateY(26px) scale(.9); } }
@keyframes out { to { opacity: 0; transform: scale(.4); } }
@keyframes burst { 0% { transform: translate(-50%, -50%) scale(1); opacity: 1; } 100% { transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(0); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .in, .top5 li, .sk, .pill { animation: none !important; } .meter i { transition: none; } }
</style>
