<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import SideNav from '../components/SideNav.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import Bubble from '../components/Bubble.vue';
import { completeNode, RoadmapError, type RoadmapNode } from '../api/roadmap';
import { skillLabel } from '../data/skills';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state, scenario, profileSkills } = useFlow();
const offsets = [0, -40, -75, -40, 0, 40, 75, 40];
const typeLabel = { tech: 'Tool', skill: 'Ability', knowledge: 'Knowledge' } as const;
const busyId = ref<string | null>(null);
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
                  :disabled="n.status !== 'available' || !!busyId"
                  :aria-label="`${skillLabel(n.skill_name)}: ${n.status === 'available' ? 'mark as done' : n.status}`"
                  @click="complete(n)"
                >
                  <Icon :name="n.status === 'completed' ? 'check' : n.status === 'available' ? 'star' : 'lock'" :size="26" />
                </button>
                <span class="lbl-wrap">
                  <span class="lbl" :class="{ dim: n.status === 'locked' }">{{ skillLabel(n.skill_name) }}</span>
                  <small>{{ typeLabel[n.skill_type] }}</small>
                  <a v-if="n.source && n.status !== 'locked'" :href="n.source" target="_blank" rel="noopener">Learn ↗</a>
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
          <p>{{ nextUp ? 'Tap the glowing star when you’ve learned it.' : 'Every skill on your roadmap is complete.' }}</p>
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
