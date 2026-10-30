<script setup lang="ts">
import '../learn.css';
import { computed, onMounted, ref } from 'vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import Mascot from '../components/Mascot.vue';
import BeeAvatar from '../components/social/BeeAvatar.vue';
import type { BeeName } from '../bee';
import { acceptFriendRequest, fetchSocial, removeFriendship, sendFriendRequest, SocialError, type Player, type Social } from '../api/social';
import { readProfileId } from '../api/profile';
import { useFlow } from '../state';

const { state } = useFlow();
const profileId = () => state.value.profileId ?? readProfileId();
const nf = new Intl.NumberFormat('en');

const social = ref<Social | null>(null);
const loadError = ref<string | null>(null);
const email = ref('');
const sending = ref(false);
const formError = ref<string | null>(null);
const notice = ref<string | null>(null);
/** The request or friend being changed, so its buttons can wait. */
const busyId = ref<string | null>(null);
const actionError = ref<string | null>(null);

const board = computed(() => social.value?.leaderboard ?? []);
/** Silver, gold, bronze: second place on the left, first in the middle, third on the right. Missing places are skipped. */
const podium = computed(() => [2, 1, 3].map((rank) => board.value.find((p) => p.rank === rank)).filter((p): p is Player => !!p));
const validEmail = computed(() => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim()));

async function load() {
  const id = profileId();
  if (!id) return;
  loadError.value = null;
  try {
    social.value = await fetchSocial(id);
  } catch (e) {
    loadError.value = e instanceof SocialError ? e.message : 'Jobee couldn’t load the leaderboard. Try again in a moment.';
  }
}

/** Run a change that returns the fresh social state; show its error if it fails. */
async function change(work: (id: string) => Promise<Social>, id: string | null = null) {
  const pid = profileId();
  if (!pid) return false;
  busyId.value = id;
  actionError.value = null;
  try {
    social.value = await work(pid);
    return true;
  } catch (e) {
    actionError.value = e instanceof SocialError ? e.message : 'That didn’t work. Try again in a moment.';
    return false;
  } finally {
    busyId.value = null;
  }
}

async function send() {
  const pid = profileId();
  if (!pid || !validEmail.value || sending.value) return;
  sending.value = true;
  formError.value = null;
  notice.value = null;
  const sent = email.value.trim();
  try {
    const before = social.value?.friends.length ?? 0;
    social.value = await sendFriendRequest(pid, sent);
    notice.value = social.value.friends.length > before ? 'You’re friends now!' : `Request sent to ${sent}.`;
    email.value = '';
  } catch (e) {
    formError.value = e instanceof SocialError ? e.message : 'That didn’t work. Try again in a moment.';
  } finally {
    sending.value = false;
  }
}

const accept = (id: string) => change((pid) => acceptFriendRequest(pid, id), id);
const remove = (id: string) => change((pid) => removeFriendship(pid, id), id);

onMounted(load);
</script>

<template>
  <div class="tab jb soc">
    <header class="soc__head">
      <div>
        <h1>Leaderboard</h1>
        <p>See how you and your friends stack up. Pollen comes from stingers and boss kills.</p>
      </div>
      <div class="soc__pollen" aria-label="Your pollen">
        <span>Your pollen</span>
        <i class="dot" aria-hidden="true" />
        <b>{{ nf.format(social?.pollen ?? 0) }}</b>
      </div>
    </header>

    <div v-if="loadError" class="learn__state">
      <Bubble :size="64">{{ loadError }}</Bubble>
      <button type="button" class="btn btn-secondary" @click="load">Try again</button>
    </div>
    <div v-else-if="!social" class="soc__grid" aria-busy="true">
      <div class="skel card soc__skel" />
      <div class="skel card soc__skel" />
    </div>

    <div v-else class="soc__grid">
      <div class="soc__main">
        <section class="podium" aria-label="Top three">
          <div v-for="p in podium" :key="p.profile_id" class="podium__slot" :data-rank="p.rank">
            <Icon v-if="p.rank === 1" class="podium__crown" name="crown" :size="28" />
            <span class="podium__fly" :style="{ animationDelay: `${p.rank * -0.9}s` }">
              <Mascot :size="p.rank === 1 ? 72 : 58" :bee="p.bee as BeeName" mood="happy" wings :look="false" />
            </span>
            <span class="podium__name">{{ p.is_me ? 'You' : p.name }}</span>
            <span class="podium__pollen"><i class="dot" aria-hidden="true" /> {{ nf.format(p.pollen) }}</span>
            <span class="podium__step"><b>{{ p.rank }}</b></span>
          </div>
        </section>

        <ol class="rows" aria-label="Leaderboard">
          <li v-for="p in board" :key="p.profile_id" class="row" :class="{ me: p.is_me }">
            <span class="row__rank">{{ p.rank }}</span>
            <BeeAvatar :bee="p.bee" :size="40" :me="p.is_me" />
            <span class="row__name">{{ p.is_me ? 'You' : p.name }}</span>
            <span class="row__pollen"><i class="dot" aria-hidden="true" /> {{ nf.format(p.pollen) }}</span>
          </li>
        </ol>
        <p v-if="board.length === 1" class="soc__hint">It’s just you for now. Add a friend and the race begins.</p>
      </div>

      <aside class="soc__side">
        <section class="card2">
          <h2>Friends</h2>
          <p class="card2__sub">Add friends by email. They need a Jobee account, since accounts are tied to emails.</p>
          <form class="add" @submit.prevent="send">
            <label class="add__field">
              <Icon name="mail" :size="18" />
              <input v-model="email" type="email" inputmode="email" autocomplete="off" spellcheck="false" placeholder="friend@email.com" aria-label="Friend’s email" :disabled="sending" />
            </label>
            <button type="submit" class="add__btn" :disabled="!validEmail || sending">{{ sending ? 'Sending…' : 'Send request' }}</button>
          </form>
          <p v-if="formError" class="msg msg--err" role="alert">{{ formError }}</p>
          <p v-else-if="notice" class="msg msg--ok" role="status">{{ notice }}</p>

          <ul v-if="social.friends.length" class="people">
            <li v-for="f in social.friends" :key="f.friendship_id" class="person">
              <BeeAvatar :bee="f.bee" :size="36" />
              <span class="person__text"><b>{{ f.name }}</b><small>{{ f.email_hint }}</small></span>
              <button type="button" class="icon-btn" :aria-label="`Remove ${f.name}`" :disabled="busyId === f.friendship_id" @click="remove(f.friendship_id)"><Icon name="x" :size="16" /></button>
            </li>
          </ul>
          <p v-else class="empty">No friends yet.</p>
        </section>

        <section v-if="social.incoming.length || social.sent.length" class="card2">
          <h2>Pending requests <span v-if="social.incoming.length" class="badge">{{ social.incoming.length }}</span></h2>
          <ul v-if="social.incoming.length" class="people">
            <li v-for="r in social.incoming" :key="r.friendship_id" class="person person--ask">
              <BeeAvatar :bee="r.bee" :size="36" />
              <span class="person__text"><b>{{ r.name }}</b><small>{{ r.email }}</small></span>
              <button type="button" class="accept" :disabled="busyId === r.friendship_id" @click="accept(r.friendship_id)">Accept</button>
              <button type="button" class="icon-btn" :aria-label="`Decline ${r.name}`" :disabled="busyId === r.friendship_id" @click="remove(r.friendship_id)"><Icon name="x" :size="16" /></button>
            </li>
          </ul>
          <template v-if="social.sent.length">
            <h3>Sent by you</h3>
            <ul class="sent">
              <li v-for="s in social.sent" :key="s.friendship_id">
                <span class="sent__email">{{ s.email }}</span>
                <span class="sent__state">{{ s.signed_up ? 'Waiting for reply' : 'Waiting for sign-up' }}</span>
                <button type="button" class="icon-btn" :aria-label="`Cancel request to ${s.email}`" :disabled="busyId === s.friendship_id" @click="remove(s.friendship_id)"><Icon name="x" :size="14" /></button>
              </li>
            </ul>
          </template>
          <p v-if="actionError" class="msg msg--err" role="alert">{{ actionError }}</p>
        </section>
        <p v-else-if="actionError" class="msg msg--err" role="alert">{{ actionError }}</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.soc { display: flex; flex-direction: column; gap: 24px; max-width: 1600px; }
.soc__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.soc__head h1 { margin: 0; font-size: 40px; line-height: 48px; font-weight: 900; }
.soc__head p { margin: 4px 0 0; color: var(--text-muted); font-size: 16px; font-weight: 600; }
.dot { display: inline-block; flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--honey); }
.soc__pollen { display: inline-flex; align-items: center; gap: 10px; padding: 10px 20px; border: 2px solid var(--honey); border-radius: var(--radius-lg); background: var(--honey-tint); font-weight: 700; color: var(--text-muted); }
.soc__pollen b { font-size: 26px; line-height: 32px; font-weight: 900; color: var(--text); font-variant-numeric: tabular-nums; }

.soc__grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 24px; align-items: start; }
.soc__main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.soc__skel { height: 320px; border-radius: var(--radius-lg); }
.soc__hint { margin: 4px 0 0; text-align: center; color: var(--text-muted); font-size: 14px; font-weight: 700; }

.podium { display: flex; align-items: flex-end; justify-content: center; gap: 0; min-height: 300px; padding: 34px 24px 0; border: 2px solid var(--honey); border-radius: 24px; background: var(--honey-tint); overflow: hidden; }
.podium__slot { position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; width: clamp(110px, 22%, 190px); }
.podium__slot[data-rank="1"] { z-index: 1; }
.podium__crown { color: var(--honey-deep); fill: var(--honey); margin-bottom: 6px; }
/* The bees hover over their step: wings flapping, drifting in a slow loop. */
.podium__fly { display: grid; place-items: center; padding: 14px 22px 6px; animation: podium-fly 4.2s ease-in-out infinite; }
@keyframes podium-fly {
  0%, 100% { transform: translate(0, 0) rotate(-3deg); }
  25% { transform: translate(10px, -10px) rotate(3deg); }
  50% { transform: translate(0, -16px) rotate(-2deg); }
  75% { transform: translate(-10px, -8px) rotate(4deg); }
}
@media (prefers-reduced-motion: reduce) { .podium__fly { animation: none; } }
.podium__name { margin-top: 4px; font-size: 16px; font-weight: 900; }
.podium__pollen { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px; color: var(--accent-text); font-size: 14px; font-weight: 900; font-variant-numeric: tabular-nums; }
.podium__step { display: grid; place-items: start center; width: 100%; padding-top: 18px; border: 2px solid var(--honey); border-bottom: 0; border-radius: 14px 14px 0 0; background: var(--surface-raised); }
.podium__step b { font-size: 40px; line-height: 44px; font-weight: 900; color: #a85800; }
.podium__slot[data-rank="1"] .podium__step { height: 110px; background: var(--honey); }
.podium__slot[data-rank="1"] .podium__step b { font-size: 50px; line-height: 54px; color: var(--on-honey); }
.podium__slot[data-rank="2"] .podium__step { height: 80px; }
.podium__slot[data-rank="3"] .podium__step { height: 56px; background: #f1ede3; }

.rows { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }
.row { display: flex; align-items: center; gap: 14px; padding: 10px 22px 10px 20px; border: 2px solid var(--line); border-radius: var(--radius-md); background: var(--surface-raised); }
.row.me { border-color: var(--honey); background: var(--honey-tint); }
.row__rank { width: 22px; font-size: 16px; font-weight: 900; text-align: center; color: var(--text-muted); }
.row__name { flex: 1; min-width: 0; font-size: 16px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row__pollen { display: inline-flex; align-items: center; gap: 8px; font-size: 17px; font-weight: 900; font-variant-numeric: tabular-nums; }

.soc__side { display: flex; flex-direction: column; gap: 16px; }
.card2 { display: flex; flex-direction: column; gap: 12px; padding: 20px; border: 2px solid var(--line); border-radius: var(--radius-lg); background: var(--surface-raised); }
.card2 h2 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 21px; line-height: 26px; font-weight: 900; }
.card2 h3 { margin: 4px 0 0; font-size: 11px; line-height: 16px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--text-muted); }
.card2__sub { margin: -6px 0 0; color: var(--text-muted); font-size: 12px; line-height: 17px; font-weight: 600; }
.badge { display: inline-grid; place-items: center; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 999px; background: #d32f2f; color: #fff; font-size: 12px; font-weight: 900; }

.add { display: flex; flex-direction: column; gap: 10px; }
.add__field { display: flex; align-items: center; gap: 10px; padding: 0 14px; border: 2px solid var(--line-strong); border-radius: 12px; background: var(--surface); color: var(--text-muted); }
.add__field:focus-within { border-color: var(--honey-deep); outline: 3px solid var(--focus); outline-offset: 2px; }
.add__field input { flex: 1; min-width: 0; padding: 12px 0; border: 0; outline: 0; background: none; color: var(--text); font: inherit; font-size: 14px; font-weight: 700; }
.add__btn { padding: 13px 16px; border: 0; border-radius: 12px; background: var(--honey); color: var(--on-honey); font: inherit; font-size: 13px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; cursor: pointer; box-shadow: 0 4px 0 var(--honey-deep); transition: transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out); }
.add__btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 0 var(--honey-deep); }
.add__btn:active:not(:disabled) { transform: translateY(3px); box-shadow: 0 1px 0 var(--honey-deep); }
.add__btn:disabled { opacity: .55; cursor: not-allowed; }
.add__btn:focus-visible, .accept:focus-visible, .icon-btn:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.msg { margin: 0; font-size: 13px; line-height: 18px; font-weight: 700; }
.msg--err { color: #b3261e; }
.msg--ok { color: #2e7d4f; }

.people { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }
.person { display: flex; align-items: center; gap: 10px; }
.person--ask { padding: 8px 10px; border: 2px solid var(--honey); border-radius: 14px; background: var(--honey-tint); }
.person__text { display: flex; flex-direction: column; flex: 1; min-width: 0; line-height: 17px; }
.person__text b { font-size: 14px; font-weight: 900; }
.person__text small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); font-size: 11px; font-weight: 600; }
.accept { padding: 7px 12px; border: 0; border-radius: 10px; background: #2e7d4f; color: #fff; font: inherit; font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; cursor: pointer; }
.accept:disabled, .icon-btn:disabled { opacity: .5; cursor: not-allowed; }
.icon-btn { flex: none; display: grid; place-items: center; width: 30px; height: 30px; border: 2px solid var(--line); border-radius: 9px; background: var(--surface-raised); color: var(--text-muted); cursor: pointer; }
.icon-btn:hover:not(:disabled) { color: var(--text); border-color: var(--line-strong); }
.empty { margin: 0; color: var(--text-muted); font-size: 13px; font-weight: 700; }

.sent { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; list-style: none; }
.sent li { display: flex; align-items: center; gap: 10px; padding: 8px 10px 8px 12px; border-radius: 10px; background: #f1ede3; font-size: 12px; font-weight: 700; }
.sent__email { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sent__state { flex: none; color: var(--text-muted); }

@media (max-width: 1100px) {
  .soc__grid { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 560px) {
  .soc__head h1 { font-size: 32px; line-height: 40px; }
  .podium { padding: 28px 8px 0; }
  .podium__slot { width: 33%; }
  .row { gap: 10px; padding: 10px 14px; }
}
</style>
