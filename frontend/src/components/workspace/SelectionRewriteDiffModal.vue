<template>
  <div
    v-if="modelValue"
    class="selection-rewrite-modal"
    data-test="selection-rewrite-diff-modal"
  >
    <div class="selection-rewrite-modal__panel selection-rewrite-modal__panel--fullscreen">
      <header class="selection-rewrite-modal__header">
        <h3>{{ PREVIEW_TITLE }}</h3>
        <button
          type="button"
          class="selection-rewrite-modal__close"
          :disabled="applying"
          @click="closeModal"
        >
          {{ CLOSE_LABEL }}
        </button>
      </header>

      <p
        v-if="waitingUserAction"
        class="selection-rewrite-modal__waiting"
        data-test="selection-rewrite-waiting-banner"
      >
        {{ WAITING_LABEL }}
      </p>

      <div
        v-if="conflicted"
        class="selection-rewrite-modal__conflict"
        data-test="selection-rewrite-conflict-banner"
      >
        <span>{{ conflictMessage || DEFAULT_CONFLICT_MESSAGE }}</span>
        <div class="selection-rewrite-modal__conflict-actions">
          <button
            type="button"
            class="selection-rewrite-modal__action selection-rewrite-modal__action--warning"
            data-test="selection-rewrite-conflict-reselect"
            @click="emit('reselect')"
          >
            {{ RESELECT_LABEL }}
          </button>
          <button
            type="button"
            class="selection-rewrite-modal__action"
            data-test="selection-rewrite-conflict-cancel"
            @click="emit('dismiss-conflict')"
          >
            {{ CANCEL_LABEL }}
          </button>
        </div>
      </div>

      <p
        v-if="applying"
        class="selection-rewrite-modal__status"
        data-test="selection-rewrite-applying-status"
      >
        {{ APPLYING_LABEL }}
      </p>

      <div class="selection-rewrite-modal__body">
        <section class="selection-rewrite-modal__column">
          <h4>{{ SOURCE_LABEL }}</h4>
          <div class="selection-rewrite-modal__content">{{ sourceText }}</div>
        </section>
        <section class="selection-rewrite-modal__column">
          <h4>{{ RESULT_LABEL }}</h4>
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
      <p class="selection-rewrite-modal__meta">
        {{ `字数：${wordCountBefore} -> ${wordCountAfter}` }}
        <span v-if="modeLabel">{{ ` | 模式：${modeLabel}` }}</span>
      </p>

      <footer v-if="!conflicted" class="selection-rewrite-modal__actions">
        <button
          v-if="!editMode"
          type="button"
          class="selection-rewrite-modal__action"
          data-test="selection-rewrite-edit"
          :disabled="applying"
          @click="editMode = true"
        >
          {{ EDIT_FIRST_LABEL }}
        </button>
        <button
          v-if="editMode"
          type="button"
          data-test="selection-rewrite-confirm-edit"
          class="selection-rewrite-modal__action"
          :class="{ 'selection-rewrite-modal__action--primary': waitingUserAction }"
          :disabled="applying"
          @click="confirmEditedAccept"
        >
          {{ CONFIRM_EDIT_LABEL }}
        </button>
        <button
          v-if="!editMode"
          type="button"
          data-test="selection-rewrite-accept"
          class="selection-rewrite-modal__action"
          :class="{ 'selection-rewrite-modal__action--primary': waitingUserAction }"
          :disabled="applying"
          @click="emitAccept(false)"
        >
          {{ ACCEPT_LABEL }}
        </button>
        <button
          type="button"
          class="selection-rewrite-modal__action"
          data-test="selection-rewrite-reject"
          :disabled="applying"
          @click="rejectCurrent"
        >
          {{ REJECT_LABEL }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const PREVIEW_TITLE = '改写结果预览'
const CLOSE_LABEL = '关闭'
const WAITING_LABEL = '等待你确认'
const DEFAULT_CONFLICT_MESSAGE = '原文已变化，请重新选择。'
const RESELECT_LABEL = '重新选择'
const CANCEL_LABEL = '取消'
const APPLYING_LABEL = '正在应用…'
const SOURCE_LABEL = '原文'
const RESULT_LABEL = '改写结果'
const EDIT_FIRST_LABEL = '编辑后接受'
const CONFIRM_EDIT_LABEL = '确认编辑并接受'
const ACCEPT_LABEL = '直接接受'
const REJECT_LABEL = '拒绝'

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
  },
  applying: {
    type: Boolean,
    default: false
  },
  waitingUserAction: {
    type: Boolean,
    default: false
  },
  conflicted: {
    type: Boolean,
    default: false
  },
  conflictMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'update:modelValue',
  'update:editedText',
  'accept',
  'reject',
  'reselect',
  'dismiss-conflict'
])

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
  z-index: 88;
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 0;
  background: rgba(15, 23, 42, 0.42);
}

.selection-rewrite-modal__panel {
  width: min(860px, 100%);
  height: 100%;
  border-radius: 24px;
  background: var(--studio-card-bg, var(--ink-surface-1));
  color: var(--studio-title, var(--ink-text-primary));
  padding: 24px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
}

.selection-rewrite-modal__panel--fullscreen {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.selection-rewrite-modal__header,
.selection-rewrite-modal__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.selection-rewrite-modal__header h3,
.selection-rewrite-modal__column h4 {
  margin: 0;
  color: var(--studio-title, var(--ink-text-primary));
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
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 16px;
  padding: 16px;
  background: var(--studio-surface, var(--ink-surface-2));
  color: var(--studio-title, var(--ink-text-primary));
  line-height: 1.7;
}

.selection-rewrite-modal__textarea {
  width: 100%;
  resize: vertical;
  font: inherit;
}

.selection-rewrite-modal__summary,
.selection-rewrite-modal__meta {
  color: var(--studio-muted, var(--ink-text-secondary));
}

.selection-rewrite-modal__waiting {
  margin: 0 0 12px;
  border: 1px solid var(--ink-accent, var(--ink-primary));
  border-radius: 12px;
  background: var(--ink-primary-soft, rgba(79, 124, 255, 0.1));
  padding: 10px 12px;
  color: var(--ink-accent, var(--ink-primary));
  font-size: 13px;
  font-weight: 600;
}

.selection-rewrite-modal__conflict {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 12px;
  border: 1px solid color-mix(in srgb, var(--ink-warning, #ff9800) 74%, white);
  border-radius: 12px;
  background: color-mix(in srgb, var(--ink-warning, #ff9800) 14%, transparent);
  padding: 10px 12px;
  color: color-mix(in srgb, var(--ink-warning, #ff9800) 80%, black);
  font-size: 13px;
  font-weight: 600;
}

.selection-rewrite-modal__conflict-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-rewrite-modal__status {
  margin: 0;
  color: var(--ink-accent, var(--ink-primary));
  font-size: 13px;
}

.selection-rewrite-modal__action {
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 999px;
  background: var(--studio-surface, var(--ink-surface-2));
  padding: 10px 16px;
  color: var(--studio-title, var(--ink-text-primary));
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.selection-rewrite-modal__action--primary {
  border-color: var(--ink-accent, var(--ink-primary));
  background: var(--ink-accent, var(--ink-primary));
  color: white;
}

.selection-rewrite-modal__action--warning {
  border-color: var(--ink-warning, #ff9800);
  background: var(--ink-warning, #ff9800);
  color: white;
}

.selection-rewrite-modal__close {
  border: none;
  background: transparent;
  color: var(--studio-muted, var(--ink-text-secondary));
  cursor: pointer;
}

.selection-rewrite-modal__close:disabled,
.selection-rewrite-modal__actions button:disabled,
.selection-rewrite-modal__conflict-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

@media (max-width: 880px) {
  .selection-rewrite-modal__panel {
    padding: 18px;
  }

  .selection-rewrite-modal__body {
    grid-template-columns: 1fr;
  }
}
</style>
