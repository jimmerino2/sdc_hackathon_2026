<script lang="ts">
export interface HoverRow { label: string; value: string; color?: string; muted?: boolean }
export interface HoverPoint { x: number; title: string; rows: HoverRow[]; dots?: { y: number; color?: string }[] }
</script>

<script setup lang="ts">
import { computed, ref } from 'vue';

/** Hover layer for an SVG chart: snaps to the nearest point (by x, or by distance for scatter charts),
 *  draws a guide line and dots, and shows the values in a tooltip. Wrap the chart's <svg> in the slot;
 *  the svg must fill the wrapper's width (its viewBox is `0 0 w h`). Arrow keys step through points. */

const props = withDefaults(defineProps<{
  w: number; h: number; points: HoverPoint[];
  /** Guide line extent in viewBox units. */
  top?: number; bottom?: number;
  /** 'x' snaps to the nearest x (time series); 'xy' to the nearest dot (scatter). */
  mode?: 'x' | 'xy';
}>(), { top: 0, mode: 'x' });

const box = ref<HTMLDivElement>();
const idx = ref<number | null>(null);
const pt = computed(() => (idx.value == null ? null : props.points[idx.value] ?? null));

function nearest(vx: number, vy: number): number | null {
  let best: number | null = null, bd = Infinity;
  props.points.forEach((p, i) => {
    const ys = props.mode === 'xy' && p.dots?.length ? p.dots.map((d) => d.y) : [vy];
    for (const y of ys) {
      const d = props.mode === 'xy' ? (p.x - vx) ** 2 + (y - vy) ** 2 : Math.abs(p.x - vx);
      if (d < bd) { bd = d; best = i; }
    }
  });
  return best;
}
function move(e: PointerEvent) {
  const r = box.value?.getBoundingClientRect();
  if (!r || !r.width) return;
  idx.value = nearest(((e.clientX - r.left) / r.width) * props.w, ((e.clientY - r.top) / r.height) * props.h);
}
function key(e: KeyboardEvent) {
  if (!props.points.length) return;
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    e.preventDefault();
    const order = props.points.map((p, i) => [p.x, i] as const).sort((a, b) => a[0] - b[0]).map((a) => a[1]);
    const at = idx.value == null ? -1 : order.indexOf(idx.value);
    const next = e.key === 'ArrowRight' ? Math.min(order.length - 1, at + 1) : Math.max(0, at < 0 ? order.length - 1 : at - 1);
    idx.value = order[next];
  } else if (e.key === 'Escape') idx.value = null;
}

const tipStyle = computed(() => {
  const p = pt.value;
  if (!p) return {};
  const ys = p.dots?.map((d) => d.y) ?? [];
  const y = ys.length ? Math.min(...ys) : (props.top + (props.bottom ?? props.h)) / 2;
  const right = p.x / props.w > 0.6;
  return {
    left: `${(p.x / props.w) * 100}%`,
    top: `${Math.max(4, (y / props.h) * 100)}%`,
    transform: `translate(${right ? 'calc(-100% - 12px)' : '12px'}, -50%)`,
  };
});
</script>

<template>
  <div ref="box" class="ch" tabindex="0" @pointermove="move" @pointerleave="idx = null" @blur="idx = null" @keydown="key">
    <slot />
    <svg v-if="pt" class="ov" :viewBox="`0 0 ${w} ${h}`" preserveAspectRatio="none" aria-hidden="true">
      <line :x1="pt.x" :x2="pt.x" :y1="top" :y2="bottom ?? h" class="guide" />
    </svg>
    <span v-for="(d, i) in pt?.dots ?? []" :key="i" class="dot" aria-hidden="true"
          :style="{ left: `${(pt!.x / w) * 100}%`, top: `${(d.y / h) * 100}%`, background: d.color ?? 'var(--ink)' }" />
    <div v-if="pt" class="tip" :style="tipStyle" role="status">
      <p class="t">{{ pt.title }}</p>
      <p v-for="r in pt.rows" :key="r.label" class="r" :class="{ m: r.muted }">
        <i v-if="r.color" :style="{ background: r.color }" /><span>{{ r.label }}</span><b>{{ r.value }}</b>
      </p>
    </div>
  </div>
</template>

<style scoped>
.ch { position: relative; touch-action: pan-y; border-radius: 8px; }
.ch :deep(svg) { display: block; }
.ov { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.guide { stroke: var(--ink); stroke-width: 1; stroke-dasharray: 3 3; opacity: .45; vector-effect: non-scaling-stroke; }
.dot { position: absolute; width: 10px; height: 10px; margin: -5px 0 0 -5px; border-radius: 50%; box-shadow: 0 0 0 2px #fff; pointer-events: none; }
.tip {
  position: absolute; z-index: 5; pointer-events: none; min-width: 190px; max-width: 300px;
  background: #fff; border: 2px solid var(--line); border-radius: 12px; padding: 8px 10px;
  box-shadow: 0 6px 20px rgba(30, 30, 30, .12); font-size: 14px; line-height: 1.35;
}
.t { font-weight: 900; margin-bottom: 4px; }
.r { display: flex; align-items: baseline; gap: 6px; }
.r span { color: var(--muted); font-weight: 700; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.r b { font-weight: 900; white-space: nowrap; font-variant-numeric: tabular-nums; }
.r.m { font-size: 13px; }
.r.m b { font-weight: 700; color: var(--muted); }
.r i { width: 8px; height: 8px; border-radius: 2px; flex: none; align-self: center; }
</style>
