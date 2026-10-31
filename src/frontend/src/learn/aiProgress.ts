import { ref } from 'vue';

/**
 * AI Fluency lesson completion and challenge reflections, kept in this browser like the chosen bee (bee.ts).
 * Deliberately separate from the roadmap: nothing here reaches the backend, career progress, stingers or the leaderboard.
 */
const LESSONS_KEY = 'jobee_ai_lessons';
const REFLECTIONS_KEY = 'jobee_ai_reflections';

export type Reflection = { used?: string; verified?: string; changed?: string };

function read<T>(key: string): Record<string, T> {
  try {
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
    const parsed: unknown = saved ? JSON.parse(saved) : null;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as Record<string, T>) : {};
  } catch {
    return {};
  }
}

function write(key: string, value: unknown) {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage is full or blocked: the page still works, the progress just lasts until a reload.
  }
}

/** Finished lesson ids by profile, so two learners sharing a browser keep their own. */
const lessons = ref(read<string[]>(LESSONS_KEY));
const reflections = ref(read<Reflection>(REFLECTIONS_KEY));

const owner = (profileId: string | null) => profileId ?? 'guest';

export const completedLessons = (profileId: string | null): string[] => lessons.value[owner(profileId)] ?? [];

/** Mark a lesson done, or not done if it already was. */
export function toggleLesson(profileId: string | null, id: string) {
  const done = completedLessons(profileId);
  const next = done.includes(id) ? done.filter((x) => x !== id) : [...done, id];
  lessons.value = { ...lessons.value, [owner(profileId)]: next };
  write(LESSONS_KEY, lessons.value);
}

export const reflectionFor = (challengeId: string): Reflection => reflections.value[challengeId] ?? {};

export function saveReflection(challengeId: string, patch: Reflection) {
  reflections.value = { ...reflections.value, [challengeId]: { ...reflectionFor(challengeId), ...patch } };
  write(REFLECTIONS_KEY, reflections.value);
}
