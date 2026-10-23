<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useProgress } from '@/stores/progress'
import { useRunner } from '@/stores/runner'
import CompanionDock from '@/components/CompanionDock.vue'
import RunnerBanner from '@/components/RunnerBanner.vue'

const route = useRoute()
const progress = useProgress()
const runner = useRunner()

const bare = computed(() => !!route.meta.bare)

onMounted(() => runner.startPolling())

const runnerLabel = computed(() => {
  if (runner.simulated) return 'Preview'
  if (runner.status === 'online') return 'Runner online'
  if (runner.status === 'offline') return 'Runner offline'
  return 'Connecting…'
})
</script>

<template>
  <div class="app" :class="{ bare }">
    <header v-if="!bare" class="topbar">
      <RouterLink to="/academy" class="brand" aria-label="The Coding Frontier — Academy">
        <span class="brand-mark" aria-hidden="true" />
        <span class="brand-text">The Coding <b>Frontier</b></span>
      </RouterLink>

      <nav class="tabs" aria-label="Main">
        <RouterLink to="/academy" class="tab" :class="{ on: route.path.startsWith('/academy') }">
          <span aria-hidden="true">📜</span> Academy
        </RouterLink>
        <RouterLink to="/frontier" class="tab" active-class="on"><span aria-hidden="true">🏕️</span> Frontier</RouterLink>
        <RouterLink to="/workshop" class="tab" active-class="on"><span aria-hidden="true">🔧</span> Workshop</RouterLink>
      </nav>

      <div class="meta">
        <span class="runner" :class="runner.simulated ? 'sim' : runner.status" :title="runner.isolation ? `Isolation: ${runner.isolation}` : runner.lastError ?? ''">
          <span class="dot" aria-hidden="true" />{{ runnerLabel }}
        </span>
        <div class="xp" :title="`${progress.xp} XP total`">
          <span class="lvl">Lv {{ progress.level }}</span>
          <div class="xp-col">
            <span class="xp-title">{{ progress.levelTitle }}</span>
            <div class="bar" role="progressbar" :aria-valuenow="Math.round(progress.levelProgress.pct)" aria-valuemin="0" aria-valuemax="100" aria-label="Progress to next level">
              <div class="fill" :style="{ width: progress.levelProgress.pct + '%' }" />
            </div>
          </div>
          <span class="xp-num">{{ progress.xp }} XP</span>
        </div>
      </div>
    </header>
    <RunnerBanner v-if="!bare" />

    <main class="main">
      <RouterView />
    </main>

    <CompanionDock v-if="progress.profile" />
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app.bare {
  height: auto;
  min-height: 100vh;
}

.topbar {
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 18px;
  background: var(--c-dark);
  color: var(--c-cream);
  border-bottom: 3px solid var(--c-primary);
  position: sticky;
  top: 0;
  z-index: 30;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  font-family: var(--font-display);
  font-size: 1.15rem;
  white-space: nowrap;
}

.brand b {
  color: var(--c-primary);
}

.brand-mark {
  width: 22px;
  height: 22px;
  background: var(--c-primary);
  box-shadow: inset -6px -6px 0 var(--c-secondary);
  transform: rotate(45deg) scale(0.8);
}

.tabs {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-m);
  text-decoration: none;
  font-weight: 800;
  color: #cfc8b8;
  transition: background 0.15s, color 0.15s;
}

.tab:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--c-cream);
}

.tab.on {
  background: var(--c-primary);
  color: var(--c-ink);
}

.meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 18px;
}

.runner {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #b8b1a2;
  white-space: nowrap;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #777;
}

.runner.online .dot {
  background: var(--c-success);
  box-shadow: 0 0 8px var(--c-success);
}

.runner.offline .dot {
  background: var(--c-danger);
}

.runner.sim .dot {
  background: var(--c-secondary);
}

.xp {
  display: flex;
  align-items: center;
  gap: 10px;
}

.lvl {
  white-space: nowrap;
  font-family: var(--font-display);
  background: var(--c-secondary);
  color: var(--c-ink);
  padding: 2px 8px;
  border-radius: var(--radius-s);
  font-size: 0.95rem;
}

.xp-col {
  display: grid;
  gap: 3px;
}

.xp-title {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #b8b1a2;
}

.bar {
  width: 120px;
  height: 8px;
  background: #3a3a3a;
  border-radius: 999px;
  overflow: hidden;
}

.fill {
  height: 100%;
  background: linear-gradient(90deg, var(--c-secondary), var(--c-primary));
  transition: width 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.xp-num {
  white-space: nowrap;
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--c-primary);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}

@media (max-width: 900px) {
  .brand-text,
  .xp-col,
  .runner {
    display: none;
  }

  .topbar {
    gap: 10px;
    padding: 0 10px;
  }

  .tab {
    padding: 6px 9px;
    font-size: 0.9rem;
  }
}

@media (max-width: 520px) {
  .tab span {
    display: none;
  }
}
</style>
