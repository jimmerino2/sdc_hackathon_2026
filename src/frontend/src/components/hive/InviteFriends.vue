<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import BeeAvatar from '../social/BeeAvatar.vue';
import Icon from '../Icon.vue';
import { go } from '../../router';
import type { HiveInvitable } from '../../api/hive';

/** Pick one of your friends to invite to the party. Only friends can be invited, so a new friend is added on Social. */
defineProps<{ friends: HiveInvitable[]; busyId?: string | null; error?: string | null }>();
const emit = defineEmits<{ close: []; invite: [profileId: string] }>();

const first = ref<HTMLButtonElement | null>(null);
const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') emit('close'); };
onMounted(() => { window.addEventListener('keydown', onKey); nextTick(() => first.value?.focus()); });
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
  <Teleport to="body">
    <div class="jb inv" role="dialog" aria-modal="true" aria-labelledby="inv-title">
      <div class="inv__dim" @click="emit('close')" />
      <div class="inv__card">
        <header>
          <div>
            <h2 id="inv-title">Invite a friend</h2>
            <p>They’ll see the invite on this page. Joining swaps their fight for yours.</p>
          </div>
          <button type="button" class="inv__x" aria-label="Close" @click="emit('close')"><Icon name="x" :size="22" /></button>
        </header>
        <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
        <ul v-if="friends.length" class="inv__list">
          <li v-for="(f, i) in friends" :key="f.profile_id">
            <button :ref="(el) => { if (i === 0) first = el as HTMLButtonElement }" type="button" class="inv__row" :disabled="busyId === f.profile_id" @click="emit('invite', f.profile_id)">
              <BeeAvatar :bee="f.bee" :size="42" />
              <span class="inv__name">{{ f.name }}</span>
              <span class="inv__go">{{ busyId === f.profile_id ? 'Inviting…' : 'Invite' }}</span>
            </button>
          </li>
        </ul>
        <div v-else class="inv__empty">
          <p>No friends to invite right now. Everyone you’re friends with is already in your party or invited.</p>
          <RouterLink :to="go('social')" class="inv__link">Add friends on Social</RouterLink>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.inv { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 16px; font-family: var(--font-sans); }
.inv__dim { position: absolute; inset: 0; background: rgba(40, 36, 28, .45); }
.inv__card { position: relative; display: flex; flex-direction: column; gap: 14px; width: min(480px, 100%); max-height: min(640px, calc(100vh - 32px)); padding: 24px; border: 2px solid var(--honey); border-radius: 24px; background: var(--surface-raised); box-shadow: var(--shadow-lift); animation: jb-rise var(--dur-base) var(--ease-out) both; }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
h2 { margin: 0; font-size: 27px; line-height: 34px; font-weight: 900; }
header p { margin: 4px 0 0; color: var(--text-muted); font-size: 16px; line-height: 23px; font-weight: 600; }
.inv__x { flex: none; display: grid; place-items: center; width: 40px; height: 40px; border: 0; border-radius: 50%; background: #f1ece0; color: var(--text); cursor: pointer; }
.inv__x:focus-visible, .inv__row:focus-visible, .inv__link:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.inv__list { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0 4px 4px 0; list-style: none; overflow-y: auto; }
.inv__row { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 14px; border: 2px solid var(--line); border-radius: var(--radius-md); background: var(--surface); color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out); }
.inv__row:hover:not(:disabled) { border-color: var(--honey); background: var(--honey-tint); }
.inv__row:disabled { opacity: .6; cursor: wait; }
.inv__name { flex: 1; min-width: 0; font-size: 18px; font-weight: 800; }
.inv__go { padding: 6px 14px; border-radius: 999px; background: var(--honey); font-size: 14px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; }
.inv__empty p { margin: 0 0 12px; color: var(--text-muted); font-size: 16px; line-height: 24px; font-weight: 600; }
.inv__link { display: inline-block; padding: 12px 20px; border-radius: var(--radius-md); background: var(--honey); color: var(--on-honey); text-decoration: none; font-size: 15px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; box-shadow: 0 4px 0 var(--honey-deep); }
@media (prefers-reduced-motion: reduce) { .inv__card { animation: none; } }
</style>
