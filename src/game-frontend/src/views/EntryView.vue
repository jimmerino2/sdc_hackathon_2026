<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FrontierEngine } from '@/game/engine'
import { useProgress } from '@/stores/progress'
import { useCompanion } from '@/stores/companion'

const canvas = ref<HTMLCanvasElement>()
const router = useRouter()
const progress = useProgress()
const companion = useCompanion()
let engine: FrontierEngine | null = null

onMounted(() => {
  engine = new FrontierEngine(canvas.value!, {}, { interactive: false })
})
onBeforeUnmount(() => engine?.destroy())

function begin() {
  if (progress.profile) {
    companion.react('welcome_back', { name: progress.profile.name })
    router.push('/academy')
  } else {
    router.push('/start')
  }
}
</script>

<template>
  <div class="entry">
    <canvas ref="canvas" class="world" aria-hidden="true" />
    <div class="card">
      <p class="eyebrow">A coding adventure</p>
      <h1>The Coding <span>Frontier</span></h1>
      <p class="lede">
        Learn Python from zero. Write a real FastAPI server. Watch it decide what happens in a world you can walk around in.
      </p>
      <ol class="loop" aria-label="How it works">
        <li>Learn</li>
        <li>Write code</li>
        <li>Run tests</li>
        <li>See it in the world</li>
        <li>Unlock more</li>
      </ol>
      <button class="btn btn-primary big" @click="begin">
        {{ progress.profile ? `Continue as ${progress.profile.name}` : 'Begin the expedition' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.entry {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  overflow: hidden;
  background: var(--c-dark);
}

.world {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.85;
}

.card {
  position: relative;
  max-width: 560px;
  text-align: center;
  background: rgba(255, 253, 245, 0.96);
  border: 3px solid var(--c-ink);
  border-radius: var(--radius-l);
  box-shadow: 0 6px 0 var(--c-ink), var(--shadow-float);
  padding: 32px 32px 28px;
}

.eyebrow {
  margin: 0 0 6px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.78rem;
  color: var(--c-secondary);
}

h1 {
  font-size: clamp(2.2rem, 6vw, 3.4rem);
  margin-bottom: 12px;
}

h1 span {
  color: var(--c-secondary);
  text-shadow: 3px 3px 0 var(--c-ink);
}

.lede {
  font-size: 1.08rem;
  color: var(--c-ink-soft);
}

.loop {
  list-style: none;
  padding: 0;
  margin: 18px 0 24px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  counter-reset: step;
}

.loop li {
  font-weight: 800;
  font-size: 0.85rem;
  background: var(--c-cream-deep);
  border-radius: 999px;
  padding: 4px 12px 4px 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  counter-increment: step;
}

.loop li::before {
  content: counter(step);
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--c-primary);
  font-size: 0.75rem;
}

.big {
  font-size: 1.15rem;
  padding: 0.8em 1.6em;
}
</style>
