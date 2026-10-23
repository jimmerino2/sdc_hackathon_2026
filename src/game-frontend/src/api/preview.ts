// PREVIEW SIMULATOR — enabled only with VITE_RUNNER_MODE=preview.
// It does NOT execute learner code. Every result is flagged `simulated: true`
// and the UI labels it as such. It exists so the interface can be walked
// through before the isolated runner is available.

import type { Api } from './client'
import type { GameActionResult, GameState, RequestResult } from './types'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
const id = () => Math.random().toString(36).slice(2, 10)

const state: GameState = {
  inventory: {},
  equipped: null,
  nodes: {
    'copper-1': { id: 'copper-1', resource: 'copper', remaining: 3 },
    'copper-2': { id: 'copper-2', resource: 'copper', remaining: 3 },
  },
  version: 1,
}

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v))

export const previewApi: Api = {
  async health() {
    return { status: 'ok', isolation: 'none (preview simulator)', simulated: true }
  },

  async evaluate(missionId) {
    await delay(500)
    return {
      run_id: id(),
      mission_id: missionId,
      status: 'passed',
      tests: [
        {
          id: 'preview',
          name: 'Preview mode — code was not executed',
          passed: true,
          message: 'Start the real runner to test your implementation.',
        },
      ],
      stdout: '',
      stderr: '',
      duration_ms: 0,
      simulated: true,
    }
  },

  async request(_missionId, _code, req): Promise<RequestResult> {
    await delay(300)
    return {
      run_id: id(),
      request: req,
      response: {
        status_code: 200,
        headers: { 'content-type': 'application/json' },
        body: { simulated: true, note: 'Preview mode does not run your route.' },
      },
      logs: '',
      duration_ms: 0,
      simulated: true,
    }
  },

  async gameState() {
    return clone(state)
  },

  async gameAction(input): Promise<GameActionResult> {
    await delay(350)
    const base = { action_id: id(), command: input.command, target: input.target, simulated: true }

    if (input.command === 'pickup' && input.target === 'crate-1') {
      if (!state.inventory.stone_pickaxe) {
        state.inventory.stone_pickaxe = 1
        state.equipped = 'stone_pickaxe'
        state.version++
      }
      return {
        ...base,
        accepted: true,
        code: 'OK',
        reason: 'You picked up a stone pickaxe.',
        effects: [{ type: 'inventory_add', item: 'stone_pickaxe', qty: 1 }],
        state: clone(state),
      }
    }

    if (input.command === 'mine') {
      const node = state.nodes[input.target]
      const tool = state.equipped ?? 'hands'
      const req = {
        method: 'POST' as const,
        path: '/mine',
        query: {},
        headers: {},
        body: { resource: node?.resource ?? 'unknown', tool },
      }
      if (!node || node.remaining <= 0) {
        return {
          ...base,
          accepted: false,
          code: 'NODE_DEPLETED',
          reason: 'This deposit is empty.',
          effects: [],
          state: clone(state),
        }
      }
      if (tool !== 'stone_pickaxe') {
        return {
          ...base,
          accepted: false,
          code: 'REJECTED_BY_ROUTE',
          reason: 'Simulated: a correct route refuses mining copper with bare hands (403).',
          trace: {
            run_id: id(),
            request: req,
            response: { status_code: 403, headers: {}, body: { detail: 'Wrong tool' } },
            logs: '',
            duration_ms: 0,
            simulated: true,
          },
          effects: [],
          state: clone(state),
        }
      }
      node.remaining--
      state.inventory.copper = (state.inventory.copper ?? 0) + 1
      state.version++
      return {
        ...base,
        accepted: true,
        code: 'OK',
        reason: 'Simulated success — your code was not executed.',
        trace: {
          run_id: id(),
          request: req,
          response: {
            status_code: 200,
            headers: {},
            body: { mined: true, resource: 'copper', amount: 1 },
          },
          logs: '',
          duration_ms: 0,
          simulated: true,
        },
        effects: [
          { type: 'inventory_add', item: 'copper', qty: 1 },
          { type: 'node_update', node_id: node.id },
        ],
        state: clone(state),
      }
    }

    return {
      ...base,
      accepted: false,
      code: 'NOT_ALLOWED',
      reason: 'Unsupported action.',
      effects: [],
      state: clone(state),
    }
  },
}
