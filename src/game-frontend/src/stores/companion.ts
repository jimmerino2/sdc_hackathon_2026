import { defineStore } from 'pinia'
import { ref } from 'vue'
import { lines, type CompanionEvent, type Mood } from '@/content/dialogue'

export interface SayContext {
  name?: string
  mission?: string
  test?: string
  count?: number
  reason?: string
  /** Override the scripted line, e.g. mission-specific test feedback. */
  text?: string
  mood?: Mood
}

// Low-value chatter is rate-limited so Wick stays charming rather than noisy.
const COOLDOWN_MS: Partial<Record<CompanionEvent, number>> = {
  enter_academy: 60000,
  enter_frontier: 60000,
  enter_workshop: 60000,
  explore: 4000,
  run_start: 15000,
  request_ok: 8000,
  node_depleted: 5000,
}

/**
 * Event-driven coach. Everything goes through `react(event, ctx)` so the
 * scripted selector can later be swapped for an AI coach with the same inputs.
 */
export const useCompanion = defineStore('companion', () => {
  const text = ref('')
  const mood = ref<Mood>('neutral')
  const open = ref(false)
  const seq = ref(0)
  const lastAt: Partial<Record<CompanionEvent, number>> = {}
  const recent: Partial<Record<CompanionEvent, number[]>> = {}

  function pick(event: CompanionEvent) {
    const pool = lines[event]
    const used = (recent[event] ??= [])
    let choices = pool.map((_, i) => i).filter((i) => !used.includes(i))
    if (choices.length === 0) {
      used.length = 0
      choices = pool.map((_, i) => i)
    }
    const idx = choices[Math.floor(Math.random() * choices.length)]
    used.push(idx)
    if (used.length > Math.max(1, pool.length - 1)) used.shift()
    return pool[idx]
  }

  function fill(template: string, ctx: SayContext) {
    return template.replace(/\{(\w+)\}/g, (_, k: keyof SayContext) => String(ctx[k] ?? ''))
  }

  function react(event: CompanionEvent, ctx: SayContext = {}) {
    const now = Date.now()
    const cd = COOLDOWN_MS[event]
    if (cd && lastAt[event] && now - lastAt[event]! < cd) return
    lastAt[event] = now

    const line = pick(event)
    text.value = ctx.text ?? fill(line.text, ctx)
    mood.value = ctx.mood ?? line.mood
    open.value = true
    seq.value++
  }

  function dismiss() {
    open.value = false
  }

  return { text, mood, open, seq, react, dismiss }
})
