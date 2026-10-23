<script setup lang="ts">
import '../learn.css';
import { computed, nextTick, onMounted, ref } from 'vue';
import SideNav from '../components/SideNav.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import SkillChips from '../components/learn/SkillChips.vue';
import SectionBanner from '../components/learn/SectionBanner.vue';
import SkillPath from '../components/learn/SkillPath.vue';
import NextUpCard, { type NextUpSkill } from '../components/learn/NextUpCard.vue';
import ProgressCard from '../components/learn/ProgressCard.vue';
import SignalCard from '../components/learn/SignalCard.vue';
import BeeGuide from '../components/learn/BeeGuide.vue';
import { completeNode, RoadmapError, type RoadmapNode, type RoadmapSource } from '../api/roadmap';
import { skillLabel } from '../data/skills';
import { allNodes, completeLocally, learningLinks, progress, resolveNodes, resolveUnits, sectionCleared, type ResolvedSkill } from '../learn/skillState';
import { prefersReducedMotion } from '../composables/useCountUp';
import { loadRoadmap, useFlow } from '../state';
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

onMounted(() => {
  // Landing here directly (e.g. after a refresh): fetch the roadmap if a role is known.
  if (state.value.roadmap.status === 'idle') loadRoadmap(state.value);
});
</script>

<template>
  <SideNav active="learn">
    <div v-if="!roadmap" class="learn__state">
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
  </SideNav>
</template>
