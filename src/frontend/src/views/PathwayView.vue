<script setup lang="ts">
import '../learn.css';
import { computed, nextTick, onMounted, ref } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import SkillChips from '../components/learn/SkillChips.vue';
import SectionBanner from '../components/learn/SectionBanner.vue';
import SkillPath from '../components/learn/SkillPath.vue';
import NextUpCard, { type NextUpSkill } from '../components/learn/NextUpCard.vue';
import ProgressCard from '../components/learn/ProgressCard.vue';
import SignalCard from '../components/learn/SignalCard.vue';
import BeeGuide from '../components/learn/BeeGuide.vue';
import { completeNode, deleteRoadmap, fetchRoadmapSummaries, RoadmapError, type RoadmapNode, type RoadmapSource, type RoadmapSummary } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { skillLabel } from '../data/skills';
import { allNodes, completeLocally, learningLinks, progress, resolveNodes, resolveUnits, sectionCleared, type ResolvedSkill } from '../learn/skillState';
import { prefersReducedMotion } from '../composables/useCountUp';
import { loadRoadmap, openRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state, scenario, profileSkills } = useFlow();

const typeLabel = { tech: 'Tool', skill: 'Ability', knowledge: 'Knowledge' } as const;
const sourceLabel: Record<RoadmapSource['source_type'] | 'link', string> = {
  project: 'Build it', certificate: 'Get certified', video: 'Watch', activity: 'Practise', link: 'Open',
};
const CHEERS = ['Nice!', 'Sweet!', 'On a roll!'];
const MAX_CHIPS = 6;

const roadmap = computed(() => state.value.roadmap.data);
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === state.value.chosenRoleId));
/** Skills the user already has for this role (from matching); after a login, their strongest saved skills. */
const haveAll = computed(() => {
  const saved = [...state.value.savedSkills].sort((a, b) => b.score - a.score).map((s) => s.name);
  const names = job.value?.skills_you_have ?? (saved.length ? saved : profileSkills.value.map((s) => s.name));
  return names.map(skillLabel);
});
const have = computed(() => haveAll.value.slice(0, MAX_CHIPS));
const haveMore = computed(() => Math.max(0, haveAll.value.length - MAX_CHIPS));

const nodes = computed(() => allNodes(roadmap.value));
const resolved = computed(() => resolveNodes(nodes.value, (n) => skillLabel(n.skill_name)));
const counts = computed(() => progress(roadmap.value));
const sections = computed(() => (roadmap.value?.sections ?? []).map((s) => ({ section: s.section, units: resolveUnits(roadmap.value!, s.section, (n) => skillLabel(n.skill_name)), count: s.units.reduce((t, u) => t + u.nodes.length, 0) })));

const selectedId = ref<string | null>(null);
const busyId = ref<string | null>(null);
const error = ref<string | null>(null);
const cleared = ref(false);
const sideCard = ref<HTMLElement | null>(null);

const firstReady = computed(() => [...resolved.value.values()].find((s) => s.state === 'ready') ?? null);
const selected = computed(() => (selectedId.value ? resolved.value.get(selectedId.value) ?? null : null));
const suggested = computed(() => selected.value ?? firstReady.value);

const kindOf = (s: ResolvedSkill) => s.node.skill_group ?? typeLabel[s.node.skill_type];
function blurbOf(n: RoadmapNode): string | null {
  const parts = [n.importance != null ? `Importance for this role: ${n.importance.toFixed(1)} / 5` : '', n.level != null ? `level needed ${n.level.toFixed(1)} / 7` : ''].filter(Boolean);
  return parts.length ? parts.join(', ') + '.' : null;
}
const nextUp = computed<NextUpSkill | null>(() => {
  const s = suggested.value;
  if (!s) return null;
  return {
    id: s.id,
    name: skillLabel(s.node.skill_name),
    state: s.state,
    kind: kindOf(s),
    blurb: blurbOf(s.node),
    blockers: s.blockers,
    links: learningLinks(s.node).map((l) => ({ ...l, kind: sourceLabel[l.kind] })),
  };
});

const message = computed(() => {
  const { done, total } = counts.value;
  if (!total) return 'I’ll be right here!';
  if (done >= total) return 'You’re role-ready!';
  if (cleared.value) return 'Section cleared!';
  if (done === 0) return 'Day 1. Start with the glowing star!';
  return `${CHEERS[done % 3]} ${total - done} to go.`;
});
const mood = computed(() => {
  const { done, total } = counts.value;
  return done === 0 ? 'wave' : done < total ? 'happy' : 'celebrate';
});

function select(s: ResolvedSkill) {
  selectedId.value = s.id;
  error.value = null;
  // With the side column stacked under the path, bring the card into view.
  if (window.matchMedia('(max-width: 1000px)').matches) {
    nextTick(() => sideCard.value?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'nearest' }));
  }
}

/** Mark the selected skill done: update the page at once, then save; put things back if saving fails. */
async function markDone() {
  const s = selected.value;
  const before = roadmap.value;
  if (!s || s.state !== 'ready' || busyId.value || !before || !state.value.profileId) return;
  const section = before.sections.find((sec) => sec.units.some((u) => u.nodes.some((n) => n.roadmap_detail_id === s.id)))!.section;
  busyId.value = s.id;
  error.value = null;
  state.value.roadmap.data = completeLocally(before, s.id);
  try {
    const saved = await completeNode(state.value.profileId, s.id);
    state.value.roadmap.data = saved;
    cleared.value = sectionCleared(saved, section);
  } catch (e) {
    state.value.roadmap.data = before;
    error.value = e instanceof RoadmapError ? e.message : 'Couldn’t save that. Try again.';
  } finally {
    busyId.value = null;
  }
}

/* ---------- the profile's roadmaps: switch between them, or delete the one on screen ---------- */
const summaries = ref<RoadmapSummary[]>([]);
const activeCode = computed(() => roadmap.value?.onet_code ?? state.value.chosenRoleId);
/** Every roadmap is gone, so there is nothing to show until the learner builds another. */
const empty = ref(false);
const confirming = ref(false);
const deleting = ref(false);
const deleteError = ref<string | null>(null);
const profileId = () => state.value.profileId ?? readProfileId();

async function refreshSummaries() {
  const id = profileId();
  if (!id) return;
  try {
    summaries.value = await fetchRoadmapSummaries(id);
  } catch {
    // The switcher just stays as it was; the roadmap itself is unaffected.
  }
}

/** Show another of the profile's roadmaps. */
async function switchTo(code: string, force = false) {
  if (!force && (code === activeCode.value || state.value.roadmap.status === 'loading')) return;
  selectedId.value = null;
  cleared.value = false;
  error.value = null;
  confirming.value = false;
  deleteError.value = null;
  openRoadmap(state.value, code);
  await loadRoadmap(state.value);
}

async function removeRoadmap() {
  const id = profileId();
  const code = roadmap.value?.onet_code;
  if (!id || !code || deleting.value) return;
  deleting.value = true;
  deleteError.value = null;
  try {
    await deleteRoadmap(id, code);
    confirming.value = false;
    await refreshSummaries();
    const next = summaries.value[0];
    if (next) await switchTo(next.onet_code, true);
    else {
      state.value.chosenRoleId = null;
      state.value.roadmap = { status: 'idle', data: null, error: null };
      empty.value = true;
    }
  } catch (e) {
    deleteError.value = e instanceof RoadmapError ? e.message : 'Jobee couldn’t delete that roadmap. Try again in a moment.';
  } finally {
    deleting.value = false;
  }
}

onMounted(async () => {
  // Landing here directly (e.g. after a refresh): fetch the roadmap if a role is known.
  const loading = state.value.roadmap.status === 'idle' ? loadRoadmap(state.value) : Promise.resolve();
  await Promise.all([loading, refreshSummaries()]);
});
</script>

<template>
  <div class="tab">
    <div v-if="summaries.length" class="jb rmbar">
      <div class="rmbar__tabs" role="tablist" aria-label="Your roadmaps">
        <button
          v-for="r in summaries"
          :key="r.onet_code"
          type="button"
          role="tab"
          class="rmbar__tab"
          :class="{ on: r.onet_code === activeCode }"
          :aria-selected="r.onet_code === activeCode"
          @click="switchTo(r.onet_code)"
        >
          <span class="rmbar__name">{{ r.title }}</span>
          <span class="rmbar__n">{{ r.onet_code === activeCode && roadmap ? counts.done : r.completed }}/{{ r.onet_code === activeCode && roadmap ? counts.total : r.total }}</span>
        </button>
      </div>
      <button v-if="roadmap" type="button" class="rmbar__del" :disabled="deleting" @click="confirming = !confirming">
        <Icon name="trash" :size="16" /> Delete
      </button>
    </div>
    <div v-if="confirming && roadmap" class="jb rmconfirm" role="alertdialog" aria-label="Delete this roadmap">
      <p>Delete the <b>{{ roadmap.title }}</b> roadmap? Your progress on it is lost. You can build it again from Roles.</p>
      <div class="rmconfirm__act">
        <button type="button" class="jb-btn jb-btn--ink" :disabled="deleting" @click="confirming = false">Keep it</button>
        <button type="button" class="rmconfirm__go" :disabled="deleting" @click="removeRoadmap">{{ deleting ? 'Deleting…' : 'Delete roadmap' }}</button>
      </div>
      <p v-if="deleteError" class="rmconfirm__err" role="alert">{{ deleteError }}</p>
    </div>

    <div v-if="empty && !roadmap" class="learn__state">
      <Bubble :size="64">No roadmaps left. Pick a role and I’ll build you a new one.</Bubble>
      <RouterLink :to="go('suggested')" class="btn btn-primary">Go to my roles</RouterLink>
    </div>

    <div v-else-if="!roadmap" class="learn__state">
      <Bubble :size="64">{{ state.roadmap.status === 'error' ? state.roadmap.error : 'Loading your roadmap…' }}</Bubble>
      <RouterLink v-if="state.roadmap.status === 'error'" :to="go('suggested')" class="btn btn-secondary">Back to my roles</RouterLink>
    </div>

    <div v-else class="jb learn">
      <div class="learn__main">
        <SkillChips :skills="have" :owned="job?.skills_owned" :total="job?.skills_total" :more="job ? haveMore : 0" />

        <template v-for="sec in sections" :key="sec.section">
          <SectionBanner
            :eyebrow="`Section ${sec.section}`"
            :title="sec.section === 1 ? roadmap.title : `Level up · part ${sec.section}`"
            :meta="`${sec.count} skills · ${sec.units.length} ${sec.units.length === 1 ? 'unit' : 'units'}`"
          />
          <div class="learn__path">
            <SkillPath
              :units="sec.units"
              :selected-id="selectedId"
              :start-id="firstReady?.id"
              :busy-id="busyId"
              :label="(s) => skillLabel(s.node.skill_name)"
              :kind="kindOf"
              @select="select"
            />
          </div>
        </template>

        <div class="jb-end"><span class="jb-end__disc"><Icon name="trophy" :size="28" /></span>Role-ready!</div>
      </div>

      <aside class="learn__side">
        <div ref="sideCard">
          <NextUpCard :skill="nextUp" :selected="!!selected" :busy="!!busyId" :error="error" @complete="markDone" />
        </div>
        <ProgressCard :done="counts.done" :total="counts.total" :role="roadmap.title" />
        <SignalCard :title="`Signal: ${scenario.label}`" />
        <BeeGuide :message="message" :mood="mood" />
      </aside>
    </div>
  </div>
</template>
