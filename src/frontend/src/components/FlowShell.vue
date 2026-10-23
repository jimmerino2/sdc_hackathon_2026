<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import Icon from './Icon.vue';
import Mascot, { type Gear, type Mood } from './Mascot.vue';
import { isLoggedIn } from '../api/profile';
import { useFlow } from '../state';
import { go, type Page, type Step } from '../router';

const props = withDefaults(
  defineProps<{
    progress: number;
    next: Page;
    skipTo?: Page;
    nextLabel?: string;
    skipLabel?: string;
    nextDisabled?: boolean;
    back?: Page;
    /** Jobee's look in the header. */
    mood?: Mood;
    gear?: Gear;
    /** Wider content column for data-heavy screens (roles, forecast). */
    wide?: boolean;
  }>(),
  { mood: 'idle', gear: 'none', wide: false },
);
const emit = defineEmits<{ next: [] }>();
const router = useRouter();
const { state } = useFlow();
const pct = computed(() => (props.progress / 5) * 100);
/** Where the close button goes: to the learner's pathway once they have an account (a confirmed email), else back to the start. */
const closeTo = computed<Step>(() => (state.value.email || isLoggedIn() ? 'pathway' : 'landing'));

function onNext() {
  emit('next');
  router.push(go(props.next));
}
</script>

<template>
  <div class="shell" :class="{ wide }">
    <header>
      <div class="inner top">
        <RouterLink :to="go(closeTo)" class="x" aria-label="Close"><Icon name="x" :size="22" :stroke="2.6" /></RouterLink>
        <div class="progress" role="progressbar" aria-label="Progress" aria-valuemin="0" aria-valuemax="5" :aria-valuenow="progress"><i :style="{ width: pct + '%' }" /></div>
      </div>
      <div class="inner say">
        <Mascot :size="64" :mood="mood" :gear="gear" class="bee" />
        <h1 class="bubble" aria-live="polite"><slot name="bubble" /></h1>
      </div>
    </header>

    <main tabindex="-1">
      <div class="inner content"><slot /></div>
    </main>

    <footer>
      <div class="inner bar">
        <RouterLink v-if="back" :to="go(back)" class="btn btn-secondary">Back</RouterLink>
        <span class="right">
          <slot name="skip">
            <RouterLink v-if="skipTo || !back" :to="go(skipTo ?? next)" class="skip">{{ skipLabel ?? 'Skip' }}</RouterLink>
          </slot>
          <button type="button" class="btn btn-primary" :disabled="nextDisabled" @click="onNext">{{ nextLabel ?? 'Continue' }}</button>
        </span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  --w: 600px;
  height: 100vh; height: 100dvh; overflow: hidden;
  display: grid; grid-template-rows: auto minmax(0, 1fr) auto;
}
.shell.wide { --w: 1180px; }
.inner { width: 100%; max-width: calc(var(--w) + 40px); margin: 0 auto; padding: 0 20px; }

/* header: progress + Jobee's prompt, never scrolls */
header { background: var(--bg); padding-top: 20px; border-bottom: 2px solid var(--line); }
.top { display: flex; align-items: center; gap: 16px; }
.top .progress { flex: 1; height: 14px; }
.x { color: #8f8a82; display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; margin-left: -8px; transition: color .15s, background .15s; }
.x:hover { color: var(--ink); background: var(--line); }

.say { display: flex; align-items: center; gap: 16px; padding-top: 18px; padding-bottom: 18px; }
.bee { flex: none; }
.bubble {
  position: relative; background: #fff; border: 2px solid var(--line-strong); border-radius: 18px;
  padding: 12px 18px; font-size: 20px; font-weight: 900; line-height: 1.3; letter-spacing: -.005em;
  text-wrap: pretty;
  animation: say .35s cubic-bezier(.2, .8, .3, 1.2) both;
}
.bubble::before, .bubble::after { content: ''; position: absolute; top: 50%; border-style: solid; }
.bubble::before { left: -12px; margin-top: -9px; border-width: 9px 12px 9px 0; border-color: transparent rgba(30, 30, 30, .12) transparent transparent; }
.bubble::after { left: -8px; margin-top: -7px; border-width: 7px 9px 7px 0; border-color: transparent #fff transparent transparent; }
@keyframes say { from { opacity: 0; transform: translateX(-6px) scale(.97); } }

/* the only scrolling region */
main { min-height: 0; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
main:focus { outline: none; }
.content { padding-top: 24px; padding-bottom: 32px; }

/* footer: always visible, same column as content */
footer { background: var(--bg); border-top: 2px solid var(--line); padding: 14px 0 calc(14px + env(safe-area-inset-bottom)); }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.right { margin-left: auto; display: flex; align-items: center; gap: 18px; }
.skip, .right :slotted(.skip) {
  font-size: 13px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
  padding: 10px 6px; border-radius: 10px; white-space: nowrap; transition: color .15s;
}
.skip:hover, .right :slotted(.skip:hover) { color: var(--ink); }

@media (max-width: 640px) {
  header { padding-top: 12px; }
  .say { gap: 12px; padding-top: 12px; padding-bottom: 12px; }
  .bee { font-size: 46px !important; }
  .bubble { font-size: 17px; padding: 10px 14px; }
  .content { padding-top: 18px; padding-bottom: 24px; }
  footer { padding-top: 10px; padding-bottom: calc(10px + env(safe-area-inset-bottom)); }
  .btn { padding: 14px 18px; font-size: 14px; }
  .right { gap: 10px; }
  .skip, .right :slotted(.skip) { font-size: 12px; letter-spacing: .05em; }
}
@media (max-height: 620px) {
  header { padding-top: 10px; }
  .say { padding-top: 8px; padding-bottom: 8px; }
  .bee { font-size: 40px !important; }
  .bubble { font-size: 16px; padding: 8px 12px; }
  .content { padding-top: 14px; }
  footer { padding-top: 8px; padding-bottom: 8px; }
  .btn { padding: 12px 18px; }
}
@media (prefers-reduced-motion: reduce) { .bubble { animation: none !important; } }
</style>
