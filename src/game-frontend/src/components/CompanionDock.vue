<script setup lang="ts">
import { ref, watch } from 'vue'
import { useCompanion } from '@/stores/companion'
import WickSprite from './WickSprite.vue'

const companion = useCompanion()
const pop = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

// Re-trigger the bubble animation and auto-hide after a reading-friendly delay.
watch(
  () => companion.seq,
  () => {
    pop.value = false
    requestAnimationFrame(() => (pop.value = true))
    if (hideTimer) clearTimeout(hideTimer)
    hideTimer = setTimeout(() => companion.dismiss(), Math.max(6000, companion.text.length * 70))
  },
)
</script>

<template>
  <aside class="dock" aria-label="Wick, your companion">
    <transition name="bubble">
      <div v-if="companion.open" class="bubble" :class="{ pop }" role="status" aria-live="polite">
        <p>{{ companion.text }}</p>
        <button class="close" aria-label="Dismiss" @click="companion.dismiss()">×</button>
      </div>
    </transition>
    <button
      class="sprite-btn"
      :aria-label="companion.open ? 'Hide Wick' : 'Show Wick\'s last message'"
      @click="companion.open = !companion.open"
    >
      <WickSprite :mood="companion.mood" :size="72" />
    </button>
  </aside>
</template>

<style scoped>
.dock {
  position: fixed;
  right: 18px;
  bottom: 14px;
  z-index: 40;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  pointer-events: none;
}

.dock > * {
  pointer-events: auto;
}

.sprite-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.bubble {
  position: relative;
  max-width: min(340px, calc(100vw - 120px));
  background: var(--c-cream);
  color: var(--c-ink);
  border: 2px solid var(--c-ink);
  border-radius: var(--radius-l) var(--radius-l) 4px var(--radius-l);
  padding: 12px 32px 12px 14px;
  box-shadow: var(--shadow-pop), var(--shadow-float);
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 30px;
}

.bubble p {
  margin: 0;
}

.bubble.pop {
  animation: pop 0.25s ease-out;
}

.close {
  position: absolute;
  top: 4px;
  right: 6px;
  border: none;
  background: none;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  color: var(--c-ink-soft);
}

.bubble-enter-active,
.bubble-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.bubble-enter-from,
.bubble-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@keyframes pop {
  0% {
    transform: scale(0.94);
  }
  60% {
    transform: scale(1.02);
  }
}

@media (max-width: 640px) {
  .dock {
    right: 8px;
    bottom: 8px;
  }
}
</style>
