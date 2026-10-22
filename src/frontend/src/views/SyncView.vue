<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { getProfile, markLoggedIn, readProfileId, sendSyncCode, SyncError, verifySyncCode } from '../api/profile';
import { useFlow } from '../state';

const { state } = useFlow();
const step = ref<'email' | 'code' | 'done'>(state.value.email ? 'done' : 'email');
const email = ref(state.value.email ?? '');
const code = ref('');
const busy = ref(false);
const error = ref<string | null>(null);
const sentTo = ref('');

const emailOk = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()));
const codeOk = computed(() => /^\d{6,8}$/.test(code.value.trim()));

function profileId() {
  state.value.profileId ??= readProfileId();
  return state.value.profileId;
}

async function run(task: () => Promise<void>) {
  error.value = null;
  busy.value = true;
  try {
    await task();
  } catch (e) {
    error.value = e instanceof SyncError ? e.message : 'Something went wrong. Try again in a moment.';
  } finally {
    busy.value = false;
  }
}

function sendCode() {
  const id = profileId();
  if (!id) {
    error.value = 'Your profile wasn’t saved. Go back and finish the questions again.';
    return;
  }
  if (!emailOk.value || busy.value) return;
  const to = email.value.trim();
  run(async () => {
    await sendSyncCode(id, to);
    sentTo.value = to;
    code.value = '';
    step.value = 'code';
  });
}

function verify() {
  const id = profileId();
  if (!id || !codeOk.value || busy.value) return;
  run(async () => {
    const profile = await verifySyncCode(id, sentTo.value, code.value.trim());
    state.value.email = profile.email ?? sentTo.value;
    markLoggedIn();
    step.value = 'done';
  });
}

function changeEmail() {
  error.value = null;
  step.value = 'email';
}

onMounted(async () => {
  // Already synced on an earlier visit: skip straight to "done".
  const id = profileId();
  if (!id || state.value.email) return;
  try {
    const profile = await getProfile(id);
    if (profile.email) {
      state.value.email = profile.email;
      markLoggedIn();
      email.value = profile.email;
      step.value = 'done';
    }
  } catch {
    // Not fatal: the user can still sync from scratch.
  }
});
</script>

<template>
  <FlowShell :progress="5" next="building" next-label="Build my roadmap" back="signal" mood="happy" :next-disabled="step !== 'done'">
    <template #bubble>Where should I save your roadmap?</template>

    <form v-if="step === 'email'" class="card block" @submit.prevent="sendCode">
      <label for="email">Email address</label>
      <input id="email" v-model="email" class="field" type="email" placeholder="you@example.com" autocomplete="email" autofocus />
      <button class="btn btn-primary" type="submit" :disabled="!emailOk || busy">{{ busy ? 'Sending…' : 'Send me a code' }}</button>
      <small>One-time code, no password.</small>
    </form>

    <form v-else-if="step === 'code'" class="card block" @submit.prevent="verify">
      <label for="code">Enter the code we sent to <strong>{{ sentTo }}</strong></label>
      <input id="code" v-model="code" class="field code" type="text" inputmode="numeric" maxlength="8" placeholder="123456" autocomplete="one-time-code" autofocus />
      <button class="btn btn-primary" type="submit" :disabled="!codeOk || busy">{{ busy ? 'Checking…' : 'Verify' }}</button>
      <div class="links">
        <button type="button" :disabled="busy" @click="sendCode">Resend code</button>
        <button type="button" :disabled="busy" @click="changeEmail">Use a different email</button>
      </div>
    </form>

    <div v-else class="card block done">
      <span class="ok" aria-hidden="true"><Icon name="check" :size="20" :stroke="3" /></span>
      <div class="txt"><strong>Email synced</strong><small>{{ state.email }}</small></div>
      <button type="button" class="change" @click="changeEmail">Change</button>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </FlowShell>
</template>

<style scoped>
.block { padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
label { font-weight: 800; font-size: 14px; }
.field {
  width: 100%; padding: 14px 16px; border: 2px solid var(--line-strong); border-radius: 14px; background: #fff;
  font: 800 16px 'Nunito', sans-serif; color: var(--ink); outline: none;
}
.field:focus { border-color: var(--orange); box-shadow: 0 0 0 4px rgba(255, 193, 7, .3); }
.field.code { letter-spacing: .3em; font-size: 20px; }
small { font-size: 12px; font-weight: 600; color: var(--muted); }
.links { display: flex; gap: 18px; }
.links button, .change { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.links button:hover, .change:hover { color: var(--ink); }
.done { flex-direction: row; align-items: center; gap: 14px; }
.ok { width: 36px; height: 36px; border-radius: 50%; background: var(--ink); color: var(--yellow); display: grid; place-items: center; flex: none; }
.txt { display: flex; flex-direction: column; flex: 1; min-width: 0; } .txt strong { font-weight: 900; } .txt small { overflow-wrap: anywhere; }
.error { margin-top: 14px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; line-height: 1.4; }
</style>
