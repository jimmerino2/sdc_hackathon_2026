<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import Bubble from '../components/Bubble.vue';
import { completeNode, RoadmapError, type RoadmapNode, type RoadmapSource } from '../api/roadmap';
import { skillLabel } from '../data/skills';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state, scenario, profileSkills } = useFlow();
/** Path geometry: each skill gets a row; orbs sway along a gentle curve inside a fixed lane so the labels line up. */
const ROW = 104;
const LANE = 150;
const SWAY = 34;
const offset = (i: number) => Math.round(Math.sin((i * Math.PI) / 3) * SWAY);
/** A smooth dotted trail through the orb centres. */
function trail(count: number) {
  const pts = Array.from({ length: count }, (_, i) => [LANE / 2 + offset(i), i * ROW + ROW / 2 - 4]);
  return pts.reduce((d, [x, y], i) => {
    if (!i) return `M${x} ${y}`;
    const [px, py] = pts[i - 1];
    const my = (py + y) / 2;
    return `${d} C${px} ${my} ${x} ${my} ${x} ${y}`;
  }, '');
}
const typeLabel = { tech: 'Tool', skill: 'Ability', knowledge: 'Knowledge' } as const;
const sourceKind: Record<RoadmapSource['source_type'], { label: string; icon: string }> = {
  project: { label: 'Build it', icon: 'code' },
  certificate: { label: 'Get certified', icon: 'grad' },
  video: { label: 'Watch', icon: 'play' },
  activity: { label: 'Practise', icon: 'target' },
};
const statusLabel = { locked: 'Locked', available: 'Ready to learn', completed: 'Completed' } as const;
const busyId = ref<string | null>(null);
/** The node whose details panel is open. */
const openId = ref<string | null>(null);
const error = ref<string | null>(null);

const roadmap = computed(() => state.value.roadmap.data);
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === state.value.chosenRoleId));
/** Skills the user already has for this role (from matching); after a login, their strongest saved skills. */
const have = computed(() => {
  const saved = [...state.value.savedSkills].sort((a, b) => b.score - a.score).map((s) => s.name);
  const names = job.value?.skills_you_have ?? (saved.length ? saved : profileSkills.value.map((s) => s.name));
  return names.slice(0, 6).map(skillLabel);
});
const allNodes = computed(() => roadmap.value?.sections.flatMap((s) => s.units.flatMap((u) => u.nodes)) ?? []);
const doneCount = computed(() => allNodes.value.filter((n) => n.status === 'completed').length);
const openNode = computed(() => allNodes.value.find((n) => n.roadmap_detail_id === openId.value) ?? null);
/** Names of the skills that come before the open node. */
const openPrereqs = computed(() => {
  const n = openNode.value;
  if (!n) return [];
  return n.previous_nodes
    .map((id) => allNodes.value.find((m) => m.skill_id === id))
    .filter((m): m is RoadmapNode => !!m);
});
const nextUp = computed(() => allNodes.value.find((n) => n.status === 'available') ?? null);

const cheer = computed(() => {
  if (!allNodes.value.length) return 'I’ll be right here!';
  if (doneCount.value === 0) return 'Day 1. Start with the first star.';
  if (doneCount.value < allNodes.value.length) return `Nice! ${allNodes.value.length - doneCount.value} to go.`;
  return 'You’re role-ready!';
});

function sectionSkills(units: { nodes: RoadmapNode[] }[]) {
  return units.reduce((n, u) => n + u.nodes.length, 0);
}

/** Site name shown under a source, e.g. docs.docker.com. */
function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/** Briefly pulse a node after jumping to it. */
const flashId = ref<string | null>(null);
let flashTimer = 0;
function jumpTo(n: RoadmapNode) {
  document.getElementById(`node-${n.roadmap_detail_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  flashId.value = n.roadmap_detail_id;
  window.clearTimeout(flashTimer);
  flashTimer = window.setTimeout(() => (flashId.value = null), 1400);
}

function close() {
  openId.value = null;
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close();
}

watch(openId, (id) => {
  if (id) window.addEventListener('keydown', onKey);
  else window.removeEventListener('keydown', onKey);
});
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey);
  window.clearTimeout(flashTimer);
});

async function complete(n: RoadmapNode) {
  if (n.status !== 'available' || busyId.value || !state.value.profileId) return;
  busyId.value = n.roadmap_detail_id;
  error.value = null;
  try {
    state.value.roadmap.data = await completeNode(state.value.profileId, n.roadmap_detail_id);
  } catch (e) {
    error.value = e instanceof RoadmapError ? e.message : 'Couldn’t save that. Try again.';
  } finally {
    busyId.value = null;
  }
}

async function markDone(n: RoadmapNode) {
  await complete(n);
  if (!error.value) close();
}

onMounted(() => {
  // Landing here directly (e.g. after a refresh): fetch the roadmap if a role is known.
  if (state.value.roadmap.status === 'idle') loadRoadmap(state.value);
});
</script>

<template>
  <div class="tab">
    <div v-if="!roadmap && state.roadmap.status === 'error'" class="state">
      <Bubble :size="64" mood="surprised">{{ state.roadmap.error }}</Bubble>
      <RouterLink :to="go('roles')" class="btn btn-secondary">Back to my roles</RouterLink>
    </div>

    <div v-else-if="!roadmap" class="grid" aria-busy="true" aria-label="Loading your roadmap">
      <div class="main">
        <span class="skel unit-skel dark-skel" />
        <span class="skel unit-skel" />
        <div class="track-skel">
          <span v-for="i in 5" :key="i" class="skel orb-skel" :style="{ '--x': offset(i - 1) + 'px' }" />
        </div>
      </div>
      <aside class="side"><span class="skel card side-skel" /><span class="skel card side-skel" /></aside>
    </div>

    <div v-else class="grid">
      <div class="main">
        <section class="unit dark">
          <p class="eyebrow">Already yours</p>
          <h2>{{ job ? `You already have ${job.skills_owned} of ${job.skills_total} key skills` : 'Skills you already bring' }}</h2>
          <div class="chips"><span v-for="s in have" :key="s" class="chip">{{ s }}</span></div>
        </section>

        <template v-for="sec in roadmap.sections" :key="sec.section">
          <section class="unit gold">
            <p class="eyebrow dk">Section {{ sec.section }}</p>
            <h2>{{ sec.section === 1 ? roadmap.title : `Level up · part ${sec.section}` }}</h2>
            <p class="meta">{{ sectionSkills(sec.units) }} skills · {{ sec.units.length }} {{ sec.units.length === 1 ? 'unit' : 'units' }}</p>
          </section>

          <div v-for="u in sec.units" :key="u.unit" class="path">
            <p class="unit-label">Unit {{ u.unit }}</p>
            <div class="track" :style="{ height: u.nodes.length * ROW + 'px' }">
              <svg class="trail" :width="LANE" :height="u.nodes.length * ROW" aria-hidden="true">
                <path :d="trail(u.nodes.length)" />
              </svg>
              <div
                v-for="(n, i) in u.nodes"
                :id="`node-${n.roadmap_detail_id}`"
                :key="n.roadmap_detail_id"
                class="node"
                :style="{ top: i * ROW + 'px' }"
              >
                <span class="lane">
                  <span class="pin" :style="{ '--x': offset(i) + 'px' }">
                    <span v-if="n.roadmap_detail_id === nextUp?.roadmap_detail_id" class="start">Start</span>
                    <button
                      type="button"
                      class="orb"
                      :class="{ ok: n.status === 'completed', lock: n.status === 'locked', busy: busyId === n.roadmap_detail_id, flash: flashId === n.roadmap_detail_id }"
                      :aria-label="`${skillLabel(n.skill_name)}: ${statusLabel[n.status].toLowerCase()}. Open details`"
                      aria-haspopup="dialog"
                      @click="openId = n.roadmap_detail_id"
                    >
                      <Icon :name="n.status === 'completed' ? 'check' : 'star'" :size="26" :stroke="2.4" />
                    </button>
                  </span>
                </span>
                <span class="lbl-wrap">
                  <span class="lbl" :class="{ dim: n.status === 'locked' }">{{ skillLabel(n.skill_name) }}</span>
                  <small>{{ n.skill_group ?? typeLabel[n.skill_type] }}</small>
                  <button type="button" class="more" @click="openId = n.roadmap_detail_id">
                    {{ n.sources.length ? `${n.sources.length} ${n.sources.length === 1 ? 'resource' : 'resources'}` : 'Details' }}
                  </button>
                </span>
              </div>
            </div>
          </div>
        </template>

        <div class="path">
          <div class="track" :style="{ height: ROW + 'px' }">
            <div class="node" style="top: 0">
              <span class="lane"><span class="pin" style="--x: 0px"><span class="orb trophy"><Icon name="trophy" :size="26" /></span></span></span>
              <span class="lbl-wrap"><span class="lbl">Role-ready!</span></span>
            </div>
          </div>
        </div>
        <p v-if="error" class="err" role="alert">{{ error }}</p>
      </div>

      <aside class="side">
        <button v-if="nextUp" type="button" class="card stat next" @click="jumpTo(nextUp)">
          <small>Next up</small>
          <strong>{{ skillLabel(nextUp.skill_name) }}</strong>
          <p>Jump to it on your path <Icon name="arrow" :size="14" :stroke="2.6" /></p>
        </button>
        <div v-else class="card stat next">
          <small>Next up</small>
          <strong>All done!</strong>
          <p>Every skill on your roadmap is complete.</p>
        </div>
        <div class="card stat">
          <small>Target role</small><h3 class="sm">{{ roadmap.title }}</h3>
          <div class="progress"><i :style="{ width: (allNodes.length ? (doneCount / allNodes.length) * 100 : 0) + '%' }" /></div>
          <p>{{ doneCount }} of {{ allNodes.length }} roadmap skills done</p>
        </div>
        <div class="signal"><Icon name="tup" :size="20" /><div><strong>Signal: {{ scenario.label }}</strong><p>Rechecked weekly against live job postings.</p></div></div>
        <div class="cheer"><Mascot :size="34" :look="false" :mood="doneCount === allNodes.length && allNodes.length ? 'happy' : 'idle'" /><p>{{ cheer }}</p></div>
      </aside>
    </div>

    <div v-if="openNode" class="backdrop" @click.self="close">
      <section class="sheet" role="dialog" aria-modal="true" :aria-label="skillLabel(openNode.skill_name)">
        <button class="x" aria-label="Close" @click="close"><Icon name="x" :size="18" /></button>
        <p class="eyebrow dk">{{ typeLabel[openNode.skill_type] }}</p>
        <h2>{{ skillLabel(openNode.skill_name) }}</h2>
        <span class="status" :class="openNode.status">{{ statusLabel[openNode.status] }}</span>

        <dl class="facts">
          <div>
            <dt>Importance for this role</dt>
            <dd>{{ openNode.importance != null ? `${openNode.importance.toFixed(1)} / 5` : '–' }}</dd>
          </div>
          <div v-if="openNode.level != null">
            <dt>Level needed</dt>
            <dd>{{ openNode.level.toFixed(1) }} / 7</dd>
          </div>
        </dl>

        <p v-if="openPrereqs.length" class="pre">
          Comes after:
          <template v-for="(p, i) in openPrereqs" :key="p.skill_id">
            <b :class="{ done: p.status === 'completed' }">{{ skillLabel(p.skill_name) }}</b><template v-if="i < openPrereqs.length - 1">, </template>
          </template>
          <template v-if="!openNode.previous_nodes_required"> (suggested, not required)</template>
        </p>

        <h3>Where to learn it</h3>
        <ul v-if="openNode.sources.length" class="sources">
          <li v-for="s in openNode.sources" :key="s.url">
            <a :href="s.url" target="_blank" rel="noopener noreferrer">
              <span class="kind"><Icon :name="sourceKind[s.source_type].icon" :size="14" /> {{ sourceKind[s.source_type].label }}</span>
              <span class="ttl">{{ s.title }}</span>
              <span class="host">{{ host(s.url) }} ↗</span>
            </a>
          </li>
        </ul>
        <p v-else-if="openNode.source"><a :href="openNode.source" target="_blank" rel="noopener noreferrer" class="solo">Open the learning material ↗</a></p>
        <p v-else class="none">We don’t have a recommended resource for this one yet.</p>

        <div class="foot">
          <button
            v-if="openNode.status === 'available'"
            class="btn btn-primary"
            :disabled="!!busyId"
            @click="markDone(openNode)"
          >{{ busyId === openNode.roadmap_detail_id ? 'Saving…' : 'I’ve learned this' }}</button>
          <p v-else-if="openNode.status === 'locked'" class="none">Finish the skills before it to unlock this one.</p>
          <p v-else class="none">You’ve completed this skill.</p>
          <p v-if="error" class="err" role="alert">{{ error }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr 280px; gap: 32px; max-width: 1000px; }
.main { min-width: 0; }
.unit { border-radius: 20px; padding: 18px 22px; margin-bottom: 16px; }
.dark { background: var(--ink); color: #fff; } .dark h2 { font-size: 22px; font-weight: 900; margin: 6px 0 14px; }
.eyebrow { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--yellow); }
.dk { color: var(--ink); opacity: .75; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; } .chip { background: #fff; color: var(--ink); border-radius: 999px; padding: 8px 14px; font-size: 12px; font-weight: 800; }
.gold { background: var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.gold h2 { font-size: 24px; font-weight: 900; margin: 4px 0; } .meta { font-size: 12px; font-weight: 800; }
.path { display: flex; flex-direction: column; align-items: center; padding: 14px 0 26px; }
.unit-label { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
.track { position: relative; width: 400px; max-width: 100%; }
.trail { position: absolute; left: 0; top: 0; overflow: visible; }
.trail path { fill: none; stroke: var(--line); stroke-width: 6; stroke-linecap: round; stroke-dasharray: 0.1 14; }
.node { position: absolute; left: 0; right: 0; height: 104px; display: flex; align-items: center; }
.lane { position: relative; width: 150px; height: 100%; flex: none; }
.pin { position: absolute; left: 50%; top: 50%; transform: translate(calc(-50% + var(--x)), -50%); margin-top: -4px; }
.orb {
  position: relative; width: 64px; height: 60px; border-radius: 50%; display: grid; place-items: center;
  background: var(--yellow); color: var(--ink); box-shadow: 0 6px 0 var(--orange); cursor: pointer;
  transition: transform .1s ease, box-shadow .1s ease, filter .15s;
}
.orb:hover { transform: translateY(-2px); box-shadow: 0 8px 0 var(--orange); }
.orb:active { transform: translateY(4px); box-shadow: 0 2px 0 var(--orange); translate: none; scale: 1; }
.orb.ok { background: var(--ink); color: var(--yellow); box-shadow: 0 6px 0 #000; }
.orb.ok:hover { box-shadow: 0 8px 0 #000; } .orb.ok:active { box-shadow: 0 2px 0 #000; }
.orb.lock { background: #eceae5; color: #b0ada8; box-shadow: 0 6px 0 #d3d0ca; }
.orb.lock:hover { box-shadow: 0 8px 0 #d3d0ca; } .orb.lock:active { box-shadow: 0 2px 0 #d3d0ca; }
.orb.busy { opacity: .6; cursor: progress; }
.orb.trophy { cursor: default; } .orb.trophy:hover, .orb.trophy:active { transform: none; box-shadow: 0 6px 0 var(--orange); }
.orb.flash { animation: flash 1.2s ease; }
@keyframes flash { 0%, 100% { transform: scale(1); } 20% { transform: scale(1.14); } 45% { transform: scale(.96); } 70% { transform: scale(1.06); } }
.start {
  position: absolute; right: calc(100% + 12px); top: 50%; transform: translateY(-50%); white-space: nowrap;
  background: #fff; border: 2px solid var(--line-strong); border-radius: 10px; padding: 3px 10px;
  color: var(--amber-ink); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase;
}
.start::after { content: ''; position: absolute; left: 100%; top: 50%; margin-top: -6px; border: 6px solid transparent; border-left-color: var(--line-strong); }
.lbl-wrap { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; min-width: 0; padding-left: 6px; }
.lbl { font-weight: 800; font-size: 15px; line-height: 1.2; } .lbl.dim { color: var(--muted); }
.lbl-wrap small { font-size: 11px; font-weight: 700; color: var(--muted); }
.more {
  margin-top: 2px; font-size: 11px; font-weight: 900; color: var(--amber-ink); padding: 3px 10px; border-radius: 999px;
  border: 2px solid var(--line-strong); background: #fff; transition: background .15s, border-color .15s;
}
.more:hover { background: var(--cream); border-color: var(--yellow); }
.unit-skel { height: 110px; border-radius: 20px; margin-bottom: 16px; }
.dark-skel { height: 130px; }
.track-skel { display: flex; flex-direction: column; align-items: center; gap: 40px; padding: 30px 0; }
.orb-skel { width: 64px; height: 60px; border-radius: 50%; transform: translateX(var(--x)); }
.side-skel { height: 120px; border-radius: 20px; }
.backdrop { position: fixed; inset: 0; background: rgba(30, 30, 30, .45); display: grid; place-items: center; padding: 16px; z-index: 50; }
.sheet { position: relative; width: min(460px, 100%); max-height: 88vh; overflow: auto; background: var(--bg); border-radius: 22px; padding: 26px 24px 22px; box-shadow: 0 8px 0 var(--yellow); }
.sheet h2 { font-size: 26px; font-weight: 900; margin: 4px 0 8px; } .sheet h3 { font-size: 13px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 18px 0 8px; }
.x { position: absolute; top: 14px; right: 14px; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; background: #fff; border: 2px solid var(--line-strong); }
.status { display: inline-block; font-size: 11px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; padding: 4px 10px; border-radius: 999px; background: var(--cream); }
.status.completed { background: var(--ink); color: var(--yellow); } .status.locked { background: var(--line); color: var(--muted); }
.facts { display: flex; gap: 12px; margin-top: 16px; } .facts div { flex: 1; background: #fff; border: 2px solid var(--line); border-radius: 14px; padding: 10px 12px; }
.facts dt { font-size: 11px; font-weight: 800; color: var(--muted); } .facts dd { font-size: 18px; font-weight: 900; margin-top: 2px; }
.pre { margin-top: 14px; font-size: 13px; font-weight: 600; } .pre b { font-weight: 800; } .pre b.done { text-decoration: line-through; color: var(--muted); }
.sources { list-style: none; display: flex; flex-direction: column; gap: 8px; padding: 0; }
.sources a { display: grid; gap: 2px; background: #fff; border: 2px solid var(--line); border-radius: 14px; padding: 10px 14px; }
.sources a:hover { border-color: var(--yellow); }
.kind { display: inline-flex; gap: 6px; align-items: center; font-size: 11px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--orange); }
.ttl { font-weight: 800; font-size: 14px; } .host { font-size: 11px; font-weight: 700; color: var(--muted); }
.solo { font-weight: 800; color: var(--orange); } .none { font-size: 13px; font-weight: 600; color: var(--muted); }
.foot { margin-top: 20px; display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.err { padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; }
.state { max-width: 560px; margin: 40px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
.side { display: flex; flex-direction: column; gap: 14px; }
.stat { padding: 18px 20px; text-align: left; }
button.next { width: 100%; box-shadow: 0 4px 0 var(--line); transition: transform .1s, box-shadow .1s, border-color .15s; }
button.next:hover { border-color: var(--yellow); transform: translateY(-1px); }
button.next:active { transform: translateY(3px); box-shadow: 0 1px 0 var(--line); translate: none; scale: 1; }
button.next p { display: flex; align-items: center; gap: 6px; color: var(--amber-ink); font-weight: 800; } .stat p { font-size: 12px; font-weight: 600; color: var(--muted); margin-top: 6px; }
.stat small { font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.next strong { display: block; font-size: 18px; font-weight: 900; margin-top: 4px; }
.sm { font-size: 20px; font-weight: 900; margin: 4px 0 10px; } .progress { height: 10px; }
.signal { display: flex; gap: 12px; background: var(--cream); border-radius: 16px; padding: 14px 16px; color: var(--orange); }
.signal strong { color: var(--ink); font-size: 14px; font-weight: 900; } .signal p { font-size: 12px; font-weight: 600; color: var(--muted); }
.cheer { display: flex; align-items: center; gap: 10px; padding: 4px 6px; }
.cheer p { font-size: 13px; font-weight: 700; color: var(--muted); }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } }
</style>
