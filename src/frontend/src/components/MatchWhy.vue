<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { capFirst, fetchRoleSdg, type RoleSdg } from '../api/sdg';
import type { JobMatch } from '../api/jobs';
import { SDG_GOALS } from '../data/interestSdgs';

/** The sub card tucked under a role's card: the SDGs the role serves, each with its targets. */
const props = defineProps<{ job: JobMatch }>();

/** One request per role, shared by every card that shows it. */
const cache = new Map<string, Promise<RoleSdg | null>>();
const roleSdg = ref<RoleSdg | null>(null);
watch(
  () => props.job.onet_code,
  async (code) => {
    roleSdg.value = null;
    if (!cache.has(code)) cache.set(code, fetchRoleSdg(code).catch(() => { cache.delete(code); return null; }));
    const r = await cache.get(code);
    if (code === props.job.onet_code) roleSdg.value = r ?? null;
  },
  { immediate: true },
);

/** The role's goals, main first; the match's own goals if the targets didn't load. */
const goals = computed(() => {
  const r = roleSdg.value;
  const list = r ? [r.main, ...r.relevant] : (props.job.sdg_reasons ?? []).map((g) => ({ sdg: g.sdg, name: g.name }));
  return list.map((g) => ({
    ...g,
    name: SDG_GOALS[g.sdg]?.title ?? g.name,
    color: SDG_GOALS[g.sdg]?.color ?? 'var(--ink)',
    targets: r?.targets.filter((t) => t.sdg === g.sdg) ?? [],
  }));
});
</script>

<template>
  <div v-if="goals.length" class="why">
    <ul class="goals">
      <li v-for="g in goals" :key="g.sdg" class="goal">
        <button type="button" class="sdg" :style="{ '--c': g.color }" :aria-describedby="`sdg-${job.onet_code}-${g.sdg}`">SDG {{ g.sdg }}</button>
        <div :id="`sdg-${job.onet_code}-${g.sdg}`" class="tip" role="tooltip">
          <p class="tip-title" :style="{ color: g.color }">SDG {{ g.sdg }} · {{ g.name }}</p>
          <ul v-if="g.targets.length" class="targets">
            <li v-for="t in g.targets" :key="t.code"><b :style="{ color: g.color }">{{ t.code }}</b> {{ capFirst(t.text) }}</li>
          </ul>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.why { margin: -6px 10px 0; padding: 12px 16px 10px; display: flex; align-items: center; gap: 10px; border: 2px solid var(--line); border-top: 0; border-radius: 0 0 14px 14px; background: #fff; }
.label { font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.goals { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; }
.goal { position: relative; }
.sdg { padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 800; color: var(--c); border: 1.5px solid var(--c); background: #fff; cursor: default; }
.goal:hover .sdg, .sdg:focus-visible { background: var(--c); color: #fff; }
.tip { display: none; position: absolute; z-index: 10; top: calc(100% + 6px); left: 0; width: min(340px, calc(100vw - 48px)); padding: 12px 14px; border-radius: 14px; background: #fff; border: 2px solid var(--line); box-shadow: 0 10px 28px rgba(30, 30, 30, .16); }
.goal:hover .tip, .goal:focus-within .tip { display: block; }
.tip-title { font-size: 14px; font-weight: 900; margin-bottom: 6px; }
.targets { list-style: none; display: flex; flex-direction: column; gap: 5px; font-size: 14px; font-weight: 600; line-height: 1.4; color: var(--muted); }
.targets b { font-weight: 900; margin-right: 4px; }
</style>
