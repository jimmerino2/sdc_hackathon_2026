<script setup lang="ts">
import { computed } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import { skillLabel } from '../data/skills';
import { personaCopy } from '../data/personaCopy';
import { useFlow } from '../state';

const { state, key } = useFlow();
/** The chosen role's match: skills the learner has and still needs. Missing after a refresh. */
const job = computed(() => state.value.jobs.data?.jobs.find((j) => j.onet_code === state.value.chosenRoleId));
const pct = computed(() => (job.value ? (job.value.skills_owned / Math.max(job.value.skills_total, 1)) * 100 : 0));
</script>

<template>
  <FlowShell :progress="5" next="sync" next-label="Build my pathway" back="signal" :mood="job ? 'happy' : 'idle'" gear="glasses">
    <template #bubble>
      <template v-if="job">You already have {{ job.skills_owned }} of {{ job.skills_total }} key skills for {{ job.title }}.</template>
      <template v-else>Here’s how close you are to this role.</template>
    </template>

    <template v-if="job">
      <div class="meter">
        <div class="progress"><i :style="{ width: pct + '%' }" /></div>
        <span>{{ job.skills_owned }}/{{ job.skills_total }}</span>
      </div>

      <section class="card block">
        <div class="head"><h2>{{ personaCopy[key].haveTitle }}</h2><span class="pill pill-dark">{{ job.skills_you_have.length }}</span></div>
        <div v-if="job.skills_you_have.length" class="chips">
          <span v-for="s in job.skills_you_have" :key="s" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s) }}</span>
        </div>
        <p v-else class="empty">None of this role’s key skills yet. Everyone starts somewhere.</p>
      </section>

      <section class="card block">
        <div class="head"><h2>{{ personaCopy[key].gapTitle }}</h2><span class="pill">{{ job.skills_to_learn.length }}</span></div>
        <div v-if="job.skills_to_learn.length" class="chips">
          <span v-for="s in job.skills_to_learn" :key="s" class="chip chip-gap"><Icon name="sparkles" :size="14" /> {{ skillLabel(s) }}</span>
        </div>
        <p v-else class="empty">You already cover every key skill for this role.</p>
        <p v-if="job.skills_to_learn.length" class="hint">Your pathway covers these, one step at a time.</p>
      </section>
    </template>
    <p v-else class="empty">Go back and pick a role to see which skills you already have and which to build.</p>
  </FlowShell>
</template>

<style scoped>
.meter { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.meter .progress { flex: 1; }
.meter span { font-weight: 900; font-size: 15px; }
.block { padding: 18px 20px; }
.block + .block { margin-top: 14px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.head h2 { font-weight: 800; font-size: 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 13px; padding: 7px 12px 7px 10px; }
.hint { margin-top: 14px; font-size: 12px; font-weight: 700; color: var(--muted); }
.empty { font-size: 14px; font-weight: 700; color: var(--muted); }
</style>
