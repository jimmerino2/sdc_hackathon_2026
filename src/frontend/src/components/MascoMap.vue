<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue';
import { EMASCO_URL, mascoRoles, type MascoMinor, type MascoUnit } from '../data/masco';

/** A role as a flowchart of the MASCO groups under it: the unit group in a tall box on the left, its minor unit groups on the right. Pick a box to read about it. */
const props = defineProps<{ onetCode: string; title: string }>();

const role = computed(() => mascoRoles[props.onetCode]);
const minors = computed(() => role.value?.minors ?? []);
const showMap = computed(() => !!minors.value.length);

/** What is shown on the right: the unit group or one of its minor unit groups. */
type Picked = { kind: 'unit'; unit: MascoUnit } | { kind: 'minor'; minor: MascoMinor };
/** The unit group is open to start with. */
const first = (): Picked | null => (role.value?.unit ? { kind: 'unit', unit: role.value.unit } : null);
const open = shallowRef<Picked | null>(first());
watch(() => props.onetCode, () => (open.value = first()));

const unitOpen = computed(() => open.value?.kind === 'unit');
const isOpen = (m: MascoMinor) => open.value?.kind === 'minor' && open.value.minor === m;
function pickUnit() {
  const unit = role.value?.unit;
  if (!unit) return;
  open.value = unitOpen.value ? null : { kind: 'unit', unit };
}
function pickMinor(minor: MascoMinor) {
  open.value = isOpen(minor) ? null : { kind: 'minor', minor };
}

const detail = computed(() => {
  const o = open.value;
  if (!o) return null;
  if (o.kind === 'minor') return { name: o.minor.name, about: o.minor.about, tasks: o.minor.tasks, url: `${EMASCO_URL}/masco/${o.minor.id}`, facts: [] as { label: string; value: string }[] };
  return {
    name: props.title,
    about: o.unit.about,
    tasks: o.unit.tasks,
    url: role.value?.url ?? EMASCO_URL,
    facts: [
      { label: 'Degree basic salary', value: o.unit.degreeSalary },
      { label: 'Yearly increment', value: o.unit.increment },
    ],
  };
});
</script>

<template>
  <div class="masco">
    <p v-if="!showMap" class="about">{{ role?.about ?? `${title} is one of the roles Jobee matches you to.` }}</p>
    <div v-else class="layout" :class="{ opened: detail }">
      <div class="flow">
        <button type="button" class="major" :class="{ on: unitOpen }" :disabled="!role?.unit" :aria-expanded="unitOpen" @click="pickUnit">
          <span>{{ title }}</span>
        </button>
        <ul class="minors" aria-label="Minor unit groups">
          <li v-for="m in minors" :key="m.id">
            <button type="button" class="minor" :class="{ on: isOpen(m) }" :aria-expanded="isOpen(m)" @click="pickMinor(m)">{{ m.name }}</button>
          </li>
        </ul>
      </div>
      <aside v-if="detail" class="detail" aria-live="polite">
        <h2>{{ detail.name }}</h2>
        <p class="d-about">{{ detail.about }}</p>
        <dl v-if="detail.facts.length" class="facts">
          <div v-for="f in detail.facts" :key="f.label"><dt>{{ f.label }}</dt><dd>{{ f.value }}</dd></div>
        </dl>
        <h3>Tasks</h3>
        <ul><li v-for="t in detail.tasks" :key="t">{{ t }}</li></ul>
        <a class="d-link" :href="detail.url" target="_blank" rel="noopener">Read the full entry on eMASCO <span aria-hidden="true">↗</span></a>
      </aside>
    </div>
    <p v-if="role?.url" class="src">
      Classification: <a :href="role.url" target="_blank" rel="noopener">eMASCO, Ministry of Human Resources</a>
    </p>
  </div>
</template>

<style scoped>
.about { font-size: 17px; font-weight: 700; line-height: 1.5; margin-bottom: 16px; max-width: 70ch; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; align-items: start; }

/* The flowchart: one tall box on the left joined by elbow lines to a stack of boxes on the right. */
.flow { display: flex; flex-direction: column; gap: 14px; background: #fff; border: 2px solid #1e1e1e; border-radius: 20px; padding: 16px; box-shadow: 0 4px 0 rgba(30, 30, 30, .12); }
.major, .minor { display: flex; align-items: center; width: 100%; height: 56px; padding: 0 18px; border: 2.5px solid #1e1e1e; border-radius: 14px; font: inherit; font-size: 15px; font-weight: 800; line-height: 1.25; color: #1e1e1e; cursor: pointer; transition: background .12s, box-shadow .12s, transform .12s; }
.major { justify-content: center; text-align: center; background: #ff9800; }
.major:disabled { cursor: default; }
.major:not(:disabled):hover { background: #ffa726; }
.minors { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
/* A short line from the box above joins each box into one column. */
.minors li { position: relative; }
.minors li::before { content: ''; position: absolute; left: 50%; top: -14px; height: 14px; border-left: 3px solid #c2bfba; }
.minor { text-align: left; background: #fff3cc; }
.minor:hover { background: #ffe9a8; }
/* The picked box stands out: filled, with a thick outline. */
.major.on, .minor.on { background: #ffc61a; box-shadow: 0 0 0 3px #fff, 0 0 0 6px #1e1e1e; transform: translateX(2px); }
.major:focus-visible, .minor:focus-visible { outline: 3px solid #ff9800; outline-offset: 4px; }

.detail { background: #fff; border: 2px solid #1e1e1e; border-radius: 20px; padding: 22px 26px; box-shadow: 0 4px 0 rgba(30, 30, 30, .12); border-top: 8px solid #ff9800; animation: d-in .18s ease-out; max-height: min(78vh, 720px); overflow-y: auto; overscroll-behavior: contain; position: sticky; top: 12px; }
@keyframes d-in { from { opacity: 0; transform: translateX(8px); } }
@media (prefers-reduced-motion: reduce) { .detail { animation: none; } }
.detail h2 { font-size: 24px; font-weight: 900; line-height: 1.2; margin: 0 0 10px; }
.detail h3 { font-size: 13px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin: 18px 0 8px; }
.d-about { font-size: 16px; font-weight: 600; line-height: 1.55; margin: 0; }
.facts { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 0; }
.facts div { flex: 1 1 150px; padding: 10px 14px; border-radius: 14px; background: #fff3cc; border: 2px solid #1e1e1e; }
.facts dt { font-size: 12px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.facts dd { margin: 2px 0 0; font-size: 18px; font-weight: 900; }
.detail ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; font-size: 15px; font-weight: 600; line-height: 1.45; }
.detail li { position: relative; padding-left: 20px; }
.detail li::before { content: ''; position: absolute; left: 0; top: .5em; width: 9px; height: 9px; border-radius: 50%; background: #ff9800; border: 2px solid #1e1e1e; box-sizing: border-box; }
.d-link { display: inline-block; margin-top: 18px; padding: 9px 16px; border: 2px solid #1e1e1e; border-radius: 999px; font-size: 14px; font-weight: 800; color: inherit; text-decoration: none; background: #fff3cc; }
.d-link:hover { background: #ffe9a8; }
.src { margin-top: 10px; font-size: 13px; font-weight: 600; color: var(--muted); }
.src a { color: inherit; text-decoration: underline; }
@media (max-width: 900px) { .layout { grid-template-columns: minmax(0, 1fr); } }
</style>
