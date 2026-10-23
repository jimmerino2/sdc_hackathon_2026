import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, ApiError, RUNNER_MODE } from '@/api/client'
import type { EvaluationResult, RequestResult, RouteRequest } from '@/api/types'

export type RunnerStatus = 'unknown' | 'online' | 'offline'

export interface HistoryEntry {
  id: string
  at: number
  source: 'workshop' | 'frontier'
  missionId: string
  result: RequestResult
}

export const useRunner = defineStore('runner', () => {
  const status = ref<RunnerStatus>('unknown')
  const isolation = ref<string | null>(null)
  const simulated = ref(RUNNER_MODE === 'preview')
  const lastError = ref<string | null>(null)
  const evaluations = ref<Record<string, EvaluationResult>>({})
  const history = ref<HistoryEntry[]>([])
  let timer: ReturnType<typeof setInterval> | null = null

  async function checkHealth() {
    try {
      const h = await api.health()
      status.value = 'online'
      isolation.value = h.isolation
      simulated.value = !!h.simulated
      lastError.value = null
    } catch (e) {
      status.value = 'offline'
      lastError.value = e instanceof Error ? e.message : String(e)
    }
  }

  function startPolling() {
    if (timer) return
    void checkHealth()
    timer = setInterval(checkHealth, 15000)
  }

  async function evaluate(missionId: string, code: string): Promise<EvaluationResult> {
    try {
      const result = await api.evaluate(missionId, code)
      status.value = 'online'
      evaluations.value[missionId] = result
      return result
    } catch (e) {
      if (e instanceof ApiError && e.status === null) status.value = 'offline'
      throw e
    }
  }

  async function sendRequest(missionId: string, code: string, req: RouteRequest) {
    try {
      const result = await api.request(missionId, code, req)
      status.value = 'online'
      log('workshop', missionId, result)
      return result
    } catch (e) {
      if (e instanceof ApiError && e.status === null) status.value = 'offline'
      throw e
    }
  }

  function log(source: HistoryEntry['source'], missionId: string, result: RequestResult) {
    history.value.unshift({ id: result.run_id, at: Date.now(), source, missionId, result })
    if (history.value.length > 30) history.value.pop()
  }

  return {
    status,
    isolation,
    simulated,
    lastError,
    evaluations,
    history,
    checkHealth,
    startPolling,
    evaluate,
    sendRequest,
    log,
  }
})
