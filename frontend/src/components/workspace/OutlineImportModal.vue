<template>
  <div v-if="visible" class="outline-import-modal" role="dialog" aria-modal="true" aria-label="导入作品大纲">
    <div class="outline-import-modal__backdrop" @click="$emit('close')" />
    <section class="outline-import-modal__card">
      <header class="outline-import-modal__header">
        <div>
          <h3>导入作品大纲</h3>
          <p>导入结果只会进入当前草稿，仍需手动保存作品大纲。</p>
        </div>
        <button type="button" class="outline-import-modal__close" aria-label="关闭导入弹窗" @click="$emit('close')">
          关闭
        </button>
      </header>

      <div class="outline-import-modal__body">
        <section class="outline-import-modal__section">
          <span class="outline-import-modal__label">上传文件</span>
          <label class="outline-import-modal__file-trigger">
            <input
              ref="fileInputRef"
              class="outline-import-modal__file-input"
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              data-testid="outline-import-file"
              @change="handleFileChange"
            >
            <span>选择 TXT / Markdown 文件</span>
          </label>
          <p v-if="selectedFileName" class="outline-import-modal__helper">已选择：{{ selectedFileName }}</p>
        </section>

        <section class="outline-import-modal__section">
          <span class="outline-import-modal__label">或粘贴作品大纲</span>
          <textarea
            v-model="inputText"
            class="outline-import-modal__textarea"
            rows="8"
            data-testid="outline-import-paste"
            placeholder="在这里粘贴作品大纲内容。"
            @input="handlePasteInput"
          />
        </section>

        <section class="outline-import-modal__section">
          <div class="outline-import-modal__metrics">
            <span data-testid="outline-import-char-count">当前字符数：{{ charCount }}</span>
            <span v-if="charCount >= OUTLINE_IMPORT_RECOMMEND_THRESHOLD && charCount < OUTLINE_IMPORT_RISK_THRESHOLD" class="outline-import-modal__hint">
              建议控制在 20,000 字以内以获得更好编辑体验。
            </span>
            <span v-if="charCount >= OUTLINE_IMPORT_RISK_THRESHOLD" class="outline-import-modal__hint outline-import-modal__hint--warn">
              当前内容较大，可能影响编辑性能。
            </span>
          </div>
          <p v-if="errorMessage" class="outline-import-modal__error" data-testid="outline-import-error">
            {{ errorMessage }}
          </p>
        </section>

        <section class="outline-import-modal__section">
          <span class="outline-import-modal__label">导入预览</span>
          <pre class="outline-import-modal__preview" data-testid="outline-import-preview">{{ previewText }}</pre>
        </section>

        <section v-if="showMergeMode" class="outline-import-modal__section">
          <span class="outline-import-modal__label">导入方式</span>
          <label class="outline-import-modal__radio">
            <input v-model="importMode" type="radio" value="replace" data-testid="outline-import-mode-replace">
            <span>覆盖当前草稿</span>
          </label>
          <label class="outline-import-modal__radio">
            <input v-model="importMode" type="radio" value="append" data-testid="outline-import-mode-append">
            <span>追加到末尾</span>
          </label>
        </section>
      </div>

      <footer class="outline-import-modal__footer">
        <button type="button" class="ghost-button" @click="$emit('close')">取消</button>
        <button
          type="button"
          class="save-button"
          data-testid="outline-import-confirm"
          :disabled="!canImport"
          @click="handleImport"
        >
          导入到草稿
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import {
  OUTLINE_IMPORT_RECOMMEND_THRESHOLD,
  OUTLINE_IMPORT_RISK_THRESHOLD,
  countOutlineImportCharacters,
  ensureNonEmptyOutlineText,
  readOutlineImportFile
} from '@/utils/outlineImport'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  currentDraftText: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'import'])

const fileInputRef = ref(null)
const selectedFileName = ref('')
const inputText = ref('')
const errorMessage = ref('')
const importMode = ref('replace')

const showMergeMode = computed(() => Boolean(String(props.currentDraftText || '')))
const previewText = computed(() => String(inputText.value || ''))
const charCount = computed(() => countOutlineImportCharacters(previewText.value))
const canImport = computed(() => previewText.value.trim().length > 0 && !errorMessage.value)

const resetState = () => {
  selectedFileName.value = ''
  inputText.value = ''
  errorMessage.value = ''
  importMode.value = 'replace'
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const setImportedText = (text, fileName = '') => {
  selectedFileName.value = String(fileName || '')
  inputText.value = String(text || '')
  errorMessage.value = ''
}

const handlePasteInput = () => {
  selectedFileName.value = ''
  errorMessage.value = ''
}

const handleFileChange = async (event) => {
  const file = event?.target?.files?.[0]
  if (!file) return
  try {
    const text = await readOutlineImportFile(file)
    setImportedText(text, file.name)
  } catch (error) {
    selectedFileName.value = ''
    inputText.value = ''
    errorMessage.value = String(error?.message || '文件读取失败。')
  }
}

const handleImport = () => {
  try {
    ensureNonEmptyOutlineText(previewText.value)
    errorMessage.value = ''
    emit('import', {
      content: previewText.value,
      mode: showMergeMode.value ? importMode.value : 'replace'
    })
  } catch (error) {
    errorMessage.value = String(error?.message || '导入内容不能为空。')
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetState()
    }
  }
)
</script>

<style scoped>
.outline-import-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
}

.outline-import-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
}

.outline-import-modal__card {
  position: relative;
  z-index: 1;
  width: min(760px, calc(100vw - 32px));
  max-height: min(90vh, 860px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
  border-radius: 24px;
  background: #ffffff;
  padding: 20px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.2);
}

.outline-import-modal__header,
.outline-import-modal__footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.outline-import-modal__header h3 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.outline-import-modal__header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.outline-import-modal__body {
  min-height: 0;
  overflow: auto;
  display: grid;
  gap: 16px;
  padding-right: 4px;
}

.outline-import-modal__section {
  display: grid;
  gap: 10px;
}

.outline-import-modal__label {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.outline-import-modal__file-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: fit-content;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #f8fafc;
  padding: 10px 16px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.outline-import-modal__file-input {
  display: none;
}

.outline-import-modal__helper,
.outline-import-modal__metrics,
.outline-import-modal__hint {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.outline-import-modal__metrics {
  display: grid;
  gap: 4px;
}

.outline-import-modal__hint--warn,
.outline-import-modal__error {
  color: #b45309;
}

.outline-import-modal__textarea,
.outline-import-modal__preview {
  width: 100%;
  min-height: 160px;
  border: 1px solid #d1d5db;
  border-radius: 16px;
  background: #ffffff;
  padding: 14px;
  color: #111827;
  font: inherit;
  line-height: 1.7;
}

.outline-import-modal__preview {
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.outline-import-modal__radio {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #374151;
  font-size: 14px;
}

.outline-import-modal__close,
.ghost-button,
.save-button {
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.outline-import-modal__close,
.ghost-button {
  background: #f3f4f6;
  color: #111827;
}

.save-button {
  background: #111827;
  color: #ffffff;
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 760px) {
  .outline-import-modal {
    padding: 16px;
  }

  .outline-import-modal__card {
    width: 100%;
    max-height: calc(100vh - 32px);
    padding: 16px;
  }

  .outline-import-modal__header,
  .outline-import-modal__footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
