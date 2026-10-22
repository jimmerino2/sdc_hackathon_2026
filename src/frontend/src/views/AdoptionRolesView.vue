<script setup lang="ts">
// Test page (not in the flow yet): RolesView's layout, showing AI adoption scenarios instead of postings.
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { scenarios } from '../data/flows';
import { skillLabel } from '../data/skills';
import { readProfileId } from '../api/profile';
import { adoptionScenario, fetchJobAdoption, monthYear, pct, type AdoptionOutlook } from '../api/adoption';
import { API_URL } from '../api/config';
import { loadJobs, useFlow } from '../state';

const CHIPS = 3; // skills shown per side on a card
/** A role card: a matched job from /jobs/recommend, or a sample role (no skills, title from the adoption data). */
interface Card { onet_code: string; icon: string; title?: string; rank?: number; skills_you_have?: string[]; skills_to_learn?: string[] }
/** Shown when there is no signed-in profile, so the page can be tested on its own. */
const SAMPLE: Card[] = [
  { onet_code: '15-1252.00', icon: 'code' },
  { onet_code: '13-2011.00', icon: 'calculator' },
  { onet_code: '29-1141.00', icon: 'stethoscope' },
];

const router = useRouter();
const { state, scenario } = useFlow();
const sIcon = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;
const trendIcon = { rising: 'tup', stable: 'arrow', falling: 'tdown' } as const;

const matched = computed(() => state.value.jobs.data?.jobs ?? []);
const roles = computed<Card[]>(() => (matched.value.length ? matched.value : SAMPLE));
const isSample = computed(() => !matched.value.length);
const adoption = ref<Record<string, AdoptionOutlook | null>>({});
const status = ref<'loading' | 'ready' | 'error'>('loading');
const selected = computed(() => state.value.chosenRoleId ?? roles.value[0]?.onet_code ?? null);

async function load() {
  status.value = 'loading';
  try {
    const rows = await Promise.all(roles.value.map((r) => fetchJobAdoption(r.onet_code)));
    adoption.value = Object.fromEntries(roles.value.map((r, i) => [r.onet_code, rows[i]]));
    status.value = 'ready';
  } catch {
    status.value = 'error';
  }
}

/** The selected scenario for one role. */
function sc(code: string) {
  return adoption.value[code]?.scenarios.find((s) => s.scenario === adoptionScenario[state.value.scenario]);
}
function last(code: string) {
  return sc(code)?.outlook.at(-1);
}
/** Change in the 12-month middle estimate vs today, in points: rising above +2, falling below -2. */
function trend(code: string): keyof typeof trendIcon {
  const a = adoption.value[code], l = last(code);
  if (!a || !l) return 'stable';
  const d = (l.p50 - a.current_rate) * 100;
  return d > 2 ? 'rising' : d < -2 ? 'falling' : 'stable';
}
function title(r: Card) {
  return r.title ?? adoption.value[r.onet_code]?.title ?? r.onet_code;
}

/** The heading follows the numbers for this tab. */
const heading = computed(() => {
  const ends = roles.value.map((r) => last(r.onet_code)?.p50).filter((v): v is number => v != null);
  const lead = `If ${scenario.value.title}`;
  if (!ends.length) return `${lead}, here’s how AI use changes in these roles.`;
  const lo = Math.min(...ends), hi = Math.max(...ends);
  return `${lead}, ${pct(lo)}–${pct(hi)} of people in these roles use AI at work within a year.`;
});
const note = computed(() => Object.values(adoption.value).find(Boolean)?.note ?? '');

function openSignal(code: string) {
  state.value.chosenRoleId = code;
  router.push({ name: 'adoption-signal', query: { role: code } });
}

onMounted(async () => {
  // Use the signed-in profile's matches when there are any; otherwise the sample roles.
  state.value.profileId ??= readProfileId();
  if (state.value.jobs.status === 'idle' && state.value.profileId) await loadJobs(state.value);
  await load();
});
watch(() => matched.value.map((j) => j.onet_code).join(), load);
</script>

<template>
  <FlowShell :progress="5" next="adoption-signal" next-label="See the AI signal" back="roles" :next-disabled="!selected" @next="state.chosenRoleId = selected">
    <div class="wrap">
      <p class="lab"><Icon name="sparkles" :size="14" /> Test page · AI adoption scenarios</p>
      <div v-if="status === 'loading' || state.jobs.status === 'loading'" class="state">
        <Bubble :size="70">Running the AI adoption scenarios for your roles…</Bubble>
      </div>

      <div v-else-if="status === 'error'" class="state">
        <Bubble :size="70">Couldn’t reach the AI adoption service at {{ API_URL }}. Make sure that backend is running and up to date.</Bubble>
        <button type="button" class="btn btn-secondary retry" @click="load"><Icon name="refresh" :size="18" /> Try again</button>
      </div>

      <template v-else>
        <div class="bar">
          <div class="tabs">
            <button v-for="s in scenarios" :key="s.key" :class="{ on: state.scenario === s.key }" @click="state.scenario = s.key">
              <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
            </button>
          </div>
        </div>
        <h1>{{ heading }}</h1>
        <div class="cards">
          <button v-for="r in roles" :key="r.onet_code" class="rc" :class="{ on: selected === r.onet_code }" @click="openSignal(r.onet_code)">
            <div class="top">
              <span class="ic"><Icon :name="r.icon" :size="22" /></span>
              <span v-if="sc(r.onet_code)" class="match"><b>{{ pct(sc(r.onet_code)!.probability) }}</b> likely</span>
            </div>
            <em v-if="r.rank === 1" class="pill pill-dark best">Best match</em>
            <h2>{{ title(r) }}</h2>
            <template v-if="adoption[r.onet_code]">
              <div class="big" :class="trend(r.onet_code)">
                <Icon :name="trendIcon[trend(r.onet_code)]" :size="26" :stroke="2.6" />
                <b>{{ pct(last(r.onet_code)!.p50) }}</b><span>use AI at work by {{ monthYear(last(r.onet_code)!.forecast_for) }}</span>
              </div>
              <div class="progress"><i :style="{ width: adoption[r.onet_code]!.current_rate * 100 + '%' }" /></div>
              <p class="small">{{ pct(adoption[r.onet_code]!.current_rate) }} today · likely {{ pct(last(r.onet_code)!.p10) }}–{{ pct(last(r.onet_code)!.p90) }} in this future</p>
              <p class="blurb">{{ adoption[r.onet_code]!.group }}</p>
            </template>
            <p v-else class="small">No AI adoption data for this role yet.</p>
            <div v-if="r.skills_you_have" class="chips">
              <span v-for="s in r.skills_you_have.slice(0, CHIPS)" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(s) }}</span>
              <span v-for="s in (r.skills_to_learn ?? []).slice(0, CHIPS)" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="13" /> {{ skillLabel(s) }}</span>
            </div>
          </button>
        </div>
        <p class="note">
          <template v-if="isSample">Not signed in, so these are sample roles. </template>
          {{ note }}
        </p>
      </template>
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { width: min(1100px, 94vw); margin-left: 50%; transform: translateX(-50%); }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
.lab { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 14px; padding: 4px 12px; border-radius: 999px; background: var(--cream); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--orange); }
.bar { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; }
.tabs { display: flex; gap: 10px; flex-wrap: wrap; }
.tabs button { display: flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: 14px; border: 2px solid var(--line-strong); background: #fff; box-shadow: 0 4px 0 rgba(30,30,30,.1); font-weight: 900; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; }
.tabs button.on { background: var(--yellow); border-color: var(--yellow); box-shadow: 0 4px 0 var(--orange); }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 22px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.rc { text-align: left; background: #fff; border: 2px solid var(--line-strong); border-radius: 22px; padding: 22px; box-shadow: 0 5px 0 var(--line); display: flex; flex-direction: column; gap: 10px; transition: transform .12s; }
.rc:hover { transform: translateY(-2px); }
.rc.on { border: 3px solid var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.top { display: flex; justify-content: space-between; align-items: center; }
.ic { width: 42px; height: 42px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.on .ic { background: var(--yellow); }
h2 { font-size: 21px; font-weight: 800; margin-top: 6px; }
.big { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 8px; } .big b { font-size: 44px; font-weight: 900; line-height: 1; } .big span { font-size: 13px; color: var(--muted); font-weight: 700; }
.big svg { color: var(--orange); align-self: center; flex: none; }
.big.falling b, .big.falling svg { color: var(--muted); }
.small { font-size: 12px; font-weight: 700; color: var(--muted); }
.match { display: inline-flex; align-items: baseline; gap: 4px; background: var(--cream); border-radius: 12px; padding: 6px 12px; font-weight: 800; font-size: 12px; color: var(--muted); }
.match b { font-size: 18px; font-weight: 900; color: var(--ink); }
.on .match { background: var(--yellow); color: var(--ink); }
.best { align-self: flex-start; }
.state { max-width: 560px; margin: 40px auto; display: flex; flex-direction: column; align-items: flex-start; gap: 18px; }
.retry { display: inline-flex; align-items: center; gap: 8px; margin-left: 82px; }
.note { margin-top: 22px; font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.5; max-width: 760px; }
.blurb { font-size: 13px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; padding: 6px 11px 6px 9px; }
@media (max-width: 960px) { .cards { grid-template-columns: 1fr; } }
</style>
