<script setup lang="ts">
import { ref } from 'vue';
import Icon from './Icon.vue';

/** An info/help question-mark button that opens the detail behind a summary in a dialog, so the page itself stays short.
 *  With `label` it shows as a small text button; without, as an icon next to a heading. */
const props = defineProps<{ title: string; label?: string; wide?: boolean; icon?: string }>();
const dlg = ref<HTMLDialogElement>();
const open = () => dlg.value?.showModal();
const close = () => dlg.value?.close();
</script>

<template>
  <button type="button" class="info" :class="{ txt: !!props.label }" :aria-label="props.label ? undefined : `Explain: ${title}`"
          :title="props.label ? undefined : 'What does this mean?'" @click="open">
    <Icon :name="props.icon ?? 'help'" :size="props.label ? 14 : 14" :stroke="2.4" /><span v-if="props.label">{{ props.label }}</span>
  </button>
  <Teleport to="body">
    <dialog ref="dlg" class="idlg" :class="{ wide }" :aria-label="title" @click.self="close">
      <div class="inner">
        <div class="top">
          <h2>{{ title }}</h2>
          <button type="button" class="close" aria-label="Close" @click="close"><Icon name="x" :size="20" /></button>
        </div>
        <div class="body"><slot /></div>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.info {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px; flex: none; vertical-align: middle;
  width: 22px; height: 22px; border-radius: 999px; background: #f0efec; color: var(--muted);
  font-size: 14px; font-weight: 800; letter-spacing: 0; text-transform: none; transition: background .1s, color .1s;
}
.info:hover { background: var(--cream); color: var(--amber-ink); }
.info.txt { width: auto; height: auto; padding: 4px 10px; color: var(--ink); }
.idlg { margin: auto; border: 0; border-radius: 20px; padding: 0; width: min(640px, calc(100vw - 32px)); max-height: calc(100vh - 48px); background: #fff; color: var(--ink); box-shadow: 0 20px 60px rgba(0, 0, 0, .25); }
.idlg.wide { width: min(860px, calc(100vw - 32px)); }
.idlg::backdrop { background: rgba(30, 30, 30, .45); }
.inner { padding: 22px 24px 26px; }
.top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 10px; }
h2 { font-size: 21px; line-height: 1.25; font-weight: 900; letter-spacing: 0; text-transform: none; color: var(--ink); }
.close { border: 0; background: #f0efec; border-radius: 999px; width: 36px; height: 36px; display: grid; place-items: center; cursor: pointer; flex: none; }
.body { font-size: 16px; line-height: 1.55; font-weight: 600; letter-spacing: 0; text-transform: none; color: var(--ink); display: flex; flex-direction: column; gap: 10px; }
.body :deep(.muted) { color: var(--muted); }
.body :deep(ul) { margin-left: 18px; display: flex; flex-direction: column; gap: 4px; }
.body :deep(h3) { font-size: 16px; font-weight: 900; margin-top: 6px; }
.body :deep(table) { width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }
.body :deep(th), .body :deep(td) { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--line); }
.body :deep(th:first-child), .body :deep(td:first-child) { text-align: left; }
.body :deep(th) { font-size: 13px; color: var(--muted); font-weight: 800; }
.body :deep(.scroll) { overflow-x: auto; }
</style>
