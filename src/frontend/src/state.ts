import { computed, reactive } from 'vue';
import { personas, scenarios, type PersonaKey, type Role, type ScenarioKey } from './data/flows';
import { DEFAULT_SKILLS, LEVEL_SCORES, levelFromScore, mergeSkills, SKILL_CHECK_SIZE } from './data/skills';
import type { SkillScore } from './api/resume';
import { fetchRecommendations, JobsError, type Recommendations } from './api/jobs';
import { ensureRoadmap, getRoadmap, RoadmapError, type Roadmap } from './api/roadmap';
import { readProfileId, saveProfileId, stageForWho, type Profile } from './api/profile';
import { bee, BEES, type BeeName } from './bee';

interface FlowState {
  name: string;
  who: number;
  mind: number[];
  /** Skill check answers: O*NET skill name -> level index (see LEVEL_SCORES). */
  levels: Record<string, number>;
  scenario: ScenarioKey;
  /** Roles page layout: role cards, or the demand-vs-AI chart. */
  rolesView: 'cards' | 'chart';
  chosenRoleId: string | null;
  profileId: string | null;
  resume: { filename: string; size: number; pages: number; skills: SkillScore[] } | null;
  jobs: { status: 'idle' | 'loading' | 'done' | 'error'; data: Recommendations | null; error: string | null };
  /** The email confirmed on the profile, once synced. */
  email: string | null;
  /** Skills already saved on the profile, when the user came back by logging in. */
  savedSkills: SkillScore[];
  roadmap: { status: 'idle' | 'loading' | 'done' | 'error'; data: Roadmap | null; error: string | null };
}

const store = reactive<Record<PersonaKey, FlowState>>({
  a: init('a'),
  b: init('b'),
  c: init('c'),
});

function init(k: PersonaKey): FlowState {
  const p = personas[k];
  return {
    name: '',
    who: p.whoIndex,
    mind: [],
    levels: {},
    scenario: 'accelerates',
    rolesView: 'cards',
    chosenRoleId: null,
    profileId: null,
    resume: null,
    jobs: { status: 'idle', data: null, error: null },
    email: null,
    savedSkills: [],
    roadmap: { status: 'idle', data: null, error: null },
  };
}

export function resetPersona(k: PersonaKey) {
  Object.assign(store[k], init(k));
}

/** Start the app as a returning user: keep their profile id and restore what the profile holds. */
export function signIn(profile: Profile) {
  const s = store.a;
  Object.assign(s, init('a'));
  s.profileId = profile.profile_id;
  s.name = profile.name;
  s.email = profile.email ?? null;
  s.savedSkills = profile.skills;
  s.who = Math.max(stageForWho.indexOf(profile.stage), 0);
  if ((BEES as readonly string[]).includes(profile.bee ?? '')) bee.value = profile.bee as BeeName; // their bee, not this browser's
  saveProfileId(profile.profile_id);
}

/** Fetch the matched roles for the saved profile into state.jobs. Never throws. */
export async function loadJobs(s: FlowState) {
  if (!s.profileId) {
    s.jobs = { status: 'error', data: null, error: 'Your profile wasn’t saved, so Jobee can’t match roles yet. Try again.' };
    return;
  }
  s.jobs = { status: 'loading', data: null, error: null };
  try {
    s.jobs = { status: 'done', data: await fetchRecommendations(s.profileId), error: null };
  } catch (e) {
    console.error(e);
    s.jobs = { status: 'error', data: null, error: e instanceof JobsError ? e.message : 'Jobee couldn’t match roles just now. Try again in a moment.' };
  }
}

/** Load the chosen role's roadmap into state.roadmap, building it first if needed. Never throws. */
export async function loadRoadmap(s: FlowState) {
  s.profileId ??= readProfileId();
  if (!s.profileId) {
    s.roadmap = { status: 'error', data: null, error: 'Your profile wasn’t saved. Go back and finish the questions again.' };
    return;
  }
  s.roadmap = { status: 'loading', data: null, error: null };
  try {
    if (!s.chosenRoleId) {
      // No role picked in this session (e.g. after logging in): resume the profile's latest saved roadmap.
      const saved = await getRoadmap(s.profileId);
      if (!saved) {
        s.roadmap = { status: 'error', data: null, error: 'You haven’t built a roadmap yet. Pick a role first, then Jobee can build it.' };
        return;
      }
      s.chosenRoleId = saved.onet_code;
      s.roadmap = { status: 'done', data: saved, error: null };
      return;
    }
    s.roadmap = { status: 'done', data: await ensureRoadmap(s.profileId, s.chosenRoleId), error: null };
  } catch (e) {
    console.error(e);
    s.roadmap = { status: 'error', data: null, error: e instanceof RoadmapError ? e.message : 'Jobee couldn’t build your roadmap just now. Try again in a moment.' };
  }
}

export function useFlow() {
  const key = computed<PersonaKey>(() => 'a'); // one persona's copy for now; the address no longer carries it
  const persona = computed(() => personas[key.value]);
  const state = computed(() => store[key.value]);
  const scenario = computed(() => scenarios.find((s) => s.key === state.value.scenario)!);
  const roles = computed<Role[]>(() => persona.value.roles[state.value.scenario]);
  const chosenRole = computed<Role>(() => {
    const all = Object.values(persona.value.roles).flat();
    return all.find((r) => r.id === state.value.chosenRoleId) ?? persona.value.roles.accelerates[0]!;
  });

  /** Skills asked about in the skill check: the resume's strongest first, then common ones. */
  const checkSkills = computed(() => {
    const fromResume = state.value.resume?.skills.map((s) => s.name) ?? [];
    return [...new Set([...fromResume, ...DEFAULT_SKILLS])].slice(0, SKILL_CHECK_SIZE);
  });
  /** The level shown for a skill: the user's answer, else a guess from the resume, else New. */
  function levelOf(name: string): number {
    const answered = state.value.levels[name];
    if (answered !== undefined) return answered;
    const seen = state.value.resume?.skills.find((s) => s.name === name);
    return seen ? levelFromScore(seen.score) : 0;
  }
  /** What goes on the profile: rated skills plus the resume's other skills, each with a 0-1 score. */
  const profileSkills = computed<SkillScore[]>(() =>
    mergeSkills(
      checkSkills.value.map((name) => ({ name, score: LEVEL_SCORES[levelOf(name)]! })),
      state.value.resume?.skills ?? [],
    ),
  );

  return { key, persona, state, scenario, roles, chosenRole, checkSkills, levelOf, profileSkills };
}
