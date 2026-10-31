<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { EMASCO_URL, mascoRoles, type MascoMinor } from '../data/masco';

/** A role as a mind map of the MASCO groups under it: the role in the middle, its minor unit groups around it. Tap one to read what eMASCO says about it. */
const props = defineProps<{ onetCode: string; title: string }>();

const role = computed(() => mascoRoles[props.onetCode]);
const minors = computed(() => role.value?.minors ?? []);
const showMap = computed(() => !!minors.value.length);

const open = ref<MascoMinor | null>(null);
watch(() => props.onetCode, () => (open.value = null));
function toggle(m: MascoMinor) {
  open.value = open.value === m ? null : m;
}

/** With many branches the map needs more room, so it grows taller and wider. */
const many = computed(() => minors.value.length > 6);
const NW = computed(() => (many.value ? 200 : 176));
const RX = computed(() => (many.value ? 290 : 230));
const RY = computed(() => (many.value ? 250 : 118));
const W = computed(() => (many.value ? 780 : 640));
const H = computed(() => (many.value ? 560 : 340));
const CX = computed(() => W.value / 2);
const CY = computed(() => H.value / 2);
/** Spread the branches evenly around the role, the first at the top. */
const nodes = computed(() =>
  minors.value.map((m, i, all) => {
    const a = -Math.PI / 2 + (i / all.length) * 2 * Math.PI;
    return { m, x: CX.value + Math.cos(a) * RX.value, y: CY.value + Math.sin(a) * RY.value };
  }),
);
/** Long names wrap over two lines. */
function lines(s: string): string[] {
  if (s.length <= 18) return [s];
  const words = s.split(' ');
  let best = [s, ''];
  let diff = Infinity;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(' '), b = words.slice(i).join(' ');
    if (Math.abs(a.length - b.length) < diff) { diff = Math.abs(a.length - b.length); best = [a, b]; }
  }
  return best;
}
</script>

<template>
  <div class="masco">
    <p class="about">{{ role?.about ?? `${title} is one of the roles Jobee matches you to.` }}</p>
    <div v-if="showMap" class="map">
      <svg v-if="minors.length" :viewBox="`0 0 ${W} ${H}`" role="group" :aria-label="`${title} and the minor unit groups under it`">
        <line v-for="n in nodes" :key="n.m.id" :x1="CX" :y1="CY" :x2="n.x" :y2="n.y" stroke="#c2bfba" stroke-width="3" stroke-linecap="round" />
        <ellipse :cx="CX" :cy="CY" rx="92" ry="44" fill="#ff9800" stroke="#1e1e1e" stroke-width="3" />
        <text text-anchor="middle" font-size="15" font-weight="900" fill="#1e1e1e">
          <tspan v-for="(l, i) in lines(title)" :key="i" :x="CX" :y="CY + (lines(title).length === 1 ? 5 : i ? 14 : -4)">{{ l }}</tspan>
        </text>
        <g
          v-for="n in nodes"
          :key="'n' + n.m.id"
          class="node"
          role="button"
          tabindex="0"
          :aria-expanded="open === n.m"
          :aria-label="`${n.m.name}: ${open === n.m ? 'hide' : 'show'} description`"
          @click="toggle(n.m)"
          @keydown.enter.prevent="toggle(n.m)"
          @keydown.space.prevent="toggle(n.m)"
        >
          <rect :x="n.x - NW / 2" :y="n.y - 22" :width="NW" height="44" rx="22" :fill="open === n.m ? '#ffd24d' : '#fff3cc'" stroke="#1e1e1e" stroke-width="2.5" />
          <text text-anchor="middle" font-size="12.5" font-weight="800" fill="#1e1e1e">
            <tspan v-for="(l, i) in lines(n.m.name)" :key="i" :x="n.x" :y="n.y + (lines(n.m.name).length === 1 ? 4 : i ? 15 : -2)">{{ l }}</tspan>
          </text>
          <circle :cx="n.x + NW / 2 - 14" :cy="n.y - 22" r="10" fill="#1e1e1e" aria-hidden="true" />
          <text :x="n.x + NW / 2 - 14" :y="n.y - 16.5" text-anchor="middle" font-size="16" font-weight="900" fill="#fff" aria-hidden="true">{{ open === n.m ? '−' : '+' }}</text>
        </g>
      </svg>
      <div v-if="open" class="detail" aria-live="polite">
        <h2>{{ open.name }}</h2>
        <p>{{ open.about }}</p>
        <h3>What they do</h3>
        <ul><li v-for="t in open.tasks" :key="t">{{ t }}</li></ul>
        <a :href="`${EMASCO_URL}/masco/${open.id}`" target="_blank" rel="noopener">Read the full entry on eMASCO</a>
      </div>
    </div>
    <p v-if="role?.url" class="src">
      Classification: <a :href="role?.url ?? EMASCO_URL" target="_blank" rel="noopener">eMASCO, Ministry of Human Resources</a>

    </p>
  </div>
</template>

<style scoped>
.about { font-size: 17px; font-weight: 700; line-height: 1.5; margin-bottom: 16px; max-width: 70ch; }
.map { position: relative; background: #fff; border: 2px solid #1e1e1e; border-radius: 20px; padding: 14px; box-shadow: 0 4px 0 rgba(30, 30, 30, .12); }
.map svg { display: block; width: 100%; max-height: 640px; }
.node { cursor: pointer; }
.node:focus-visible { outline: 3px solid #ff9800; outline-offset: 2px; }
.node:hover rect { fill: #ffe9a8; }
.detail { margin-top: 8px; padding: 16px 8px 4px; border-top: 2px dashed #c2bfba; }
.detail h2 { font-size: 21px; font-weight: 900; margin: 0 0 8px; }
.detail h3 { font-size: 14px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 14px 0 6px; }
.detail p { font-size: 16px; font-weight: 600; line-height: 1.5; margin: 0; }
.detail ul { margin: 0; padding-left: 20px; font-size: 15px; font-weight: 600; line-height: 1.5; }
.detail a { display: inline-block; margin-top: 12px; font-size: 14px; font-weight: 800; color: inherit; }
.src { margin-top: 10px; font-size: 13px; font-weight: 600; color: var(--muted); }
.src a { color: inherit; text-decoration: underline; }
</style>
