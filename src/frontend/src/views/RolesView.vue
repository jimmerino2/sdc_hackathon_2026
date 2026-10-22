<script setup lang="ts">
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { scenarios } from '../data/flows';
import { useFlow } from '../state';

const { state, roles, scenario, chosenRole } = useFlow();
const sIcon = { accelerates: 'tup', steady: 'arrow', slows: 'tdown' } as const;

function pick(id: string) { state.value.chosenRoleId = id; }
function isSelected(id: string, idx: number) {
  const chosen = state.value.chosenRoleId;
  return chosen ? chosen === id : idx === 0;
}
function choose() {
  if (!state.value.chosenRoleId) state.value.chosenRoleId = roles.value[0]!.id;
}
void chosenRole;
</script>

<template>
  <FlowShell :progress="5" next="gap" next-label="Choose this role" skip-label="Save for later" skip-to="resources" @next="choose">
    <div class="wrap">
      <div class="tabs">
        <button v-for="s in scenarios" :key="s.key" :class="{ on: state.scenario === s.key }" @click="state.scenario = s.key; state.chosenRoleId = null">
          <Icon :name="sIcon[s.key]" :size="18" /> {{ s.label }}
        </button>
      </div>
      <h1>{{ scenario.heading }}</h1>
      <div class="cards">
        <button v-for="(r, i) in roles" :key="r.id" class="rc" :class="{ on: isSelected(r.id, i) }" @click="pick(r.id)">
          <div class="top">
            <span class="ic"><Icon :name="r.icon === 'code' ? 'code' : r.icon" :size="22" /></span>
            <em v-if="i === 0" class="pill pill-dark">Best match</em>
          </div>
          <h2>{{ r.title }}</h2>
          <div class="big"><b>{{ r.match }}%</b><span>match today</span></div>
          <div class="progress"><i :style="{ width: (r.haveCount / r.total) * 100 + '%' }" /></div>
          <p class="small">{{ r.haveCount }} of {{ r.total }} skills already yours</p>
          <span class="growth"><Icon name="tup" :size="16" /> {{ r.growth }}</span>
          <p class="blurb">{{ r.blurb }}</p>
          <div class="chips">
            <span v-for="s in r.have" :key="s" class="chip chip-have"><Icon name="check" :size="13" :stroke="3" /> {{ s }}</span>
            <span v-for="s in r.gap" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="13" /> {{ s }}</span>
          </div>
        </button>
      </div>
    </div>
  </FlowShell>
</template>

<style scoped>
.wrap { width: min(1100px, 94vw); margin-left: 50%; transform: translateX(-50%); }
:global(main:has(.wrap)) { max-width: none !important; padding-top: 16px !important; }
.tabs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 22px; }
.tabs button { display: flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: 14px; border: 2px solid var(--line-strong); background: #fff; box-shadow: 0 4px 0 rgba(30,30,30,.1); font-weight: 900; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; }
.tabs button.on { background: var(--yellow); border-color: var(--yellow); box-shadow: 0 4px 0 var(--orange); }
h1 { font-size: 30px; font-weight: 900; margin-bottom: 22px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.rc { text-align: left; background: #fff; border: 2px solid var(--line-strong); border-radius: 22px; padding: 22px; box-shadow: 0 5px 0 var(--line); display: flex; flex-direction: column; gap: 10px; transition: transform .12s; }
.rc:hover { transform: translateY(-2px); }
.rc.on { border: 3px solid var(--yellow); box-shadow: 0 5px 0 var(--orange); }
.top { display: flex; justify-content: space-between; align-items: center; }
.ic { width: 42px; height: 42px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.on .ic { background: var(--yellow); }
h2 { font-size: 21px; font-weight: 800; margin-top: 6px; }
.big { display: flex; align-items: baseline; gap: 8px; } .big b { font-size: 44px; font-weight: 900; line-height: 1; } .big span { font-size: 13px; color: var(--muted); font-weight: 700; }
.small { font-size: 12px; font-weight: 700; color: var(--muted); }
.growth { display: inline-flex; align-self: flex-start; align-items: center; gap: 6px; background: var(--cream); border-radius: 12px; padding: 7px 12px; font-weight: 800; font-size: 12px; color: var(--ink); }
.growth svg { color: var(--orange); }
.blurb { font-size: 13px; color: var(--muted); font-weight: 600; line-height: 1.4; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; padding: 6px 11px 6px 9px; }
@media (max-width: 960px) { .cards { grid-template-columns: 1fr; } }
</style>
