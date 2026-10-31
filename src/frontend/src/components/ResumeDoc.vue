<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import type { Mark, ResumePreview } from '../api/readResumePdf';

const props = defineProps<{
  doc: ResumePreview;
  /** Highlights above this distance (px from the top) are shown; Infinity shows them all. */
  reveal: number;
  /** Where the scan line is, or null once it has finished. */
  scan: number | null;
  /** When set, only keywords in it are highlighted (the skills the AI confirmed) and the scan position is ignored. */
  shownKeys: Set<string> | null;
  /** Skill whose highlights stand out while the rest fade. */
  focusKey: string | null;
}>();

const box = ref<HTMLElement>();
const pageEls = ref<HTMLElement[]>([]);

onMounted(() => pageEls.value.forEach((el, i) => el.prepend(props.doc.pages[i].canvas)));

const marksOn = (page: number) => props.doc.marks.filter((m) => m.page === page);
const isHot = (m: Mark) => !!props.focusKey && m.key.toLowerCase() === props.focusKey.toLowerCase();
const scrolls = () => !!box.value && box.value.scrollHeight > box.value.clientHeight;

// While scanning, the document follows the scan line.
watch(
  () => props.scan,
  (y) => {
    if (y !== null && scrolls()) box.value!.scrollTop = Math.max(0, y - box.value!.clientHeight / 2);
  },
);
watch(
  () => props.focusKey,
  (key) => {
    const first = key && props.doc.marks.find(isHot);
    if (first && scrolls()) box.value!.scrollTo({ top: Math.max(0, first.y - 120), behavior: 'smooth' });
  },
);
</script>

<template>
  <div ref="box" class="doc" :class="{ focus: !!focusKey }" tabindex="0" aria-label="Preview of your resume with skills highlighted">
    <div class="in">
      <i class="scan" :class="{ off: scan === null }" :style="{ transform: `translateY(${Math.min(scan ?? 0, doc.height - 3)}px)` }" aria-hidden="true" />
      <div v-for="(p, i) in doc.pages" :key="i" :ref="(el) => (pageEls[i] = el as HTMLElement)" class="page" :style="{ width: p.width + 'px', height: p.height + 'px' }">
        <i
          v-for="(m, j) in marksOn(i)"
          :key="j"
          class="hl"
          :class="{ on: shownKeys ? shownKeys.has(m.key.toLowerCase()) : m.y <= reveal, hot: isHot(m) }"
          :style="{ left: m.left + 'px', top: m.top + 'px', width: m.width + 'px', height: m.height + 'px' }"
          aria-hidden="true"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.doc {
  position: relative; width: 420px; max-width: 100%; max-height: min(600px, calc(100dvh - 250px)); overflow: auto; background: #fff;
  border: 2px solid var(--line-strong); border-radius: 12px; box-shadow: 0 8px 24px rgba(30, 30, 30, .08); scrollbar-width: thin;
  animation: rise .5s cubic-bezier(.22, 1, .36, 1) both;
}
.in { position: relative; }
.page { position: relative; line-height: 0; }
.page + .page { border-top: 2px dashed var(--line-strong); }
.page :deep(canvas) { display: block; }

/* Highlights multiply over the page so the text underneath stays readable. */
.hl {
  position: absolute; border-radius: 3px; background: var(--yellow); mix-blend-mode: multiply; opacity: .72;
  transform: scaleX(0); transform-origin: left; transition: transform .45s cubic-bezier(.22, 1, .36, 1), opacity .2s; pointer-events: none;
}
.hl.on { transform: scaleX(1); }
.focus .hl { opacity: .14; }
.focus .hl.hot { opacity: 1; box-shadow: 0 0 0 2px var(--ink); animation: hot .9s ease-in-out infinite; }
@keyframes hot { 50% { box-shadow: 0 0 0 5px var(--ink); } }

.scan {
  position: absolute; left: 0; right: 0; top: 0; height: 3px; z-index: 3; background: var(--yellow);
  box-shadow: 0 0 14px 3px var(--yellow); pointer-events: none; transition: opacity .6s;
}
.scan::before { content: ''; position: absolute; left: 0; right: 0; bottom: 3px; height: 70px; background: linear-gradient(to bottom, transparent, var(--cream)); opacity: .7; }
.scan.off { opacity: 0; }

@keyframes rise { from { opacity: 0; transform: translateY(14px) scale(.96); } }
@media (prefers-reduced-motion: reduce) { .focus .hl.hot, .doc { animation: none; } }
</style>
