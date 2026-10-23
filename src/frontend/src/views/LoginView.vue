<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import Logo from '../components/Logo.vue';
import Bubble from '../components/Bubble.vue';
import { sendLoginCode, SyncError, verifyLoginCode } from '../api/profile';
import { signIn } from '../state';
import { go } from '../router';

const router = useRouter();
const step = ref<'email' | 'code'>('email');
const email = ref('');
const code = ref('');
const sentTo = ref('');
const busy = ref(false);
const error = ref<string | null>(null);

const emailOk = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()));
const codeOk = computed(() => /^\d{6,8}$/.test(code.value.trim()));

/** Jobee follows along: perks up when the input looks right, thinks while waiting, startles on an error. */
const mood = computed(() => {
  if (error.value) return 'surprised';
  if (busy.value) return 'thinking';
  return (step.value === 'email' ? emailOk.value : codeOk.value) ? 'happy' : 'wave';
});

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
  if (!emailOk.value || busy.value) return;
  const to = email.value.trim();
  run(async () => {
    await sendLoginCode(to);
    sentTo.value = to;
    code.value = '';
    step.value = 'code';
  });
}

function verify() {
  if (!codeOk.value || busy.value) return;
  run(async () => {
    signIn(await verifyLoginCode(sentTo.value, code.value.trim()));
    router.push(go('pathway'));
  });
}

function changeEmail() {
  error.value = null;
  step.value = 'email';
}
</script>

<template>
  <div class="page">
    <header><Logo /></header>
    <main>
      <h1>Welcome back</h1>
      <Bubble class="b" :size="60" :mood="mood">
        {{ step === 'email' ? 'Enter the email you saved your roadmap with and I’ll send you a code.' : 'Check your inbox! I just sent you a code.' }}
      </Bubble>

      <form v-if="step === 'email'" class="card block" @submit.prevent="sendCode">
        <label for="email">Email address</label>
        <input id="email" v-model="email" class="field" type="email" placeholder="you@example.com" autocomplete="email" autofocus />
        <button class="btn btn-primary" type="submit" :disabled="!emailOk || busy">{{ busy ? 'Sending…' : 'Send me a code' }}</button>
      </form>

      <form v-else class="card block" @submit.prevent="verify">
        <label for="code">Enter the code we sent to <strong>{{ sentTo }}</strong></label>
        <input id="code" v-model="code" class="field code" type="text" inputmode="numeric" maxlength="8" placeholder="12345678" autocomplete="one-time-code" autofocus />
        <button class="btn btn-primary" type="submit" :disabled="!codeOk || busy">{{ busy ? 'Checking…' : 'Log in' }}</button>
        <div class="links">
          <button type="button" :disabled="busy" @click="sendCode">Resend code</button>
          <button type="button" :disabled="busy" @click="changeEmail">Use a different email</button>
        </div>
      </form>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <RouterLink :to="go('landing')" class="back">Back</RouterLink>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; display: flex; flex-direction: column; }
header { padding: 32px 80px; }
main { width: 100%; max-width: 480px; margin: 0 auto; padding: 24px 20px 60px; }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 22px; }
.block { padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
label { font-weight: 800; font-size: 14px; }
.field {
  width: 100%; padding: 14px 16px; border: 2px solid var(--line-strong); border-radius: 14px; background: #fff;
  font: 800 16px 'Nunito', sans-serif; color: var(--ink); outline: none;
}
.field:focus { border-color: var(--orange); }
.field.code { letter-spacing: .3em; font-size: 20px; }
.links { display: flex; gap: 18px; }
.links button, .back { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.links button:hover, .back:hover { color: var(--ink); }
.back { display: inline-block; margin-top: 22px; }
.error { margin-top: 14px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; line-height: 1.4; }
@media (max-width: 900px) { header { padding: 20px; } }
</style>
