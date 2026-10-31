<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = withDefaults(
  defineProps<{
    avoid?: string[];       // 花朵要避开的元素（CSS 选择器）
    bottomReserve?: number; // 视口底部留空高度（px），避开底部按钮区
  }>(),
  { avoid: () => ['.skip'], bottomReserve: 90 },
);

interface Flower {
  id: number;
  x: number;      // 视口 px（花朵中心）
  y: number;
  size: number;
  hue: number;
  life: number;   // ms
  born: number;
  petals: number;
}
interface Pop { id: number; x: number; y: number; text: string; hue: number }

const MAX_FLOWERS = 14;
const TOP_RESERVE = 70;  // 顶部留空
const AVOID_PAD = 24;    // 避开区域外扩的安全距离

const flowers = ref<Flower[]>([]);
const pops = ref<Pop[]>([]);
const bee = ref<HTMLElement>();
const beeVisible = ref(false);
let uid = 0;
let timer: number | undefined;
let lastX = 0;
let facing = 1;

const rand = (a: number, b: number) => a + Math.random() * (b - a);

function blockedRects(): DOMRect[] {
  const rects: DOMRect[] = [];
  for (const sel of props.avoid) {
    document.querySelectorAll(sel).forEach((el) => rects.push(el.getBoundingClientRect()));
  }
  return rects;
}

function spawn() {
  if (flowers.value.length >= MAX_FLOWERS) return;
  const size = Math.round(rand(28, 76));
  const half = size / 2;
  const minY = TOP_RESERVE + half;
  const maxY = window.innerHeight - props.bottomReserve - half;
  if (maxY <= minY) return; // 视口太小，不生成

  const rects = blockedRects();
  for (let i = 0; i < 15; i++) {
    const x = rand(half + 8, window.innerWidth - half - 8);
    const y = rand(minY, maxY);
    const hit = rects.some(
      (r) =>
        x + half > r.left - AVOID_PAD &&
        x - half < r.right + AVOID_PAD &&
        y + half > r.top - AVOID_PAD &&
        y - half < r.bottom + AVOID_PAD,
    );
    if (hit) continue;
    flowers.value.push({
      id: ++uid,
      x,
      y,
      size,
      hue: Math.round(rand(0, 360)),
      life: rand(3500, 6000),
      born: performance.now(),
      petals: Math.random() < 0.5 ? 5 : 6,
    });
    return;
  }
}

function tick() {
  const now = performance.now();
  flowers.value = flowers.value.filter((f) => now - f.born < f.life);
  if (Math.random() < 0.8) spawn();
}

function collect(f: Flower) {
  // 越小的花越难点，分数越高
  const points = f.size < 40 ? 3 : f.size < 58 ? 2 : 1;
  flowers.value = flowers.value.filter((x) => x.id !== f.id);
  const p: Pop = { id: ++uid, x: f.x, y: f.y, text: `+${points}`, hue: f.hue };
  pops.value.push(p);
  setTimeout(() => {
    pops.value = pops.value.filter((x) => x.id !== p.id);
  }, 700);
}

function onMove(e: PointerEvent) {
  beeVisible.value = true;
  if (Math.abs(e.clientX - lastX) > 2) facing = e.clientX > lastX ? 1 : -1;
  lastX = e.clientX;
  if (bee.value) {
    bee.value.style.transform = `translate(${e.clientX}px, ${e.clientY}px) translate(-50%, -50%) scaleX(${-facing})`;
  }
}

onMounted(() => {
  document.documentElement.classList.add('bee-cursor');
  window.addEventListener('pointermove', onMove);
  window.addEventListener('pointerdown', onMove);
  for (let i = 0; i < 5; i++) spawn();
  timer = window.setInterval(tick, 400);
});

onBeforeUnmount(() => {
  document.documentElement.classList.remove('bee-cursor');
  window.removeEventListener('pointermove', onMove);
  window.removeEventListener('pointerdown', onMove);
  clearInterval(timer);
});
</script>

<template>
  <Teleport to="body">
    <div class="game" aria-hidden="true">
      <button
        v-for="f in flowers"
        :key="f.id"
        type="button"
        tabindex="-1"
        class="flower"
        :style="{
          left: f.x + 'px',
          top: f.y + 'px',
          width: f.size + 'px',
          height: f.size + 'px',
          animationDuration: f.life + 'ms',
        }"
        @pointerdown.prevent.stop="collect(f)"
      >
        <svg viewBox="-50 -50 100 100">
          <ellipse
            v-for="i in f.petals"
            :key="i"
            cx="0"
            cy="-24"
            rx="14"
            ry="24"
            :fill="`hsl(${(f.hue + i * 12) % 360} 85% 62%)`"
            :transform="`rotate(${(360 / f.petals) * i})`"
          />
          <circle r="11" fill="#ffc107" stroke="#f57c00" stroke-width="3" />
        </svg>
      </button>

      <span
        v-for="p in pops"
        :key="p.id"
        class="pop"
        :style="{ left: p.x + 'px', top: p.y + 'px', color: `hsl(${p.hue} 80% 40%)` }"
      >{{ p.text }}</span>

      <div v-show="beeVisible" ref="bee" class="bee">🐝</div>
    </div>
  </Teleport>
</template>

<style scoped>
.game { position: fixed; inset: 0; z-index: 50; pointer-events: none; overflow: hidden; }

.flower {
  position: absolute; padding: 0; background: none; border: 0;
  pointer-events: auto;
  transform: translate(-50%, -50%) scale(0);
  animation-name: bloom; animation-timing-function: ease-in-out; animation-fill-mode: forwards;
}
.flower svg { width: 100%; height: 100%; display: block; animation: sway 2.4s ease-in-out infinite; }
@keyframes bloom {
  0%   { transform: translate(-50%, -50%) scale(0); }
  8%   { transform: translate(-50%, -50%) scale(1.15); }
  14%  { transform: translate(-50%, -50%) scale(1); }
  85%  { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(.2); opacity: 0; }
}
@keyframes sway { 50% { transform: rotate(8deg); } }

.pop {
  position: absolute; font-weight: 900; font-size: 23px;
  transform: translate(-50%, -50%); animation: rise .7s ease-out forwards;
}
@keyframes rise { to { transform: translate(-50%, -140%); opacity: 0; } }

.bee {
  position: absolute; left: 0; top: 0; font-size: 38px; line-height: 1;
  will-change: transform; filter: drop-shadow(0 3px 2px rgba(0, 0, 0, .2));
}

@media (prefers-reduced-motion: reduce) {
  .flower svg { animation: none; }
}
</style>

<style>
/* 全局隐藏原生光标，换成蜜蜂（组件卸载时类名会被移除） */
html.bee-cursor, html.bee-cursor * { cursor: none !important; }
</style>