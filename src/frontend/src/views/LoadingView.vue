<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import Icon from '../components/Icon.vue';
import Mascot from '../components/Mascot.vue';
import { mindOptions } from '../data/flows';
import { createProfile, ProfileNotFound, readProfileId, saveProfileId, stageForWho, updateProfile } from '../api/profile';
import { loadJobs, useFlow } from '../state';
import { go } from '../router';

const { key, state, profileSkills } = useFlow();
const router = useRouter();
const stage = ref(0);
const working = ref(true);
let timer: number | undefined;

const items = computed(() => [
  `${state.value.resume ? 'Read your resume' : 'Read your skill check'} · ${profileSkills.value.length} skills found`,
  'Matched your skills to O*NET 31.0',
  'Finding your best-fit roles across 3 AI futures',
]);

async function saveProfile() {
  const s = state.value;
  const body = {
    name: s.name,
    stage: stageForWho[s.who]!,
    concerns: s.mind.map((i) => mindOptions[i]!.title).join('; '),
    skills: profileSkills.value,
    experience: [],
  };
  const id = readProfileId();
  try {
    // A stored id means this browser already has a profile: update it instead of making another.
    const profile = id
      ? await updateProfile(id, body).catch((e) => {
          if (e instanceof ProfileNotFound) return createProfile(body);
          throw e;
        })
      : await createProfile(body);
    s.profileId = profile.profile_id;
    saveProfileId(profile.profile_id);
  } catch (e) {
    console.error(e);
    s.profileId = null;
  }
}

onMounted(async () => {
  // The last step waits on the real work (saving the profile, then matching roles), so the roles page opens ready.
  timer = window.setInterval(() => {
    if (stage.value < items.value.length - 1) stage.value++;
    else if (!working.value) {
      clearInterval(timer);
      stage.value = items.value.length;
      router.push(go(key.value, 'roles'));
    }
  }, 1400);
  await saveProfile();
  await loadJobs(state.value);
  working.value = false;
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <div class="page">
    <div class="halo"><Mascot :size="100" class="m" /></div>
    <h1>Mapping your future…</h1>
    <p class="sub">Hang tight, this can take up to half a minute.</p>
    <div class="progress"><i :style="{ width: Math.min(100, 12 + (stage * 88) / items.length) + '%' }" /></div>
    <ul class="card">
      <li v-for="(t, i) in items" :key="t" :class="{ done: i < stage, now: i === stage, wait: i > stage }">
        <span class="dot"><Icon v-if="i <= stage" :name="i < stage ? 'check' : 'sparkles'" :size="13" :stroke="3" /></span>
        {{ t }}
      </li>
    </ul>
    <div class="know">
      <small>Did you know?</small>
      <p>Software roles that use AI tools are growing faster than the ones that don’t. That’s your opening.</p>
    </div>
    <RouterLink :to="go(key, 'roles')" class="skip">Skip</RouterLink>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; max-width: 400px; margin: 0 auto; padding: 60px 20px; display: flex; flex-direction: column; align-items: center; }
.halo { width: 150px; height: 150px; border-radius: 50%; background: var(--cream); display: grid; place-items: center; margin-bottom: 28px; animation: float 2.4s ease-in-out infinite; }
@keyframes float { 50% { transform: translateY(-8px); } }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 8px; } .sub { color: var(--muted); font-weight: 600; font-size: 14px; margin-bottom: 24px; }
.progress { width: 100%; height: 12px; margin-bottom: 20px; }
ul { list-style: none; width: 100%; padding: 12px 20px; display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }
li { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 14px; }
.dot { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; flex: none; border: 2px solid var(--line-strong); }
.done .dot { background: var(--ink); color: var(--yellow); border-color: var(--ink); }
.now .dot { background: var(--yellow); border-color: var(--yellow); color: var(--ink); }
.wait { color: var(--muted); }
.know { width: 100%; background: var(--cream); border-radius: 16px; padding: 14px 18px; }
.know small { font-size: 10px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.know p { font-weight: 800; font-size: 14px; line-height: 1.4; margin-top: 4px; }
.skip { margin-top: 22px; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
</style>
