import { onBeforeUnmount, ref } from 'vue';

/** A boolean that switches on for `ms` after `trigger()` (restarting if already on). Used to replay one-shot CSS animations. */
export function useFlash(ms: number) {
  const on = ref(false);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function trigger() {
    clearTimeout(timer);
    on.value = false;
    timer = setTimeout(() => {
      on.value = true;
      timer = setTimeout(() => (on.value = false), ms);
    }, 24);
  }
  onBeforeUnmount(() => clearTimeout(timer));
  return { on, trigger };
}
