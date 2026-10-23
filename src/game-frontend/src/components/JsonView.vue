<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: unknown }>()

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// Tiny tokenizer: colour keys, strings, numbers and literals.
const html = computed(() => {
  if (props.value === undefined) return '<span class="j-null">(empty)</span>'
  const src = typeof props.value === 'string' ? JSON.stringify(props.value) : JSON.stringify(props.value, null, 2)
  return escape(src ?? 'undefined').replace(
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (_m, str: string, colon: string, lit: string, num: string) => {
      if (str) return colon ? `<span class="j-key">${str}</span>${colon}` : `<span class="j-str">${str}</span>`
      if (lit) return `<span class="j-lit">${lit}</span>`
      return `<span class="j-num">${num}</span>`
    },
  )
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html — escaped above -->
  <pre class="json dev-scroll" v-html="html" />
</template>

<style scoped>
.json {
  margin: 0;
  padding: 10px 12px;
  background: #1a1a1a;
  color: var(--c-panel-text);
  border-radius: var(--radius-s);
  overflow: auto;
  font-size: 0.84rem;
  line-height: 1.5;
  max-height: 320px;
}

.json :deep(.j-key) {
  color: #ce93d8;
}

.json :deep(.j-str) {
  color: #a5d6a7;
}

.json :deep(.j-num),
.json :deep(.j-lit) {
  color: var(--c-primary);
}

.json :deep(.j-null) {
  color: var(--c-panel-muted);
  font-style: italic;
}
</style>
