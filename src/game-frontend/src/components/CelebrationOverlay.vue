<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { CompletionResult } from '@/stores/progress'
import type { Mission } from '@/content/missions'
import { missionById } from '@/content/missions'
import { achievementById } from '@/content/achievements'
import WickSprite from './WickSprite.vue'

const props = defineProps<{ mission: Mission; result: CompletionResult; simulated: boolean }>()
defineEmits<{ close: []; next: [id: string]; frontier: [] }>()

const shownXp = ref(0)
const primary = ref<HTMLButtonElement>()

onMounted(() => {
  primary.value?.focus()
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduced) {
    shownXp.value = props.result.xp
    return
  }
  const start = performance.now()
  const tick = (now: number) => {
    const p = Math.min(1, (now - start) / 900)
    shownXp.value = Math.round(props.result.xp * (1 - Math.pow(1 - p, 3)))
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})
</script>

<template>
  <div class="backdrop" role="dialog" aria-modal="true" aria-labelledby="celebrate-title" @keydown.esc="$emit('close')">
    <div class="card">
      <div class="rays" aria-hidden="true" />
      <WickSprite mood="proud" :size="96" class="sprite" />
      <p class="eyebrow">Mission complete</p>
      <h2 id="celebrate-title">{{ mission.title }}</h2>
      <p v-if="simulated" class="sim">Preview mode — no code was executed. This progress is kept separate.</p>

      <div class="xp">
        <span class="plus">+{{ shownXp }}</span>
        <span>XP</span>
      </div>
      <p v-if="result.levelUp" class="level">Level {{ result.levelUp }} reached!</p>

      <ul v-if="result.achievements.length" class="badges">
        <li v-for="a in result.achievements" :key="a">
          <span class="badge-icon">{{ achievementById[a].icon }}</span>
          <div>
            <strong>{{ achievementById[a].title }}</strong>
            <small>{{ achievementById[a].description }}</small>
          </div>
        </li>
      </ul>

      <div v-if="result.unlocked.length" class="unlocked">
        <span class="tag">Unlocked</span>
        <span v-for="u in result.unlocked" :key="u">{{ missionById[u].icon }} {{ missionById[u].title }}</span>
      </div>

      <div class="actions">
        <button v-if="mission.game" ref="primary" class="btn btn-primary" @click="$emit('frontier')">
          Try it in the Frontier →
        </button>
        <button
          v-else-if="result.unlocked.length"
          ref="primary"
          class="btn btn-primary"
          @click="$emit('next', result.unlocked[0])"
        >
          Next mission →
        </button>
        <button class="btn" @click="$emit('close')">Back to the map</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: rgba(30, 30, 30, 0.6);
  padding: 16px;
  animation: fade 0.2s ease-out;
}

.card {
  position: relative;
  overflow: hidden;
  width: min(460px, 100%);
  background: var(--c-cream);
  border: 3px solid var(--c-ink);
  border-radius: var(--radius-l);
  box-shadow: 0 6px 0 var(--c-ink), var(--shadow-float);
  padding: 28px 28px 24px;
  text-align: center;
  animation: rise 0.35s cubic-bezier(0.2, 1.4, 0.4, 1);
}

.rays {
  position: absolute;
  inset: -50%;
  background: repeating-conic-gradient(from 0deg, rgba(255, 193, 7, 0.16) 0 10deg, transparent 10deg 20deg);
  animation: spin 18s linear infinite;
  pointer-events: none;
}

.card > *:not(.rays) {
  position: relative;
}

.sprite {
  margin: 0 auto 4px;
}

.eyebrow {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  color: var(--c-secondary);
  margin: 0;
}

h2 {
  font-size: 1.9rem;
  margin: 4px 0 8px;
}

.sim {
  font-size: 0.85rem;
  background: rgba(255, 152, 0, 0.15);
  border-radius: var(--radius-s);
  padding: 6px 10px;
}

.xp {
  font-family: var(--font-display);
  font-size: 1.4rem;
  display: flex;
  justify-content: center;
  align-items: baseline;
  gap: 6px;
}

.plus {
  font-size: 3rem;
  color: var(--c-secondary);
  text-shadow: 2px 2px 0 var(--c-ink);
}

.level {
  font-weight: 800;
  color: var(--c-ink);
}

.badges {
  list-style: none;
  padding: 0;
  margin: 12px 0;
  display: grid;
  gap: 8px;
  text-align: left;
}

.badges li {
  display: flex;
  gap: 12px;
  align-items: center;
  background: var(--c-white);
  border: 2px solid var(--c-primary);
  border-radius: var(--radius-m);
  padding: 8px 12px;
  animation: rise 0.4s 0.3s both;
}

.badge-icon {
  font-size: 1.8rem;
}

.badges small {
  display: block;
  color: var(--c-ink-soft);
}

.unlocked {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  margin: 10px 0;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 16px;
}

@keyframes rise {
  from {
    transform: translateY(20px) scale(0.96);
    opacity: 0;
  }
}

@keyframes fade {
  from {
    opacity: 0;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
