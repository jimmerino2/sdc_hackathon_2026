<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { FrontierEngine } from '@/game/engine'
import type { WorldObject } from '@/game/world'
import { GAME_MISSION_ID, missionById } from '@/content/missions'
import { achievementById } from '@/content/achievements'
import { objectLore } from '@/content/dialogue'
import { useGame } from '@/stores/game'
import { useProgress } from '@/stores/progress'
import { useWorkspace } from '@/stores/workspace'
import { useCompanion } from '@/stores/companion'
import { useRunner } from '@/stores/runner'
import { statusClass, STATUS_TEXT } from '@/lib/format'
import JsonView from '@/components/JsonView.vue'

const canvas = ref<HTMLCanvasElement>()
const game = useGame()
const progress = useProgress()
const workspace = useWorkspace()
const companion = useCompanion()
const runner = useRunner()

let engine: FrontierEngine | null = null
const target = ref<WorldObject | null>(null)
const logOpen = ref(true)
const npcLine = ref<string | null>(null)

const mineMission = missionById[GAME_MISSION_ID]
const mineState = computed(() => progress.missionState(GAME_MISSION_ID))
const inventory = computed(() => game.state?.inventory ?? {})
const hasPickaxe = computed(() => (inventory.value.stone_pickaxe ?? 0) > 0)
const latest = computed(() => game.actions[0] ?? null)

const objective = computed(() => {
  if (mineState.value === 'locked')
    return { title: 'Explore the camp', text: `The mining rig needs a server. Reach "${mineMission.title}" in the Academy to write one.` }
  if (!hasPickaxe.value) return { title: 'Gear up', text: 'Grab the pickaxe from the supply crate near the campfire.' }
  if (mineState.value !== 'completed')
    return { title: 'Test your route', text: 'Mine copper on the ridge. Every swing calls your POST /mine route — even unfinished.' }
  return { title: 'Copper run', text: 'Your route is live. Mine the ridge, then check the Field Log to see each request.' }
})

const prompt = computed(() => {
  const o = target.value
  if (!o) return null
  const verb = { mine: 'Mine', pickup: 'Search', talk: 'Talk to', inspect: 'Inspect' }[o.action ?? 'inspect']
  const sub =
    o.action === 'mine' ? 'calls your POST /mine' : o.action === 'pickup' && hasPickaxe.value ? 'already searched' : null
  return { text: `${verb} ${o.label}`, sub }
})

const slots = computed(() => {
  const items = [
    { id: 'stone_pickaxe', icon: '⛏️', label: 'Stone pickaxe' },
    { id: 'copper', icon: '🟧', label: 'Copper ore' },
    { id: 'tin', icon: '⬜', label: 'Tin ore' },
  ]
  const filled = items.filter((i) => (inventory.value[i.id] ?? 0) > 0)
  return Array.from({ length: 6 }, (_, i) => {
    const it = filled[i]
    return it ? { ...it, qty: inventory.value[it.id], equipped: game.state?.equipped === it.id } : null
  })
})

onMounted(async () => {
  engine = new FrontierEngine(
    canvas.value!,
    {
      onInteract: interact,
      onTargetChange: (o) => (target.value = o),
    },
    { interactive: true },
  )
  canvas.value!.focus({ preventScroll: true })
  companion.react('enter_frontier')
  await game.load()
})

onBeforeUnmount(() => engine?.destroy())

watch(
  () => game.state,
  (s) => engine?.setView({ nodes: s?.nodes ?? {}, hasPickaxe: (s?.inventory.stone_pickaxe ?? 0) > 0 }),
  { deep: true, immediate: true },
)

function marloSays() {
  if (mineState.value === 'locked')
    return "Copper's up on the ridge, but the rig won't swing without a server telling it what's allowed. Academy first."
  if (mineState.value !== 'completed')
    return "Grab the pickaxe from the crate, then try a deposit. If your route's wrong, the rock will let you know."
  return 'That route of yours holds up. Bring me enough copper and we\'ll talk about firing up the smelter.'
}

async function interact(o: WorldObject) {
  if (game.busy) return
  npcLine.value = null

  if (o.action === 'talk') {
    npcLine.value = marloSays()
    return
  }
  if (o.action === 'inspect') {
    companion.react('explore', { reason: objectLore[o.kind] ?? o.label })
    return
  }
  if (!game.state) {
    companion.react('runner_offline')
    engine?.feedback(o.id, 'fail', 'Simulator offline')
    return
  }

  if (o.action === 'pickup') {
    if (hasPickaxe.value) {
      engine?.feedback(o.id, 'info', 'Empty')
      return
    }
    try {
      const r = await game.act('pickup', o.id)
      engine?.feedback(o.id, r.accepted ? 'success' : 'fail', r.accepted ? '+1 pickaxe' : r.reason)
      if (r.accepted) companion.react('pickup')
    } catch {
      companion.react('runner_offline')
    }
    return
  }

  if (o.action === 'mine') {
    if (mineState.value === 'locked') {
      engine?.feedback(o.id, 'fail', 'No route yet')
      companion.react('mine_locked')
      return
    }
    engine?.startSwing()
    try {
      const r = await game.act('mine', o.id, {
        missionId: GAME_MISSION_ID,
        code: workspace.code(GAME_MISSION_ID),
      })
      logOpen.value = true
      if (r.accepted) {
        const qty = r.effects.find((e) => e.type === 'inventory_add')?.qty ?? 1
        engine?.feedback(o.id, 'success', `+${qty} copper`)
        companion.react('mine_success')
        if (r.reward?.granted) progress.addXp(r.reward.xp)
        if (!r.simulated && progress.grantAchievement('first-ore')) {
          setTimeout(() => companion.react('achievement', { reason: achievementById['first-ore'].title }), 2200)
        }
        return
      }
      const status = r.trace?.response?.status_code
      engine?.feedback(o.id, 'fail', status ? `${status}` : 'Failed')
      switch (r.code) {
        case 'REJECTED_BY_ROUTE':
          companion.react('mine_rejected', { reason: r.reason })
          break
        case 'ROUTE_ERROR':
          companion.react('mine_error', { reason: r.trace?.error?.message ?? r.reason })
          break
        case 'INVALID_RESPONSE':
          companion.react('mine_invalid', { reason: r.reason })
          break
        case 'NODE_DEPLETED':
          companion.react('node_depleted')
          break
        case 'MISSION_LOCKED':
          companion.react('mine_locked')
          break
        default:
          companion.react('mine_invalid', { reason: r.reason })
      }
    } catch {
      engine?.feedback(o.id, 'fail', 'Runner offline')
      companion.react('runner_offline')
    }
  }
}

const verdict = (code: string, accepted: boolean) =>
  accepted ? 'Accepted' : ({ REJECTED_BY_ROUTE: 'Refused by your route', ROUTE_ERROR: 'Route crashed', INVALID_RESPONSE: 'Rejected by simulator', NODE_DEPLETED: 'Deposit empty', MISSION_LOCKED: 'Mission locked', NOT_ALLOWED: 'Not allowed', OK: 'Accepted' } as Record<string, string>)[code] ?? code
</script>

<template>
  <div class="frontier">
    <canvas ref="canvas" class="world" tabindex="0" aria-label="The Frontier. Move with WASD or arrow keys, or click a tile. Press E to interact." />

    <div v-if="game.loadError && !game.state" class="hud-banner" role="alert">
      World state unavailable — the trusted simulator isn't reachable. You can look around; actions need the backend.
      <button class="btn btn-sm" @click="game.load()">Retry</button>
    </div>

    <section class="objective">
      <p class="eyebrow">Objective</p>
      <h2>{{ objective.title }}</h2>
      <p>{{ objective.text }}</p>
      <RouterLink
        v-if="mineState !== 'locked' && mineState !== 'completed'"
        :to="{ name: 'lesson', params: { missionId: GAME_MISSION_ID } }"
        class="btn btn-sm btn-primary"
      >
        Edit my /mine route
      </RouterLink>
    </section>

    <div class="controls" aria-hidden="true">
      <span><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> / click to move</span>
      <span><kbd>E</kbd> interact</span>
    </div>

    <transition name="fade">
      <div v-if="npcLine" class="npc-box" role="dialog" aria-label="Surveyor Marlo">
        <strong>Surveyor Marlo</strong>
        <p>{{ npcLine }}</p>
        <button class="btn btn-sm" @click="npcLine = null">Got it</button>
      </div>
    </transition>

    <div class="bottom">
      <transition name="fade">
        <div v-if="prompt" class="prompt">
          <kbd>E</kbd>
          <span>{{ prompt.text }}</span>
          <small v-if="prompt.sub">{{ prompt.sub }}</small>
          <span v-if="game.busy" class="busy">…</span>
        </div>
      </transition>
      <ul class="hotbar" aria-label="Inventory">
        <li v-for="(s, i) in slots" :key="i" :class="{ filled: s, equipped: s?.equipped }" :title="s?.label">
          <template v-if="s">
            <span class="item" aria-hidden="true">{{ s.icon }}</span>
            <span class="qty">{{ s.qty }}</span>
            <span class="sr-only">{{ s.label }}: {{ s.qty }}</span>
          </template>
        </li>
      </ul>
    </div>

    <aside class="log" :class="{ closed: !logOpen }" aria-label="Field log">
      <button class="log-head" :aria-expanded="logOpen" @click="logOpen = !logOpen">
        <span>📓 Field Log</span>
        <span class="count">{{ game.actions.length }}</span>
        <span class="chev" aria-hidden="true">{{ logOpen ? '▾' : '▸' }}</span>
      </button>
      <div v-if="logOpen" class="log-body dev-scroll">
        <p v-if="!latest" class="empty">
          Actions you take in the world appear here — including the exact request the game sent to your route and what it answered.
        </p>
        <template v-else>
          <div class="entry latest">
            <div class="verdict" :class="latest.accepted ? 'ok' : 'bad'">
              {{ verdict(latest.code, latest.accepted) }}
              <span v-if="latest.simulated" class="sim">simulated</span>
            </div>
            <p class="reason">{{ latest.reason }}</p>
            <template v-if="latest.trace">
              <h4>Request <span class="mono">{{ latest.trace.request.method }} {{ latest.trace.request.path }}</span></h4>
              <JsonView :value="latest.trace.request.body" />
              <h4>
                Response
                <span v-if="latest.trace.response" class="status-code" :class="statusClass(latest.trace.response.status_code)">
                  {{ latest.trace.response.status_code }} {{ STATUS_TEXT[latest.trace.response.status_code] ?? '' }}
                </span>
                <span v-else class="status-code status-err">no response</span>
              </h4>
              <JsonView v-if="latest.trace.response" :value="latest.trace.response.body" />
              <pre v-if="latest.trace.error" class="err">{{ latest.trace.error.type }}: {{ latest.trace.error.message }}</pre>
              <pre v-if="latest.trace.logs" class="logs">{{ latest.trace.logs }}</pre>
            </template>
            <div v-if="latest.effects.length" class="effects">
              <h4>World changes</h4>
              <ul>
                <li v-for="(e, i) in latest.effects" :key="i">{{ e.type }} {{ e.item ?? e.node_id ?? '' }} {{ e.qty ? '×' + e.qty : '' }}</li>
              </ul>
            </div>
            <RouterLink v-if="latest.command === 'mine'" to="/workshop" class="btn btn-dark btn-sm">Replay in Workshop →</RouterLink>
          </div>
          <ul class="older">
            <li v-for="a in game.actions.slice(1, 8)" :key="a.action_id">
              <span :class="a.accepted ? 'ok' : 'bad'">{{ a.accepted ? '✔' : '✘' }}</span>
              {{ a.command }} {{ a.target }}
              <span v-if="a.trace?.response" class="status-code" :class="statusClass(a.trace.response.status_code)">{{ a.trace.response.status_code }}</span>
            </li>
          </ul>
        </template>
      </div>
    </aside>

    <p v-if="runner.simulated" class="sim-note">Preview mode: world responses are simulated.</p>
  </div>
</template>

<style scoped>
.frontier {
  position: relative;
  flex: 1;
  min-height: 480px;
  background: var(--c-dark);
  overflow: hidden;
}

.world {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  outline: none;
}

.hud-banner {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--c-danger-soft);
  color: #7d1f19;
  padding: 8px 14px;
  border-radius: var(--radius-m);
  border: 2px solid var(--c-ink);
  font-size: 0.88rem;
  display: flex;
  gap: 10px;
  align-items: center;
  max-width: calc(100% - 32px);
  z-index: 5;
}

.objective {
  position: absolute;
  top: 16px;
  left: 16px;
  width: min(300px, calc(100% - 32px));
  background: rgba(255, 253, 245, 0.95);
  border: 2px solid var(--c-ink);
  border-radius: var(--radius-m);
  box-shadow: var(--shadow-pop);
  padding: 12px 14px;
}

.objective .eyebrow {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--c-secondary);
}

.objective h2 {
  font-size: 1.15rem;
  margin: 2px 0 4px;
}

.objective p {
  font-size: 0.88rem;
  margin-bottom: 8px;
}

.controls {
  position: absolute;
  left: 16px;
  bottom: 16px;
  display: grid;
  gap: 4px;
  color: #cfc8b8;
  font-size: 0.8rem;
}

.controls kbd {
  margin-right: 2px;
  color: var(--c-cream);
}

.npc-box {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: min(420px, calc(100% - 32px));
  background: var(--c-cream);
  border: 3px solid var(--c-ink);
  border-radius: var(--radius-m);
  box-shadow: 0 4px 0 var(--c-ink);
  padding: 12px 16px;
  z-index: 6;
}

.npc-box strong {
  font-family: var(--font-display);
  color: #4b7bb5;
}

.npc-box p {
  margin: 4px 0 10px;
}

.bottom {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.prompt {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 30, 30, 0.9);
  color: var(--c-cream);
  border: 2px solid var(--c-primary);
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 800;
  white-space: nowrap;
}

.prompt kbd {
  background: var(--c-primary);
  color: var(--c-ink);
  border-color: var(--c-ink);
}

.prompt small {
  font-weight: 600;
  color: var(--c-primary);
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.busy {
  animation: blink 0.6s steps(2) infinite;
}

.hotbar {
  list-style: none;
  display: flex;
  gap: 4px;
  padding: 5px;
  margin: 0;
  background: rgba(30, 30, 30, 0.88);
  border: 2px solid #000;
  border-radius: var(--radius-m);
}

.hotbar li {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: #3a3530;
  box-shadow: inset 0 0 0 2px #2a2622, inset 0 3px 0 rgba(255, 255, 255, 0.05);
  display: grid;
  place-items: center;
}

.hotbar li.equipped {
  box-shadow: inset 0 0 0 2px var(--c-primary);
}

.item {
  font-size: 1.5rem;
}

.qty {
  position: absolute;
  right: 4px;
  bottom: 1px;
  font-family: var(--font-display);
  color: var(--c-cream);
  text-shadow: 1px 1px 0 #000;
  font-size: 0.9rem;
}

.log {
  position: absolute;
  top: 16px;
  right: 16px;
  width: min(360px, calc(100% - 32px));
  max-height: calc(100% - 140px);
  display: flex;
  flex-direction: column;
  background: rgba(38, 38, 38, 0.96);
  color: var(--c-panel-text);
  border: 2px solid #000;
  border-radius: var(--radius-m);
  box-shadow: var(--shadow-float);
  overflow: hidden;
}

.log-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--c-panel-2);
  border: none;
  cursor: pointer;
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--c-primary);
  text-align: left;
}

.count {
  font-family: var(--font-body);
  font-size: 0.75rem;
  background: #444;
  color: var(--c-cream);
  padding: 0 7px;
  border-radius: 999px;
}

.chev {
  margin-left: auto;
}

.log-body {
  overflow-y: auto;
  padding: 12px 14px 14px;
}

.empty {
  font-size: 0.88rem;
  color: var(--c-panel-muted);
}

.verdict {
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}

.verdict.ok {
  color: #8be08f;
}

.verdict.bad {
  color: #ff8a83;
}

.verdict .sim {
  font-size: 0.7rem;
  background: rgba(255, 152, 0, 0.2);
  color: var(--c-secondary);
  padding: 0 6px;
  border-radius: 999px;
}

.reason {
  font-size: 0.88rem;
  margin: 4px 0 8px;
}

h4 {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--c-panel-muted);
  margin: 10px 0 5px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.mono {
  font-family: var(--font-mono);
  text-transform: none;
  letter-spacing: 0;
  color: var(--c-primary);
}

.err,
.logs {
  margin: 6px 0 0;
  padding: 8px 10px;
  border-radius: var(--radius-s);
  font-size: 0.8rem;
  white-space: pre-wrap;
  background: #1a1a1a;
}

.err {
  color: #ff8a83;
}

.effects ul {
  margin: 0;
  padding-left: 18px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.latest .btn {
  margin-top: 12px;
}

.older {
  list-style: none;
  padding: 10px 0 0;
  margin: 12px 0 0;
  border-top: 1px solid var(--c-panel-line);
  display: grid;
  gap: 4px;
  font-size: 0.82rem;
  font-family: var(--font-mono);
}

.older .ok {
  color: #8be08f;
}

.older .bad {
  color: #ff8a83;
}

.sim-note {
  position: absolute;
  bottom: 84px;
  left: 16px;
  margin: 0;
  font-size: 0.75rem;
  color: var(--c-secondary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@media (max-width: 900px) {
  .log {
    top: auto;
    bottom: 140px;
    max-height: 40%;
  }

  .log.closed {
    width: auto;
  }

  .controls {
    display: none;
  }

  .hotbar li {
    width: 40px;
    height: 40px;
  }
}
</style>
