<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import Icon from '../Icon.vue';
import Robbee from './Robbee.vue';
import { createChallenge, fetchChallengeRoles, RoadmapError, type ChallengeRole, type RoadmapChallenge } from '../../api/roadmap';

/** Pick a tech role and have a new challenge written for it (20-40 seconds). */
const props = defineProps<{ profileId: string }>();
const emit = defineEmits<{ close: []; created: [challenge: RoadmapChallenge] }>();

const roles = ref<ChallengeRole[] | null>(null);
const error = ref<string | null>(null);
/** The role a challenge is being written for. */
const writing = ref<ChallengeRole | null>(null);
const first = ref<HTMLButtonElement | null>(null);

async function load() {
  error.value = null;
  try {
    roles.value = await fetchChallengeRoles(props.profileId);
    nextTick(() => first.value?.focus());
  } catch (e) {
    error.value = e instanceof RoadmapError ? e.message : 'Jobee couldn’t load the roles. Try again in a moment.';
  }
}

async function pick(r: ChallengeRole) {
  if (writing.value) return;
  writing.value = r;
  error.value = null;
  try {
    emit('created', await createChallenge(props.profileId, r.onet_code));
  } catch (e) {
    error.value = e instanceof RoadmapError ? e.message : 'Jobee couldn’t write a challenge just now. Try again in a moment.';
    writing.value = null;
  }
}

const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && !writing.value) emit('close'); };
onMounted(() => { window.addEventListener('keydown', onKey); load(); });
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
  <Teleport to="body">
    <div class="jb nc" role="dialog" aria-modal="true" aria-labelledby="nc-title">
      <div class="nc__dim" @click="!writing && emit('close')" />
      <div class="nc__card">
        <template v-if="writing">
          <div class="nc__writing" aria-live="polite">
            <Robbee :size="120" />
            <h2 id="nc-title">Writing a {{ writing.title }} challenge…</h2>
            <p>Robbee is drafting a fresh project from the role’s skills and your interests. This takes about half a minute.</p>
            <span class="nc__dots" aria-hidden="true"><i /><i /><i /></span>
          </div>
        </template>
        <template v-else>
          <header class="nc__head">
            <div>
              <h2 id="nc-title">New challenge</h2>
              <p>Pick a role. You’ll get a new project for it, different from the ones you already have.</p>
            </div>
            <button type="button" class="nc__x" aria-label="Close" @click="emit('close')"><Icon name="x" :size="22" /></button>
          </header>
          <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
          <div v-if="!roles && !error" class="nc__list" aria-busy="true">
            <div v-for="i in 5" :key="i" class="skel card nc__skel" />
          </div>
          <ul v-else-if="roles" class="nc__list">
            <li v-for="(r, i) in roles" :key="r.onet_code">
              <button :ref="(el) => { if (i === 0) first = el as HTMLButtonElement }" type="button" class="nc__role" @click="pick(r)">
                <span class="nc__icon"><Icon :name="r.icon ?? 'code'" :size="20" /></span>
                <span class="nc__name">{{ r.title }}</span>
                <span v-if="r.suggested" class="nc__tag">Suggested</span>
                <span v-if="r.challenges" class="nc__count">{{ r.challenges }} {{ r.challenges === 1 ? 'challenge' : 'challenges' }}</span>
                <Icon class="nc__go" name="arrow" :size="18" />
              </button>
            </li>
          </ul>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.nc { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 16px; font-family: var(--font-sans); }
.nc__dim { position: absolute; inset: 0; background: rgba(40, 36, 28, .45); }
.nc__card { position: relative; display: flex; flex-direction: column; gap: 14px; width: min(620px, 100%); max-height: min(720px, calc(100vh - 32px)); padding: 24px; border: 2px solid var(--honey); border-radius: 24px; background: var(--surface-raised); box-shadow: var(--shadow-lift); animation: jb-rise var(--dur-base) var(--ease-out) both; }
.nc__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.nc__head h2, .nc__writing h2 { margin: 0; font-size: 30px; line-height: 36px; font-weight: 900; }
.nc__head p, .nc__writing p { margin: 4px 0 0; color: var(--text-muted); font-size: 16px; line-height: 23px; font-weight: 600; }
.nc__x { flex: none; display: grid; place-items: center; width: 40px; height: 40px; border: 0; border-radius: 50%; background: #f1ece0; color: var(--text); cursor: pointer; }
.nc__x:focus-visible, .nc__role:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.nc__list { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0 4px 4px 0; list-style: none; overflow-y: auto; }
.nc__skel { height: 56px; border-radius: var(--radius-md); }
.nc__role { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border: 2px solid var(--line); border-radius: var(--radius-md); background: var(--surface); color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out); }
.nc__role:hover { border-color: var(--honey); background: var(--honey-tint); }
.nc__icon { flex: none; display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: var(--honey); color: var(--on-honey); }
.nc__name { flex: 1; min-width: 0; font-size: 16px; font-weight: 800; }
.nc__tag { padding: 2px 10px; border-radius: var(--radius-pill); background: var(--banner-ink); color: var(--honey); font-size: 13px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.nc__count { color: var(--text-muted); font-size: 14px; font-weight: 700; white-space: nowrap; }
.nc__go { flex: none; color: var(--text-muted); }
.nc__writing { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 12px 8px; text-align: center; }
.nc__dots { display: flex; gap: 8px; margin-top: 6px; }
.nc__dots i { width: 10px; height: 10px; border-radius: 50%; background: var(--honey); animation: nc-dot 1s ease-in-out infinite; }
.nc__dots i:nth-child(2) { animation-delay: .15s; } .nc__dots i:nth-child(3) { animation-delay: .3s; }
@keyframes nc-dot { 0%, 100% { opacity: .35; transform: translateY(0); } 50% { opacity: 1; transform: translateY(-5px); } }
@media (prefers-reduced-motion: reduce) { .nc__card, .nc__dots i { animation: none; } }
@media (max-width: 520px) { .nc__card { padding: 18px; } .nc__count { display: none; } }
</style>
