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

/** A challenge just written from the picker: put it first and open it. */
function added(c: RoadmapChallenge) {
  picking.value = false;
  challenges.value = [c, ...(challenges.value ?? [])];
  const rm = state.value.roadmap.data;
  if (c.roadmap_id && rm?.roadmap_id === c.roadmap_id) {
    state.value.roadmap.data = { ...rm, challenges: [...(rm.challenges ?? []), c] };
  }
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
    if (openId.value) reveal(openId.value);
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
    awarded.value = res.stinger_awarded;
    if (res.passed && res.challenge.stage === 1) attack(res.challenge);
    else if (res.passed) show("patched", res.challenge);
  } catch (e) {
    errors.value = {
      ...errors.value,
      [c.challenge_id]:
        e instanceof RoadmapError ? e.message : "Jobee couldn’t judge that just now. Try again in a moment.",
    };
  } finally {
    busy.value = null;
  }
}

/* ---------- Robbee's attack: warning, then assessing the damage while stage 2 is written, then the new brief ---------- */
const phase = ref<HivePhase | null>(null);
const shown = ref<RoadmapChallenge | null>(null);
const alertError = ref<string | null>(null);
/** The last pass paid a stinger; false when a completed challenge was resubmitted. */
const awarded = ref(true);
const WARNING_MS = 2600;
const MIN_ASSESS_MS = 1800;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function show(p: HivePhase, c: RoadmapChallenge) {
  shown.value = c;
  alertError.value = null;
  phase.value = p;
}

/** Robbee rewrites a passed stage 1. The rewrite runs during the warning; the damage report covers what's left. */
async function attack(c: RoadmapChallenge, skipWarning = false) {
  const id = profileId();
  if (!id) return;
  show(skipWarning ? "assessing" : "warning", c);
  const job = advanceChallenge(id, c.challenge_id).then(
    (x) => ({ ok: true as const, x }),
    (e) => ({ ok: false as const, e }),
  );
  if (!skipWarning) {
    await wait(WARNING_MS);
    if (phase.value !== "warning") return void job.then((r) => r.ok && replace(r.x));
    phase.value = "assessing";
  }
  const [r] = await Promise.all([job, wait(MIN_ASSESS_MS)]);
  if (r.ok) replace(r.x);
  if (phase.value !== "assessing") return;
  if (r.ok) show("rewritten", r.x);
  else
    alertError.value =
      r.e instanceof RoadmapError ? r.e.message : "Robbee couldn’t rewrite the brief just now. Try again in a moment.";
}

function startStage2() {
  const c = shown.value;
  phase.value = null;
  if (c) reveal(c.challenge_id);
}

onMounted(load);
</script>

<template>
  <div class="tab jb chal">
    <header class="chal__head">
      <div>
        <h1>Challenges</h1>
        <p>Real-world projects for your tech roles. Score 85+ to land a stinger on Robbee.</p>
      </div>
      <HiveSwitch current="challenges" />
    </header>

    <section class="boss" aria-labelledby="boss-name">
      <div class="boss__art"><Robbee :size="170" /></div>
      <div class="boss__copy">
        <span class="boss__eyebrow">Boss Information</span>
        <h2 id="boss-name">Robbee <small>The Unemployed Chud</small></h2>
        <p>
          Bitter that he couldn't find a tech job due to a massive skill issue, Robbee now regularly harasses bees like
          you. This includes saying you'll end up like him, asking for referrals, internships, or if your dad knows a
          guy.
        </p>
        <br />
        <p>Please don't tell him to "just put the fries in the bag", that raises his cortisol levels real bad...</p>
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
        <RouterLink :to="go('hive')" class="boss__cta">Protect the hive</RouterLink>
      </div>
    </section>

    <div class="chal__listhead">
      <h2>Your challenges</h2>
      <button type="button" class="chal__new" @click="picking = true">+ New challenge</button>
    </div>

    <div v-if="loadError" class="learn__state">
      <Bubble :size="64">{{ loadError }}</Bubble>
      <button type="button" class="btn btn-secondary" @click="load">Try again</button>
    </div>
    <div v-else-if="!challenges" class="chal__list" aria-busy="true">
      <div v-for="i in 3" :key="i" class="skel card chal__skel" />
    </div>
    <div v-else-if="!challenges.length" class="learn__state">
      <Bubble :size="64">No challenges yet. Pick a tech role and Robbee will have a project waiting.</Bubble>
      <button type="button" class="btn btn-primary" @click="picking = true">Start a challenge</button>
    </div>
    <div v-else class="chal__list">
      <ChallengeRow
        v-for="c in challenges"
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
.chal__head h1 {
  margin: 0;
  font-size: 40px;
  line-height: 48px;
  font-weight: 900;
}
.chal__head p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 16px;
  font-weight: 600;
}

.boss {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(220px, 360px);
  align-items: center;
  gap: 32px;
  padding: 26px 30px;
  border: 2px solid var(--honey);
  border-radius: 28px;
  background: var(--surface-raised);
}
.boss__art {
  display: grid;
  place-items: center;
  width: 250px;
  height: 250px;
  border-radius: 24px;
  background: #fdf0c8;
}
.boss__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #d9580a;
}
.boss h2 {
  margin: 6px 0 8px;
  font-size: 38px;
  line-height: 44px;
  font-weight: 900;
}
.boss h2 small {
  margin-left: 6px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-muted);
}
.boss p {
  margin: 0;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
}
.boss__pips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}
.boss__pip {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #eeeae0;
  color: #b7b2a3;
}
.boss__pip.on {
  background: var(--honey);
  color: var(--on-honey);
}
.boss__count {
  margin-left: 6px;
  font-size: 15px;
  font-weight: 800;
}
.boss__side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.boss__cta {
  display: block;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--honey);
  color: var(--on-honey);
  text-align: center;
  text-decoration: none;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  box-shadow: 0 4px 0 var(--honey-deep);
  transition:
    transform var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}
.boss__cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 0 var(--honey-deep);
}

.chal__listhead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}
.chal__listhead h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 900;
}
.chal__new {
  padding: 11px 22px;
  border-radius: var(--radius-md);
  background: var(--honey);
  color: var(--on-honey);
  text-decoration: none;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
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
  .chal__head h1 {
    font-size: 32px;
    line-height: 40px;
  }
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
    font-size: 30px;
    line-height: 36px;
  }
}
</style>
