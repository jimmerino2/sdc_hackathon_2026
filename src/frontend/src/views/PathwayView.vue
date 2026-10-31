<script setup lang="ts">
import '../learn.css';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import InfoDialog from '../components/InfoDialog.vue';
import SectionBanner from '../components/learn/SectionBanner.vue';
import SkillPath from '../components/learn/SkillPath.vue';
import NextUpCard, { type NextUpSkill } from '../components/learn/NextUpCard.vue';
import ShareCard from '../components/learn/ShareCard.vue';
import { fetchProgrammes, type Programme } from '../api/hrd';
import { formatMinutes } from '../learn/time';
import ForecastCard from '../components/learn/ForecastCard.vue';
import BeeGuide from '../components/learn/BeeGuide.vue';
import ChallengeBanner from '../components/learn/ChallengeBanner.vue';
import NextMoveCard from '../components/learn/NextMoveCard.vue';
import { completeNode, deleteRoadmap, fetchRoadmapSummaries, RoadmapError, type RoadmapNode, type RoadmapSource, type RoadmapSummary } from '../api/roadmap';
import { readProfileId } from '../api/profile';
import { skillLabel } from '../data/skills';
import { allNodes, completeLocally, isGuide, learningLinks, progress, resolveNodes, resolveUnits, sectionCleared, type ResolvedSkill } from '../learn/skillState';
import { prefersReducedMotion } from '../composables/useCountUp';
import { useTallAside } from '../composables/useTallAside';
import { loadRoleForecast, normalizeSkillName, type RoleForecast } from '../occupational/forecastMatch';
import type { SkillRow } from '../api/occupational';
import { loadRoadmap, openRoadmap, useFlow } from '../state';
import { useRoute } from 'vue-router';
import { go } from '../router';

const { state } = useFlow();
const route = useRoute();
/** Development only (never in a production build): ?share shows the LinkedIn card before the role is complete, to try it out. */
const devShare = computed(() => import.meta.env.DEV && route.query.share !== undefined);

const typeLabel = { tech: 'Tool', skill: 'Ability', knowledge: 'Knowledge' } as const;
const sourceLabel: Record<RoadmapSource['source_type'] | 'link', string> = {
  project: 'Build it', certificate: 'Get certified', video: 'Watch', activity: 'Practice', link: 'Open',
};
const CHEERS = ['Nice!', 'Sweet!', 'On a roll!'];

const roadmap = computed(() => state.value.roadmap.data);

const nodes = computed(() => allNodes(roadmap.value));
const resolved = computed(() => resolveNodes(nodes.value, (n) => skillLabel(n.skill_name)));
const counts = computed(() => progress(roadmap.value));
const isRoleReady = computed(() => counts.value.total > 0 && counts.value.done >= counts.value.total);
const sections = computed(() => (roadmap.value?.sections ?? []).map((s) => {
  const nodes = s.units.flatMap((u) => u.nodes);
  const left = nodes.filter((n) => n.status !== 'completed').reduce((t, n) => t + (n.minutes ?? 0), 0);
  const time = !roadmap.value?.minutes_total ? '' : left ? ` · about ${formatMinutes(left)} left` : ' · nothing left';
  return { section: s.section, title: s.title, units: resolveUnits(roadmap.value!, s.section, (n) => skillLabel(n.skill_name)), count: nodes.length, time };
}));

const selectedId = ref<string | null>(null);
/** The skill's materials card was closed by its X; the demand forecast stays up for the selected skill until it's deselected. */
const materialsClosed = ref(false);
watch(selectedId, () => { materialsClosed.value = false; });
const busyId = ref<string | null>(null);
const error = ref<string | null>(null);
const cleared = ref(false);
const sideCard = ref<HTMLElement | null>(null);

/* ---------- roadmap tabs: arrow buttons page through them instead of a scrollbar ---------- */
const tabsEl = ref<HTMLElement | null>(null);
const canPrev = ref(false);
const canNext = ref(false);
function updateTabArrows() {
  const el = tabsEl.value;
  canPrev.value = !!el && el.scrollLeft > 1;
  canNext.value = !!el && el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
}
function pageTabs(dir: -1 | 1) {
  const el = tabsEl.value;
  el?.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
}
let tabsObserver: ResizeObserver | undefined;
watch(tabsEl, (el) => {
  tabsObserver?.disconnect();
  if (!el) return;
  tabsObserver = new ResizeObserver(updateTabArrows);
  tabsObserver.observe(el);
  updateTabArrows();
});
onBeforeUnmount(() => tabsObserver?.disconnect());
const side = ref<HTMLElement | null>(null);
useTallAside(side, sideCard);

/* ---------- demand forecast: a trend badge on tech skills that match the AI-prediction data ---------- */
const roleForecast = ref<RoleForecast | null>(null);

/** The forecast row for a resolved skill, when it's a 'tech' node matched by name; null otherwise. */
function forecastRowFor(s: ResolvedSkill): SkillRow | null {
  if (s.node.skill_type !== 'tech' || !roleForecast.value) return null;
  return roleForecast.value.rows.get(normalizeSkillName(skillLabel(s.node.skill_name))) ?? null;
}
const forecastDirectionFor = (s: ResolvedSkill) => forecastRowFor(s)?.direction ?? null;
/** The demand forecast for the selected skill, shown alongside its sources (not instead of). */
const forecastSelected = computed(() => {
  const s = selected.value;
  const row = s && forecastRowFor(s);
  return s && row ? { name: skillLabel(s.node.skill_name), row } : null;
});

watch(() => roadmap.value?.onet_code, async (code) => {
  roleForecast.value = null;
  selectedId.value = null;
  if (code) roleForecast.value = await loadRoleForecast(code);
}, { immediate: true });

const firstReady = computed(() => [...resolved.value.values()].find((s) => s.state === 'ready') ?? null);
const selected = computed(() => (selectedId.value ? resolved.value.get(selectedId.value) ?? null : null));
/** The skill whose materials show: the selected one, until its card is closed. */
const materialsSelected = computed(() => (materialsClosed.value ? null : selected.value));
const suggested = computed(() => materialsSelected.value ?? firstReady.value);

const kindOf = (s: ResolvedSkill) => (isGuide(s) ? 'AI skill' : s.node.skill_group ?? typeLabel[s.node.skill_type]);
/** The selected node when it is a section's AI study guide: its card replaces the demand forecast. */
const guideSelected = computed(() => (selected.value && isGuide(selected.value) ? { name: skillLabel(selected.value.node.skill_name) } : null));
function blurbOf(n: RoadmapNode): string | null {
  if (n.kind === 'ai_guide') return n.guide?.description ?? null;
  const parts = [n.importance != null ? `Importance for this role: ${n.importance.toFixed(1)} / 5` : '', n.level != null ? `level needed ${n.level.toFixed(1)} / 7` : ''].filter(Boolean);
  return parts.length ? parts.join(', ') + '.' : null;
}
const nextUp = computed<NextUpSkill | null>(() => {
  const s = suggested.value;
  if (!s) return null;
  return {
    id: s.id,
    name: skillLabel(s.node.skill_name),
    skillName: s.node.skill_name,
    state: s.state,
    kind: kindOf(s),
    blurb: blurbOf(s.node),
    ai: isGuide(s),
    steps: s.node.guide?.steps ?? [],
    blockers: s.blockers,
    links: learningLinks(s.node).map((l) => ({ ...l, kind: sourceLabel[l.kind] })),
    time: s.node.minutes
      ? { text: formatMinutes(s.node.minutes), note: s.node.minutes_basis === 'stated' ? `length stated by “${s.node.minutes_source}”` : 'our estimate' }
      : null,
  };
});

/* ---------- HRD Corp courses for the selected skill (paid; the employer claims the fee) ---------- */
const programmes = ref<Programme[] | null>(null);
watch(() => (selected.value && !isGuide(selected.value) ? selected.value.node.skill_name : null), async (skill) => {
  programmes.value = null;
  if (!skill) return;
  const found = await fetchProgrammes(skill);
  if (selected.value?.node.skill_name === skill) programmes.value = found; // ignore an answer for a skill the learner already left
}, { immediate: true });

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


const otherIncompleteRoadmap = computed(() => {
  const other = summaries.value.find((s) => s.onet_code !== activeCode.value && s.completed < s.total);
  if (!other) return null;
  return {
    onet_code: other.onet_code,
    title: other.title,
    completed: other.completed,
    total: other.total,
  };
});

const hasActiveChallenge = computed(() => {
  return !!challenge.value && !challenge.value.completed_at;
});

const activeChallengeId = computed(() => {
  return challenge.value?.challenge_id ?? null;
});

function select(s: ResolvedSkill) {
  if (selectedId.value === s.id) {
    selectedId.value = null;
    return;
  }
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

/** The roadmap's challenge in progress (tech roles only), shown above the path; it is worked on from the Challenges page. */
const challenge = computed(() => {
  const all = roadmap.value?.challenges ?? [];
  return all.find((c) => !c.completed_at) ?? all[0] ?? null;
});

/* ---------- the profile's roadmaps: switch between them, or delete the one on screen ---------- */
const summaries = ref<RoadmapSummary[]>([]);
const activeCode = computed(() => roadmap.value?.onet_code ?? state.value.chosenRoleId);
/** One chip per roadmap with its progress. The one on screen counts live, and still shows if the list couldn't load. */
const roadmapTabs = computed(() => {
  const r = roadmap.value;
  const list = summaries.value.length || !r ? summaries.value : [{ onet_code: r.onet_code, title: r.title, completed: counts.value.done, total: counts.value.total }];
  return list.map((s) => {
    const live = s.onet_code === activeCode.value && r;
    const done = live ? counts.value.done : s.completed;
    const total = live ? counts.value.total : s.total;
    return { code: s.onet_code, title: s.title, done, total, pct: total ? Math.round((done / total) * 100) : 0 };
  });
});
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

/** Tabs added or progress changed: re-check the arrows, and bring the active tab into view. */
watch([() => roadmapTabs.value, activeCode], () => nextTick(() => {
  updateTabArrows();
  tabsEl.value?.querySelector('.rmbar__tab.on')?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
}));
</script>

<template>
  <div class="tab">
    <div v-if="roadmapTabs.length" class="jb rmbar">
      <div class="rmbar__strip">
      <button v-if="canPrev || canNext" type="button" class="rmbar__nav" :disabled="!canPrev" aria-label="Previous roadmaps" @click="pageTabs(-1)">
        <Icon name="chevron" :size="18" class="rmbar__prev" />
      </button>
      <div ref="tabsEl" class="rmbar__tabs" role="tablist" aria-label="Your roadmaps" @scroll.passive="updateTabArrows">
        <button
          v-for="r in roadmapTabs"
          :key="r.code"
          type="button"
          role="tab"
          class="rmbar__tab"
          :class="{ on: r.code === activeCode }"
          :aria-selected="r.code === activeCode"
          :aria-label="`${r.title}, ${r.done} of ${r.total} skills done`"
          @click="switchTo(r.code)"
        >
          <span class="rmbar__name">{{ r.title }}</span>
          <span class="rmbar__bar" aria-hidden="true"><i :style="{ width: r.pct + '%' }" /></span>
          <span class="rmbar__n">{{ r.done }}/{{ r.total }}</span>
        </button>
      </div>
      <button v-if="canPrev || canNext" type="button" class="rmbar__nav" :disabled="!canNext" aria-label="Next roadmaps" @click="pageTabs(1)">
        <Icon name="chevron" :size="18" class="rmbar__next" />
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
        <template v-for="sec in sections" :key="sec.section">
          <SectionBanner
            :eyebrow="`Section ${sec.section}`"
            :title="sec.title ?? (sec.section === 1 ? roadmap.title : `Level up · part ${sec.section}`)"
            :meta="`${sec.count} skills · ${sec.units.length} ${sec.units.length === 1 ? 'unit' : 'units'}${sec.time}`"
          >
            <InfoDialog v-if="roadmap.minutes_total" title="How we estimate time">
              <p>Each step shows how long it should take. Some come straight from the course or video page, which states its own length. The rest use our own formula, so they are estimates.</p>
              <ul>
                <li><b>{{ roadmap.stated_steps ?? 0 }} {{ roadmap.stated_steps === 1 ? 'step' : 'steps' }}</b>: the length is stated by the first resource that gives one (at least an hour; a short clip doesn’t teach a skill).</li>
                <li><b>{{ roadmap.estimated_steps ?? 0 }} {{ roadmap.estimated_steps === 1 ? 'step' : 'steps' }}</b>: our formula, a base time for the kind of resource (build a project, take a course, watch a video, practice) × how deep the skill is for the role.</li>
              </ul>
              <p class="muted">Skills you already have count as done, so they add no time.</p>
            </InfoDialog>
          </SectionBanner>
          <div class="learn__path">
            <SkillPath
              :units="sec.units"
              :selected-id="selectedId"
              :start-id="firstReady?.id"
              :busy-id="busyId"
              :label="(s) => skillLabel(s.node.skill_name)"
              :kind="kindOf"
              :forecast="forecastDirectionFor"
              @select="select"
            />
          </div>
        </template>

        <RouterLink v-if="isRoleReady" :to="go('suggested')" class="jb-end jb-end--reached" aria-label="Role-ready! Explore your next pathway">
          <span class="jb-end__disc"><Icon name="trophy" :size="28" /></span>
          <strong>Role-ready!</strong>
          <span class="jb-end__link">Choose your next role pathway →</span>
        </RouterLink>
        <div v-else class="jb-end jb-end--pending">
          <span class="jb-end__disc"><Icon name="trophy" :size="28" /></span>Role-ready!
        </div>
      </div>

      <aside ref="side" class="learn__side">
        <!-- IN-PROGRESS STATE: when roadmap is being worked on -->
        <template v-if="!isRoleReady">
          <div ref="sideCard" class="learn__sidecards">
            <NextUpCard
              :skill="nextUp"
              :selected="!!materialsSelected"
              :programmes="programmes"
              :closable="!!materialsSelected"
              :busy="!!busyId"
              :error="error"
              @complete="markDone"
              @close="materialsClosed = true"
            />
            <ShareCard
              v-if="devShare && roadmap"
              :role="roadmap.title"
              :skills="counts.total"
              :sections="roadmap.sections.length"
              :minutes="roadmap.minutes_total"
              :name="state.name"
            />
            <ForecastCard
              v-if="forecastSelected && roleForecast"
              :name="forecastSelected.name"
              :row="forecastSelected.row"
              :occupation="roleForecast.occupation"
              :country="roleForecast.country"
            />
            <ChallengeBanner v-if="challenge" :challenge="challenge" />
          </div>
        </template>

        <!-- COMPLETED STATE: celebration, skills learned chips, next move -->
        <template v-else>
          <div ref="sideCard" class="learn__sidecards">
            <NextUpCard
              v-if="materialsSelected"
              :skill="nextUp"
              :selected="true"
              :programmes="programmes"
              closable
              eyebrow="Skill materials"
              @close="materialsClosed = true"
            />
            <ForecastCard
              v-if="selected && forecastSelected && roleForecast"
              :name="forecastSelected.name"
              :row="forecastSelected.row"
              :occupation="roleForecast.occupation"
              :country="roleForecast.country"
            />
            <ShareCard
              v-if="roadmap"
              :role="roadmap.title"
              :skills="counts.total"
              :sections="roadmap.sections.length"
              :minutes="roadmap.minutes_total"
              :name="state.name"
            />
            <NextMoveCard
              :other-roadmap="otherIncompleteRoadmap"
              :has-challenge="hasActiveChallenge"
              :challenge-id="activeChallengeId"
              @switch-roadmap="switchTo"
            />
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>
