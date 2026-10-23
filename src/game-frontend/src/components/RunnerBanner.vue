<script setup lang="ts">
import { useRunner } from '@/stores/runner'

const runner = useRunner()
</script>

<template>
  <div v-if="runner.simulated" class="banner preview" role="status">
    <strong>Preview mode.</strong>
    Results are simulated and your code is <em>not</em> executed. Set <code>VITE_RUNNER_MODE=live</code> to use the real runner.
  </div>
  <div v-else-if="runner.status === 'offline'" class="banner offline" role="alert">
    <strong>Code runner unreachable.</strong>
    Tests, Workshop requests and mining need the backend. {{ runner.lastError }}
    <button class="btn btn-sm" @click="runner.checkHealth()">Retry</button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  padding: 7px 16px;
  font-size: 0.88rem;
  border-bottom: 2px solid var(--c-ink);
}

.preview {
  background: repeating-linear-gradient(-45deg, #ffc107 0 14px, #ffcd38 14px 28px);
  color: var(--c-ink);
}

.preview code {
  background: rgba(255, 255, 255, 0.5);
}

.offline {
  background: var(--c-danger-soft);
  color: #7d1f19;
}
</style>
