<script setup lang="ts">
import "../learn.css";
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import Bubble from "../components/Bubble.vue";
import ChallengeRow from "../components/hive/ChallengeRow.vue";
import HiveAlert, { type HivePhase } from "../components/hive/HiveAlert.vue";
import HiveSwitch from "../components/hive/HiveSwitch.vue";
import NewChallenge from "../components/hive/NewChallenge.vue";
import Robbee from "../components/hive/Robbee.vue";
import Stinger from "../components/hive/Stinger.vue";
import {
  advanceChallenge,
  fetchChallenges,
  RoadmapError,
  submitChallenge,
  type RoadmapChallenge,
} from "../api/roadmap";
import { fetchHive, type Hive } from "../api/hive";
import { readProfileId } from "../api/profile";
import { prefersReducedMotion } from "../composables/useCountUp";
import { useFlow } from "../state";
import { go } from "../router";

const { state } = useFlow();
const route = useRoute();
const profileId = () => state.value.profileId ?? readProfileId();

const challenges = ref<RoadmapChallenge[] | null>(null);
/** Earned stingers not yet spent on Robbee. */
const stingers = ref(0);
/** The learner's fight, for the boss card: Robbee's HP and how many stings have landed. */
const fight = ref<Hive["fight"] | null>(null);
const loadError = ref<string | null>(null);
/** The challenge opened from the Learn page's banner (?open=<id>), or by the learner. */
const openId = ref<string | null>(typeof route.query.open === "string" ? route.query.open : null);
const busy = ref<string | null>(null);
const errors = ref<Record<string, string>>({});
/** The "+ New challenge" role picker is open. */
const picking = ref(false);

/** Filter challenges: current active challenges (default), past completed challenges, or all */
const tab = ref<"current" | "past" | "all">("current");

const isChallengeComplete = (c: RoadmapChallenge) =>
  !!c.completed_at || (c.stage === 2 && (c.status === "passed" || c.status === "advancing"));

const activeChallenges = computed(() => (challenges.value ?? []).filter((c) => !isChallengeComplete(c)));
const pastChallenges = computed(() => (challenges.value ?? []).filter((c) => isChallengeComplete(c)));

/** A challenge just written from the picker: put it first and open it. */
function added(c: RoadmapChallenge) {
  picking.value = false;
  challenges.value = [c, ...(challenges.value ?? [])];
  const rm = state.value.roadmap.data;
  if (c.roadmap_id && rm?.roadmap_id === c.roadmap_id) {
    state.value.roadmap.data = { ...rm, challenges: [...(rm.challenges ?? []), c] };
  }
  tab.value = "current";
  reveal(c.challenge_id);
}
const slots = computed(() => fight.value?.stings_to_kill ?? 5);
const dealt = computed(() => fight.value?.stings_dealt ?? 0);

async function load() {
  const id = profileId();
  if (!id) return;
  loadError.value = null;
  try {
    const list = await fetchChallenges(id);
    challenges.value = list.challenges;
    stingers.value = list.stingers_available;

    if (openId.value) {
      const opened = list.challenges.find((c) => c.challenge_id === openId.value);
      if (opened && isChallengeComplete(opened)) {
        tab.value = "past";
      }
      reveal(openId.value);
    } else if (activeChallenges.value.length === 0 && pastChallenges.value.length > 0) {
      tab.value = "past";
    }
  } catch (e) {
    loadError.value =
      e instanceof RoadmapError ? e.message : "Jobee couldn’t load your challenges. Try again in a moment.";
  }
  // The boss card is a nicety: the list stands without it.
  fetchHive(id).then((h) => (fight.value = h.fight)).catch(() => undefined);
}

/** Put a changed challenge in the list, and in the Learn page's roadmap if it is the one on screen there. */
function replace(c: RoadmapChallenge) {
  challenges.value = (challenges.value ?? []).map((x) => (x.challenge_id === c.challenge_id ? c : x));
  const rm = state.value.roadmap.data;
  if (rm?.challenges?.some((x) => x.challenge_id === c.challenge_id)) {
    state.value.roadmap.data = {
      ...rm,
      challenges: rm.challenges.map((x) => (x.challenge_id === c.challenge_id ? c : x)),
    };
  }
}

function reveal(id: string) {
  openId.value = id;
  nextTick(() =>
    document
      .getElementById(`challenge-${id}`)
      ?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" }),
  );
}

async function submit(c: RoadmapChallenge, repoUrl: string) {
  const id = profileId();
  if (!id || busy.value) return;
  busy.value = c.challenge_id;
  errors.value = { ...errors.value, [c.challenge_id]: "" };
  try {
    const res = await submitChallenge(id, c.challenge_id, repoUrl);
    replace(res.challenge);
    stingers.value = res.stingers_available;
    if (res.passed) {
      if (c.stage === 1) {
        // Stage 1 passed: Robbee rewrites the brief
        attack(res.challenge);
      } else {
        // Stage 2 passed: challenge is complete
        shown.value = res.challenge;
        phase.value = "patched";
        awarded.value = res.stinger_awarded;
      }
    }
  } catch (e) {
    errors.value = {
      ...errors.value,
      [c.challenge_id]: e instanceof RoadmapError ? e.message : "Couldn’t judge that just now. Try again.",
    };
  } finally {
    busy.value = null;
  }
}

/* ---------- Robbee's attack: warning, then assessing the damage while stage 2 is written, then the new brief ---------- */
const phase = ref<HivePhase | null>(null);
const shown = ref<RoadmapChallenge | null>(null);
const awarded = ref(false);
const alertError = ref<string | null>(null);

/** Robbee rewrites a passed stage 1. The rewrite runs during the warning; the damage report covers what's left. */
async function attack(c: RoadmapChallenge, retry = false) {
  const id = profileId();
  if (!id) return;
  shown.value = c;
  alertError.value = null;
  phase.value = retry ? "assessing" : "warning";
  awarded.value = false;

  const writing = advanceChallenge(id, c.challenge_id)
    .then((advanced) => {
      replace(advanced);
      shown.value = advanced;
    })
    .catch((e) => {
      alertError.value =
        e instanceof RoadmapError ? e.message : "Robbee couldn’t rewrite the brief just now. Try again in a moment.";
    });

  if (!retry) {
    // Show the warning for at least 3.2s, then swap to the damage report once the rewrite has arrived (or failed).
    await Promise.all([new Promise((ok) => setTimeout(ok, 3200)), writing]);
  } else {
    await writing;
  }
  if (!alertError.value) phase.value = "rewritten";
}

function startStage2() {
  const id = shown.value?.challenge_id;
  phase.value = null;
  if (id) {
    openId.value = id;
    reveal(id);
  }
}

onMounted(() => {
  if (route.query.new === "1") picking.value = true;
  load();
});
</script>

<template>
  <div class="tab jb chal">
    <header class="chal__head">
      <div>
        <p class="eyebrow">Challenges</p>
        <p class="chal__sub">Real-world projects for your tech roles. Score 85+ to land a stinger on Robbee.</p>
      </div>
      <HiveSwitch current="challenges" />
    </header>

    <section class="boss" aria-labelledby="boss-name">
      <div class="boss__art"><Robbee :size="170" /></div>
      <div class="boss__copy">
        <span class="boss__eyebrow">Boss Information</span>
        <h2 id="boss-name">Robbee <small>The Unemployed Chud</small></h2>
        <p class="boss__say">
          Bitter that he couldn't find a tech job due to a massive skill issue, Robbee now regularly harasses bees like
          you. This includes saying you'll end up like him, asking for referrals, internships, or if your dad knows a
          guy.
        </p>
        <p class="boss__say">Please don't tell him to "just put the fries in the bag", that raises his cortisol levels real bad...</p>
        <div class="boss__pips" :aria-label="`${dealt} of ${slots} stings landed on Robbee, ${stingers} stingers ready`">
          <span v-for="i in slots" :key="i" class="boss__pip" :class="{ on: i <= dealt }"
            ><Stinger :size="20"
          /></span>
          <span class="boss__count">
            <template v-if="fight">HP {{ fight.hp }}% · </template>{{ stingers }} {{ stingers === 1 ? "stinger" : "stingers" }} ready
          </span>
        </div>
      </div>
      <div class="boss__side">
        <RouterLink :to="go('hive')" class="jb-btn jb-btn--primary">Protect the hive</RouterLink>
      </div>
    </section>

    <!-- Header with split tabs -->
    <div class="chal__listhead">
      <div class="chal__filter-wrap">
        <h2>{{ tab === 'past' ? 'Past challenges' : tab === 'all' ? 'All challenges' : 'Your challenges' }}</h2>
        <div v-if="pastChallenges.length" class="btn-group" role="tablist" aria-label="Filter challenges">
          <button
            type="button"
            role="tab"
            :class="{ on: tab === 'current' }"
            :aria-selected="tab === 'current'"
            @click="tab = 'current'"
          >
            <span>Current</span>
            <span v-if="activeChallenges.length" class="chal__tab-n">{{ activeChallenges.length }}</span>
          </button>
          <button
            type="button"
            role="tab"
            :class="{ on: tab === 'past' }"
            :aria-selected="tab === 'past'"
            @click="tab = 'past'"
          >
            <span>Past</span>
            <span class="chal__tab-n">{{ pastChallenges.length }}</span>
          </button>
          <button
            v-if="activeChallenges.length && pastChallenges.length"
            type="button"
            role="tab"
            :class="{ on: tab === 'all' }"
            :aria-selected="tab === 'all'"
            @click="tab = 'all'"
          >
            <span>All</span>
            <span class="chal__tab-n">{{ (challenges ?? []).length }}</span>
          </button>
        </div>
      </div>

      <button type="button" class="jb-btn jb-btn--primary" @click="picking = true">+ New challenge</button>
    </div>

    <!-- Error State -->
    <div v-if="loadError" class="learn__state">
      <Bubble :size="64">{{ loadError }}</Bubble>
      <button type="button" class="btn btn-secondary" @click="load">Try again</button>
    </div>

    <!-- Loading Skeleton -->
    <div v-else-if="!challenges" class="chal__list" aria-busy="true">
      <div v-for="i in 3" :key="i" class="skel card chal__skel" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!challenges.length" class="learn__state">
      <Bubble :size="64">No challenges yet. Pick a tech role and Robbee will have a project waiting.</Bubble>
      <button type="button" class="btn btn-primary" @click="picking = true">Start a challenge</button>
    </div>

    <!-- All Tab: Split into Current and Past sections -->
    <div v-else-if="tab === 'all'" class="chal__grouped">
      <section v-if="activeChallenges.length" class="chal__section">
        <div class="chal__section-head">
          <h3>Current challenges</h3>
          <span class="chal__badge">{{ activeChallenges.length }} active</span>
        </div>
        <div class="chal__list">
          <ChallengeRow
            v-for="c in activeChallenges"
            :key="c.challenge_id"
            :challenge="c"
            :open="openId === c.challenge_id"
            :busy="busy === c.challenge_id"
            :error="errors[c.challenge_id] || null"
            @toggle="openId = openId === c.challenge_id ? null : c.challenge_id"
            @submit="(u) => submit(c, u)"
            @advance="attack(c)"
          />
        </div>
      </section>

      <section v-if="pastChallenges.length" class="chal__section">
        <div class="chal__section-head">
          <h3>Past challenges</h3>
          <span class="chal__badge chal__badge--done">{{ pastChallenges.length }} completed</span>
        </div>
        <div class="chal__list">
          <ChallengeRow
            v-for="c in pastChallenges"
            :key="c.challenge_id"
            :challenge="c"
            :open="openId === c.challenge_id"
            :busy="busy === c.challenge_id"
            :error="errors[c.challenge_id] || null"
            @toggle="openId = openId === c.challenge_id ? null : c.challenge_id"
            @submit="(u) => submit(c, u)"
            @advance="attack(c)"
          />
        </div>
      </section>
    </div>

    <!-- Current Tab: ONLY Current Active Challenges -->
    <div v-else-if="tab === 'current'" class="chal__list">
      <template v-if="activeChallenges.length">
        <ChallengeRow
          v-for="c in activeChallenges"
          :key="c.challenge_id"
          :challenge="c"
          :open="openId === c.challenge_id"
          :busy="busy === c.challenge_id"
          :error="errors[c.challenge_id] || null"
          @toggle="openId = openId === c.challenge_id ? null : c.challenge_id"
          @submit="(u) => submit(c, u)"
          @advance="attack(c)"
        />
      </template>
      <div v-else class="learn__state">
        <Bubble :size="64">No active challenges right now. You’re all caught up!</Bubble>
        <div class="chal__empty-actions">
          <button type="button" class="btn btn-primary" @click="picking = true">Start a challenge</button>
          <button v-if="pastChallenges.length" type="button" class="btn btn-secondary" @click="tab = 'past'">
            View past challenges ({{ pastChallenges.length }})
          </button>
        </div>
      </div>
    </div>

    <!-- Past Tab: ONLY Completed Past Challenges -->
    <div v-else-if="tab === 'past'" class="chal__list">
      <template v-if="pastChallenges.length">
        <ChallengeRow
          v-for="c in pastChallenges"
          :key="c.challenge_id"
          :challenge="c"
          :open="openId === c.challenge_id"
          :busy="busy === c.challenge_id"
          :error="errors[c.challenge_id] || null"
          @toggle="openId = openId === c.challenge_id ? null : c.challenge_id"
          @submit="(u) => submit(c, u)"
          @advance="attack(c)"
        />
      </template>
      <div v-else class="learn__state">
        <Bubble :size="64">No completed challenges yet. Complete both stages of a challenge to see it here.</Bubble>
      </div>
    </div>

    <HiveAlert
      v-if="phase && shown"
      :phase="phase"
      :title="shown.title"
      :twist="shown.twist"
      :stingers="stingers"
      :awarded="awarded"
      :error="alertError"
      @close="phase = null"
      @start="startStage2"
      @retry="attack(shown, true)"
    />
    <NewChallenge v-if="picking && profileId()" :profile-id="profileId()!" @close="picking = false" @created="added" />
  </div>
</template>

<style scoped>
.chal {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1600px;
}
.chal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.eyebrow {
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--orange);
}
.chal__sub {
  margin: 4px 0 0;
  font-size: 15px;
  line-height: 21px;
  color: var(--text-muted);
  font-weight: 600;
}

.boss {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 24px;
  padding: 24px 28px;
  border-radius: var(--radius-lg);
  background: var(--surface-raised);
  border: 2px solid var(--line);
  box-shadow: var(--shadow-soft);
}
.boss__art {
  width: 200px;
  height: 200px;
  border-radius: var(--radius-md);
  background: #fdecea;
  border: 2px solid #f1b8b3;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.boss__copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.boss__eyebrow {
  font-size: 13px;
  line-height: 18px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #b3261e;
}
.boss h2 {
  margin: 0;
  font-size: 38px;
  line-height: 46px;
  font-weight: 900;
}
.boss h2 small {
  margin-left: 10px;
  font-size: 16px;
  line-height: 23px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.boss p {
  margin: 0;
  font-size: 16px;
  line-height: 23px;
  font-weight: 600;
  color: var(--text-muted);
}
.boss p.boss__say {
  font-family: 'Patrick Hand', 'Comic Sans MS', cursive;
  font-size: 20px;
  line-height: 27px;
  font-weight: 400;
  color: var(--text);
}
.boss__pips {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.boss__pip {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface);
  border: 2px solid var(--line-strong);
  color: var(--locked-edge);
  opacity: 0.55;
  transition:
    transform var(--dur-fast) var(--ease-bounce),
    background var(--dur-base),
    color var(--dur-base),
    opacity var(--dur-base);
}
.boss__pip.on {
  background: var(--honey);
  border-color: var(--honey-deep);
  color: var(--on-honey);
  opacity: 1;
  box-shadow: 0 3px 0 var(--honey-deep);
}
.boss__count {
  margin-left: 6px;
  font-size: 15px;
  line-height: 21px;
  font-weight: 800;
  color: var(--accent-text);
}
.boss__side {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.chal__listhead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.chal__filter-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.chal__listhead h2 {
  margin: 0;
  font-size: 30px;
  font-weight: 900;
}
.chal__tab-n {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--surface);
  border: 1px solid var(--line-strong);
  font-size: 13px;
  font-weight: 900;
  color: var(--text);
}
.chal__grouped {
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.chal__section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chal__section-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chal__section-head h3 {
  margin: 0;
  font-size: 23px;
  font-weight: 900;
}
.chal__badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  background: var(--honey-tint);
  color: var(--accent-text);
  font-size: 14px;
  line-height: 18px;
  font-weight: 800;
}
.chal__badge--done {
  background: var(--surface);
  border: 1px solid var(--line-strong);
  color: var(--text-muted);
}
.chal__empty-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.chal__list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chal__skel {
  height: 112px;
  border-radius: var(--radius-lg);
}

@media (max-width: 1100px) {
  .boss {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .boss__side {
    grid-column: 1 / -1;
  }
  .boss__art {
    width: 180px;
    height: 180px;
  }
  .boss__art :deep(svg) {
    width: 130px;
    height: auto;
  }
}
@media (max-width: 640px) {
  .boss {
    grid-template-columns: 1fr;
    padding: 20px;
    gap: 18px;
  }
  .boss__art {
    width: 100%;
    height: 170px;
  }
  .boss h2 {
    font-size: 34px;
    line-height: 41px;
  }
}
</style>
