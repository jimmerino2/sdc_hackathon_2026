import { onBeforeUnmount, onMounted, type Ref } from 'vue';

/**
 * Duolingo-style scrolling for a tall sticky side column.
 *
 * `outer` is the sticky, viewport-height wrapper; `inner` is its content, which is slid
 * up/down inside it. On a change of scroll direction the content holds still for `dead`
 * px of page scroll, then follows the page until it hits its own top/bottom. Near either
 * end of the page it snaps to the matching end so nothing is ever unreachable.
 */
export function useTallAside(
  outer: Ref<HTMLElement | null>,
  inner: Ref<HTMLElement | null>,
  { dead = 120, edge = 160, narrow = '(max-width: 1000px)' } = {},
) {
  let scroller: HTMLElement | Window = window;
  let last = 0;
  let dir = 0;
  let deadLeft = dead;
  let offset = 0;
  let raf = 0;
  let ro: ResizeObserver | undefined;

  const scrollParent = (el: HTMLElement | null): HTMLElement | Window => {
    for (let p = el?.parentElement; p; p = p.parentElement) {
      if (/(auto|scroll)/.test(getComputedStyle(p).overflowY)) return p;
    }
    return window;
  };
  const pos = () => (scroller instanceof Window ? scroller.scrollY : scroller.scrollTop);
  const view = () => (scroller instanceof Window ? window.innerHeight : scroller.clientHeight);
  const total = () =>
    scroller instanceof Window ? document.documentElement.scrollHeight : scroller.scrollHeight;

  const frame = () => {
    raf = 0;
    const o = outer.value;
    const i = inner.value;
    if (!o || !i) return;
    if (window.matchMedia(narrow).matches) {
      i.style.transform = '';
      offset = 0;
      return;
    }
    const y = pos();
    const max = Math.max(0, i.offsetHeight - o.clientHeight);
    const d = y - last;
    last = y;
    if (d) {
      const s = Math.sign(d);
      if (s !== dir) { dir = s; deadLeft = dead; }
      const used = Math.min(deadLeft, Math.abs(d));
      deadLeft -= used;
      offset += s * (Math.abs(d) - used);
    }
    if (y >= total() - view() - edge) offset = max;
    else if (y <= edge) offset = 0;
    offset = Math.min(max, Math.max(0, offset));
    i.style.transform = offset ? `translate3d(0, ${-offset}px, 0)` : '';
  };
  const schedule = () => { raf ||= requestAnimationFrame(frame); };

  onMounted(() => {
    scroller = scrollParent(outer.value);
    last = pos();
    scroller.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    if (inner.value) {
      ro = new ResizeObserver(schedule);
      ro.observe(inner.value);
    }
    schedule();
  });
  onBeforeUnmount(() => {
    scroller.removeEventListener('scroll', schedule);
    window.removeEventListener('resize', schedule);
    ro?.disconnect();
    cancelAnimationFrame(raf);
  });
}
