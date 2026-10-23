<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProgress } from '@/stores/progress'
import { useCompanion } from '@/stores/companion'
import WickSprite from '@/components/WickSprite.vue'

const router = useRouter()
const progress = useProgress()
const companion = useCompanion()

const step = ref(0)
const name = ref('')

const steps = computed(() => [
  {
    mood: 'curious' as const,
    title: 'Who goes there?',
    text: "I'm Wick — lantern, guide, critic. Every expedition needs a name on the roster. What's yours?",
  },
  {
    mood: 'happy' as const,
    title: `Welcome to camp, ${name.value.trim() || 'Explorer'}.`,
    text: "Out here, nothing works by magic. The old mining rig only moves when a server tells it what's allowed — and you're going to write that server.",
  },
  {
    mood: 'smug' as const,
    title: 'Here is how it works',
    text: "You've never written code before? Perfect, neither had anyone else once. We start tiny.",
  },
])

function next() {
  if (step.value === 0 && !name.value.trim()) return
  if (step.value < steps.value.length - 1) {
    step.value++
    return
  }
  progress.createProfile(name.value)
  companion.react('welcome', {})
  router.push('/academy')
}
</script>

<template>
  <div class="onboarding">
    <div class="panel">
      <div class="wick-col">
        <WickSprite :mood="steps[step].mood" :size="120" />
      </div>
      <div class="content">
        <p class="progress" :aria-label="`Step ${step + 1} of 3`">
          <span v-for="i in 3" :key="i" :class="{ on: i - 1 <= step }" />
        </p>
        <h1>{{ steps[step].title }}</h1>
        <p class="text">{{ steps[step].text }}</p>

        <form v-if="step === 0" @submit.prevent="next">
          <label for="name">Your explorer name</label>
          <input id="name" v-model="name" maxlength="24" autocomplete="nickname" placeholder="e.g. Robin" autofocus />
        </form>

        <ul v-else-if="step === 2" class="pillars">
          <li>
            <span class="ic">📜</span>
            <div><strong>Academy</strong> — short lessons. You write real Python and automated tests check it.</div>
          </li>
          <li>
            <span class="ic">🏕️</span>
            <div><strong>Frontier</strong> — walk the world. When you mine, the game calls <em>your</em> code.</div>
          </li>
          <li>
            <span class="ic">🔧</span>
            <div><strong>Workshop</strong> — send requests to your server and see exactly what comes back.</div>
          </li>
        </ul>

        <div class="actions">
          <button v-if="step > 0" class="btn btn-ghost" @click="step--">Back</button>
          <button class="btn btn-primary" :disabled="step === 0 && !name.trim()" @click="next">
            {{ step === steps.length - 1 ? 'Open the Academy' : 'Continue' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.onboarding {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 193, 7, 0.18), transparent 40%),
    radial-gradient(circle at 80% 90%, rgba(255, 152, 0, 0.14), transparent 40%),
    var(--c-cream);
}

.panel {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 24px;
  max-width: 720px;
  width: 100%;
  background: var(--c-white);
  border: 3px solid var(--c-ink);
  border-radius: var(--radius-l);
  box-shadow: 0 6px 0 var(--c-ink);
  padding: 32px;
}

.wick-col {
  display: grid;
  place-items: center;
  background: var(--c-dark);
  border-radius: var(--radius-m);
}

.progress {
  display: flex;
  gap: 6px;
  margin: 0 0 14px;
}

.progress span {
  width: 28px;
  height: 6px;
  border-radius: 3px;
  background: var(--c-cream-line);
}

.progress span.on {
  background: var(--c-secondary);
}

h1 {
  font-size: 1.9rem;
}

.text {
  font-size: 1.05rem;
  color: var(--c-ink-soft);
}

label {
  display: block;
  font-weight: 800;
  margin-bottom: 6px;
}

input {
  width: 100%;
  font: inherit;
  font-size: 1.1rem;
  padding: 10px 14px;
  border: 2px solid var(--c-ink);
  border-radius: var(--radius-m);
  background: var(--c-cream);
}

input:focus {
  outline: none;
  border-color: var(--c-secondary);
  box-shadow: 0 0 0 3px rgba(255, 152, 0, 0.3);
}

.pillars {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 10px;
}

.pillars li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: var(--c-cream);
  border-radius: var(--radius-m);
  padding: 10px 14px;
}

.ic {
  font-size: 1.5rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}

@media (max-width: 640px) {
  .panel {
    grid-template-columns: 1fr;
    padding: 20px;
  }

  .wick-col {
    padding: 10px;
  }
}
</style>
