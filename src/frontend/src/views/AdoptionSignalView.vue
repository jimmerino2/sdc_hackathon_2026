<script setup lang="ts">
// Test page (not in the flow yet): SignalView's layout, showing the AI adoption Monte Carlo and this week's odds.
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import ChartWatcher from '../components/ChartWatcher.vue';
import Icon from '../components/Icon.vue';
import { scenarios, type ScenarioKey } from '../data/flows';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { SOFTWARE_DEVELOPERS_ONET } from '../api/forecast';
import { API_URL } from '../api/config';
import {
  adoptionScenario, fetchJobAdoption, fetchOddsHistory, fetchSkillDemand, monthYear, pct,
  type AdoptionOutlook, type OddsWeek, type SkillDemandPoint,
} from '../api/adoption';

const route = useRoute();
const { state } = useFlow();
/** The role to show: ?role= from the roles test page, else the chosen role, else Software Developers. */
const onetCode = computed(() => (route.query.role as string | undefined) ?? state.value.chosenRoleId ?? SOFTWARE_DEVELOPERS_ONET);
const icons = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;
const blurbs: Record<ScenarioKey, string> = {
  accelerates: 'AI use at work grows faster than its pace over the last two years.',
  steady: 'AI use keeps growing at today’s pace.',
  slows: 'AI use slips back: cost, rules or backlash slow it down.',
};
const active = computed(() => state.value.scenario);

const data = ref<AdoptionOutlook | null>(null);
const history = ref<OddsWeek[]>([]);
const demand = ref<SkillDemandPoint[]>([]);
const status = ref<'loading' | 'ready' | 'error'>('loading');

onMounted(async () => {
  try {
    data.value = await fetchJobAdoption(onetCode.value);
    if (data.value) [history.value, demand.value] = await Promise.all([fetchOddsHistory(data.value.soc_major), fetchSkillDemand(onetCode.value)]);
    status.value = data.value ? 'ready' : 'error';
  } catch {
    status.value = 'error';
  }
});

function scen(k: ScenarioKey) {
  return data.value?.scenarios.find((s) => s.scenario === adoptionScenario[k]);
}
/** Middle estimate (% of workers) at months 0, 3, 6, 9, 12 for one scenario. */
function series(k: ScenarioKey): { m: number; v: number }[] {
  const s = scen(k);
  if (!s || !data.value) return [];
  return [{ m: 0, v: data.value.current_rate * 100 }, ...s.outlook.map((o) => ({ m: o.horizon_months, v: o.p50 * 100 }))];
}

// Chart geometry: x = months ahead, y = % of workers using AI at work.
const X0 = 34, X1 = 420, Y0 = 8, Y1 = 172;
const band = computed(() => scen(active.value)?.outlook ?? []);
const yRange = computed(() => {
  const vals = scenarios.flatMap((s) => series(s.key).map((p) => p.v));
  for (const o of band.value) vals.push(o.p10 * 100, o.p90 * 100);
  if (!vals.length) return { lo: 0, hi: 100 };
  return { lo: Math.max(0, Math.floor(Math.min(...vals) / 10) * 10), hi: Math.min(100, Math.ceil(Math.max(...vals) / 10) * 10) };
});
const sx = (m: number) => X0 + (m / 12) * (X1 - X0);
const sy = (v: number) => Y1 - ((v - yRange.value.lo) / (yRange.value.hi - yRange.value.lo)) * (Y1 - Y0);
const ticks = computed(() => {
  const out: number[] = [];
  for (let t = yRange.value.lo; t <= yRange.value.hi; t += 10) out.push(t);
  return out;
});
const pts = (k: ScenarioKey) => series(k).map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
const rangePoly = computed(() => {
  const o = band.value, now = (data.value?.current_rate ?? 0) * 100;
  if (!o.length) return '';
  const up = [{ m: 0, v: now }, ...o.map((h) => ({ m: h.horizon_months, v: h.p90 * 100 }))];
  const dn = [{ m: 0, v: now }, ...o.map((h) => ({ m: h.horizon_months, v: h.p10 * 100 }))].reverse();
  return [...up, ...dn].map((p) => `${sx(p.m)},${sy(p.v)}`).join(' ');
});
const endLabel = computed(() => {
  const l = series(active.value).at(-1);
  return l ? `${Math.round(l.v)}%` : '';
});
const axis = computed(() => (data.value ? [`${data.value.forecast_from} · today`, ...data.value.scenarios[0]!.outlook.map((o) => o.forecast_for)] : []));
/** e.g. "29% likely · 82% by Jul 2027". */
function outcome(k: ScenarioKey) {
  const s = scen(k), l = s?.outlook.at(-1);
  if (!s || !l) return 'No forecast yet';
  return `${pct(s.probability)} likely · ${pct(l.p50)} by ${monthYear(l.forecast_for)}`;
}
const title = computed(() => data.value?.title ?? 'This role');
const score = computed(() => data.value?.score ?? null);
const signals = computed(() => [...(score.value?.signals ?? [])].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)));
const lean = computed(() => {
  const s = score.value?.score ?? 0;
  return s > 0.15 ? 'toward AI accelerating' : s < -0.15 ? 'toward AI slowing' : 'roughly balanced';
});
/** Latest week's ad share per skill, highest first. */
const skills = computed(() => {
  const wk = demand.value.reduce((m, d) => (d.week > m ? d.week : m), '');
  return demand.value.filter((d) => d.week === wk).sort((a, b) => b.share - a.share);
});
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === onetCode.value));
const firstName = computed(() => state.value.name.trim().split(/\s+/)[0] ?? '');
</script>

<template>
  <FlowShell :progress="5" next="sync" next-label="Build my pathway" back="adoption-roles" @next="state.chosenRoleId = onetCode">
    <div class="wrap">
      <section class="left">
        <p class="lab"><Icon name="sparkles" :size="14" /> Test page · AI adoption scenarios</p>
        <p class="eyebrow">Your AI signal</p>
        <h1>How much AI will {{ title }} use?</h1>
        <div class="card chart">
          <small>{{ title }} · AI use at work</small>
          <h2>Three possible futures, next 12 months</h2>
          <p v-if="status === 'loading'" class="state">Running the Monte Carlo scenarios…</p>
          <p v-else-if="status === 'error'" class="state">Couldn’t load AI adoption for this role from {{ API_URL }}. Make sure that backend is running and up to date.</p>
          <template v-else>
            <svg viewBox="0 0 440 190" role="img" :aria-label="`Share of ${title} using AI at work under three scenarios`">
              <g stroke="#eceae5"><line v-for="t in ticks" :key="t" :x1="X0" :x2="X1" :y1="sy(t)" :y2="sy(t)" /></g>
              <text v-for="t in ticks" :key="'l' + t" :x="X0 - 6" :y="sy(t) + 3" font-size="9" font-weight="800" text-anchor="end" fill="#8a8782">{{ t }}%</text>
              <polygon :points="rangePoly" fill="#fff3cc" opacity=".7" />
              <polyline v-for="s in scenarios.filter((x) => x.key !== active)" :key="s.key" :points="pts(s.key)" fill="none" stroke="#c2bfba" stroke-width="3" stroke-dasharray="2 5" stroke-linecap="round" />
              <polyline :points="pts(active)" fill="none" stroke="#ff9800" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
              <circle v-for="p in series(active)" :key="p.m" :cx="sx(p.m)" :cy="sy(p.v)" r="4" fill="#1e1e1e" />
              <text :x="X1" :y="sy(series(active).at(-1)?.v ?? 0) - 10" font-size="11" font-weight="900" text-anchor="end" fill="#1e1e1e">{{ endLabel }}</text>
            </svg>
            <div class="axis"><span v-for="a in axis" :key="a">{{ a }}</span></div>
            <p class="note">
              Share of {{ title }} who say they use AI for their job, today {{ pct(data!.current_rate) }}, simulated 10,000 times under each future.
              Shaded band is the likely range (10–90%) for the selected future. {{ data!.is_proxy_for_malaysia ? 'US survey data stands in for Malaysia. ' : '' }}Not a measure of job loss.
            </p>
          </template>
        </div>
      </section>
      <section class="right">
        <ChartWatcher class="bub">I re-check the odds every week as new evidence comes in.</ChartWatcher>
        <button v-for="s in scenarios" :key="s.key" class="option sc" :class="{ selected: state.scenario === s.key }" @click="state.scenario = s.key">
          <span class="ic"><Icon :name="icons[s.key]" :size="22" /></span>
          <span>
            <em class="pill" :class="{ 'pill-yellow': state.scenario === s.key }">{{ outcome(s.key) }}</em>
            <h3>{{ s.title }}</h3><p>{{ blurbs[s.key] }}</p>
          </span>
          <span v-if="state.scenario === s.key" class="tick"><Icon name="check" :size="14" :stroke="3" /></span>
        </button>
        <p class="hint">Odds from {{ score?.week ?? 'the default starting point' }} · tap a future to see it on the chart.</p>
      </section>

      <section v-if="status === 'ready'" class="why-row">
        <p class="eyebrow">Why the odds moved</p>
        <h1>This week’s evidence leans {{ lean }}</h1>
        <div class="gap-cards">
          <div class="card block">
            <div class="head"><h2>What we saw</h2><span class="pill pill-dark">{{ signals.length }} signals</span></div>
            <ul v-if="signals.length" class="sig">
              <li v-for="(s, i) in signals" :key="i">
                <span class="ic2" :class="s.value >= 0 ? 'up' : 'down'"><Icon :name="s.kind === 'news' ? 'file' : 'chart-bar'" :size="16" /></span>
                <span>
                  <a v-if="s.url" :href="s.url" target="_blank" rel="noopener">{{ s.label }}</a><template v-else>{{ s.label }}</template>
                  <small>{{ s.kind === 'news' ? 'News' : 'Data' }} · {{ s.source }} · pushes {{ s.value >= 0 ? 'toward faster' : 'toward slower' }} adoption</small>
                </span>
              </li>
            </ul>
            <p v-else class="empty">No scoring run yet: the odds are the 25 / 50 / 25 starting point.</p>
          </div>
          <div class="card block">
            <div class="head"><h2>Odds over time</h2><span class="pill">{{ history.length }} {{ history.length === 1 ? 'week' : 'weeks' }}</span></div>
            <div v-if="history.length" class="hist">
              <div v-for="w in history" :key="w.week" class="wk">
                <span class="wl">{{ w.week }}</span>
                <span class="stack">
                  <i class="a" :style="{ width: w.p_accelerates * 100 + '%' }">{{ pct(w.p_accelerates) }}</i>
                  <i class="h" :style="{ width: w.p_holds * 100 + '%' }">{{ pct(w.p_holds) }}</i>
                  <i class="d" :style="{ width: w.p_declines * 100 + '%' }">{{ pct(w.p_declines) }}</i>
                </span>
              </div>
              <p class="legend"><i class="a" /> accelerates <i class="h" /> holds <i class="d" /> declines</p>
            </div>
            <p v-else class="empty">The first weekly scoring run will start the history.</p>
          </div>
        </div>
      </section>

      <section class="gap-row">
        <p class="eyebrow">Skills in demand</p>
        <h1>What employers ask for in {{ title }} ads</h1>
        <div class="gap-cards">
          <div class="card block">
            <div class="head"><h2>Live job ads</h2><span class="pill">{{ skills[0]?.week ?? 'collecting' }}</span></div>
            <ul v-if="skills.length" class="bars">
              <li v-for="s in skills" :key="s.skill"><span>{{ s.skill }}</span><i :style="{ width: Math.max(2, (s.share / skills[0]!.share) * 100) + '%' }" /><b>{{ s.ads.toLocaleString() }}</b></li>
            </ul>
            <p v-else class="empty">Skill counts come from a monthly Adzuna run (US ads), filled over three days to stay within the free tier. None yet for this role.</p>
          </div>
          <div class="card block">
            <div class="head"><h2>Your skill gap</h2><span class="pill">{{ job ? `${job.skills_owned} of ${job.skills_total}` : 'not signed in' }}</span></div>
            <template v-if="job">
              <Bubble class="b" :size="48">You already have {{ job.skills_owned }} of {{ job.skills_total }} key skills{{ firstName ? `, ${firstName}` : '' }}.</Bubble>
              <div class="chips">
                <span v-for="s in job.skills_you_have" :key="s" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s) }}</span>
                <span v-for="s in job.skills_to_learn" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="14" /> {{ skillLabel(s) }}</span>
              </div>
            </template>
            <p v-else class="empty">Pick this role from your matches to see which skills you already have and which to build.</p>
          </div>
        </div>
      </section>
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; width: min(1180px, 94vw); margin-left: 50%; transform: translateX(-50%); padding-top: 0; }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
.lab { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; margin-bottom: 10px; padding: 4px 12px; border-radius: 999px; background: var(--cream); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--orange); }
h1 { font-size: 30px; font-weight: 900; margin: 6px 0 22px; line-height: 1.15; }
.chart { padding: 22px 24px; }
.chart small { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.chart h2 { font-weight: 900; font-size: 20px; margin: 6px 0 14px; }
svg { width: 100%; overflow: visible; margin-top: 16px; }
.state { margin: 18px 0 6px; font-size: 13px; font-weight: 700; color: var(--muted); }
.axis { display: flex; justify-content: space-between; font-size: 10px; font-weight: 900; color: var(--muted); letter-spacing: .05em; text-transform: uppercase; margin-top: 8px; }
.note { margin-top: 14px; font-size: 11px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.right { display: flex; flex-direction: column; gap: 14px; }
.bub { margin-bottom: 8px; flex-direction: row-reverse; }
.sc { align-items: flex-start; } .sc h3 { margin-top: 4px; font-size: 17px; }
.sc p { font-size: 13px; line-height: 1.35; }
.hint { font-size: 12px; font-weight: 700; color: var(--muted); }
.why-row, .gap-row { grid-column: 1 / -1; margin-top: 12px; }
.gap-row .b { margin-bottom: 14px; }
.gap-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.block { padding: 20px 22px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.head h2 { font-weight: 900; font-size: 17px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.empty { font-size: 13px; font-weight: 700; color: var(--muted); }
.sig { list-style: none; display: flex; flex-direction: column; gap: 12px; }
.sig li { display: flex; gap: 10px; align-items: flex-start; font-size: 13px; font-weight: 700; line-height: 1.35; }
.sig a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--line-strong); }
.sig small { display: block; margin-top: 2px; font-size: 11px; color: var(--muted); font-weight: 600; }
.ic2 { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; flex: none; }
.ic2.up { background: var(--cream); color: var(--orange); }
.ic2.down { background: var(--line); color: var(--muted); }
.hist { display: flex; flex-direction: column; gap: 8px; }
.wk { display: flex; align-items: center; gap: 10px; }
.wl { width: 72px; font-size: 11px; font-weight: 900; color: var(--muted); }
.stack { flex: 1; display: flex; height: 26px; border-radius: 8px; overflow: hidden; }
.stack i, .legend i { font-style: normal; font-size: 11px; font-weight: 900; display: grid; place-items: center; }
.a { background: var(--yellow); } .h { background: var(--cream); } .d { background: var(--line); color: var(--muted); }
.legend { margin-top: 6px; display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: var(--muted); }
.legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-left: 8px; }
.bars { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.bars li { display: grid; grid-template-columns: 140px 1fr 64px; align-items: center; gap: 10px; font-size: 13px; font-weight: 700; }
.bars i { height: 12px; border-radius: 6px; background: var(--yellow); }
.bars b { text-align: right; font-size: 12px; color: var(--muted); }
@media (max-width: 900px) { .wrap, .gap-cards { grid-template-columns: 1fr; } }
</style>
