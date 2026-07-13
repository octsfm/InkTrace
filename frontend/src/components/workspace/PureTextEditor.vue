<template>
  <div class="pure-text-editor" :data-theme="theme">
    <div v-if="showSoftLimitWarning" class="soft-limit-banner">
      当前章节已超过 20 万有效字符，建议尽快拆分章节以保持流畅编辑。
    </div>

    <div class="pure-text-editor__surface">
    <MentionHighlight
      v-if="mentions.length"
      class="pure-text-editor__mention-layer"
      :style="mentionLayerStyle"
      :content="modelValue"
      :mentions="mentions"
      :summary-by-id="mentionSummaryById"
      @mention-hover="$emit('mention-hover', $event)"
    />
    <textarea
      ref="textareaRef"
      class="pure-textarea"
      :style="textareaStyle"
      :value="modelValue"
      :placeholder="placeholder"
      title="仅支持纯文本输入"
      spellcheck="false"
      @input="onInput"
      @paste="onPaste"
      @click="emitCursorState"
      @keyup="emitCursorState"
      @select="emitSelectionState"
      @scroll="emitScrollState"
    />
    </div>

    <div class="editor-footer">
            <span class="word-count">本章字数 {{ formattedWordCount }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { countEffectiveCharacters, exceedsSoftLimit } from '@/utils/textMetrics'
import MentionHighlight from './MentionHighlight.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  chapterId: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '开始创作...'
  },
  fontFamily: {
    type: String,
    default: 'system-ui'
  },
  fontSize: {
    type: Number,
    default: 18
  },
  lineHeight: {
    type: Number,
    default: 1.8
  },
  theme: {
    type: String,
    default: 'light'
  },
  mentions: { type: Array, default: () => [] },
  mentionSummaryById: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'cursor-change', 'scroll-change', 'selection-change', 'mention-hover'])

const textareaRef = ref(null)
const scrollTop = ref(0)
const effectiveWordCount = computed(() => countEffectiveCharacters(props.modelValue))
const formattedWordCount = computed(() => effectiveWordCount.value.toLocaleString('zh-CN'))
const showSoftLimitWarning = computed(() => exceedsSoftLimit(props.modelValue))
const textareaStyle = computed(() => ({
  fontFamily: String(props.fontFamily || 'system-ui'),
  fontSize: `${Number(props.fontSize || 18)}px`,
  lineHeight: String(props.lineHeight || 1.8)
}))
const mentionLayerStyle = computed(() => ({
  ...textareaStyle.value,
  transform: `translateY(-${scrollTop.value}px)`
}))

const normalizeNonNegative = (value) => {
  const next = Number(value)
  return Number.isFinite(next) && next >= 0 ? next : 0
}

const parsePixelValue = (value, fallback = 0) => {
  const next = Number.parseFloat(value)
  return Number.isFinite(next) ? next : fallback
}

const resolveLineHeight = (value, fontSize) => {
  const normalized = String(value || '').trim()
  if (!normalized || normalized === 'normal') return fontSize * 1.8
  if (normalized.endsWith('px')) return parsePixelValue(normalized, fontSize * 1.8)
  const next = Number.parseFloat(normalized)
  if (!Number.isFinite(next)) return fontSize * 1.8
  return next <= 4 ? next * fontSize : next
}

const measureSelectionAnchor = (target, end) => {
  const style = window.getComputedStyle(target)
  const fontSize = parsePixelValue(style.fontSize, 18)
  const lineHeight = resolveLineHeight(style.lineHeight, fontSize)
  const paddingLeft = parsePixelValue(style.paddingLeft, 0)
  const paddingRight = parsePixelValue(style.paddingRight, 0)
  const paddingTop = parsePixelValue(style.paddingTop, 0)
  const availableWidth = Math.max(1, Number(target.clientWidth || 0) - paddingLeft - paddingRight)
  const approximateCharWidth = Math.max(1, fontSize * 0.56)
  const columnCapacity = Math.max(1, Math.floor(availableWidth / approximateCharWidth))
  const textBeforeSelectionEnd = String(target.value || '').slice(0, Math.max(0, Number(end || 0)))
  const logicalLines = textBeforeSelectionEnd.split('\n')
  let visualLineIndex = 0
  for (let index = 0; index < logicalLines.length - 1; index += 1) {
    const line = logicalLines[index]
    visualLineIndex += Math.floor(line.length / columnCapacity) + 1
  }
  const lastLine = logicalLines.at(-1) || ''
  visualLineIndex += Math.floor(lastLine.length / columnCapacity)
  const lineColumn = lastLine.length % columnCapacity
  return {
    anchorX: Math.round(Math.min(
      Number(target.clientWidth || 0),
      paddingLeft + (lineColumn * approximateCharWidth)
    )),
    anchorY: Math.round(Math.max(0, paddingTop + (visualLineIndex * lineHeight) - Number(target.scrollTop || 0))),
    anchorHeight: Math.round(lineHeight),
    containerWidth: Number(target.clientWidth || 0)
  }
}

const emitCursorState = () => {
  const target = textareaRef.value
  if (!target) return
  emit('cursor-change', {
    cursorPosition: Number(target.selectionStart || 0)
  })
}

const emitSelectionState = () => {
  const target = textareaRef.value
  if (!target) return
  const start = Number(target.selectionStart || 0)
  const end = Number(target.selectionEnd || 0)
  const anchor = measureSelectionAnchor(target, end)
  emit('selection-change', {
    text: String(target.value || '').slice(start, end),
    start,
    end,
    ...anchor
  })
}

const emitScrollState = () => {
  const target = textareaRef.value
  if (!target) return
  scrollTop.value = Number(target.scrollTop || 0)
  emit('scroll-change', {
    scrollTop: Number(target.scrollTop || 0)
  })
}

const restoreViewport = ({ cursorPosition = 0, scrollTop = 0 } = {}) => {
  const target = textareaRef.value
  if (!target) return
  requestAnimationFrame(() => {
    const contentLength = String(target.value || '').length
    const nextCursor = Math.min(normalizeNonNegative(cursorPosition), contentLength)
    const maxScrollTop = Math.max(0, Number(target.scrollHeight || 0) - Number(target.clientHeight || 0))
    const nextScrollTop = Math.min(normalizeNonNegative(scrollTop), maxScrollTop)
    if (typeof target.setSelectionRange === 'function') {
      target.setSelectionRange(nextCursor, nextCursor)
    } else {
      target.selectionStart = nextCursor
      target.selectionEnd = nextCursor
    }
    target.scrollTop = nextScrollTop
    emitCursorState()
    emitScrollState()
  })
}

const getViewport = () => {
  const target = textareaRef.value
  if (!target) {
    return {
      cursorPosition: 0,
      scrollTop: 0
    }
  }
  return {
    cursorPosition: Number(target.selectionStart || 0),
    scrollTop: Number(target.scrollTop || 0)
  }
}

const focusEditor = () => {
  textareaRef.value?.focus?.()
}

const onInput = (event) => {
  emit('update:modelValue', event.target.value)
  emitCursorState()
}

const insertPlainTextAtSelection = (text) => {
  const target = textareaRef.value
  if (!target) return undefined
  const source = String(props.modelValue || '')
  const start = Number(target.selectionStart || 0)
  const end = Number(target.selectionEnd || 0)
  const nextValue = `${source.slice(0, start)}${text}${source.slice(end)}`
  target.value = nextValue
  emit('update:modelValue', nextValue)
  requestAnimationFrame(() => {
    const nextCursor = start + text.length
    target.selectionStart = nextCursor
    target.selectionEnd = nextCursor
    emitCursorState()
  })
  return {
    text,
    start,
    end: start + text.length
  }
}

const onPaste = (event) => {
  event.preventDefault()
  const text = event.clipboardData?.getData('text/plain') || ''
  insertPlainTextAtSelection(text)
}

defineExpose({ restoreViewport, getViewport, focusEditor, insertPlainTextAtSelection })
</script>

<style scoped>
.pure-text-editor {
  --editor-border: var(--studio-border, var(--ink-border-strong, #d1d5db));
  --editor-bg: var(--studio-card-bg, var(--ink-surface-1, #ffffff));
  --editor-text: var(--studio-title, var(--ink-text-primary, #111827));
  --editor-muted: var(--studio-muted, var(--ink-text-muted, #6b7280));
  --editor-warning-border: var(--ink-warning-text, #fdba74);
  --editor-warning-bg: var(--ink-warning-bg, #fff7ed);
  --editor-warning-text: var(--ink-warning-text, #c2410c);
  --editor-focus: var(--ink-accent, #2563eb);

  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  font-size: 12px;
  color: var(--editor-muted);
}

.soft-limit-banner {
  border: 1px solid var(--editor-warning-border);
  border-radius: 16px;
  background: var(--editor-warning-bg);
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--editor-warning-text);
}

.pure-textarea {
  width: 100%;
  flex: 1;
  min-height: 420px;
  resize: none;
  border: 1px solid var(--editor-border);
  border-radius: 20px;
  background: var(--editor-bg);
  padding: 28px;
  font-size: 16px;
  line-height: 1.9;
  color: var(--editor-text);
  outline: none;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.pure-text-editor__surface {
  position: relative;
  display: flex;
  flex: 1;
  min-height: 420px;
  overflow: hidden;
  border-radius: 20px;
}

.pure-text-editor__mention-layer {
  position: absolute;
  z-index: 2;
  inset: 0;
  min-height: 420px;
  box-sizing: border-box;
  padding: 28px;
  font-size: 16px;
  line-height: 1.9;
  transition: none;
}

.pure-text-editor__surface .pure-textarea {
  position: relative;
  z-index: 1;
  min-height: 100%;
  background: transparent;
}

.pure-textarea::placeholder {
  color: color-mix(in srgb, var(--editor-text) 45%, transparent);
}

.pure-textarea:focus {
  border-color: var(--editor-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--editor-focus) 24%, transparent);
}

.word-count {
  font-weight: 600;
  color: var(--editor-text);
}
</style>
