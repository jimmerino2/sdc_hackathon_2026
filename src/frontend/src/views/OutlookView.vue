<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { fetchOutlook, fetchTargets, type OutlookRow, type OutlookStatus, type TargetSummary } from '../api/outlook';
import { COUNTRIES, OCCUPATIONS, SECTORS } from '../data/outlookNames';

/** One card per forecast target. They measure different things and are never combined. */
interface Card {
  target: string;
  eyebrow: string;
  title: string;
  blurb: string;
  names?: Record<string, string>;
  /** Unit code as the API reports it -> the key used in `names` (BTOS units carry their question wording). */
  key?: (unit: string) => string;
  defaultUnit: string;
  pickerLabel?: string;
  minutes?: boolean;
}

const cards: Card[] = [
  {
    target: 'frontier_time_horizon', eyebrow: 'AI capability', title: 'How long a task can the best AI finish?',
    blurb: 'Length of software tasks (in a skilled person’s working time) the best measured model completes half the time. Source: METR, via Epoch AI.',
    defaultUnit: 'v1.1', minutes: true,
  },
  {
    target: 'ai_mention_share', eyebrow: 'Skill demand', title: 'How many job ads ask for AI?',
    blurb: 'Share of new job ads that mention AI. Source: Indeed Hiring Lab.',
    names: COUNTRIES, defaultUnit: 'US', pickerLabel: 'Country',
  },
  {
    target: 'btos_ai_use_rate', eyebrow: 'Business adoption', title: 'How many US businesses use AI?',
    blurb: 'Share of US businesses that used AI in the last two weeks. Source: US Census Bureau survey.',
    names: SECTORS, key: (u) => u.split('|')[0], defaultUnit: 'US|new', pickerLabel: 'Sector',
  },
  {
    target: 'worker_genai_use_rate', eyebrow: 'Worker adoption', title: 'How many workers use AI on the job?',
    blurb: 'Share of employed US adults using generative AI for their job. Source: Real-Time Population Survey.',
    names: OCCUPATIONS, defaultUnit: '00', pickerLabel: 'Occupation group',
  },
];

const status = ref<'loading' | 'done' | 'error'>('loading');
const summaries = ref<Record<string, TargetSummary>>({});
const rows = ref<Record<string, OutlookRow[]>>({});
const picked = reactive<Record<string, string>>(Object.fromEntries(cards.map((c) => [c.target, c.defaultUnit])));

async function load() {
  status.value = 'loading';
  try {
    const list = await fetchTargets();
    summaries.value = Object.fromEntries(list.map((t) => [t.target, t]));
    const got = await Promise.all(list.map((t) => fetchOutlook(t.target)));
    rows.value = Object.fromEntries(list.map((t, i) => [t.target, got[i]]));
    status.value = 'done';
  } catch {
    status.value = 'error';
  }
}
onMounted(load);

const shown = computed(() => cards.filter((c) => rows.value[c.target]?.length));

function units(c: Card): string[] {
  return [...new Set((rows.value[c.target] ?? []).map((r) => r.unit))];
}
function unitName(c: Card, u: string): string {
  return c.names?.[c.key ? c.key(u) : u] ?? u;
}
function selected(c: Card): OutlookRow[] {
  const all = rows.value[c.target] ?? [];
  const u = all.some((r) => r.unit === picked[c.target]) ? picked[c.target] : all[0]?.unit;
  return all.filter((r) => r.unit === u).sort((a, b) => a.h - b.h);
}

function fmt(c: Card, v: number | null): string {
  if (v == null) return '–';
  if (!c.minutes) return `${v.toFixed(1)}%`;
  if (v < 90) return `${Math.round(v)} min`;
  const h = v / 60;
  return `${h < 10 ? h.toFixed(1) : Math.round(h).toLocaleString('en')} hours`;
}
function horizon(r: OutlookRow): string {
  if (r.period_unit === 'fortnight') return `in about ${Math.round((r.h * 14) / 30.4)} months`;
  if (r.period_unit === 'quarter') return r.h === 1 ? 'next quarter' : `in ${r.h} quarters`;
  return r.h === 1 ? 'next month' : `in ${r.h} months`;
}
/** BTOS periods come as "202701 (ref 2027-01-03)": show the date only. */
function period(p: string): string {
  const m = p.match(/ref (\d{4}-\d{2}-\d{2})/);
  const d = m ? new Date(m[1]) : /^\d{4}-\d{2}$/.test(p) ? new Date(`${p}-01`) : null;
  if (d && !isNaN(+d)) return d.toLocaleDateString('en', m ? { day: 'numeric', month: 'short', year: 'numeric' } : { month: 'short', year: 'numeric' });
  const q = p.match(/^(\d{4})Q(\d)$/);
  return q ? `Q${q[2]} ${q[1]}` : p;
}

const STATUS: Record<OutlookStatus, { label: string; tone: 'good' | 'neutral' | 'caution'; icon: string }> = {
  validated: { label: 'Beat “no change” in testing', tone: 'good', icon: 'check' },
  baseline: { label: 'No model beat “no change”', tone: 'neutral', icon: 'scale' },
  not_demonstrably_better: { label: 'Not shown to beat “no change”', tone: 'caution', icon: 'shield-alert' },
  baseline_retained: { label: 'Model failed its test: showing “no change”', tone: 'caution', icon: 'shield-alert' },
};

/** One shared scale per card so the horizons compare at a glance; log for time horizons (they double). */
function scale(c: Card, rs: OutlookRow[]) {
  const vals = rs.flatMap((r) => [r.low ?? r.forecast, r.high ?? r.forecast, r.forecast, r.last_observed]);
  const f = (v: number) => (c.minutes ? Math.log2(v) : v);
  let lo = Math.min(...vals.map(f));
  let hi = Math.max(...vals.map(f));
  const pad = (hi - lo) * 0.06 || 1;
  lo -= pad;
  hi += pad;
  return (v: number | null) => (v == null ? 0 : ((f(v) - lo) / (hi - lo)) * 100);
}

function warnings(rs: OutlookRow[]): string[] {
  return [...new Set(rs.flatMap((r) => r.warnings))];
}
function asOf(c: Card): string | null {
  const s = summaries.value[c.target];
  const h = s && Object.values(s.source_health)[0];
  return h?.last_available_at ? new Date(h.last_available_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' }) : null;
}
const REGIMES = [
  { key: 'p_acceleration', label: 'Faster', color: '#eb6834' },
  { key: 'p_stable', label: 'About the same', color: '#9e9a92' },
  { key: 'p_slowdown', label: 'Slower', color: '#2a78d6' },
] as const;
const pct = (v: number | null) => `${Math.round((v ?? 0) * 100)}%`;
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">AI outlook</p>
      <h1>Where AI and jobs look to be heading</h1>
      <Bubble :size="56" class="intro">
        These are trend outlooks from public data, not promises. Each one says how it did when we tested it on months it hadn’t seen, so you know how much weight to give it.
      </Bubble>

      <div v-if="status === 'loading'" class="grid" aria-busy="true" aria-label="Loading the outlook">
        <span v-for="n in 4" :key="n" class="skel card card-skel" />
      </div>

      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="64">Jobee couldn’t load the outlook just now. Try again in a moment.</Bubble>
        <button type="button" class="btn btn-secondary" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <div v-else class="grid">
        <section v-for="c in shown" :key="c.target" class="card outlook" :aria-labelledby="`h-${c.target}`">
          <p class="kicker">{{ c.eyebrow }}</p>
          <h2 :id="`h-${c.target}`">{{ c.title }}</h2>
          <p class="blurb">{{ c.blurb }}</p>

          <label v-if="c.pickerLabel && units(c).length > 1" class="picker">
            <span>{{ c.pickerLabel }}</span>
            <select v-model="picked[c.target]">
              <option v-for="u in units(c)" :key="u" :value="u">{{ unitName(c, u) }}</option>
            </select>
          </label>

          <template v-for="rs in [selected(c)]" :key="'rs'">
            <p v-if="rs.length" class="now">
              <span class="now-val">{{ fmt(c, rs[0].last_observed) }}</span>
              <span class="now-lbl">latest, {{ period(rs[0].last_observed_period) }}</span>
            </p>

            <ul class="rows">
              <li v-for="r in rs" :key="r.h" class="row">
                <div class="row-head">
                  <span class="when">{{ horizon(r) }} <span class="muted">· {{ period(r.target_period) }}</span></span>
                  <span class="val">{{ fmt(c, r.forecast) }}</span>
                </div>
                <div v-for="s in [scale(c, rs)]" :key="'s'" class="track"
                     :title="`${horizon(r)}: ${fmt(c, r.forecast)} (likely ${fmt(c, r.low)} to ${fmt(c, r.high)})`">
                  <span class="band" :style="{ left: `${s(r.low)}%`, width: `${Math.max(1, s(r.high) - s(r.low))}%` }" />
                  <span class="tick now-tick" :style="{ left: `${s(r.last_observed)}%` }" aria-hidden="true" />
                  <span class="dot" :style="{ left: `${s(r.forecast)}%` }" aria-hidden="true" />
                </div>
                <p class="range">Likely range {{ fmt(c, r.low) }} to {{ fmt(c, r.high) }}</p>
                <p v-if="r.low != null && r.high != null && (r.forecast < r.low || r.forecast > r.high)" class="skew">
                  Forecasts like this have always come in too {{ r.forecast < r.low ? 'low' : 'high' }}, so the range is the better guide here.
                </p>
                <span class="chip" :class="STATUS[r.status].tone">
                  <Icon :name="STATUS[r.status].icon" :size="14" /> {{ STATUS[r.status].label }}
                </span>

                <div v-if="r.p_acceleration != null" class="regime">
                  <p class="regime-q">Will progress speed up {{ horizon(r) }}?</p>
                  <div class="stack" role="img"
                       :aria-label="REGIMES.map((g) => `${g.label} ${pct(r[g.key])}`).join(', ')">
                    <span v-for="g in REGIMES" v-show="(r[g.key] ?? 0) > 0" :key="g.key" class="seg"
                          :style="{ flexGrow: r[g.key] ?? 0, background: g.color }" :title="`${g.label}: ${pct(r[g.key])}`" />
                  </div>
                  <ul class="legend">
                    <li v-for="g in REGIMES" :key="g.key"><span class="sw" :style="{ background: g.color }" />{{ g.label }} <b>{{ pct(r[g.key]) }}</b></li>
                  </ul>
                </div>
              </li>
            </ul>

            <p class="key"><span class="sw-dot" /> forecast <span class="sw-band" /> likely range (80%) <span class="sw-tick" /> latest</p>

            <details v-if="warnings(rs).length" class="notes">
              <summary>What to keep in mind</summary>
              <ul><li v-for="w in warnings(rs)" :key="w">{{ w }}</li></ul>
            </details>
            <p v-if="asOf(c)" class="asof">Data as of {{ asOf(c) }}</p>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; min-width: 0; }
.eyebrow, .kicker { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
h1 { margin: 6px 0 14px; font-size: 28px; line-height: 1.15; }
.intro { margin-bottom: 22px; max-width: 720px; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.card-skel { height: 420px; }
.outlook { padding: 20px; display: flex; flex-direction: column; gap: 10px; }
h2 { font-size: 19px; line-height: 1.25; }
.blurb { font-size: 13px; color: var(--muted); line-height: 1.45; }
.picker { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); }
.picker select { font: inherit; font-size: 14px; font-weight: 700; color: var(--ink); padding: 8px 10px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; }
.now { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.now-val { font-size: 26px; font-weight: 900; }
.now-lbl { font-size: 12px; font-weight: 700; color: var(--muted); }
.rows { list-style: none; display: flex; flex-direction: column; gap: 14px; padding: 0; margin: 0; }
.row { border-top: 2px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 6px; }
.row-head { display: flex; justify-content: space-between; gap: 8px; font-size: 14px; font-weight: 800; }
.muted { color: var(--muted); font-weight: 700; }
.val { font-size: 16px; font-weight: 900; white-space: nowrap; }
.track { position: relative; height: 18px; }
.track::before { content: ''; position: absolute; left: 0; right: 0; top: 8px; height: 2px; background: var(--line); }
.band { position: absolute; top: 4px; height: 10px; border-radius: 4px; background: var(--cream); border: 2px solid var(--yellow); box-sizing: border-box; }
.dot { position: absolute; top: 3px; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; background: var(--ink); box-shadow: 0 0 0 2px #fff; }
.tick { position: absolute; top: 1px; width: 2px; height: 16px; margin-left: -1px; background: var(--muted); }
.range { font-size: 12px; font-weight: 700; color: var(--muted); }
.skew { font-size: 12px; font-weight: 700; color: var(--amber-ink); line-height: 1.4; }
.chip { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.chip.good { background: #e7f4ea; color: #1e5e30; }
.chip.neutral { background: #f0efec; color: var(--ink); }
.chip.caution { background: var(--cream); color: var(--amber-ink); }
.regime { margin-top: 4px; display: flex; flex-direction: column; gap: 6px; }
.regime-q { font-size: 13px; font-weight: 800; }
.stack { display: flex; gap: 2px; height: 12px; }
.seg { border-radius: 4px; min-width: 4px; }
.legend { list-style: none; display: flex; flex-wrap: wrap; gap: 4px 14px; padding: 0; margin: 0; font-size: 12px; font-weight: 700; color: var(--muted); }
.legend b { color: var(--ink); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.key { font-size: 11px; font-weight: 700; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sw-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ink); }
.sw-band { width: 18px; height: 8px; border-radius: 3px; background: var(--cream); border: 2px solid var(--yellow); margin-left: 6px; }
.sw-tick { width: 2px; height: 12px; background: var(--muted); margin-left: 6px; }
.notes { font-size: 12px; color: var(--muted); }
.notes summary { cursor: pointer; font-weight: 800; color: var(--ink); }
.notes ul { margin: 6px 0 0 16px; display: flex; flex-direction: column; gap: 4px; line-height: 1.4; }
.asof { font-size: 11px; font-weight: 700; color: var(--muted); margin-top: auto; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 860px) {
  .grid { grid-template-columns: minmax(0, 1fr); }
  h1 { font-size: 23px; }
}
</style>
