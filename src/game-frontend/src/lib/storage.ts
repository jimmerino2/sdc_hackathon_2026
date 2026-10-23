// Small key-value persistence interface. Today it is browser localStorage;
// swap the implementation for server-side persistence without touching stores.

import { RUNNER_MODE } from '@/api/client'

export interface KeyValueStore {
  load<T>(key: string): T | null
  save<T>(key: string, value: T): void
  remove(key: string): void
}

// Preview-mode progress is kept apart so simulated results never mix with real ones.
const PREFIX = RUNNER_MODE === 'preview' ? 'frontier:preview:' : 'frontier:'

export const localStore: KeyValueStore = {
  load<T>(key: string): T | null {
    try {
      const raw = localStorage.getItem(PREFIX + key)
      return raw ? (JSON.parse(raw) as T) : null
    } catch {
      return null
    }
  },
  save<T>(key: string, value: T) {
    try {
      localStorage.setItem(PREFIX + key, JSON.stringify(value))
    } catch {
      /* storage full or blocked: progress stays in memory for this session */
    }
  },
  remove(key: string) {
    try {
      localStorage.removeItem(PREFIX + key)
    } catch {
      /* ignore */
    }
  },
}

export const storage: KeyValueStore = localStore
