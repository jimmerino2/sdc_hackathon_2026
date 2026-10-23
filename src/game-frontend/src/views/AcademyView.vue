<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { missions, WORLD_1, type Mission } from '@/content/missions'
import { achievements } from '@/content/achievements'
import { useProgress } from '@/stores/progress'
import { useCompanion } from '@/stores/companion'

const router = useRouter()
const progress = useProgress()
const companion = useCompanion()
const shaking = ref<string | null>(null)

// Narrow screens squeeze the trail's zig-zag so nodes stay on screen.
const spread = ref(1)
const updateSpread = () => (spread.value = window.innerWidth < 600 ? 0.45 : 1)
onMounted(() => {
  updateSpread()
  window.addEventListener('resize', updateSpread)
  companion.react('enter_academy')
})
onBeforeUnmount(() => window.removeEventListener('resize', updateSpread))

const SPACING = 132
const OFFSETS = [0, 110, -40, -130, -20, 120, 30]

const CHAPTER_GAP = 56

const nodes = computed(() => {
  let y = 20
  return missions.map((m, i) => {
    const newChapter = i === 0 || missions[i - 1].chapter !== m.chapter
    y += (i === 0 ? 0 : SPACING) + (newChapter ? CHAPTER_GAP : 0)
    return {
      mission: m,
      state: progress.missionState(m.id),
      x: OFFSETS[i % OFFSETS.length] * spread.value,
      y,
      newChapter,
    }
  })
})

const trailHeight = computed(() => nodes.value.at(-1)!.y + 110)

// Smooth trail through node centres, split into walked / unwalked parts.
function segment(a: { x: number; y: number }, b: { x: number; y: number }) {
  const my = (a.y + b.y) / 2
  return `M ${a.x} ${a.y} C ${a.x} ${my}, ${b.x} ${my}, ${b.x} ${b.y}`
}

const segments = computed(() =>
  nodes.value.slice(1).map((n, i) => ({
    d: segment(nodes.value[i], n),
    walked: nodes.value[i].state === 'completed',
  })),
)

const todayDone = computed(() => {
  const today = new Date().toDateString()
  return Object.values(progress.completed).filter((c) => new Date(c.at).toDateString() === today).length
})

function open(m: Mission, state: string) {
  if (state === 'locked') {
    shaking.value = m.id
    setTimeout(() => (shaking.value = null), 400)
    const missing = m.prerequisites.map((p) => missions.find((x) => x.id === p)!.title).join(', ')
    companion.react('explore', { reason: `Locked. Finish "${missing}" first and this one lights up.` })
    return
  }
  if (m.comingSoon) {
    companion.react('explore', { reason: `"${m.title}" is still being surveyed. You've cleared everything that's built — nice.` })
    return
  }
  router.push({ name: 'lesson', params: { missionId: m.id } })
}
</script>

<template>
  <div class="academy">
    <section class="trail-col">
      <header class="world-head">
        <p class="eyebrow">World {{ WORLD_1.id }}</p>
        <h1>{{ WORLD_1.title }}</h1>
        <p>{{ WORLD_1.blurb }}</p>
      </header>

      <div class="trail" :style="{ height: trailHeight + 'px' }">
        <svg class="path" width="1" :height="trailHeight" aria-hidden="true">
          <path v-for="(s, i) in segments" :key="i" :d="s.d" :class="{ walked: s.walked }" />
        </svg>

        <template v-for="n in nodes" :key="n.mission.id">
          <div v-if="n.newChapter" class="chapter" :style="{ top: n.y - 86 + 'px' }">
            {{ n.mission.chapter }}
          </div>
          <div class="node-wrap" :style="{ top: n.y + 'px', left: `calc(50% + ${n.x}px)` }">
            <button
              class="node"
              :class="[n.state, { soon: n.mission.comingSoon, shake: shaking === n.mission.id, next: progress.nextMission?.id === n.mission.id }]"
              :aria-label="`${n.mission.title} — ${n.mission.comingSoon ? 'coming soon' : n.state}`"
              @click="open(n.mission, n.state)"
            >
              <span class="icon" aria-hidden="true">{{ n.state === 'locked' ? '🔒' : n.mission.icon }}</span>
              <span v-if="n.state === 'completed'" class="check" aria-hidden="true">✓</span>
            </button>
            <div class="label">
              <strong>{{ n.mission.title }}</strong>
              <span>{{ n.mission.comingSoon ? 'Coming soon' : n.mission.concept }}</span>
              <span v-if="n.mission.game && n.state !== 'locked'" class="tag game-tag">⛏ Powers the Frontier</span>
            </div>
            <div v-if="progress.nextMission?.id === n.mission.id" class="you-are-here" aria-hidden="true">Start here</div>
          </div>
        </template>
      </div>
    </section>

    <aside class="side">
      <section v-if="progress.nextMission" class="next">
        <p class="eyebrow">Up next</p>
        <h2>{{ progress.nextMission.icon }} {{ progress.nextMission.title }}</h2>
        <p>{{ progress.nextMission.objective }}</p>
        <button class="btn btn-primary" @click="open(progress.nextMission, progress.missionState(progress.nextMission.id))">
          {{ progress.missionState(progress.nextMission.id) === 'active' ? 'Resume mission' : 'Start mission' }}
        </button>
      </section>
      <section v-else class="next done">
        <p class="eyebrow">World 1</p>
        <h2>Chapter cleared</h2>
        <p>You've completed every mission that's built so far. Go mine some copper with your route.</p>
        <RouterLink to="/frontier" class="btn btn-primary">To the Frontier</RouterLink>
      </section>

      <section class="stat-block">
        <h3>Expedition log</h3>
        <div class="meter">
          <div class="meter-fill" :style="{ width: (progress.worldProgress.done / progress.worldProgress.total) * 100 + '%' }" />
        </div>
        <p class="small">{{ progress.worldProgress.done }} of {{ progress.worldProgress.total }} missions complete · {{ progress.xp }} XP</p>
        <div class="daily" :class="{ met: todayDone > 0 }">
          <span aria-hidden="true">{{ todayDone > 0 ? '☀️' : '🌤️' }}</span>
          <div>
            <strong>Today's objective</strong>
            <span>{{ todayDone > 0 ? 'Done — one mission cleared today.' : 'Clear one mission today.' }}</span>
          </div>
        </div>
      </section>

      <section class="stat-block">
        <h3>Badges</h3>
        <ul class="badges">
          <li v-for="a in achievements" :key="a.id" :class="{ earned: progress.achievements[a.id] }" :title="a.description">
            <span class="b-icon" aria-hidden="true">{{ progress.achievements[a.id] ? a.icon : '?' }}</span>
            <div>
              <strong>{{ a.title }}</strong>
              <small>{{ a.description }}</small>
            </div>
          </li>
        </ul>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.academy {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 0;
  flex: 1;
  background:
    radial-gradient(circle at 15% 10%, rgba(255, 193, 7, 0.12), transparent 30%),
    var(--c-cream);
}

.trail-col {
  padding: 28px 24px 120px;
  overflow: hidden;
}

.world-head {
  max-width: 560px;
  margin: 0 auto 10px;
  text-align: center;
}

.world-head h1 {
  font-size: 2.3rem;
}

.world-head p {
  color: var(--c-ink-soft);
}

.eyebrow {
  margin: 0 0 4px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.75rem;
  color: var(--c-secondary);
}

.trail {
  position: relative;
  max-width: 560px;
  margin: 30px auto 0;
}

.path {
  position: absolute;
  top: 0;
  left: 50%;
  overflow: visible;
}

.path path {
  fill: none;
  stroke: var(--c-cream-line);
  stroke-width: 10;
  stroke-linecap: round;
  stroke-dasharray: 2 18;
}

.path path.walked {
  stroke: var(--c-primary);
  stroke-dasharray: none;
}

.chapter {
  position: absolute;
  left: 0;
  right: 0;
  text-align: center;
  font-family: var(--font-display);
  font-size: 0.9rem;
  color: var(--c-ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.node-wrap {
  position: absolute;
  transform: translate(-50%, -38px);
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 180px;
}

.node {
  position: relative;
  width: 76px;
  height: 70px;
  border-radius: 50%;
  border: 3px solid var(--c-ink);
  background: var(--c-white);
  box-shadow: 0 6px 0 var(--c-ink);
  cursor: pointer;
  font-size: 1.9rem;
  display: grid;
  place-items: center;
  transition: transform 0.12s;
}

.node:hover {
  transform: translateY(-2px);
}

.node:active {
  transform: translateY(3px);
  box-shadow: 0 2px 0 var(--c-ink);
}

.node.available,
.node.active {
  background: var(--c-primary);
}

.node.next {
  animation: glow 1.8s ease-in-out infinite;
}

.node.completed {
  background: var(--c-secondary);
}

.node.locked {
  background: var(--c-cream-deep);
  border-color: var(--c-locked);
  box-shadow: 0 6px 0 var(--c-locked);
  font-size: 1.4rem;
  filter: grayscale(0.4);
}

.node.soon:not(.locked) {
  border-style: dashed;
  background: var(--c-white);
}

.node.shake {
  animation: shake 0.35s;
}

.check {
  position: absolute;
  right: -6px;
  top: -6px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--c-success);
  color: white;
  font-size: 0.9rem;
  font-weight: 900;
  display: grid;
  place-items: center;
  border: 2px solid var(--c-ink);
}

.label {
  margin-top: 12px;
  text-align: center;
  display: grid;
  gap: 1px;
  line-height: 1.25;
}

.label strong {
  font-size: 0.98rem;
}

.label span {
  font-size: 0.8rem;
  color: var(--c-ink-soft);
}

.game-tag {
  justify-self: center;
  margin-top: 4px;
  background: var(--c-dark) !important;
  color: var(--c-primary) !important;
}

.you-are-here {
  position: absolute;
  top: 22px;
  left: calc(50% + 48px);
  white-space: nowrap;
  font-family: var(--font-display);
  font-size: 0.8rem;
  background: var(--c-ink);
  color: var(--c-primary);
  padding: 2px 8px;
  border-radius: var(--radius-s);
  animation: bob 1.4s ease-in-out infinite;
}

.side {
  border-left: 2px solid var(--c-cream-line);
  padding: 24px 22px 120px;
  display: grid;
  align-content: start;
  gap: 22px;
  background: rgba(246, 240, 220, 0.5);
}

.next {
  background: var(--c-dark);
  color: var(--c-cream);
  border-radius: var(--radius-l);
  padding: 18px 20px 20px;
}

.next h2 {
  font-size: 1.35rem;
}

.next p:not(.eyebrow) {
  color: #cfc8b8;
  font-size: 0.95rem;
}

.stat-block h3 {
  font-size: 1.05rem;
}

.meter {
  height: 12px;
  background: var(--c-cream-line);
  border-radius: 999px;
  overflow: hidden;
  border: 2px solid var(--c-ink);
}

.meter-fill {
  height: 100%;
  background: var(--c-primary);
  transition: width 0.6s;
}

.small {
  font-size: 0.85rem;
  color: var(--c-ink-soft);
  margin-top: 6px;
}

.daily {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: var(--radius-m);
  background: var(--c-white);
  border: 2px dashed var(--c-cream-line);
}

.daily.met {
  border: 2px solid var(--c-primary);
}

.daily span:first-child {
  font-size: 1.5rem;
}

.daily div {
  display: grid;
  font-size: 0.88rem;
}

.badges {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.badges li {
  display: flex;
  gap: 10px;
  align-items: center;
  opacity: 0.55;
}

.badges li.earned {
  opacity: 1;
}

.b-icon {
  width: 40px;
  height: 40px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--c-cream-deep);
  border: 2px solid var(--c-cream-line);
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--c-locked);
}

.earned .b-icon {
  background: var(--c-primary);
  border-color: var(--c-ink);
}

.badges strong {
  display: block;
  font-size: 0.9rem;
}

.badges small {
  color: var(--c-ink-soft);
  font-size: 0.78rem;
}

@keyframes glow {
  50% {
    box-shadow: 0 6px 0 var(--c-ink), 0 0 0 10px rgba(255, 193, 7, 0.3);
  }
}

@keyframes shake {
  25% {
    transform: translateX(-6px);
  }
  75% {
    transform: translateX(6px);
  }
}

@keyframes bob {
  50% {
    transform: translateX(4px);
  }
}

@media (max-width: 960px) {
  .academy {
    grid-template-columns: 1fr;
  }

  .side {
    border-left: none;
    border-top: 2px solid var(--c-cream-line);
  }
}

@media (max-width: 520px) {
  .node-wrap {
    width: 140px;
  }
}
</style>
