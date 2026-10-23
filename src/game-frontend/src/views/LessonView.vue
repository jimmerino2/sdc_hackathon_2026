<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { missionById } from '@/content/missions'
import { achievementById, levelTitles } from '@/content/achievements'
import { useProgress, type CompletionResult } from '@/stores/progress'
import { useWorkspace } from '@/stores/workspace'
import { useRunner } from '@/stores/runner'
import { useCompanion } from '@/stores/companion'
import { inline } from '@/lib/format'
import CodeEditor from '@/components/CodeEditor.vue'
import TestResults from '@/components/TestResults.vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'

const props = defineProps<{ missionId: string }>()
const router = useRouter()
const progress = useProgress()
const workspace = useWorkspace()
const runner = useRunner()
const companion = useCompanion()

const mission = computed(() => missionById[props.missionId])
const state = computed(() => (mission.value ? progress.missionState(mission.value.id) : 'locked'))
const code = computed({
  get: () => workspace.code(props.missionId),
  set: (v: string) => workspace.setCode(props.missionId, v),
})

const running = ref(false)
const requestError = ref<string | null>(null)
const lastRunCode = ref<string | null>(null)
const celebration = ref<CompletionResult | null>(null)
const hintsShown = computed(() => progress.attemptsFor(props.missionId).hintsShown)
const result = computed(() => runner.evaluations[props.missionId] ?? null)
const stale = computed(() => lastRunCode.value !== null && lastRunCode.value !== code.value)

function guard() {
  const m = mission.value
  if (!m || m.comingSoon || state.value === 'locked') {
    router.replace('/academy')
    return false
  }
  return true
}

onMounted(() => {
  if (!guard()) return
  progress.setActive(props.missionId)
  companion.react('mission_start', { mission: mission.value.title })
})
watch(() => props.missionId, () => {
  lastRunCode.value = null
  requestError.value = null
  if (guard()) progress.setActive(props.missionId)
})

function showHint() {
  const m = mission.value
  if (hintsShown.value >= m.hints.length) return
  progress.recordHint(m.id)
  companion.react(hintsShown.value >= m.hints.length ? 'hints_exhausted' : 'hint')
}

function resetCode() {
  if (!confirm('Restore the starter code? Your current code for this mission will be replaced.')) return
  workspace.reset(props.missionId)
}

async function run(submit: boolean) {
  if (running.value) return
  const m = mission.value
  running.value = true
  requestError.value = null
  companion.react('run_start')
  const source = code.value
  try {
    const r = await runner.evaluate(m.id, source)
    lastRunCode.value = source
    const passed = r.status === 'passed'
    const priorFails = progress.attemptsFor(m.id).failedRuns
    progress.recordRun(m.id, passed)

    if (r.status === 'timeout') {
      companion.react('timeout')
    } else if (r.status === 'error' && r.error) {
      const specific = m.feedback[r.error.category]
      companion.react('code_error', { reason: r.error.message, text: specific })
    } else if (!passed) {
      const failing = r.tests.filter((t) => !t.passed)
      const first = failing[0]
      const specific = first && (m.feedback[first.id] ?? (first.category && m.feedback[first.category]))
      const fails = progress.attemptsFor(m.id).failedRuns
      if (fails >= 3 && fails % 3 === 0) companion.react('tests_failed_repeat', { count: fails })
      else companion.react('tests_failed', { count: failing.length, text: specific || undefined })
    } else if (!submit || progress.isCompleted(m.id)) {
      companion.react('tests_passed', {
        text: progress.isCompleted(m.id) ? undefined : 'All green! Press Submit to lock it in and claim your XP.',
      })
    } else {
      const done = progress.completeMission(m.id, r.run_id)
      if (done.granted) {
        celebration.value = done
        if (priorFails === 0) companion.react('tests_passed_first_try')
        else companion.react('tests_passed_after_fail')
        const last = done.achievements.at(-1)
        if (last) setTimeout(() => companion.react('achievement', { reason: achievementById[last].title }), 2600)
        if (done.levelUp) setTimeout(() => companion.react('level_up', { reason: levelTitles[done.levelUp! - 1] }), 5200)
      }
    }
  } catch (e) {
    requestError.value = e instanceof Error ? e.message : String(e)
    companion.react('runner_offline')
  } finally {
    running.value = false
  }
}

function goNext(id: string) {
  celebration.value = null
  router.push({ name: 'lesson', params: { missionId: id } })
}
</script>

<template>
  <div v-if="mission && !mission.comingSoon" class="lesson">
    <article class="learn">
      <RouterLink to="/academy" class="back">← World map</RouterLink>
      <header>
        <div class="badge" aria-hidden="true">{{ mission.icon }}</div>
        <div>
          <p class="eyebrow">{{ mission.chapter }} · Mission {{ mission.order }}</p>
          <h1>{{ mission.title }}</h1>
          <div class="chips">
            <span class="tag">{{ mission.concept }}</span>
            <span class="tag xp">+{{ mission.xp }} XP</span>
            <span v-if="state === 'completed'" class="tag done">✓ Completed</span>
          </div>
        </div>
      </header>

      <p class="narrative" v-html="inline(mission.narrative)" />

      <section>
        <h2>Learn</h2>
        <template v-for="(b, i) in mission.lesson" :key="i">
          <p v-if="b.kind === 'p'" v-html="inline(b.text)" />
          <figure v-else-if="b.kind === 'code' || b.kind === 'output'" :class="['snippet', b.kind]">
            <figcaption v-if="b.caption">{{ b.caption }}</figcaption>
            <pre><code>{{ b.text }}</code></pre>
          </figure>
          <dl v-else-if="b.kind === 'term'" class="term">
            <dt>{{ b.term }}</dt>
            <dd v-html="inline(b.text)" />
          </dl>
        </template>
      </section>

      <section class="task">
        <h2>Your task</h2>
        <ol>
          <li v-for="(t, i) in mission.task" :key="i" v-html="inline(t)" />
        </ol>
        <p class="tip">Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> in the editor to run the tests.</p>
      </section>

      <section class="hints">
        <h2>Hints</h2>
        <ol v-if="hintsShown > 0">
          <li v-for="(h, i) in mission.hints.slice(0, hintsShown)" :key="i" v-html="inline(h)" />
        </ol>
        <button
          v-if="hintsShown < mission.hints.length"
          class="btn btn-sm"
          @click="showHint"
        >
          💡 {{ hintsShown === 0 ? 'Show a hint' : 'Another hint' }} ({{ hintsShown }}/{{ mission.hints.length }})
        </button>
        <p v-else class="small">That's every hint. Each one maps to a piece of the solution.</p>
      </section>

      <aside class="link">
        <span aria-hidden="true">🗺️</span>
        <p>{{ mission.frontierLink }}</p>
      </aside>
    </article>

    <section class="dev">
      <div class="toolbar">
        <span class="file"><span class="dot" />{{ mission.id }}.py</span>
        <button class="btn btn-ghost btn-sm reset" @click="resetCode">↺ Reset</button>
        <RouterLink v-if="mission.workshop" to="/workshop" class="btn btn-ghost btn-sm reset" :title="'Open this code in the Workshop'">🔧 Workshop</RouterLink>
        <div class="spacer" />
        <button class="btn btn-dark btn-sm" :disabled="running" @click="run(false)">▶ Run tests</button>
        <button class="btn btn-primary btn-sm" :disabled="running" @click="run(true)">
          {{ state === 'completed' ? 'Re-submit' : 'Submit' }}
        </button>
      </div>
      <div class="editor-wrap">
        <CodeEditor
          v-model="code"
          :error-line="!stale ? result?.error?.line ?? null : null"
          :label="`Code for ${mission.title}`"
          @run="run(false)"
        />
      </div>
      <div v-if="requestError" class="req-error" role="alert">
        <strong>Couldn't reach the runner.</strong> {{ requestError }} Your code is saved — try again once the backend is running.
      </div>
      <TestResults class="results" :tests="mission.tests" :result="result" :running="running" :stale="stale" />
    </section>

    <CelebrationOverlay
      v-if="celebration"
      :mission="mission"
      :result="celebration"
      :simulated="runner.simulated"
      @close="celebration = null; router.push('/academy')"
      @next="goNext"
      @frontier="celebration = null; router.push('/frontier')"
    />
  </div>
</template>

<style scoped>
.lesson {
  display: grid;
  grid-template-columns: minmax(340px, 44%) 1fr;
  flex: 1;
  min-height: 0;
}

.learn {
  overflow-y: auto;
  padding: 20px 32px 120px;
  background: var(--c-cream);
}

.back {
  display: inline-block;
  font-weight: 800;
  font-size: 0.9rem;
  text-decoration: none;
  color: var(--c-ink-soft);
  margin-bottom: 14px;
}

.back:hover {
  color: var(--c-ink);
}

header {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}

.badge {
  width: 64px;
  height: 64px;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 2rem;
  background: var(--c-primary);
  border: 3px solid var(--c-ink);
  border-radius: 18px;
  box-shadow: 0 4px 0 var(--c-ink);
}

.eyebrow {
  margin: 0;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.72rem;
  color: var(--c-secondary);
}

h1 {
  font-size: 1.9rem;
  margin: 2px 0 6px;
}

.chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag.xp {
  background: var(--c-primary);
  color: var(--c-ink);
}

.tag.done {
  background: var(--c-success-soft);
  color: #2e7d32;
}

.narrative {
  font-size: 1.05rem;
  border-left: 4px solid var(--c-secondary);
  padding: 4px 0 4px 14px;
  color: var(--c-ink);
  font-style: italic;
}

.learn section {
  margin-top: 26px;
}

h2 {
  font-size: 1.2rem;
  color: var(--c-ink);
  display: flex;
  align-items: center;
  gap: 8px;
}

h2::before {
  content: '';
  width: 10px;
  height: 10px;
  background: var(--c-secondary);
  transform: rotate(45deg);
}

.snippet {
  margin: 0 0 14px;
  border-radius: var(--radius-m);
  overflow: hidden;
}

.snippet figcaption {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 5px 12px 0;
}

.snippet pre {
  margin: 0;
  padding: 10px 14px 12px;
  overflow-x: auto;
  font-size: 0.9rem;
  line-height: 1.55;
}

.snippet.code {
  background: var(--c-dark);
  color: var(--c-panel-text);
}

.snippet.code figcaption {
  color: var(--c-primary);
}

.snippet.output {
  background: var(--c-white);
  border: 2px dashed var(--c-cream-line);
}

.snippet.output figcaption {
  color: var(--c-ink-soft);
}

.term {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 10px;
  margin: 0 0 8px;
  padding: 8px 12px;
  background: var(--c-white);
  border-radius: var(--radius-s);
}

.term dt {
  font-weight: 800;
}

.term dd {
  margin: 0;
}

.task ol {
  padding-left: 0;
  list-style: none;
  counter-reset: t;
  display: grid;
  gap: 8px;
}

.task li {
  counter-increment: t;
  display: flex;
  gap: 10px;
  align-items: baseline;
  background: var(--c-white);
  border: 2px solid var(--c-cream-line);
  border-radius: var(--radius-m);
  padding: 8px 12px;
}

.task li::before {
  content: counter(t);
  flex: none;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--c-primary);
  font-weight: 800;
  font-size: 0.8rem;
}

.tip,
.small {
  font-size: 0.85rem;
  color: var(--c-ink-soft);
}

.hints ol {
  padding-left: 22px;
}

.hints li {
  margin-bottom: 6px;
}

.link {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 26px;
  padding: 12px 16px;
  background: var(--c-dark);
  color: var(--c-cream);
  border-radius: var(--radius-m);
}

.link span {
  font-size: 1.6rem;
}

.link p {
  margin: 0;
}

.dev {
  display: flex;
  flex-direction: column;
  background: var(--c-dark);
  min-height: 0;
  border-left: 3px solid var(--c-ink);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--c-panel);
  border-bottom: 1px solid var(--c-panel-line);
}

.file {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--c-panel-text);
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 6px;
}

.file .dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--c-primary);
}

.reset {
  color: var(--c-panel-muted);
  text-decoration: none;
}

.reset:hover {
  color: var(--c-cream);
  background: rgba(255, 255, 255, 0.06) !important;
}

.spacer {
  flex: 1;
}

.editor-wrap {
  flex: 1;
  min-height: 200px;
  overflow: hidden;
}

.req-error {
  background: rgba(229, 83, 75, 0.18);
  color: #ffc7c2;
  padding: 8px 14px;
  font-size: 0.88rem;
}

.results {
  flex: 0 0 38%;
  min-height: 170px;
  border-top: 1px solid var(--c-panel-line);
}

@media (max-width: 900px) {
  .lesson {
    grid-template-columns: 1fr;
    flex: none;
  }

  .learn {
    padding: 16px 16px 40px;
  }

  .editor-wrap {
    flex: none;
    height: 380px;
  }

  .results {
    flex: none;
  }

  .dev {
    border-left: none;
    border-top: 3px solid var(--c-ink);
    padding-bottom: 100px;
  }

  .term {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
