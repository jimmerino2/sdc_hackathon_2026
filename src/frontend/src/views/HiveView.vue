<script setup lang="ts">
import '../learn.css';
import { computed, onBeforeUnmount, onMounted, ref, type ComponentPublicInstance } from 'vue';
import Bubble from '../components/Bubble.vue';
import HiveAlert from '../components/hive/HiveAlert.vue';
import HiveScene from '../components/hive/HiveScene.vue';
import HiveSwitch from '../components/hive/HiveSwitch.vue';
import InviteFriends from '../components/hive/InviteFriends.vue';
import PartyBee from '../components/hive/PartyBee.vue';
import Robbee from '../components/hive/Robbee.vue';
import Stinger from '../components/hive/Stinger.vue';
import Icon from '../components/Icon.vue';
import BeeAvatar from '../components/social/BeeAvatar.vue';
import {
  acceptInvite, fetchHive, HiveError, inviteFriend, leaveParty, markRewardSeen, removeInvite, sting,
  type Hive, type HiveEvent, type HiveInvite, type HiveReward,
} from '../api/hive';
import { readProfileId } from '../api/profile';
import { prefersReducedMotion } from '../composables/useCountUp';
import { useFlow } from '../state';
import { go } from '../router';

/**
 * Protect the Hive: fight Robbee with stingers, alone or in a party of up to 4 friends. A sting takes 20% off his HP
 * and pays 500 pollen; the killing blow pays 1,000 to every member who stung that round, and a fresh Robbee returns.
 * The page polls so party members see each other's stings.
 */
const { state } = useFlow();
const profileId = () => state.value.profileId ?? readProfileId();
const nf = new Intl.NumberFormat('en');
const POLL_MS = 10_000;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const quick = () => prefersReducedMotion();

const hive = ref<Hive | null>(null);
const loadError = ref<string | null>(null);
const actionError = ref<string | null>(null);
const busy = ref(false);

/* ---------- what is on screen: Robbee's HP is shown separately, so a kill can play out before he resets ---------- */
const shownHp = ref(100);
const pose = ref<'idle' | 'hit' | 'defeated'>('idle');
/** The sky has cleared: Robbee was just beaten. */
const cleared = ref(false);
/** The kill is being played out (animation, then the popup); polling changes nothing meanwhile. */
const sequence = ref(false);
const returning = ref(false);
const rewardOpen = ref<HiveReward | null>(null);

const dealt = computed(() => Math.min(5, Math.round((100 - shownHp.value) / 20)));
const storm = computed(() => (cleared.value ? 0 : (100 - shownHp.value) / 100));
const me = computed(() => hive.value?.members.find((m) => m.is_me) ?? null);
/** Me first, then the party in the order they joined. */
const party = computed(() => {
  const all = hive.value?.members ?? [];
  return [...all.filter((m) => m.is_me), ...all.filter((m) => !m.is_me)];
});
const max = computed(() => hive.value?.fight.max_party ?? 4);
/** The four places around the hive: members first, then invites waiting, then empty seats to invite into. */
const seats = computed(() => {
  const h = hive.value;
  if (!h) return [];
  const out: ({ kind: 'bee'; m: (typeof party.value)[number] } | { kind: 'wait'; o: Hive['outgoing'][number] } | { kind: 'open' })[] = [];
  party.value.forEach((m) => out.push({ kind: 'bee', m }));
  h.outgoing.forEach((o) => out.length < max.value && out.push({ kind: 'wait', o }));
  while (out.length < max.value) out.push({ kind: 'open' });
  return out.slice(0, max.value);
});
const available = computed(() => hive.value?.stingers_available ?? 0);

/* ---------- loading and polling ---------- */
const seen = new Set<string>();
let first = true;

async function load() {
  const id = profileId();
  if (!id) return;
  try {
    const h = await fetchHive(id);
    loadError.value = null;
    first ? start(h) : poll(h);
  } catch (e) {
    if (!hive.value) loadError.value = e instanceof HiveError ? e.message : 'Jobee couldn’t load the hive. Try again in a moment.';
  }
}

/** The first load: take the fight as it is, and show a kill popup that was waiting. */
function start(h: Hive) {
  first = false;
  hive.value = h;
  shownHp.value = h.fight.hp;
  h.events.forEach((e) => seen.add(e.event_id));
  if (h.reward) playDefeat(h, true);
}

/** A later refresh: take the new state; play other members' stings and any kill that happened while we weren't acting. */
function poll(h: Hive) {
  if (busy.value || sequence.value) return;
  const before = shownHp.value;
  hive.value = h;
  const fresh = h.events.filter((e) => !seen.has(e.event_id));
  fresh.forEach((e) => seen.add(e.event_id));
  if (h.reward && !rewardOpen.value) return void playDefeat(h);
  fresh.filter((e) => e.kind === 'sting' && !e.is_me).reverse().forEach((e, i) => setTimeout(() => strikeBee(e.profile_id), i * 650));
  if (h.fight.hp < before) flashHit();
  shownHp.value = h.fight.hp;
}

/** The lobby changed under us (joined or left a party): start over from what the server says. */
function resync(h: Hive) {
  hive.value = h;
  shownHp.value = h.fight.hp;
  seen.clear();
  h.events.forEach((e) => seen.add(e.event_id));
  if (h.reward) playDefeat(h, true);
}

let timer: number | undefined;
const onVisible = () => document.visibilityState === 'visible' && load();
onMounted(() => {
  load();
  timer = window.setInterval(() => document.visibilityState === 'visible' && load(), POLL_MS);
  document.addEventListener('visibilitychange', onVisible);
});
onBeforeUnmount(() => { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); });

/* ---------- animation helpers ---------- */
const stage = ref<HTMLElement | null>(null);
const robbeeEl = ref<HTMLElement | null>(null);
const bees = new Map<string, ComponentPublicInstance & { strike: (dx: number, dy: number) => void; el: HTMLElement | null }>();
const setBee = (id: string, el: unknown) => (el ? bees.set(id, el as never) : bees.delete(id));

type Floater = { id: number; text: string; kind: 'dmg' | 'pollen'; x: number; y: number };
const floaters = ref<Floater[]>([]);
let floaterId = 0;
function floatAt(el: HTMLElement | null | undefined, text: string, kind: Floater['kind'], dx = 0, dy = 0) {
  const box = stage.value?.getBoundingClientRect();
  const r = el?.getBoundingClientRect();
  if (!box || !r) return;
  const f = { id: ++floaterId, text, kind, x: r.left + r.width / 2 - box.left + dx, y: r.top - box.top + dy };
  floaters.value = [...floaters.value, f];
  setTimeout(() => (floaters.value = floaters.value.filter((x) => x.id !== f.id)), 1500);
}

/** A bee dives at Robbee. */
function strikeBee(profile: string) {
  const bee = bees.get(profile);
  const from = bee?.el?.getBoundingClientRect();
  const to = robbeeEl.value?.getBoundingClientRect();
  if (!bee || !from || !to || quick()) return flashHit();
  bee.strike((to.left + to.width / 2 - (from.left + from.width / 2)) * 0.82, (to.top + to.height / 2 - (from.top + from.height / 2)) * 0.82 - 20);
  setTimeout(flashHit, 340);
}

function flashHit() {
  if (pose.value === 'defeated') return;
  pose.value = 'hit';
  setTimeout(() => pose.value === 'hit' && (pose.value = 'idle'), 520);
}

/* ---------- stinging ---------- */
async function doSting() {
  const id = profileId();
  if (!id || busy.value || sequence.value || !hive.value || available.value < 1) return;
  busy.value = true;
  actionError.value = null;
  try {
    const res = await sting(id);
    res.hive.events.forEach((e) => seen.add(e.event_id));
    hive.value = res.hive;
    if (me.value) strikeBee(me.value.profile_id);
    await wait(quick() ? 0 : 340);
    floatAt(robbeeEl.value, '−20%', 'dmg', 90, -10);
    floatAt(me.value ? bees.get(me.value.profile_id)?.el : null, `+${nf.format(res.pollen)} pollen`, 'pollen', -40, -70);
    if (res.defeated) await playDefeat(res.hive);
    else shownHp.value = res.hive.fight.hp;
  } catch (e) {
    actionError.value = e instanceof HiveError ? e.message : 'That didn’t work. Try again in a moment.';
    load();
  } finally {
    busy.value = false;
  }
}

/** Robbee goes down, the sky clears, then the party's popup. instant: skip the wait (a kill we only just found out about). */
async function playDefeat(h: Hive, instant = false) {
  sequence.value = true;
  shownHp.value = 0;
  pose.value = 'defeated';
  cleared.value = true;
  if (!instant && !quick()) await wait(1900);
  rewardOpen.value = h.reward;
}

async function closeReward() {
  const r = rewardOpen.value;
  const id = profileId();
  rewardOpen.value = null;
  if (r && id) {
    try { hive.value = await markRewardSeen(id, r.reward_id); } catch { /* it will show again next time, which is fine */ }
  }
  pose.value = 'idle';
  cleared.value = false;
  shownHp.value = hive.value?.fight.hp ?? 100;
  returning.value = true;
  setTimeout(() => (returning.value = false), 1100);
  sequence.value = false;
  if (hive.value?.reward) playDefeat(hive.value, true); // another kill was waiting
}

/* ---------- parties ---------- */
const picking = ref(false);
const inviteBusy = ref<string | null>(null);
const inviteError = ref<string | null>(null);
const confirmJoin = ref<HiveInvite | null>(null);
const confirmLeave = ref(false);

/** Run a party change that returns the fresh state. */
async function party_(work: (id: string) => Promise<Hive>, fresh = false): Promise<boolean> {
  const id = profileId();
  if (!id) return false;
  try {
    const h = await work(id);
    fresh ? resync(h) : (hive.value = h);
    return true;
  } catch (e) {
    actionError.value = e instanceof HiveError ? e.message : 'That didn’t work. Try again in a moment.';
    return false;
  }
}

async function invite(profile: string) {
  inviteBusy.value = profile;
  inviteError.value = null;
  const id = profileId();
  try {
    if (id) hive.value = await inviteFriend(id, profile);
    if (!hive.value?.invitable.length || (hive.value?.members.length ?? 0) + (hive.value?.outgoing.length ?? 0) >= max.value) picking.value = false;
  } catch (e) {
    inviteError.value = e instanceof HiveError ? e.message : 'The invite didn’t go through. Try again in a moment.';
  } finally {
    inviteBusy.value = null;
  }
}

/** Joining swaps this fight for theirs, so ask first if there is something to lose. */
function join(inv: HiveInvite) {
  const hurt = shownHp.value < 100 || (me.value?.stings ?? 0) > 0 || party.value.length > 1;
  if (hurt) confirmJoin.value = inv;
  else doJoin(inv);
}
async function doJoin(inv: HiveInvite) {
  confirmJoin.value = null;
  actionError.value = null;
  await party_((id) => acceptInvite(id, inv.invite_id), true);
}
const decline = (inviteId: string) => party_((id) => removeInvite(id, inviteId));
async function leave() {
  confirmLeave.value = false;
  actionError.value = null;
  await party_((id) => leaveParty(id), true);
}

/* ---------- the feed ---------- */
function eventText(e: HiveEvent): string {
  const who = e.is_me ? 'You' : e.name;
  switch (e.kind) {
    case 'sting': return `${who} stung Robbee${e.challenge_title ? ` with ${e.challenge_title}` : ''}`;
    case 'twist': return `Robbee changed your brief for ${e.challenge_title ?? 'a challenge'}`;
    case 'defeat': return `${who} landed the final sting. A fresh Robbee clocks in`;
    case 'join': return `${who} joined the party`;
    default: return `${who} left the party`;
  }
}
const eventTag = (e: HiveEvent) => (e.kind === 'twist' ? 'Boss twist' : e.kind === 'defeat' ? 'Victory' : e.kind === 'sting' && e.is_me ? `+${nf.format(e.pollen)} pollen` : '');

</script>

<template>
  <div class="tab jb hp">
    <header class="hp__head">
      <div>
        <p class="eyebrow">Challenges</p>
        <p class="hp__sub">Team up against Robbee. Every stinger counts for the whole party.</p>
      </div>
      <HiveSwitch current="hive" />
    </header>

    <div v-if="loadError" class="learn__state">
      <Bubble :size="64">{{ loadError }}</Bubble>
      <button type="button" class="btn btn-secondary" @click="load">Try again</button>
    </div>
    <div v-else-if="!hive" class="hp__stage skel card" aria-busy="true" />

    <template v-else>
      <ul v-if="hive.invites.length" class="invites" aria-label="Party invites">
        <li v-for="inv in hive.invites" :key="inv.invite_id" class="invite">
          <BeeAvatar :bee="inv.from_bee" :size="42" />
          <p><b>{{ inv.from_name }}</b> invited you to their party <small>{{ inv.party_size }}/{{ max }} · Robbee at {{ inv.hp }}% HP</small></p>
          <button type="button" class="invite__join" @click="join(inv)">Join</button>
          <button type="button" class="invite__x" :aria-label="`Decline ${inv.from_name}`" @click="decline(inv.invite_id)"><Icon name="x" :size="16" /></button>
        </li>
      </ul>
      <div v-if="confirmJoin" class="confirm" role="alertdialog" aria-label="Join this party">
        <p>Joining <b>{{ confirmJoin.from_name }}</b>’s party replaces your current fight{{ party.length > 1 ? ' and takes you out of your party' : '' }}. Your progress on this Robbee is lost.</p>
        <div class="confirm__act">
          <button type="button" class="jb-btn jb-btn--ink" @click="confirmJoin = null">Stay</button>
          <button type="button" class="confirm__go" @click="doJoin(confirmJoin)">Join party</button>
        </div>
      </div>

      <section ref="stage" class="hp__stage" :class="{ storming: storm > 0.45 }" aria-label="The hive fight">
        <HiveScene :storm="storm" :cracks="dealt" :clear="cleared" />

        <div class="hpcard" role="status">
          <span class="hpcard__eyebrow">The hive is under attack</span>
          <h2>Robbee <small>HP {{ shownHp }}%</small></h2>
          <div class="hpcard__bar" role="progressbar" aria-label="Robbee's HP" :aria-valuenow="shownHp" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: shownHp + '%' }" /></div>
          <div class="hpcard__pips">
            <span v-for="i in hive.fight.stings_to_kill" :key="i" class="hpcard__pip" :class="{ on: i <= dealt }"><Stinger :size="18" /></span>
            <b>{{ dealt }} / {{ hive.fight.stings_to_kill }} stingers</b>
          </div>
        </div>

        <button v-if="party.length > 1 && !confirmLeave" type="button" class="leave" @click="confirmLeave = true">Leave party</button>
        <div v-else-if="confirmLeave" class="leave leave--ask">
          Leave this party?
          <button type="button" @click="leave">Leave</button>
          <button type="button" @click="confirmLeave = false">Stay</button>
        </div>

        <div ref="robbeeEl" class="boss" :class="{ returning }">
          <Robbee :size="196" :pose="pose" />
        </div>

        <template v-for="(s, i) in seats" :key="i">
          <div class="seat" :class="`seat--${i}`">
            <PartyBee v-if="s.kind === 'bee'" :ref="(el) => setBee(s.m.profile_id, el)" :bee="s.m.bee" :name="s.m.name" :stings="s.m.stings" :me="s.m.is_me" :delay="i * 0.8" />
            <div v-else-if="s.kind === 'wait'" class="slot slot--wait">
              <span class="slot__ring"><BeeAvatar :bee="s.o.bee" :size="64" /></span>
              <span class="slot__label">{{ s.o.name }} · invited</span>
              <button type="button" class="slot__cancel" :aria-label="`Cancel invite to ${s.o.name}`" @click="decline(s.o.invite_id)"><Icon name="x" :size="14" /></button>
            </div>
            <button v-else type="button" class="slot" aria-label="Invite a friend" @click="picking = true; inviteError = null">
              <span class="slot__ring" aria-hidden="true">+</span>
              <span class="slot__label">Invite</span>
            </button>
          </div>
        </template>

        <div class="sting">
          <button type="button" class="sting__btn" :disabled="available < 1 || busy || sequence" @click="doSting">
            <Stinger :size="22" /> Sting <span class="sting__n">×{{ available }}</span>
          </button>
          <RouterLink v-if="available < 1" :to="go('challenges')" class="sting__hint">Out of stingers? Pass a challenge stage to earn one.</RouterLink>
        </div>

        <span v-for="f in floaters" :key="f.id" class="floater" :class="`floater--${f.kind}`" :style="{ left: f.x + 'px', top: f.y + 'px' }" aria-hidden="true">{{ f.text }}</span>
      </section>
      <p v-if="actionError" class="hp__err" role="alert">{{ actionError }}</p>

      <section class="feed" aria-labelledby="feed-title">
        <h2 id="feed-title">Recent hits</h2>
        <ul v-if="hive.events.length">
          <li v-for="e in hive.events" :key="e.event_id">
            <span class="feed__icon"><Icon v-if="e.kind === 'join' || e.kind === 'leave'" name="users" :size="16" /><Stinger v-else :size="16" /></span>
            <span class="feed__text">{{ eventText(e) }}</span>
            <span class="feed__tag" :class="{ 'feed__tag--twist': e.kind === 'twist', 'feed__tag--win': e.kind === 'defeat' }">{{ eventTag(e) }}</span>
          </li>
        </ul>
        <p v-else class="feed__empty">No hits yet. Spend a stinger to take the first swing.</p>
      </section>
    </template>

    <InviteFriends v-if="picking && hive" :friends="hive.invitable" :busy-id="inviteBusy" :error="inviteError" @close="picking = false" @invite="invite" />
    <HiveAlert v-if="rewardOpen" phase="defeated" title="" :stingers="0" :party="rewardOpen.party" :reward="rewardOpen.pollen" @close="closeReward" />
  </div>
</template>

<style scoped>
.hp { display: flex; flex-direction: column; gap: 20px; max-width: 1600px; }
.hp__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.eyebrow { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
.hp__sub { margin: 4px 0 0; color: var(--text-muted); font-size: 13px; line-height: 18px; font-weight: 600; }
.hp__err { margin: -8px 0 0; color: #b3261e; font-size: 14px; font-weight: 700; }

.invites { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }
.invite { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border: 2px solid var(--honey); border-radius: var(--radius-md); background: var(--honey-tint); }
.invite p { flex: 1; min-width: 0; margin: 0; font-size: 15px; font-weight: 600; }
.invite small { display: block; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.invite__join { padding: 9px 18px; border: 0; border-radius: 10px; background: #2e7d4f; color: #fff; font: inherit; font-size: 12px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; cursor: pointer; }
.invite__x { display: grid; place-items: center; width: 34px; height: 34px; border: 2px solid var(--line); border-radius: 10px; background: var(--surface-raised); color: var(--text-muted); cursor: pointer; }
.invite__join:focus-visible, .invite__x:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.confirm { padding: 14px 18px; border: 2px solid var(--pop-orange); border-radius: var(--radius-md); background: #fff4e6; }
.confirm p { margin: 0 0 10px; font-size: 14px; line-height: 20px; font-weight: 600; }
.confirm__act { display: flex; gap: 10px; }
.confirm__go { padding: 10px 18px; border: 0; border-radius: var(--radius-md); background: #d32f2f; color: #fff; font: inherit; font-size: 13px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; cursor: pointer; }

/* the stage: the scene fills it, everything else is placed over it */
.hp__stage { position: relative; overflow: hidden; width: 100%; aspect-ratio: 1600 / 760; min-height: 560px; border: 2px solid var(--honey); border-radius: 28px; background: #bfe6f8; isolation: isolate; }
.hpcard { position: absolute; left: 4%; top: 17%; z-index: 3; width: min(400px, 38%); padding: 16px 20px; border: 2px solid var(--honey); border-radius: 18px; background: rgba(255, 255, 255, .95); box-shadow: var(--shadow-soft); }
.hpcard__eyebrow { color: #d32f2f; font-size: 12px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }
.hpcard h2 { margin: 4px 0 8px; font-size: 30px; line-height: 36px; font-weight: 900; }
.hpcard h2 small { margin-left: 4px; color: #d32f2f; font-size: 15px; font-weight: 900; }
.hpcard__bar { height: 18px; border: 1px solid #e9e1cc; border-radius: 999px; background: #f4efe3; overflow: hidden; }
.hpcard__bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #b3261e, #e04a43); transition: width .7s cubic-bezier(.3, .8, .3, 1); }
.hpcard__pips { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.hpcard__pip { display: grid; place-items: center; width: 26px; height: 26px; color: #c8c2b2; transition: color .3s, transform .3s var(--ease-bounce); }
.hpcard__pip.on { color: #1b1b1b; transform: scale(1.15); }
.hpcard__pips b { margin-left: 4px; font-size: 15px; font-weight: 800; }
.leave { position: absolute; right: 3%; top: 4%; z-index: 4; padding: 8px 16px; border: 2px solid rgba(255, 255, 255, .8); border-radius: 999px; background: rgba(30, 30, 30, .55); color: #fff; font: inherit; font-size: 13px; font-weight: 800; cursor: pointer; backdrop-filter: blur(4px); }
.leave--ask { display: flex; align-items: center; gap: 10px; cursor: default; }
.leave--ask button { padding: 4px 12px; border: 0; border-radius: 999px; background: #fff; font: inherit; font-size: 12px; font-weight: 900; cursor: pointer; }
.leave:focus-visible, .leave--ask button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }

.boss { position: absolute; left: 50%; top: 64%; z-index: 2; transform: translate(-50%, -50%); }
.boss.returning { animation: robbee-return 1s cubic-bezier(.3, 1.4, .5, 1) both; }
@keyframes robbee-return { from { opacity: 0; transform: translate(-50%, -190%) scale(.7); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }

.seat { position: absolute; z-index: 3; transform: translate(-50%, -50%); }
.seat--0 { left: 16%; top: 57%; }
.seat--1 { left: 84%; top: 57%; }
.seat--2 { left: 27%; top: 82%; }
.seat--3 { left: 73%; top: 82%; }
.slot { position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px; border: 0; background: none; font: inherit; cursor: pointer; }
.slot__ring { display: grid; place-items: center; width: 84px; height: 84px; border: 3px dashed rgba(90, 80, 60, .6); border-radius: 50%; background: rgba(255, 255, 255, .35); color: #5a503c; font-size: 38px; font-weight: 400; line-height: 1; transition: transform var(--dur-fast) var(--ease-bounce), background var(--dur-fast) var(--ease-out); }
button.slot:hover .slot__ring { transform: scale(1.08); background: rgba(255, 255, 255, .6); }
.slot--wait { cursor: default; }
.slot--wait .slot__ring { border-style: dashed; border-color: var(--honey-deep); background: rgba(255, 239, 199, .6); }
.slot__label { padding: 2px 10px; border-radius: 999px; background: rgba(255, 255, 255, .72); font-size: 14px; font-weight: 800; white-space: nowrap; color: #1b1b1b; }
.slot__cancel { position: absolute; right: -6px; top: -6px; display: grid; place-items: center; width: 24px; height: 24px; border: 0; border-radius: 50%; background: #fff; color: #444; cursor: pointer; box-shadow: var(--shadow-soft); }
.slot:focus-visible, .slot__cancel:focus-visible { outline: 3px solid var(--focus); outline-offset: 4px; border-radius: 12px; }

.sting { position: absolute; left: 50%; bottom: 4%; z-index: 4; display: flex; flex-direction: column; align-items: center; gap: 8px; transform: translateX(-50%); }
.sting__btn { display: inline-flex; align-items: center; gap: 10px; padding: 14px 34px; border: 0; border-radius: 16px; background: var(--honey); color: var(--on-honey); font: inherit; font-size: 20px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; cursor: pointer; box-shadow: 0 6px 0 var(--honey-deep); transition: transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out); }
.sting__btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 0 var(--honey-deep); }
.sting__btn:active:not(:disabled) { transform: translateY(4px); box-shadow: 0 1px 0 var(--honey-deep); }
.sting__btn:disabled { opacity: .6; cursor: not-allowed; }
.sting__btn:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
.sting__n { padding: 2px 10px; border-radius: 999px; background: #1b1b1b; color: var(--honey); font-size: 15px; letter-spacing: 0; }
.sting__hint { padding: 4px 12px; border-radius: 999px; background: rgba(255, 255, 255, .85); color: var(--text); font-size: 13px; font-weight: 800; text-decoration: none; }

.floater { position: absolute; z-index: 6; transform: translate(-50%, 0); font-size: 26px; font-weight: 900; pointer-events: none; text-shadow: 0 2px 0 rgba(255, 255, 255, .9), 0 0 12px rgba(255, 255, 255, .8); animation: floater 1.5s ease-out forwards; }
.floater--dmg { color: #d32f2f; font-size: 34px; }
.floater--pollen { color: #b87a00; }
@keyframes floater { 0% { opacity: 0; transform: translate(-50%, 10px) scale(.6); } 15% { opacity: 1; transform: translate(-50%, -6px) scale(1.15); } 100% { opacity: 0; transform: translate(-50%, -80px) scale(1); } }

.feed { padding: 22px 26px; border: 2px solid var(--line); border-radius: var(--radius-lg); background: var(--surface-raised); }
.feed h2 { margin: 0 0 12px; font-size: 24px; font-weight: 900; }
.feed ul { display: flex; flex-direction: column; gap: 12px; margin: 0; padding: 0; list-style: none; }
.feed li { display: flex; align-items: center; gap: 14px; font-size: 15px; font-weight: 600; }
.feed__icon { flex: none; display: grid; place-items: center; width: 22px; color: #1b1b1b; }
.feed__text { flex: 1; min-width: 0; }
.feed__tag { flex: none; color: #b87a00; font-size: 14px; font-weight: 800; }
.feed__tag--twist { color: #d9580a; }
.feed__tag--win { color: #2e7d4f; }
.feed__empty { margin: 0; color: var(--text-muted); font-size: 14px; font-weight: 700; }

@media (prefers-reduced-motion: reduce) { .boss.returning, .floater { animation: none; } .floater { opacity: 1; } }
@media (max-width: 900px) {

  .hp__stage { aspect-ratio: auto; min-height: 780px; }
  .hpcard { left: 3%; right: 3%; top: 56px; width: auto; }
  .leave { top: 12px; right: 12px; }
  .boss :deep(svg) { width: 140px; height: auto; }
  .seat { transform: translate(-50%, -50%) scale(.78); }
  .seat--0 { left: 19%; top: 58%; }
  .seat--1 { left: 81%; top: 58%; }
  .seat--2 { left: 25%; top: 77%; }
  .seat--3 { left: 75%; top: 77%; }
  .slot__ring { width: 68px; height: 68px; }
  .sting { bottom: 2%; }
}
</style>
