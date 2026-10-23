<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Compartment, EditorState, RangeSet } from '@codemirror/state'
import { Decoration, EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { bracketMatching, HighlightStyle, indentOnInput, indentUnit, syntaxHighlighting } from '@codemirror/language'
import { python } from '@codemirror/lang-python'
import { json } from '@codemirror/lang-json'
import { tags as t } from '@lezer/highlight'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: 'python' | 'json'
    readonly?: boolean
    errorLine?: number | null
    label?: string
    minHeight?: string
  }>(),
  { language: 'python', readonly: false, errorLine: null, label: 'Code editor', minHeight: '200px' },
)
const emit = defineEmits<{ 'update:modelValue': [value: string]; run: [] }>()

const host = ref<HTMLDivElement>()
let view: EditorView | null = null
const errorDeco = new Compartment()

const highlight = HighlightStyle.define([
  { tag: t.keyword, color: '#ffb74d', fontWeight: '600' },
  { tag: [t.definitionKeyword, t.modifier, t.controlKeyword], color: '#ffb74d', fontWeight: '600' },
  { tag: [t.string, t.special(t.string)], color: '#a5d6a7' },
  { tag: [t.number, t.bool, t.null], color: '#ffc107' },
  { tag: t.comment, color: '#8d8579', fontStyle: 'italic' },
  { tag: [t.function(t.variableName), t.function(t.propertyName)], color: '#90caf9' },
  { tag: t.definition(t.variableName), color: '#fffdf5' },
  { tag: t.className, color: '#ffcc80' },
  { tag: [t.propertyName, t.attributeName], color: '#ce93d8' },
  { tag: t.operator, color: '#ffe082' },
  { tag: t.meta, color: '#ff9800' },
  { tag: t.variableName, color: '#ece6d8' },
])

const theme = EditorView.theme(
  {
    '&': {
      backgroundColor: '#1e1e1e',
      color: '#ece6d8',
      fontSize: '14px',
      height: '100%',
    },
    '.cm-scroller': { fontFamily: 'var(--font-mono)', lineHeight: '1.65' },
    '.cm-content': { caretColor: '#ffc107', padding: '10px 0' },
    '.cm-cursor': { borderLeftColor: '#ffc107', borderLeftWidth: '2px' },
    '.cm-gutters': { backgroundColor: '#1e1e1e', color: '#5f5a52', border: 'none' },
    '.cm-activeLine': { backgroundColor: 'rgba(255,193,7,0.05)' },
    '.cm-activeLineGutter': { backgroundColor: 'transparent', color: '#ffc107' },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': {
      backgroundColor: 'rgba(255,152,0,0.28) !important',
    },
    '.cm-matchingBracket': { backgroundColor: 'rgba(255,193,7,0.2)', outline: 'none' },
    '.cm-error-line': { backgroundColor: 'rgba(229,83,75,0.18)', boxShadow: 'inset 3px 0 0 #e5534b' },
  },
  { dark: true },
)

function errorDecorations(line: number | null) {
  if (!view || !line || line < 1 || line > view.state.doc.lines) return EditorView.decorations.of(RangeSet.empty)
  const from = view.state.doc.line(line).from
  return EditorView.decorations.of(Decoration.set([Decoration.line({ class: 'cm-error-line' }).range(from)]))
}

onMounted(() => {
  view = new EditorView({
    parent: host.value!,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        highlightActiveLineGutter(),
        history(),
        indentOnInput(),
        bracketMatching(),
        indentUnit.of('    '),
        EditorState.tabSize.of(4),
        props.language === 'python' ? python() : json(),
        syntaxHighlighting(highlight),
        theme,
        EditorState.readOnly.of(props.readonly),
        EditorView.contentAttributes.of({ 'aria-label': props.label }),
        keymap.of([
          {
            key: 'Mod-Enter',
            run: () => {
              emit('run')
              return true
            },
          },
          indentWithTab,
          ...defaultKeymap,
          ...historyKeymap,
        ]),
        errorDeco.of([]),
        EditorView.updateListener.of((u) => {
          if (u.docChanged) emit('update:modelValue', u.state.doc.toString())
        }),
      ],
    }),
  })
  view.dispatch({ effects: errorDeco.reconfigure(errorDecorations(props.errorLine)) })
})

watch(
  () => props.modelValue,
  (v) => {
    if (view && v !== view.state.doc.toString()) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: v } })
    }
  },
)

watch(
  () => props.errorLine,
  (line) => view?.dispatch({ effects: errorDeco.reconfigure(errorDecorations(line)) }),
)

onBeforeUnmount(() => view?.destroy())
</script>

<template>
  <div ref="host" class="code-editor" :style="{ minHeight }" />
</template>

<style scoped>
.code-editor {
  height: 100%;
  overflow: hidden;
  background: #1e1e1e;
}

.code-editor :deep(.cm-editor) {
  height: 100%;
}

.code-editor :deep(.cm-editor.cm-focused) {
  outline: none;
}
</style>
