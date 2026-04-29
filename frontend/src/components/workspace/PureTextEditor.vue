<template>
  <div class="pure-text-editor">
    <div v-if="showSoftLimitWarning" class="soft-limit-banner">
      当前章节已超过 20 万有效字符，建议尽快拆分章节以保持流畅编辑。
    </div>

    <textarea
      ref="textareaRef"
      class="pure-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      title="仅支持纯文本输入"
      spellcheck="false"
      @input="onInput"
      @paste="onPaste"
      @click="emitCursorState"
      @keyup="emitCursorState"
      @scroll="emitScrollState"
    />

    <div class="editor-footer">
      <span class="word-count">本章字数 {{ formattedWordCount }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { countEffectiveCharacters, exceedsSoftLimit } from '@/utils/textMetrics'

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
  }
})

const emit = defineEmits(['update:modelValue', 'cursor-change', 'scroll-change'])

const textareaRef = ref(null)
const effectiveWordCount = computed(() => countEffectiveCharacters(props.modelValue))
const formattedWordCount = computed(() => effectiveWordCount.value.toLocaleString('zh-CN'))
const showSoftLimitWarning = computed(() => exceedsSoftLimit(props.modelValue))

const normalizeNonNegative = (value) => {
  const next = Number(value)
  return Number.isFinite(next) && next >= 0 ? next : 0
}

const emitCursorState = () => {
  const target = textareaRef.value
  if (!target) return
  emit('cursor-change', {
    cursorPosition: Number(target.selectionStart || 0)
  })
}

const emitScrollState = () => {
  const target = textareaRef.value
  if (!target) return
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
    target.selectionStart = nextCursor
    target.selectionEnd = nextCursor
    target.scrollTop = nextScrollTop
    emitCursorState()
    emitScrollState()
  })
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
  if (!target) return
  const source = String(props.modelValue || '')
  const start = Number(target.selectionStart || 0)
  const end = Number(target.selectionEnd || 0)
  const nextValue = `${source.slice(0, start)}${text}${source.slice(end)}`
  emit('update:modelValue', nextValue)
  requestAnimationFrame(() => {
    const nextCursor = start + text.length
    target.selectionStart = nextCursor
    target.selectionEnd = nextCursor
    emitCursorState()
  })
}

const onPaste = (event) => {
  event.preventDefault()
  const text = event.clipboardData?.getData('text/plain') || ''
  insertPlainTextAtSelection(text)
}

defineExpose({
  restoreViewport,
  focusEditor
})
</script>

<style scoped>
.pure-text-editor {
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
  color: #6b7280;
}

.soft-limit-banner {
  border: 1px solid #fdba74;
  border-radius: 16px;
  background: #fff7ed;
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.6;
  color: #c2410c;
}

.pure-textarea {
  width: 100%;
  flex: 1;
  min-height: 420px;
  resize: none;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  background: #ffffff;
  padding: 28px;
  font-size: 16px;
  line-height: 1.9;
  color: #111827;
  outline: none;
}

.pure-textarea:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.word-count {
  font-weight: 600;
  color: #111827;
}
</style>
