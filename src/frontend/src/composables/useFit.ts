import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

/** Scale (<= 1) that makes a stage of `width` (fixed, or read each time) fit the element bound to `el`. */
export function useFit(width: number | (() => number)) {
  const el = ref<HTMLElement | null>(null);
  const box = ref(0);
  const scale = computed(() => {
    const w = typeof width === 'function' ? width() : width;
    return box.value > 0 && w > 0 ? Math.min(1, box.value / w) : 1;
  });
  let ro: ResizeObserver | undefined;
  function measure() {
    box.value = el.value?.clientWidth ?? 0;
  }
  onMounted(() => {
    measure();
    if (typeof ResizeObserver !== 'undefined' && el.value) {
      ro = new ResizeObserver(measure);
      ro.observe(el.value);
    } else window.addEventListener('resize', measure);
  });
  onBeforeUnmount(() => {
    ro?.disconnect();
    window.removeEventListener('resize', measure);
  });
  return { el, scale };
}
