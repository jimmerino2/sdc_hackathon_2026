import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { missions, missionById } from '@/content/missions'
import { LEVEL_THRESHOLDS, levelTitles } from '@/content/achievements'
import { storage } from '@/lib/storage'

export type MissionState = 'locked' | 'available' | 'active' | 'completed'

interface Profile {
  name: string
  createdAt: string
}

interface Attempts {
  runs: number
  failedRuns: number
  hintsShown: number
}

interface Saved {
  profile: Profile | null
  xp: number
  completed: Record<string, { at: string; runId: string }>
  achievements: Record<string, string>
  attempts: Record<string, Attempts>
  activeMission: string | null
}

export interface CompletionResult {
  granted: boolean
  xp: number
  achievements: string[]
  unlocked: string[]
  levelUp: number | null
}

const KEY = 'progress.v1'

function levelFor(xp: number) {
  let level = 1
  LEVEL_THRESHOLDS.forEach((t, i) => {
    if (xp >= t) level = i + 1
  })
  return level
}

export const useProgress = defineStore('progress', () => {
  const saved = storage.load<Saved>(KEY)
  const profile = ref<Profile | null>(saved?.profile ?? null)
  const xp = ref(saved?.xp ?? 0)
  const completed = ref<Saved['completed']>(saved?.completed ?? {})
  const achievements = ref<Saved['achievements']>(saved?.achievements ?? {})
  const attempts = ref<Saved['attempts']>(saved?.attempts ?? {})
  const activeMission = ref<string | null>(saved?.activeMission ?? null)

  watch(
    [profile, xp, completed, achievements, attempts, activeMission],
    () =>
      storage.save<Saved>(KEY, {
        profile: profile.value,
        xp: xp.value,
        completed: completed.value,
        achievements: achievements.value,
        attempts: attempts.value,
        activeMission: activeMission.value,
      }),
    { deep: true },
  )

  const level = computed(() => levelFor(xp.value))
  const levelTitle = computed(() => levelTitles[level.value - 1] ?? levelTitles.at(-1)!)
  const levelProgress = computed(() => {
    const cur = LEVEL_THRESHOLDS[level.value - 1] ?? 0
    const next = LEVEL_THRESHOLDS[level.value]
    if (next === undefined) return { pct: 100, into: xp.value - cur, span: 0 }
    return { pct: ((xp.value - cur) / (next - cur)) * 100, into: xp.value - cur, span: next - cur }
  })

  function isCompleted(id: string) {
    return id in completed.value
  }

  function missionState(id: string): MissionState {
    if (isCompleted(id)) return 'completed'
    const m = missionById[id]
    if (!m || !m.prerequisites.every(isCompleted)) return 'locked'
    return activeMission.value === id ? 'active' : 'available'
  }

  /** The mission the roadmap should point the learner at. */
  const nextMission = computed(
    () => missions.find((m) => !m.comingSoon && missionState(m.id) !== 'completed' && missionState(m.id) !== 'locked') ?? null,
  )

  const worldProgress = computed(() => {
    const real = missions.filter((m) => !m.comingSoon)
    return { done: real.filter((m) => isCompleted(m.id)).length, total: real.length }
  })

  function attemptsFor(id: string): Attempts {
    return (attempts.value[id] ??= { runs: 0, failedRuns: 0, hintsShown: 0 })
  }

  function recordRun(id: string, passed: boolean) {
    const a = attemptsFor(id)
    a.runs++
    if (!passed) a.failedRuns++
  }

  function recordHint(id: string) {
    attemptsFor(id).hintsShown++
  }

  function setActive(id: string) {
    if (missionState(id) !== 'locked' && !isCompleted(id)) activeMission.value = id
  }

  function grantAchievement(id: string): boolean {
    if (achievements.value[id]) return false
    achievements.value[id] = new Date().toISOString()
    return true
  }

  /**
   * Record a mission as complete after the runner reported every test passing.
   * Idempotent: replays of the same or a later passing run grant nothing.
   */
  function completeMission(id: string, runId: string): CompletionResult {
    const m = missionById[id]
    if (!m || isCompleted(id) || missionState(id) === 'locked') {
      return { granted: false, xp: 0, achievements: [], unlocked: [], levelUp: null }
    }
    const before = level.value
    const firstEver = Object.keys(completed.value).length === 0
    completed.value[id] = { at: new Date().toISOString(), runId }
    xp.value += m.xp
    if (activeMission.value === id) activeMission.value = null

    const earned: string[] = []
    if (firstEver && grantAchievement('first-steps')) earned.push('first-steps')
    if (attemptsFor(id).failedRuns > 0 && grantAchievement('debugger')) earned.push('debugger')
    if (m.achievementOnComplete && grantAchievement(m.achievementOnComplete)) earned.push(m.achievementOnComplete)

    const unlocked = m.unlocks.filter((u) => missionState(u) !== 'locked')
    return {
      granted: true,
      xp: m.xp,
      achievements: earned,
      unlocked,
      levelUp: level.value > before ? level.value : null,
    }
  }

  function addXp(amount: number) {
    xp.value += amount
  }

  function createProfile(name: string) {
    profile.value = { name: name.trim() || 'Explorer', createdAt: new Date().toISOString() }
  }

  function resetAll() {
    profile.value = null
    xp.value = 0
    completed.value = {}
    achievements.value = {}
    attempts.value = {}
    activeMission.value = null
  }

  return {
    profile,
    xp,
    completed,
    achievements,
    attempts,
    activeMission,
    level,
    levelTitle,
    levelProgress,
    nextMission,
    worldProgress,
    isCompleted,
    missionState,
    attemptsFor,
    recordRun,
    recordHint,
    setActive,
    grantAchievement,
    completeMission,
    addXp,
    createProfile,
    resetAll,
  }
})
