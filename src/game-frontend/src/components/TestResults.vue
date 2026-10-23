<script setup lang="ts">
import { computed } from 'vue'
import type { EvaluationResult } from '@/api/types'
import type { MissionTest } from '@/content/missions'

const props = defineProps<{
  tests: MissionTest[]
  result: EvaluationResult | null
  running: boolean
  stale: boolean
}>()

const rows = computed(() => {
  const outcomes = new Map(props.result?.tests.map((t) => [t.id, t]) ?? [])
  const known = props.tests.map((t) => ({ ...t, outcome: outcomes.get(t.id) ?? null }))
  // Anything the runner reports that the lesson didn't describe is still shown.
  const extra = (props.result?.tests ?? [])
    .filter((o) => !props.tests.some((t) => t.id === o.id))
    .map((o) => ({ id: o.id, name: o.name, expects: '', outcome: o }))
  return [...known, ...extra]
})

const summary = computed(() => {
  const r = props.result
  if (!r) return null
  const passed = r.tests.filter((t) => t.passed).length
  return { passed, total: r.tests.length }
})
</script>

<template>
  <section class="results dev-scroll" aria-live="polite">
    <header>
      <h3>Tests</h3>
      <span v-if="running" class="state running">Running…</span>
      <template v-else-if="result">
        <span v-if="result.simulated" class="state sim">Simulated</span>
        <span
          class="state"
          :class="result.status === 'passed' ? 'pass' : 'fail'"
        >
          <template v-if="result.status === 'timeout'">Timed out</template>
          <template v-else-if="result.status === 'error'">Couldn't run</template>
          <template v-else>{{ summary!.passed }} / {{ summary!.total }} passed</template>
        </span>
        <span class="time">{{ result.duration_ms }} ms</span>
      </template>
      <span v-if="stale && result && !running" class="stale">Code changed since this run</span>
    </header>

    <div v-if="result?.error" class="error-box">
      <strong>{{ result.error.type }}<template v-if="result.error.line"> on line {{ result.error.line }}</template></strong>
      <p>{{ result.error.message }}</p>
    </div>

    <ul>
      <li
        v-for="row in rows"
        :key="row.id"
        :class="row.outcome ? (row.outcome.passed ? 'ok' : 'bad') : 'pending'"
      >
        <span class="icon" aria-hidden="true">{{ row.outcome ? (row.outcome.passed ? '✔' : '✘') : '○' }}</span>
        <div>
          <div class="name">{{ row.name }}</div>
          <div v-if="row.outcome && !row.outcome.passed && row.outcome.message" class="msg">
            {{ row.outcome.message }}
          </div>
          <div v-else-if="!row.outcome && row.expects" class="expects">{{ row.expects }}</div>
        </div>
        <span class="sr-only">{{ row.outcome ? (row.outcome.passed ? 'passed' : 'failed') : 'not run' }}</span>
      </li>
    </ul>

    <details v-if="result && (result.stdout || result.stderr)" class="output">
      <summary>Program output</summary>
      <pre v-if="result.stdout">{{ result.stdout }}</pre>
      <pre v-if="result.stderr" class="stderr">{{ result.stderr }}</pre>
    </details>
  </section>
</template>

<style scoped>
.results {
  background: var(--c-panel);
  color: var(--c-panel-text);
  padding: 12px 16px 16px;
  overflow: auto;
}

header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

h3 {
  font-size: 1rem;
  margin: 0;
  color: var(--c-primary);
}

.state {
  font-size: 0.78rem;
  font-weight: 800;
  padding: 0.1em 0.6em;
  border-radius: 999px;
}

.state.pass {
  background: rgba(76, 175, 80, 0.22);
  color: #8be08f;
}

.state.fail {
  background: rgba(229, 83, 75, 0.22);
  color: #ff8a83;
}

.state.running {
  background: rgba(255, 193, 7, 0.18);
  color: var(--c-primary);
}

.state.sim {
  background: rgba(255, 152, 0, 0.2);
  color: var(--c-secondary);
}

.time,
.stale {
  font-size: 0.78rem;
  color: var(--c-panel-muted);
}

.stale {
  font-style: italic;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 2px;
}

li {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 8px;
  padding: 7px 8px;
  border-radius: var(--radius-s);
}

li.bad {
  background: rgba(229, 83, 75, 0.1);
}

.icon {
  font-weight: 800;
  text-align: center;
}

li.ok .icon {
  color: #8be08f;
}

li.bad .icon {
  color: #ff8a83;
}

li.pending .icon {
  color: var(--c-panel-muted);
}

.name {
  font-weight: 700;
  font-size: 0.92rem;
}

.msg {
  font-size: 0.86rem;
  color: #ffc7c2;
  margin-top: 2px;
  font-family: var(--font-mono);
  white-space: pre-wrap;
}

.expects {
  font-size: 0.84rem;
  color: var(--c-panel-muted);
}

.error-box {
  background: rgba(229, 83, 75, 0.14);
  border-left: 3px solid var(--c-danger);
  padding: 8px 12px;
  border-radius: var(--radius-s);
  margin-bottom: 10px;
  font-size: 0.9rem;
}

.error-box p {
  margin: 4px 0 0;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  white-space: pre-wrap;
}

.output {
  margin-top: 10px;
  font-size: 0.85rem;
}

.output summary {
  cursor: pointer;
  color: var(--c-panel-muted);
}

.output pre {
  background: #1a1a1a;
  padding: 8px 10px;
  border-radius: var(--radius-s);
  white-space: pre-wrap;
  margin: 6px 0 0;
}

.output .stderr {
  color: #ff8a83;
}
</style>
