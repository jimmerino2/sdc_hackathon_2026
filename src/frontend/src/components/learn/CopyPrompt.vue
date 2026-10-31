<script setup lang="ts">
import { ref } from 'vue';
import Icon from '../Icon.vue';

/** A prompt in a monospace block with a copy button. */
const props = defineProps<{ text: string; label?: string }>();

const copied = ref(false);
const failed = ref(false);

async function copy() {
  failed.value = false;
  try {
    await navigator.clipboard.writeText(props.text);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    failed.value = true;
  }
}
</script>

<template>
  <div class="jb-prompt">
    <div class="jb-prompt__top">
      <span class="jb-prompt__label">{{ label ?? 'Prompt' }}</span>
      <button type="button" class="jb-prompt__copy" :aria-label="`Copy ${label ?? 'prompt'}`" @click="copy">
        <Icon :name="copied ? 'check' : 'copy'" :size="16" />{{ copied ? 'Copied' : 'Copy' }}
      </button>
    </div>
    <pre tabindex="0">{{ text }}</pre>
    <span class="sr-only" aria-live="polite">{{ copied ? 'Copied to clipboard' : '' }}</span>
    <p v-if="failed" class="jb-next__err" role="alert">Couldn’t copy. Select the text and copy it yourself.</p>
  </div>
</template>

<style scoped>
.jb-prompt { min-width: 0; border: 2px solid var(--line); border-radius: var(--radius-md); background: var(--surface); overflow: hidden; }
.jb-prompt__top { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 6px 8px 6px 14px; border-bottom: 2px solid var(--line); }
.jb-prompt__label { font-size: 13px; line-height: 18px; font-weight: 800; color: var(--text-muted); }
.jb-prompt__copy { display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 6px 12px; border: 2px solid var(--line-strong); border-radius: var(--radius-pill); background: var(--surface-raised); color: var(--text); font-size: 14px; line-height: 18px; font-weight: 800; cursor: pointer; transition: background var(--dur-fast); }
.jb-prompt__copy:hover { background: var(--honey-tint); }
pre { margin: 0; padding: 12px 14px; white-space: pre-wrap; overflow-wrap: anywhere; font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 14px; line-height: 21px; color: var(--text); }
.jb-next__err { margin: 0; padding: 0 14px 10px; }
</style>
