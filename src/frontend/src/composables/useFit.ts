import { onBeforeUnmount, onMounted, ref } from 'vue';

/** Scale (<= 1) that makes a stage of fixed `width` fit the element bound to `el`. */
export function useFit(width: number) {
  const el = ref<HTMLElement | null>(null);
  const scale = ref(1);
  let ro: ResizeObserver | undefined;
  function measure() {
    const w = el.value?.clientWidth ?? 0;
    scale.value = w > 0 ? Math.min(1, w / width) : 1;
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
