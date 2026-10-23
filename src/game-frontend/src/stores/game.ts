import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, ApiError } from '@/api/client'
import type { GameActionResult, GameCommand, GameState } from '@/api/types'
import { useRunner } from './runner'

/**
 * Client mirror of the trusted simulation. The backend is the source of truth:
 * this store only ever replaces its state with what the backend returns.
 */
export const useGame = defineStore('game', () => {
  const state = ref<GameState | null>(null)
  const actions = ref<GameActionResult[]>([])
  const busy = ref(false)
  const loadError = ref<string | null>(null)

  async function load() {
    try {
      state.value = await api.gameState()
      loadError.value = null
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : String(e)
    }
  }

  function apply(next: GameState) {
    if (!state.value || next.version >= state.value.version) state.value = next
  }

  async function act(command: GameCommand, target: string, extra: { missionId?: string; code?: string } = {}) {
    busy.value = true
    try {
      const result = await api.gameAction({
        command,
        target,
        mission_id: extra.missionId,
        code: extra.code,
      })
      apply(result.state)
      actions.value.unshift(result)
      if (actions.value.length > 20) actions.value.pop()
      if (result.trace) useRunner().log('frontier', extra.missionId ?? '', result.trace)
      return result
    } catch (e) {
      if (e instanceof ApiError && e.status === null) useRunner().status = 'offline'
      throw e
    } finally {
      busy.value = false
    }
  }

  return { state, actions, busy, loadError, load, act }
})
