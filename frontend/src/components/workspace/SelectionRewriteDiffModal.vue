<template>
  <div
    v-if="modelValue"
    class="selection-rewrite-modal"
    data-test="selection-rewrite-diff-modal"
  >
    <div class="selection-rewrite-modal__panel">
      <header class="selection-rewrite-modal__header">
        <h3>改写结果预览</h3>
        <button type="button" class="selection-rewrite-modal__close" @click="closeModal">关闭</button>
      </header>

      <div class="selection-rewrite-modal__body">
        <section class="selection-rewrite-modal__column">
          <h4>原文</h4>
          <div class="selection-rewrite-modal__content">{{ sourceText }}</div>
        </section>
        <section class="selection-rewrite-modal__column">
          <h4>改写结果</h4>
          <textarea
            v-if="editMode"
            :value="localEditedText"
            class="selection-rewrite-modal__textarea"
            data-test="selection-rewrite-edit-input"
            @input="handleEditedInput"
          />
          <div v-else class="selection-rewrite-modal__content">{{ localEditedText }}</div>
        </section>
      </div>

      <p v-if="diffSummary" class="selection-rewrite-modal__summary">{{ diffSummary }}</p>
      <p class="selection-rewrite-modal__meta">字数：{{ wordCountBefore }} -> {{ wordCountAfter }}<span v-if="modeLabel"> | 模式：{{ modeLabel }}</span></p>

      <footer class="selection-rewrite-modal__actions">
        <button
          v-if="!editMode"
          type="button"
          data-test="selection-rewrite-edit"
          @click="editMode = true"
        >
          编辑后接受
        </button>
        <button
          v-if="editMode"
          type="button"
          data-test="selection-rewrite-confirm-edit"
          @click="confirmEditedAccept"
        >
          确认编辑并接受
        </button>
        <button
          v-if="!editMode"
          type="button"
          data-test="selection-rewrite-accept"
          @click="emitAccept(false)"
        >
          直接接受
        </button>
        <button
          type="button"
          data-test="selection-rewrite-reject"
          @click="rejectCurrent"
        >
          拒绝
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  sourceText: {
    type: String,
    default: ''
  },
  editedText: {
    type: String,
    default: ''
  },
  diffSummary: {
    type: String,
    default: ''
  },
  wordCountBefore: {
    type: Number,
    default: 0
  },
  wordCountAfter: {
    type: Number,
    default: 0
  },
  modeLabel: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'update:editedText', 'accept', 'reject'])
const editMode = ref(false)
const localEditedText = ref(String(props.editedText || ''))

watch(() => props.modelValue, (nextValue) => {
  if (!nextValue) {
    editMode.value = false
  }
})

watch(() => props.editedText, (nextValue) => {
  localEditedText.value = String(nextValue || '')
})

const closeModal = () => {
  editMode.value = false
  emit('update:modelValue', false)
}

const emitAccept = (edited) => {
  emit('accept', {
    finalText: String(localEditedText.value || ''),
    edited
  })
}

const handleEditedInput = (event) => {
  localEditedText.value = String(event?.target?.value || '')
  emit('update:editedText', localEditedText.value)
}

const confirmEditedAccept = () => {
  emitAccept(true)
}

const rejectCurrent = () => {
  editMode.value = false
  emit('reject')
  emit('update:modelValue', false)
}
</script>

<style scoped>
.selection-rewrite-modal {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
}

.selection-rewrite-modal__panel {
  width: min(800px, 100%);
  border-radius: 24px;
  background: #ffffff;
  padding: 24px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
}

.selection-rewrite-modal__header,
.selection-rewrite-modal__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.selection-rewrite-modal__body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin: 20px 0;
}

.selection-rewrite-modal__column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selection-rewrite-modal__content,
.selection-rewrite-modal__textarea {
  min-height: 180px;
  border: 1px solid #d1d5db;
  border-radius: 16px;
  padding: 16px;
  background: #f8fafc;
  color: #111827;
  line-height: 1.7;
}

.selection-rewrite-modal__textarea {
  width: 100%;
  resize: vertical;
  font: inherit;
}

.selection-rewrite-modal__summary,
.selection-rewrite-modal__meta {
  color: #4b5563;
}

.selection-rewrite-modal__close {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
}
</style>
