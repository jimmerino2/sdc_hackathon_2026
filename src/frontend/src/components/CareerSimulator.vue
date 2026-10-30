<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import Bubble from './Bubble.vue';
import Icon from './Icon.vue';
import InfoDialog from './InfoDialog.vue';
import { backendScenario } from '../api/forecast';
import { JobsError, simulateSkills, type RoleComparison, type SimulateResult, type SkillOption } from '../api/jobs';
import { listRoadmaps, type RoadmapSummary } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { scenarios } from '../data/flows';
import { LEVEL_SCORES, skillLabel } from '../data/skills';
import { go } from '../router';
import { openRoadmap, useFlow } from '../state';

/** "What if you learned a new skill?" Tap a skill and every role's bar grows. Every number comes from POST /jobs/simulate,
 *  which runs the real matching on a temporary copy of the profile. Nothing here is saved. */
const router = useRouter();
const { state } = useFlow();

const SUGGESTED = 12; // skills shown before searching
const MAX_PICKS = 12; // what POST /jobs/simulate accepts
const REMAINING_SHOWN = 4;
const LEVELS = [{ name: 'Basic', score: LEVEL_SCORES[1] }, { name: 'Good', score: LEVEL_SCORES[2] }, { name: 'Strong', score: LEVEL_SCORES[3] }];

const picked = ref<Record<string, number>>({}); // skill name -> simulated score
const result = ref<SimulateResult | null>(null);
const options = ref<SkillOption[]>([]); // kept from the first answer, so the list doesn't reshuffle while choosing
const status = ref<'loading' | 'ready' | 'error'>('loading');
const busy = ref(false);
const error = ref('');
const open = ref<string | null>(null);
const target = ref<string | null>(null);
const roadmaps = ref<Record<string, RoadmapSummary>>({});
const query = ref('');
const showAll = ref(false);

const scenario = computed(() => backendScenario[state.value.scenario]);
const pickedList = computed(() => Object.entries(picked.value).map(([name, score]) => ({ name, score })));
const hasPicks = computed(() => pickedList.value.length > 0);
const atLimit = computed(() => pickedList.value.length >= MAX_PICKS);

let latest = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
async function run() {
  const id = state.value.profileId ?? readProfileId();
  if (!id) {
    status.value = 'error';
    error.value = 'Jobee couldn’t find your profile. Log in again to try this.';
    return;
  }
  const mine = ++latest;
  busy.value = true;
  try {
    const res = await simulateSkills(id, pickedList.value);
    if (mine !== latest) return; // a newer choice is already on its way
    result.value = res;
    if (!options.value.length) options.value = res.options;
    status.value = 'ready';
    error.value = '';
  } catch (e) {
    if (mine !== latest) return;
    error.value = e instanceof JobsError ? e.message : 'Jobee couldn’t work that out. Try again in a moment.';
    status.value = result.value ? 'ready' : 'error';
  } finally {
    if (mine === latest) busy.value = false;
  }
}
watch(picked, () => {
  clearTimeout(timer);
  timer = setTimeout(run, 200);
}, { deep: true });
onMounted(() => {
  run();
  const id = state.value.profileId ?? readProfileId();
  if (id) listRoadmaps(id).then((r) => { roadmaps.value = r; }).catch(() => {});
});

function toggle(o: SkillOption) {
  if (o.name in picked.value) delete picked.value[o.name];
  else if (!atLimit.value) picked.value[o.name] = o.trial;
}
function reset() {
  picked.value = {};
  open.value = null;
}
const optionOf = (name: string) => options.value.find((o) => o.name === name);
/** A level at or below what the learner already has adds nothing, so it isn't offered. */
const levelsFor = (name: string) => LEVELS.filter((l) => l.score > (optionOf(name)?.current ?? 0));
const gainOf = (o: SkillOption) => o.gains.find((g) => g.scenario === scenario.value)?.best_change ?? 0;
const rising = (o: SkillOption) => o.emerging || o.demand?.direction === 'rising';
const bestRoleOf = (o: SkillOption) => o.gains.find((g) => g.scenario === scenario.value)?.best_role;
const levelOf = (o: SkillOption) => LEVELS.find((l) => l.score === o.trial)?.name;
/** Real skills from this learner's list, so the explanation matches the tiles on the page. */
const sampleUp = computed(() => [...options.value].sort((a, b) => gainOf(b) - gainOf(a)).find((o) => gainOf(o) > 0));
const sampleNone = computed(() => options.value.find((o) => gainOf(o) === 0));

const shownOptions = computed(() => {
  const q = query.value.trim().toLowerCase();
  const list = [...options.value].sort((a, b) => gainOf(b) - gainOf(a));
  if (q) return list.filter((o) => skillLabel(o.name).toLowerCase().includes(q) || o.name.toLowerCase().includes(q));
  return showAll.value ? list : list.filter((o) => gainOf(o) > 0).slice(0, SUGGESTED);
});

const at = (r: RoleComparison) => r.scenarios.find((s) => s.scenario === scenario.value)!;
const roles = computed(() => [...(result.value?.roles ?? [])].sort((a, b) => at(a).simulated_rank - at(b).simulated_rank));
const summary = computed(() => result.value?.summary.find((s) => s.scenario === scenario.value));
const moved = (r: RoleComparison) => at(r).current_rank - at(r).simulated_rank;
const best = computed(() => [...roles.value].sort((a, b) => at(b).change - at(a).change)[0] ?? null);
const improved = computed(() => roles.value.filter((r) => at(r).change > 0).length);
const newTop = computed(() => (summary.value && summary.value.current_top !== summary.value.simulated_top ? summary.value.simulated_top : null));

const chosen = computed(() => roles.value.find((r) => r.onet_code === (target.value ?? best.value?.onet_code)) ?? null);
const hasRoadmap = computed(() => !!chosen.value && !!roadmaps.value[chosen.value.onet_code]);
/** Build these skills: the existing roadmap flow, with the simulated skills brought forward. */
function build() {
  const r = chosen.value;
  if (!r) return;
  if (hasRoadmap.value) {
    openRoadmap(state.value, r.onet_code);
    router.push(go('pathway'));
    return;
  }
  openRoadmap(state.value, r.onet_code, pickedList.value.map((s) => s.name));
  router.push(go('generating'));
}
</script>

<template>
  <div class="sim">
    <h1>What if you learned a new skill?</h1>
    <p class="lead">Tap a skill. Watch your role matches change. Nothing is saved.</p>

    <div v-if="status === 'loading'" class="skel card load" aria-busy="true" aria-label="Loading" />
    <div v-else-if="status === 'error'" class="state">
      <Bubble :size="64">{{ error }}</Bubble>
      <button type="button" class="btn btn-secondary" @click="run"><Icon name="refresh" :size="18" /> Try again</button>
    </div>

    <div v-else-if="result" class="grid">
      <section class="card pad graph" :class="{ busy }" aria-live="polite">
        <div class="headline">
          <template v-if="!hasPicks"><b>Your matches today</b></template>
          <template v-else-if="best && at(best).change > 0">
            <b class="big">+{{ at(best).change }} points</b>
            <span>for {{ best.title }}</span>
            <small>{{ improved }} of {{ roles.length }} roles go up<template v-if="newTop"> · New top match: {{ newTop }}</template></small>
          </template>
          <template v-else>
            <b>No change to your matches</b>
            <small>Try a skill with a + number.</small>
          </template>
        </div>

        <p v-if="error" class="err" role="alert">{{ error }}</p>

        <TransitionGroup tag="ul" name="race" class="roles">
          <li v-for="r in roles" :key="r.onet_code">
            <button type="button" class="rrow" :aria-expanded="open === r.onet_code" @click="open = open === r.onet_code ? null : r.onet_code">
              <span class="rtop">
                <span class="rname">{{ r.title }}<em v-if="moved(r)" :class="moved(r) > 0 ? 'trend-up' : 'trend-down'">{{ moved(r) > 0 ? '▲' : '▼' }}{{ Math.abs(moved(r)) }}</em></span>
                <span class="rval">
                  <b>{{ at(r).simulated_percent }}%</b>
                  <em v-if="at(r).change" class="delta" :class="at(r).change > 0 ? 'up' : 'down'">{{ at(r).change > 0 ? '+' : '' }}{{ at(r).change }}</em>
                </span>
              </span>
              <span class="track" role="img" :aria-label="`${r.title}: ${at(r).current_percent}% now, ${at(r).simulated_percent}% with these skills`">
                <i class="now" :style="{ width: `${Math.min(at(r).current_percent, at(r).simulated_percent)}%` }" />
                <i class="diff" :class="{ down: at(r).change < 0 }" :style="{ width: `${Math.abs(at(r).change)}%` }" />
              </span>
            </button>
            <div v-if="open === r.onet_code" class="more">
              <p v-if="at(r).change < 0" class="muted">{{ at(r).explanation }}</p>
              <div v-if="r.skills_gained.length" class="chips">
                <span v-for="g in r.skills_gained" :key="g.name" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ skillLabel(g.name) }}</span>
              </div>
              <div v-if="r.skills_remaining.length" class="chips">
                <span class="still">Still to learn</span>
                <span v-for="s in r.skills_remaining.slice(0, REMAINING_SHOWN)" :key="s" class="chip chip-gap">{{ skillLabel(s) }}</span>
                <span v-if="r.skills_remaining.length > REMAINING_SHOWN" class="still">+{{ r.skills_remaining.length - REMAINING_SHOWN }} more</span>
              </div>
            </div>
          </li>
        </TransitionGroup>

        <div class="legend">
          <span class="key"><i class="now" /> Today</span>
          <span class="key"><i class="diff" /> With new skills</span>
          <div class="futures" role="group" aria-label="AI future">
            <button v-for="s in scenarios" :key="s.key" type="button" :class="{ on: state.scenario === s.key }" :aria-pressed="state.scenario === s.key" @click="state.scenario = s.key">{{ s.label }}</button>
          </div>
        </div>
      </section>

      <section class="card pad picker">
        <div class="row-head">
          <h2>Pick a skill</h2>
          <button v-if="hasPicks" type="button" class="link" @click="reset">Clear</button>
        </div>

        <ul v-if="hasPicks" class="picked">
          <li v-for="s in pickedList" :key="s.name">
            <span class="pname">{{ skillLabel(s.name) }}</span>
            <span class="levels" role="group" :aria-label="`Level for ${skillLabel(s.name)}`">
              <button v-for="l in levelsFor(s.name)" :key="l.name" type="button" :class="{ on: picked[s.name] === l.score }" :aria-pressed="picked[s.name] === l.score" @click="picked[s.name] = l.score">{{ l.name }}</button>
            </span>
            <button type="button" class="rm" :aria-label="`Remove ${skillLabel(s.name)}`" @click="delete picked[s.name]"><Icon name="x" :size="14" /></button>
          </li>
        </ul>

        <label class="search">
          <Icon name="search" :size="16" />
          <input v-model="query" type="search" :placeholder="`Search ${options.length} skills`" :aria-label="`Search ${options.length} skills`" />
        </label>

        <p v-if="!query && !showAll" class="sub">Best for you</p>
        <ul class="tiles" :class="{ long: showAll || query }">
          <li v-for="o in shownOptions" :key="o.name">
            <button type="button" class="tile" :class="{ on: o.name in picked }" :aria-pressed="o.name in picked" :disabled="atLimit && !(o.name in picked)" @click="toggle(o)">
              <span class="tname">{{ skillLabel(o.name) }}<span v-if="rising(o)" class="trend-up" title="Rising in job ads" aria-label="Rising in job ads"><Icon name="tup" :size="13" /></span></span>
              <b v-if="gainOf(o) > 0" class="tgain">+{{ gainOf(o) }}</b>
              <span v-else class="tnone" title="Won’t change your matches">–</span>
            </button>
          </li>
          <li v-if="!shownOptions.length" class="muted none">No skills found.</li>
        </ul>

        <div class="foot">
          <button v-if="!query" type="button" class="link" @click="showAll = !showAll">{{ showAll ? 'Show fewer' : `Show all ${options.length} skills` }}</button>
          <InfoDialog title="Where these numbers come from" label="Where do these numbers come from?">
            <div v-if="sampleUp" class="ex">
              <span class="tile"><span class="tname">{{ skillLabel(sampleUp.name) }}</span><b class="tgain">+{{ gainOf(sampleUp) }}</b></span>
              <p>Learning {{ skillLabel(sampleUp.name) }} to {{ levelOf(sampleUp) }} adds {{ gainOf(sampleUp) }} points to {{ bestRoleOf(sampleUp) }}. Jobee reran your real match to get this.</p>
            </div>
            <div v-if="sampleNone" class="ex">
              <span class="tile"><span class="tname">{{ skillLabel(sampleNone.name) }}</span><span class="tnone">–</span></span>
              <p>{{ skillLabel(sampleNone.name) }} won’t change your matches. Each role only counts its 10 key skills.</p>
            </div>
            <dl class="src">
              <dt>Skill list</dt><dd>O*NET, the US occupation database.</dd>
              <dt>Skill weight</dt><dd>O*NET again. Tools it labels In Demand count 4.0 and Hot Technology 3.5. Abilities use its importance ratings.</dd>
              <dt>Your level</dt><dd>Your resume and skill check. Basic counts 33%, Good 67% and Strong 100%. Jobee set this scale.</dd>
              <dt>Rising arrow</dt><dd>Sampled Hacker News job ads, not Malaysian vacancies. It doesn’t change your match.</dd>
            </dl>
          </InfoDialog>
        </div>
        <p v-if="atLimit" class="muted">You can try {{ MAX_PICKS }} skills at a time.</p>

        <div v-if="hasPicks" class="next">
          <label class="target"><span>Learn these for</span>
            <select :value="chosen?.onet_code" @change="target = ($event.target as HTMLSelectElement).value">
              <option v-for="r in roles" :key="r.onet_code" :value="r.onet_code">{{ r.title }}</option>
            </select>
          </label>
          <button type="button" class="btn btn-primary" @click="build"><Icon name="route" :size="18" /> {{ hasRoadmap ? 'Open my roadmap' : 'Build these skills' }}</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
h1 { font-size: 28px; font-weight: 900; line-height: 1.15; margin-bottom: 6px; }
h2 { font-size: 17px; font-weight: 900; }
.lead { font-size: 15px; font-weight: 700; color: var(--muted); margin-bottom: 16px; }
.load { height: 420px; }
.state { max-width: 560px; display: flex; flex-direction: column; align-items: flex-start; gap: 14px; }
.state .btn { display: inline-flex; align-items: center; gap: 8px; }
.grid { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: 18px; align-items: start; }
.pad { padding: 20px 22px; }
.muted { font-size: 13px; font-weight: 600; color: var(--muted); line-height: 1.45; }
.err { padding: 10px 14px; border-radius: 12px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 13px; }
.link { font-size: 13px; font-weight: 900; color: var(--amber-ink); text-decoration: underline; }

.graph { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 16px; transition: opacity .15s; }
.graph.busy { opacity: .7; }
.headline { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; min-height: 58px; }
.headline b { font-size: 19px; font-weight: 900; }
.headline .big { font-size: 30px; line-height: 1.1; color: #1e7a3c; }
.headline span { font-size: 17px; font-weight: 800; }
.headline small { flex-basis: 100%; font-size: 13px; font-weight: 700; color: var(--muted); }

.roles { list-style: none; display: flex; flex-direction: column; gap: 4px; }
.race-move { transition: transform .45s ease; }
.rrow { width: 100%; display: flex; flex-direction: column; gap: 5px; padding: 6px 8px; border-radius: 10px; text-align: left; }
.rrow:hover { background: #faf9f6; }
.rtop { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.rname { min-width: 0; font-size: 14px; font-weight: 800; }
.rname em { margin-left: 6px; font-size: 11px; font-weight: 900; font-style: normal; }
.rval { flex: none; display: inline-flex; align-items: center; gap: 6px; font-size: 15px; font-variant-numeric: tabular-nums; }
.rval b { font-weight: 900; }
.delta { padding: 1px 7px; border-radius: 999px; font-size: 12px; font-weight: 900; font-style: normal; }
.delta.up { background: #e7f4ea; color: #1e5e30; }
.delta.down { background: #fdecea; color: #a12a22; }
.track { display: flex; height: 12px; border-radius: 999px; background: var(--line); overflow: hidden; }
.track i { display: block; height: 100%; transition: width .45s ease; }
.now { background: var(--orange); }
.diff { background: #2f9e52; }
.diff.down { background: #d9534a; }
.more { display: flex; flex-direction: column; gap: 6px; padding: 4px 8px 10px; }
.chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.chip { font-size: 12px; padding: 4px 10px; }
.still { font-size: 12px; font-weight: 800; color: var(--muted); }

.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; font-size: 12px; font-weight: 800; color: var(--muted); }
.key { display: inline-flex; align-items: center; gap: 5px; }
.key i { width: 12px; height: 12px; border-radius: 4px; }
.futures { display: flex; flex-wrap: wrap; gap: 4px; margin-left: auto; }
.futures button { padding: 5px 10px; border-radius: 9px; font-size: 11.5px; font-weight: 900; color: var(--muted); background: #f0efec; }
.futures button.on { background: var(--yellow); color: var(--ink); }

.picker { display: flex; flex-direction: column; gap: 12px; }
.row-head { display: flex; justify-content: space-between; align-items: center; }
.picked, .tiles { list-style: none; }
.picked { display: flex; flex-direction: column; gap: 6px; }
.picked li { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 6px 8px 6px 12px; border-radius: 12px; background: var(--cream); }
.pname { flex: 1; min-width: 80px; font-size: 13px; font-weight: 900; }
.levels { display: inline-flex; padding: 3px; border-radius: 10px; background: #fff; }
.levels button { padding: 4px 9px; border-radius: 8px; font-size: 11px; font-weight: 900; color: var(--muted); }
.levels button.on { background: var(--ink); color: var(--yellow); }
.rm { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: #fff; }
.search { display: flex; align-items: center; gap: 8px; padding: 9px 12px; border: 2px solid var(--line-strong); border-radius: 12px; color: var(--muted); background: #fff; }
.search input { flex: 1; min-width: 0; border: 0; outline: 0; font: inherit; font-size: 14px; font-weight: 700; color: var(--ink); background: transparent; }
.sub { font-size: 12px; font-weight: 800; color: var(--muted); }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.tiles.long { max-height: 380px; overflow-y: auto; }
.tile { width: 100%; height: 100%; display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 9px 11px; border-radius: 12px; border: 2px solid var(--line-strong); background: #fff; text-align: left; }
.tile:disabled { opacity: .45; }
.tile.on { border-color: var(--orange); background: #fffaf0; }
.tname { min-width: 0; display: inline-flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 800; overflow-wrap: anywhere; }
.tname span { flex: none; display: inline-flex; }
.tgain { flex: none; font-size: 14px; font-weight: 900; color: #1e7a3c; }
.tnone { flex: none; font-size: 14px; font-weight: 800; color: var(--muted); }
.none { grid-column: 1 / -1; }
.foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; }
.ex { display: grid; grid-template-columns: 170px minmax(0, 1fr); align-items: center; gap: 14px; }
.ex p { font-size: 14px; line-height: 1.45; }
.src { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 8px 12px; margin-top: 6px; padding-top: 12px; border-top: 2px solid var(--line); font-size: 13.5px; line-height: 1.45; }
.src dt { font-weight: 900; }
.src dd { font-weight: 600; color: var(--muted); }
.next { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 10px; padding-top: 12px; border-top: 2px solid var(--line); }
.next .btn { display: inline-flex; align-items: center; gap: 8px; }
.target { flex: 1; min-width: 170px; display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 800; color: var(--muted); }
.target select { font: inherit; font-size: 14px; font-weight: 700; color: var(--ink); padding: 8px 10px; border: 2px solid var(--line-strong); border-radius: 12px; background: #fff; width: 100%; }
@media (max-width: 860px) {
  h1 { font-size: 23px; }
  .grid { grid-template-columns: minmax(0, 1fr); }
  .graph { position: static; }
  .tiles.long { max-height: 320px; }
}
@media (max-width: 520px) {
  .ex { grid-template-columns: 1fr; gap: 6px; }
  .src { grid-template-columns: 1fr; gap: 2px; }
  .src dd { margin-bottom: 6px; }
}
@media (prefers-reduced-motion: reduce) {
  .race-move, .track i { transition: none; }
}
</style>
