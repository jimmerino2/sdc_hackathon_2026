<script setup lang="ts">
import { computed } from 'vue';
import SideNav from '../components/SideNav.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import { pathwayFor } from '../data/flows';
import { useFlow } from '../state';
import { go } from '../router';

const { key, persona, state, chosenRole, scenario } = useFlow();
const nodes = computed(() => pathwayFor(chosenRole.value));
const offsets = [0, -40, -75, -40, 0];
const done = computed(() => state.value.doneNodes);
const have = computed(() => persona.value.skills.filter((_, i) => state.value.levels[i]! >= 1).map((s) => s.name).slice(0, 5));
function complete(i: number) { if (i === done.value && i < nodes.value.length) state.value.doneNodes++; }
</script>

<template>
  <SideNav active="learn">
    <div class="grid">
      <div class="main">
        <section class="unit dark">
          <p class="eyebrow">Unit 1 · Already yours</p>
          <h2>You tested out of {{ have.length }} skills</h2>
          <div class="chips"><span v-for="s in have" :key="s" class="chip">{{ s }}</span></div>
        </section>
        <section class="unit gold">
          <div class="row">
            <div>
              <p class="eyebrow dk">Unit 2 · Close your gap</p>
              <h2>{{ chosenRole.title }}</h2>
              <p class="meta">{{ nodes.length }} skills · ~{{ persona.weeksToGo }} weeks · {{ persona.minutesPerDay }} min a day</p>
            </div>
            <RouterLink :to="go(key, 'resources')" class="guide"><Icon name="book" :size="16" /> Guidebook</RouterLink>
          </div>
        </section>

        <div class="path">
          <div v-for="(n, i) in nodes" :key="n" class="node" :style="{ transform: `translateX(${offsets[i]}px)` }">
            <span v-if="i === done" class="start">Start</span>
            <button class="orb" :class="{ cur: i === done, ok: i < done, lock: i > done }" :disabled="i > done" :aria-label="n" @click="complete(i)">
              <Icon :name="i < done ? 'check' : i === done ? 'star' : 'lock'" :size="26" />
            </button>
            <span class="lbl" :class="{ dim: i > done }">{{ n }}</span>
          </div>
          <div class="node end" :style="{ transform: 'translateX(5px)' }">
            <span class="orb trophy"><Icon name="trophy" :size="26" /></span><span class="lbl">Role-ready!</span>
          </div>
          <div class="guide-mascot"><Mascot :size="80" /><p class="bubble">{{ done === 0 ? 'Day 1. I’ll be right here!' : done < nodes.length ? 'Nice one! Keep going.' : 'You’re role-ready!' }}</p></div>
        </div>
      </div>

      <aside class="side">
        <div class="card stat"><div class="day"><h3>Day {{ done + 1 }}</h3><Icon name="flame" :size="26" /></div><p>Finish one lesson today to start your streak.</p></div>
        <div class="card stat">
          <small>Target role</small><h3 class="sm">{{ chosenRole.title }}</h3>
          <div class="progress"><i :style="{ width: ((chosenRole.haveCount + done) / chosenRole.total) * 100 + '%' }" /></div>
          <p>{{ chosenRole.haveCount + done }} of {{ chosenRole.total }} skills · ~{{ Math.max(persona.weeksToGo - done * 2, 0) }} weeks to go</p>
        </div>
        <div class="signal"><Icon name="tup" :size="20" /><div><strong>Signal: {{ scenario.label }}</strong><p>Rechecked weekly against live job postings.</p></div></div>
      </aside>
    </div>
  </SideNav>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr 280px; gap: 32px; max-width: 1000px; }
.unit { border-radius: 20px; padding: 18px 22px; margin-bottom: 16px; }
.dark { background: var(--ink); color: #fff; } .dark h2 { font-size: 22px; font-weight: 900; margin: 6px 0 14px; }
.eyebrow { font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--yellow); }
.dk { color: var(--ink); opacity: .75; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; } .chip { background: #fff; color: var(--ink); border-radius: 999px; padding: 8px 14px; font-size: 12px; font-weight: 800; }
.gold { background: var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.gold h2 { font-size: 24px; font-weight: 900; margin: 4px 0; } .meta { font-size: 12px; font-weight: 800; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.guide { display: inline-flex; gap: 8px; align-items: center; border: 2px solid var(--ink); border-radius: 12px; padding: 10px 14px; font-weight: 900; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.path { position: relative; display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 18px 0 40px; }
.node { position: relative; display: flex; align-items: center; gap: 14px; width: 240px; transition: transform .2s; }
.orb { width: 62px; height: 58px; border-radius: 50%; display: grid; place-items: center; flex: none; background: var(--yellow); box-shadow: 0 6px 0 var(--orange); }
.orb.cur { outline: 4px solid var(--yellow); outline-offset: 5px; background: var(--yellow); }
.orb.ok { background: var(--ink); color: var(--yellow); box-shadow: 0 6px 0 #000; }
.orb.lock { background: #eceae5; box-shadow: 0 6px 0 #c2bfba; color: #b0ada8; cursor: not-allowed; }
.orb.trophy { background: var(--yellow); }
.start { position: absolute; top: -26px; left: 6px; border: 2px solid var(--yellow); border-radius: 10px 10px 0 0; padding: 2px 14px; color: var(--orange); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; background: var(--bg); }
.lbl { font-weight: 800; font-size: 15px; } .lbl.dim { color: var(--muted); }
.guide-mascot { position: absolute; left: 0; bottom: 20px; display: flex; flex-direction: column; gap: 8px; }
.bubble { background: #fff; border: 2px solid var(--line); border-radius: 14px; padding: 10px 14px; font-weight: 800; font-size: 14px; width: 150px; }
.side { display: flex; flex-direction: column; gap: 14px; }
.stat { padding: 18px 20px; } .stat p { font-size: 12px; font-weight: 600; color: var(--muted); margin-top: 6px; }
.day { display: flex; justify-content: space-between; align-items: center; color: var(--orange); } .day h3 { font-size: 32px; font-weight: 900; color: var(--ink); }
.stat small { font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.sm { font-size: 20px; font-weight: 900; margin: 4px 0 10px; } .progress { height: 10px; }
.signal { display: flex; gap: 12px; background: var(--cream); border-radius: 16px; padding: 14px 16px; color: var(--orange); }
.signal strong { color: var(--ink); font-size: 14px; font-weight: 900; } .signal p { font-size: 12px; font-weight: 600; color: var(--muted); }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } .guide-mascot { display: none; } }
</style>
