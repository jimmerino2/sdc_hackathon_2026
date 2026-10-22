<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import SideNav from '../components/SideNav.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import Bubble from '../components/Bubble.vue';
import { completeNode, RoadmapError, type RoadmapNode, type RoadmapSource } from '../api/roadmap';
import { skillLabel } from '../data/skills';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state, scenario, profileSkills } = useFlow();
const offsets = [0, -40, -75, -40, 0, 40, 75, 40];
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
  if (doneCount.value === 0) return 'Day 1. Start with the glowing star!';
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
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));

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
  <SideNav active="learn">
    <div v-if="!roadmap" class="state">
      <Bubble :size="64">{{ state.roadmap.status === 'error' ? state.roadmap.error : 'Loading your roadmap…' }}</Bubble>
      <RouterLink v-if="state.roadmap.status === 'error'" :to="go('roles')" class="btn btn-secondary">Back to my roles</RouterLink>
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
            <div class="row">
              <div>
                <p class="eyebrow dk">Section {{ sec.section }}</p>
                <h2>{{ sec.section === 1 ? roadmap.title : `Level up · part ${sec.section}` }}</h2>
                <p class="meta">{{ sectionSkills(sec.units) }} skills · {{ sec.units.length }} {{ sec.units.length === 1 ? 'unit' : 'units' }}</p>
              </div>
              <RouterLink v-if="sec.section === 1" :to="go('resources')" class="guide"><Icon name="book" :size="16" /> Guidebook</RouterLink>
            </div>
          </section>

          <div class="path">
            <template v-for="u in sec.units" :key="u.unit">
              <p class="unit-label">Unit {{ u.unit }}</p>
              <div
                v-for="(n, i) in u.nodes"
                :key="n.roadmap_detail_id"
                class="node"
                :style="{ transform: `translateX(${offsets[i % offsets.length]}px)` }"
              >
                <span v-if="n.roadmap_detail_id === nextUp?.roadmap_detail_id" class="start">Start</span>
                <button
                  class="orb"
                  :class="{ cur: n.status === 'available', ok: n.status === 'completed', lock: n.status === 'locked', busy: busyId === n.roadmap_detail_id }"
                  :aria-label="`${skillLabel(n.skill_name)}: ${statusLabel[n.status].toLowerCase()}. Open details`"
                  aria-haspopup="dialog"
                  @click="openId = n.roadmap_detail_id"
                >
                  <Icon :name="n.status === 'completed' ? 'check' : n.status === 'available' ? 'star' : 'lock'" :size="26" />
                </button>
                <span class="lbl-wrap">
                  <span class="lbl" :class="{ dim: n.status === 'locked' }">{{ skillLabel(n.skill_name) }}</span>
                  <small>{{ typeLabel[n.skill_type] }}</small>
                  <button class="more" @click="openId = n.roadmap_detail_id">
                    {{ n.sources.length ? `${n.sources.length} ${n.sources.length === 1 ? 'resource' : 'resources'}` : 'Details' }}
                  </button>
                </span>
              </div>
            </template>
          </div>
        </template>

        <div class="path">
          <div class="node end"><span class="orb trophy"><Icon name="trophy" :size="26" /></span><span class="lbl">Role-ready!</span></div>
        </div>
        <p v-if="error" class="err" role="alert">{{ error }}</p>
      </div>

      <aside class="side">
        <div class="card stat next">
          <small>Next up</small>
          <strong>{{ nextUp ? skillLabel(nextUp.skill_name) : 'All done!' }}</strong>
          <p>{{ nextUp ? 'Tap a skill to see how to learn it, then mark it done.' : 'Every skill on your roadmap is complete.' }}</p>
        </div>
        <div class="card stat">
          <small>Target role</small><h3 class="sm">{{ roadmap.title }}</h3>
          <div class="progress"><i :style="{ width: (allNodes.length ? (doneCount / allNodes.length) * 100 : 0) + '%' }" /></div>
          <p>{{ doneCount }} of {{ allNodes.length }} roadmap skills done</p>
        </div>
        <div class="signal"><Icon name="tup" :size="20" /><div><strong>Signal: {{ scenario.label }}</strong><p>Rechecked weekly against live job postings.</p></div></div>
        <div class="cheer"><Mascot :size="72" :mood="doneCount === 0 ? 'wave' : doneCount < allNodes.length ? 'happy' : 'celebrate'" /><p class="bubble">{{ cheer }}</p></div>
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
  </SideNav>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr 280px; gap: 32px; max-width: 1000px; }
.unit { border-radius: 20px; padding: 18px 22px; margin-bottom: 16px; }
.dark { background: var(--ink); color: #fff; } .dark h2 { font-size: 22px; font-weight: 900; margin: 6px 0 14px; }
.eyebrow { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--yellow); }
.dk { color: var(--ink); opacity: .75; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; } .chip { background: #fff; color: var(--ink); border-radius: 999px; padding: 8px 14px; font-size: 12px; font-weight: 800; }
.gold { background: var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.gold h2 { font-size: 24px; font-weight: 900; margin: 4px 0; } .meta { font-size: 12px; font-weight: 800; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.guide { display: inline-flex; gap: 8px; align-items: center; border: 2px solid var(--ink); border-radius: 12px; padding: 10px 14px; font-weight: 900; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.path { position: relative; display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 18px 0 40px; }
.unit-label { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.node { position: relative; display: flex; align-items: center; gap: 14px; width: 240px; transition: transform .2s; }
.orb { width: 62px; height: 58px; border-radius: 50%; display: grid; place-items: center; flex: none; background: var(--yellow); box-shadow: 0 6px 0 var(--orange); }
.orb.cur { outline: 4px solid var(--yellow); outline-offset: 5px; background: var(--yellow); }
.orb.ok { background: var(--ink); color: var(--yellow); box-shadow: 0 6px 0 #000; cursor: default; }
.orb.lock { background: #eceae5; box-shadow: 0 6px 0 #c2bfba; color: #b0ada8; cursor: not-allowed; }
.orb.busy { opacity: .6; cursor: progress; }
.orb.trophy { background: var(--yellow); }
.start { position: absolute; top: -26px; left: 6px; border: 2px solid var(--yellow); border-radius: 10px 10px 0 0; padding: 2px 14px; color: var(--orange); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; background: var(--bg); }
.lbl-wrap { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.lbl { font-weight: 800; font-size: 15px; } .lbl.dim { color: var(--muted); }
.lbl-wrap small { font-size: 11px; font-weight: 700; color: var(--muted); }
.lbl-wrap a { font-size: 11px; font-weight: 900; color: var(--orange); }
.lbl-wrap .more { align-self: flex-start; font-size: 11px; font-weight: 900; color: var(--orange); text-align: left; }
.orb { cursor: pointer; }
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
.stat { padding: 18px 20px; } .stat p { font-size: 12px; font-weight: 600; color: var(--muted); margin-top: 6px; }
.stat small { font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.next strong { display: block; font-size: 18px; font-weight: 900; margin-top: 4px; }
.sm { font-size: 20px; font-weight: 900; margin: 4px 0 10px; } .progress { height: 10px; }
.signal { display: flex; gap: 12px; background: var(--cream); border-radius: 16px; padding: 14px 16px; color: var(--orange); }
.signal strong { color: var(--ink); font-size: 14px; font-weight: 900; } .signal p { font-size: 12px; font-weight: 600; color: var(--muted); }
.cheer { display: flex; align-items: center; gap: 10px; }
.bubble { background: #fff; border: 2px solid var(--line); border-radius: 14px; padding: 10px 14px; font-weight: 800; font-size: 14px; }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } }
</style>
