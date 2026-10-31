<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue';
import { capFirst } from '../api/sdg';
import { SDG_GOALS } from '../data/interestSdgs';

/**
 * A chip that shows the SDG targets behind a skill or interest on hover, focus or tap. The card is fixed to the screen
 * beside the chip, so opening it never makes the page taller; it flips above the chip when there is no room below and
 * closes on scroll. Chip classes go on the button; the slot is its label.
 */
defineOptions({ inheritAttrs: false });
defineProps<{
  title: string;
  targets: { code: string; sdg: number; text: string }[];
  /** A goal's colour: shows the chip as a small outlined "SDG n" pill in that colour instead of a full chip. */
  pill?: string;
}>();

const id = `tip-${useId()}`;
const open = ref(false);
const pos = ref({ top: 0, left: 0 });
async function show(e: Event) {
  const at = (e.currentTarget as HTMLElement).getBoundingClientRect();
  open.value = true;
  pos.value = { top: at.bottom + 8, left: at.left };
  await nextTick();
  const r = document.getElementById(id)?.getBoundingClientRect();
  if (!r || !open.value) return;
  const below = at.bottom + 8 + r.height <= window.innerHeight - 8;
  pos.value = {
    top: below ? at.bottom + 8 : Math.max(8, at.top - 8 - r.height),
    left: Math.max(16, Math.min(at.left, window.innerWidth - 16 - r.width)),
  };
}
const hide = () => (open.value = false);
onMounted(() => window.addEventListener('scroll', hide, { capture: true, passive: true }));
onBeforeUnmount(() => window.removeEventListener('scroll', hide, { capture: true }));
const color = (sdg: number) => SDG_GOALS[sdg]?.color ?? 'var(--ink)';
</script>

<template>
  <span class="sdgtip" @mouseenter="show" @mouseleave="hide">
    <button
      type="button"
      v-bind="$attrs"
      :class="pill ? 'sdg-pill' : 'chip tip-chip'"
      :style="pill ? { '--c': pill } : undefined"
      :aria-expanded="open"
      :aria-describedby="open ? id : undefined"
      @focus="show"
      @blur="hide"
      @click="show"
      @keydown.esc="hide"
    ><slot /></button>
    <Teleport to="body">
      <div v-if="open" :id="id" class="tip" role="tooltip" :style="{ top: `${pos.top}px`, left: `${pos.left}px` }">
        <p class="tip-title">{{ title }}</p>
        <ul class="tip-targets">
          <li v-for="t in targets" :key="t.code"><b :style="{ color: color(t.sdg) }">{{ t.code }}</b> {{ capFirst(t.text) }}</li>
        </ul>
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.tip-chip { cursor: help; font-size: 15px; padding: 8px 14px; white-space: normal; text-align: left; line-height: 1.25; }
.tip-chip.chip-have { border: 2px solid var(--ink); }
.tip-chip:focus-visible { outline: 3px solid var(--orange); outline-offset: 2px; }
.sdg-pill { padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 800; color: var(--c); border: 1.5px solid var(--c); background: #fff; cursor: help; }
.sdg-pill:hover, .sdg-pill[aria-expanded='true'], .sdg-pill:focus-visible { background: var(--c); color: #fff; }
.tip { position: fixed; z-index: 50; width: min(340px, calc(100vw - 32px)); padding: 14px 16px; border-radius: 16px; background: #fff; border: 2px solid var(--line); box-shadow: 0 10px 28px rgba(30, 30, 30, .16); pointer-events: none; }
.tip-title { font-size: 16px; font-weight: 900; margin-bottom: 8px; }
.tip-targets { list-style: none; display: flex; flex-direction: column; gap: 6px; font-size: 15px; font-weight: 600; line-height: 1.4; color: var(--muted); }
.tip-targets b { font-weight: 900; margin-right: 4px; }
</style>
