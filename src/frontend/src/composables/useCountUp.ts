import { onBeforeUnmount, ref, watch, type Ref } from 'vue';

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** A number that eases from its previous value to `target` (instantly when the user prefers reduced motion). */
export function useCountUp(target: Ref<number>, ms = 800) {
  const value = ref(0);
  let from = 0;
  let raf = 0;
  function run(to: number) {
    cancelAnimationFrame(raf);
    if (prefersReducedMotion()) {
      value.value = from = to;
      return;
    }
    const start = performance.now();
    const a = from;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / ms);
      value.value = Math.round(a + (to - a) * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
      else from = to;
    };
    raf = requestAnimationFrame(tick);
  }
  watch(target, run, { immediate: true });
  onBeforeUnmount(() => cancelAnimationFrame(raf));
  return value;
}
