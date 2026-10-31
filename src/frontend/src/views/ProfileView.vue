<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import Bubble from '../components/Bubble.vue';
import BeePicker from '../components/BeePicker.vue';
import Icon from '../components/Icon.vue';
import InterestPicker from '../components/InterestPicker.vue';
import SdgTip from '../components/SdgTip.vue';
import { bee, type BeeName } from '../bee';
import { fetchSkillSdgs, type SkillSdg } from '../api/sdg';
import { INTEREST_SDGS } from '../data/interestSdgs';
import { fetchInterests, MAX_INTERESTS, type Interest } from '../api/interests';
import { getProfile, readProfileId, setBee, stageForWho, updateProfile } from '../api/profile';
import { fetchLearnedSkills, fetchRoadmapSummaries, type LearnedSkill, type RoadmapSummary } from '../api/roadmap';
import { whoOptions } from '../data/flows';
import { roadmapStatus } from '../data/roadmapStatus';
import { skillLabel } from '../data/skills';
import { openRoadmap, useFlow } from '../state';
import { go } from '../router';

const router = useRouter();
const { state } = useFlow();
const profileId = () => state.value.profileId ?? readProfileId();

// ---- name
const name = ref(state.value.name);
const editing = ref(false);
const draft = ref('');
const savingName = ref(false);
const nameError = ref('');

function startEdit() {
  draft.value = name.value;
  nameError.value = '';
  editing.value = true;
}

async function saveName() {
  const next = draft.value.trim();
  const id = profileId();
  if (!next || !id || savingName.value) return;
  if (next === name.value) {
    editing.value = false;
    return;
  }
  savingName.value = true;
  nameError.value = '';
  try {
    const saved = await updateProfile(id, { name: next });
    name.value = saved.name;
    state.value.name = saved.name;
    editing.value = false;
  } catch {
    nameError.value = 'Couldn’t save your name. Try again.';
  } finally {
    savingName.value = false;
  }
}

// ---- education level (the career stage picked in onboarding)
const stageError = ref('');
const stageSaved = ref(false);
let stageTimer: number | undefined;

/** Switch right away, then save it; put the old level back if saving fails. */
async function pickStage(next: number) {
  const id = profileId();
  const previous = state.value.who;
  if (next === previous || !id) return;
  state.value.who = next;
  stageError.value = '';
  stageSaved.value = false;
  try {
    await updateProfile(id, { stage: stageForWho[next]! });
    stageSaved.value = true;
    window.clearTimeout(stageTimer);
    stageTimer = window.setTimeout(() => (stageSaved.value = false), 2500);
  } catch {
    state.value.who = previous;
    stageError.value = 'Couldn’t save your education level. Try again.';
  }
}

// ---- interests
const interestOptions = ref<Interest[] | null>(null);
const interestsLoadError = ref(false);
const editingInterests = ref(false);
const interestDraft = ref<number[]>([]);
const savingInterests = ref(false);
const interestsError = ref('');

const pickedInterests = computed(() => (interestOptions.value ?? []).filter((i) => state.value.interests.includes(i.id)));

function startInterestEdit() {
  interestDraft.value = state.value.interests.slice(0, MAX_INTERESTS);
  interestsError.value = '';
  editingInterests.value = true;
}

async function saveInterests() {
  const id = profileId();
  if (!id || !interestDraft.value.length || savingInterests.value) return;
  savingInterests.value = true;
  interestsError.value = '';
  try {
    const saved = await updateProfile(id, { interests: interestDraft.value });
    state.value.interests = saved.interests;
    editingInterests.value = false;
  } catch {
    interestsError.value = 'Couldn’t save your interests. Try again.';
  } finally {
    savingInterests.value = false;
  }
}

// ---- bee
const beeError = ref('');
const beeSaved = ref(false);
let beeTimer: number | undefined;

/** Switch right away so the whole app follows, then save it; put the old bee back if saving fails. */
async function pickBee(next: BeeName) {
  const id = profileId();
  const previous = bee.value;
  if (next === previous) return;
  bee.value = next;
  beeError.value = '';
  beeSaved.value = false;
  if (!id) return;
  try {
    await setBee(id, next);
    beeSaved.value = true;
    window.clearTimeout(beeTimer);
    beeTimer = window.setTimeout(() => (beeSaved.value = false), 2500);
  } catch {
    bee.value = previous;
    beeError.value = 'Couldn’t save your bee. Try again.';
  }
}

// ---- roadmaps and learned skills load on their own, so one failing doesn't hide the other
const roadmaps = ref<RoadmapSummary[] | null>(null);
const roadmapsError = ref(false);
const learned = ref<LearnedSkill[] | null>(null);
/** The SDG targets behind each skill and interest chip, shown on hover. A chip with none stays plain. */
const skillSdgs = ref<Map<string, SkillSdg>>(new Map());
onMounted(async () => (skillSdgs.value = await fetchSkillSdgs()));
const interestTargets = (name: string) => (INTEREST_SDGS[name] ?? []).flatMap((g) => g.targets.map((t) => ({ ...t, sdg: g.sdg })));
const learnedError = ref(false);

const active = computed(() => (roadmaps.value ?? []).filter((r) => r.status !== 'completed'));
const finished = computed(() => (roadmaps.value ?? []).filter((r) => r.status === 'completed'));

/** Learned skills bundled by skill group; skills with no group go last. */
const learnedGroups = computed(() => {
  const groups = new Map<string, LearnedSkill[]>();
  for (const s of learned.value ?? []) {
    const key = s.skill_group ?? 'Other skills';
    groups.set(key, [...(groups.get(key) ?? []), s]);
  }
  return [...groups].sort(([a], [b]) => Number(a === 'Other skills') - Number(b === 'Other skills') || a.localeCompare(b));
});

function openRole(r: RoadmapSummary) {
  openRoadmap(state.value, r.onet_code);
  router.push(go('pathway'));
}

onMounted(() => {
  fetchInterests().then((i) => (interestOptions.value = i)).catch(() => (interestsLoadError.value = true));
  const id = profileId();
  if (!id) {
    roadmapsError.value = true;
    learnedError.value = true;
    return;
  }
  getProfile(id).then((p) => {
    name.value = p.name;
    state.value.name = p.name;
    state.value.who = Math.max(stageForWho.indexOf(p.stage), 0);
    state.value.interests = p.interests ?? [];
  }).catch(() => {});
  fetchRoadmapSummaries(id).then((r) => (roadmaps.value = r)).catch(() => (roadmapsError.value = true));
  fetchLearnedSkills(id).then((l) => (learned.value = l)).catch(() => (learnedError.value = true));
});
</script>

<template>
  <div class="tab">
    <div class="page">
      <p class="eyebrow">Profile</p>

      <!-- Name -->
      <section class="card block">
        <h2>Your name</h2>
        <form v-if="editing" class="edit" @submit.prevent="saveName">
          <input v-model="draft" class="field" type="text" maxlength="40" placeholder="Your first name or nickname" autocomplete="given-name" autofocus />
          <button class="btn btn-primary" type="submit" :disabled="!draft.trim() || savingName">{{ savingName ? 'Saving…' : 'Save' }}</button>
          <button class="btn btn-secondary" type="button" :disabled="savingName" @click="editing = false">Cancel</button>
        </form>
        <div v-else class="show">
          <strong class="nm">{{ name || 'Your name' }}</strong>
          <button type="button" class="link" @click="startEdit"><Icon name="pencil" :size="16" /> Edit</button>
        </div>
        <p v-if="nameError" class="error" role="alert">{{ nameError }}</p>
      </section>

      <!-- Education level -->
      <section class="card block">
        <div class="head">
          <h2>Your education level</h2>
          <span v-if="stageSaved" class="saved"><Icon name="check" :size="14" :stroke="3" /> Saved</span>
        </div>
        <p class="hint">It counts towards how well each role matches you. New matches use it the next time you regenerate your roles.</p>
        <div class="stages" role="radiogroup" aria-label="Education level">
          <button
            v-for="(o, i) in whoOptions"
            :key="o.title"
            type="button"
            role="radio"
            class="option stage"
            :class="{ selected: state.who === i }"
            :aria-checked="state.who === i"
            @click="pickStage(i)"
          >
            <span class="stage-ic" aria-hidden="true"><Icon :name="o.icon" :size="20" /></span>
            <span class="stage-txt"><h3>{{ o.title }}</h3><span>{{ o.sub }}</span></span>
            <span v-if="state.who === i" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
          </button>
        </div>
        <p v-if="stageError" class="error" role="alert">{{ stageError }}</p>
      </section>

      <!-- Interests -->
      <section class="card block">
        <div class="head">
          <h2>Your interests</h2>
          <button v-if="!editingInterests && interestOptions" type="button" class="link" @click="startInterestEdit"><Icon name="pencil" :size="16" /> Edit</button>
        </div>
        <p class="hint">They steer your matches towards the goals you care about. New matches use them the next time you regenerate your roles.</p>
        <p v-if="interestsLoadError" class="hint">Couldn’t load the interests right now.</p>
        <div v-else-if="interestOptions === null" class="skels" aria-hidden="true"><span class="skel chips-skel" /></div>
        <form v-else-if="editingInterests" @submit.prevent="saveInterests">
          <InterestPicker v-model="interestDraft" :interests="interestOptions" hint-id="profile-interests-hint" />
          <div class="actions">
            <button class="btn btn-primary" type="submit" :disabled="!interestDraft.length || savingInterests">{{ savingInterests ? 'Saving…' : 'Save' }}</button>
            <button class="btn btn-secondary" type="button" :disabled="savingInterests" @click="editingInterests = false">Cancel</button>
          </div>
        </form>
        <div v-else-if="pickedInterests.length" class="chips">
          <template v-for="i in pickedInterests" :key="i.id">
            <SdgTip v-if="interestTargets(i.interest).length" :title="i.interest" :targets="interestTargets(i.interest)" class="chip-have"><Icon :name="i.icon" :size="14" /> {{ i.interest }}</SdgTip>
            <span v-else class="chip chip-have"><Icon :name="i.icon" :size="14" /> {{ i.interest }}</span>
          </template>
        </div>
        <p v-else class="hint">None picked yet.</p>
        <p v-if="interestsError" class="error" role="alert">{{ interestsError }}</p>
      </section>

      <!-- Bee -->
      <section class="card block">
        <div class="head">
          <h2>Your bee</h2>
          <span v-if="beeSaved" class="saved"><Icon name="check" :size="14" :stroke="3" /> Saved</span>
        </div>
        <p class="hint">Pick who keeps you company. It changes everywhere in the app.</p>
        <BeePicker :columns="4" @pick="pickBee" />
        <p v-if="beeError" class="error" role="alert">{{ beeError }}</p>
      </section>

      <!-- Roadmaps -->
      <section class="card block">
        <h2>Your roadmaps</h2>
        <p v-if="roadmapsError" class="hint">Couldn’t load your roadmaps right now.</p>
        <div v-else-if="roadmaps === null" class="skels" aria-hidden="true"><span class="skel" style="height: 92px" /><span class="skel" style="height: 92px" /></div>
        <template v-else-if="roadmaps.length">
          <div v-for="(group, i) in [active, finished]" :key="i">
            <h3 v-if="group.length" class="sub">{{ i === 0 ? 'Active' : 'Completed' }}</h3>
            <article v-for="r in group" :key="r.onet_code" class="rm">
              <div class="rt">
                <strong>{{ r.title }}</strong>
                <span class="chip-s" :class="roadmapStatus(r).key">
                  <Icon v-if="roadmapStatus(r).key === 'completed'" name="check" :size="13" :stroke="3" /> {{ roadmapStatus(r).label }}
                </span>
              </div>
              <div class="bar">
                <div class="progress"><i :style="{ width: (r.total ? (r.completed / r.total) * 100 : 0) + '%' }" /></div>
                <small>{{ r.completed }} of {{ r.total }} skills · {{ r.total ? Math.round((r.completed / r.total) * 100) : 0 }}%</small>
              </div>
              <button type="button" class="btn btn-secondary go" @click="openRole(r)"><Icon name="route" :size="16" /> View roadmap</button>
            </article>
          </div>
        </template>
        <div v-else class="empty">
          <Bubble :size="52">No roadmaps yet. Pick a role and I’ll build one for you.</Bubble>
          <RouterLink :to="go('suggested')" class="btn btn-secondary">See my roles</RouterLink>
        </div>
      </section>

      <!-- Skills learned -->
      <section class="card block">
        <div class="head">
          <h2>Skills you’ve learned</h2>
          <span v-if="learned?.length" class="pill pill-dark">{{ learned.length }} skills</span>
        </div>
        <p v-if="learnedError" class="hint">Couldn’t load your skills right now.</p>
        <div v-else-if="learned === null" class="skels" aria-hidden="true"><span class="skel line" style="width: 30%" /><span class="skel chips-skel" /></div>
        <template v-else-if="learned.length">
          <div v-for="[group, skills] in learnedGroups" :key="group" class="grp">
            <h3 class="sub">{{ group }}</h3>
            <div class="chips">
              <template v-for="s in skills" :key="s.skill_name">
                <SdgTip v-if="skillSdgs.get(s.skill_name)?.targets.length" :title="skillLabel(s.skill_name)" :targets="skillSdgs.get(s.skill_name)!.targets" class="chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s.skill_name) }}</SdgTip>
                <span v-else class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s.skill_name) }}</span>
              </template>
            </div>
          </div>
        </template>
        <Bubble v-else :size="52">Nothing yet. Finish a skill on your roadmap and it’ll show up here.</Bubble>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 820px; display: flex; flex-direction: column; gap: 18px; }
.eyebrow { font-size: 13px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.block { padding: 20px 24px; }
h2 { font-weight: 900; font-size: 20px; margin-bottom: 12px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.hint { font-size: 15px; font-weight: 600; color: var(--muted); margin-bottom: 14px; }
.error { margin-top: 12px; padding: 10px 14px; border-radius: 12px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 15px; }
.saved { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 900; color: var(--orange); }

.show { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.nm { font-size: 30px; font-weight: 900; overflow-wrap: anywhere; }
.link { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.link:hover { color: var(--ink); }
.edit { display: flex; gap: 10px; flex-wrap: wrap; }
.field { flex: 1; min-width: 200px; padding: 12px 16px; border: 2px solid var(--line-strong); border-radius: 14px; background: #fff; font: 800 16px 'Nunito', sans-serif; color: var(--ink); outline: none; }
.field:focus { border-color: var(--orange); }

.stages { display: flex; flex-direction: column; gap: 10px; }
.stage { align-items: center; gap: 14px; padding: 14px 16px; text-align: left; }
.stage-ic { flex: none; width: 40px; height: 40px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.selected .stage-ic { background: var(--yellow); }
.stage-txt { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.stage-txt h3 { font-size: 18px; }
.stage-txt span { font-size: 14px; font-weight: 600; color: var(--muted); }

.sub { font-size: 13px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin: 14px 0 8px; }
.rm { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 8px 16px; padding: 14px 0; border-top: 2px solid var(--line); }
.rm:first-of-type { border-top: 0; }
.rt { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rt strong { font-size: 18px; font-weight: 900; }
.chip-s { display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 999px; font-size: 14px; font-weight: 800; border: 2px solid var(--line-strong); color: var(--muted); background: #fff; }
.chip-s.ready { background: var(--cream); border-color: var(--yellow); color: var(--ink); }
.chip-s.started { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.chip-s.completed { background: var(--ink); border-color: var(--ink); color: var(--yellow); }
.bar { grid-column: 1; display: flex; flex-direction: column; gap: 4px; }
.bar .progress { height: 10px; }
.bar small { font-size: 14px; font-weight: 700; color: var(--muted); }
.go { grid-column: 2; grid-row: 1 / span 2; display: inline-flex; align-items: center; gap: 8px; }
.empty { display: flex; flex-direction: column; align-items: flex-start; gap: 14px; }

.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.actions { display: flex; gap: 10px; margin-top: 14px; }
.chip { font-size: 14px; padding: 6px 11px 6px 9px; }
@media (max-width: 600px) { .rm { grid-template-columns: 1fr; } .go { grid-column: 1; grid-row: auto; } }
.skels { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.chips-skel { height: 34px; width: 80%; border-radius: 999px; }
</style>
