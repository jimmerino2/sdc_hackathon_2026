<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PollenField from '../components/PollenField.vue';
import { bee } from '../bee';
import { setBee, createProfile, ProfileNotFound, readProfileId, saveProfileId, stageForWho, updateProfile } from '../api/profile';
import { loadJobs, useFlow } from '../state';
import { go } from '../router';
import { personaCopy } from '../data/personaCopy';

const { state, key, profileSkills } = useFlow();
const router = useRouter();
const stage = ref(0);
const working = ref(true);
let timer: number | undefined;

const items = computed(() => [
  `${state.value.resume ? 'Read your resume' : 'Read your skill check'} · ${profileSkills.value.length} skills found`,
  'Matched your skills to O*NET 31.0',
  personaCopy[key.value].loadingMatch,
]);

async function saveProfile() {
  const s = state.value;
  const body = {
    name: s.name.trim() || 'Jobee learner',
    stage: stageForWho[s.who]!,
    interests: s.interests,
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
    await setBee(profile.profile_id, bee.value).catch((e) => console.error(e));
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
      router.push(go('roles'));
    }
  }, 1400);
  await saveProfile();
  await loadJobs(state.value);
  working.value = false;
});
onBeforeUnmount(() => clearInterval(timer));

const pct = computed(() => Math.round(Math.min(100, 12 + (stage.value * 88) / items.value.length)));
const status = computed(() => items.value[Math.min(stage.value, items.value.length - 1)]);
</script>

<template>
  <div class="page">
    <div class="stack">
      <PollenField />
      <div class="progress" role="progressbar" aria-label="Mapping your future" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="pct"><i :style="{ width: pct + '%' }" /></div>
      <p class="status" role="status" aria-live="polite">
        <Transition name="swap" mode="out-in"><span :key="status">{{ status }}</span></Transition>
      </p>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px 20px; gap: 28px; }
.stack { width: 100%; max-width: 440px; display: flex; flex-direction: column; align-items: center; }
.stack :deep(.fpv) { margin-bottom: 28px; }
.progress { width: 100%; height: 14px; margin-bottom: 18px; }
.status { min-height: 2.8em; text-align: center; font-weight: 800; font-size: 17px; line-height: 1.4; color: var(--ink); }
.swap-enter-active, .swap-leave-active { transition: opacity .2s ease, transform .2s ease; }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
