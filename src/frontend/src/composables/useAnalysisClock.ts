import { computed, onBeforeUnmount, ref, toValue, type MaybeRefOrGetter } from 'vue';

/** How long the wait usually is when the server hasn't said (the skills step took 30-45 s in tests), used only to pace what the page shows. */
export const EXPECTED_MS = 40_000;
/** When each of the four stages starts, as a fraction of the expected time. */
export const STAGE_STARTS = [0, 0.12, 0.42, 0.78];
/** The scan line reaches the bottom of the document at this fraction of the expected time. */
export const SCAN_END = 0.66;

/** Never reaches 100% until the response arrives; holds at 94% if it's late. */
export function progressAt(f: number): number {
  return Math.min(0.94, 1 - Math.exp(-3 * f));
}

export function stageAt(f: number): number {
  return STAGE_STARTS.reduce((s, start, i) => (f >= start ? i : s), 0);
}

export function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** A clock for the wait: everything the analysis page shows is derived from how long it has been. */
export function useAnalysisClock(expectedMs: MaybeRefOrGetter<number> = EXPECTED_MS) {
  const elapsed = ref(0);
  let t0 = 0;
  let timer: number | undefined;

  function start() {
    stop();
    t0 = Date.now();
    elapsed.value = 0;
    timer = window.setInterval(() => (elapsed.value = Date.now() - t0), 100);
  }
  function stop() {
    window.clearInterval(timer);
    timer = undefined;
  }
  onBeforeUnmount(stop);

  const f = computed(() => elapsed.value / toValue(expectedMs));
  return {
    elapsed,
    f,
    progress: computed(() => progressAt(f.value)),
    stage: computed(() => stageAt(f.value)),
    /** Taking longer than expected. */
    slow: computed(() => f.value > 1),
    start,
    stop,
  };
}
