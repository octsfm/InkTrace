<template>
  <div v-if="modelValue" class="modal-mask" @click.self="close">
    <div class="modal-panel">
      <div class="modal-header">
        <div>
          <h3>导出 TXT</h3>
          <p>{{ work?.title || '当前作品' }}</p>
        </div>
        <button type="button" class="ghost-button" @click="close">关闭</button>
      </div>

      <div class="modal-body">
        <label class="check-row">
          <input v-model="includeTitles" type="checkbox" />
          <span>包含章节标题</span>
        </label>

        <label class="field-block">
          <span class="field-label">章节间空行</span>
          <select v-model.number="gapLines" class="field-input">
            <option :value="0">0 行</option>
            <option :value="1">1 行</option>
            <option :value="2">2 行</option>
          </select>
        </label>
      </div>

      <div class="modal-footer">
        <button type="button" class="ghost-button" @click="close">取消</button>
        <button type="button" class="primary-button" :disabled="submitting" @click="submit">
          {{ submitting ? '导出中...' : '导出 .txt' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { v1IOApi } from '@/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  work: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'exported'])

const includeTitles = ref(true)
const gapLines = ref(1)
const submitting = ref(false)

const close = () => {
  emit('update:modelValue', false)
}

const resolveExportFileName = () => {
  const safeTitle = String(props.work?.title || 'inktrace-work')
    .replace(/[\\/:*?"<>|]/g, '_')
    .trim() || 'inktrace-work'
  return `${safeTitle}.txt`
}

const resolveFileNameFromDisposition = (disposition = '') => {
  const value = String(disposition || '')
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].trim().replace(/^"|"$/g, ''))
  }
  const plainMatch = value.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] ? plainMatch[1].trim() : ''
}

const triggerDownload = (blob, fileName) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const submit = async () => {
  if (submitting.value || !props.work?.id) return
  submitting.value = true
  try {
    const response = await v1IOApi.exportTxt(props.work.id, {
      include_titles: includeTitles.value,
      gap_lines: gapLines.value
    })
    const blobSource = response?.data ?? response
    const blob = blobSource instanceof Blob
      ? blobSource
      : new Blob([blobSource || ''], { type: 'text/plain;charset=utf-8' })
    const responseFileName = resolveFileNameFromDisposition(response?.headers?.['content-disposition'])
    triggerDownload(blob, responseFileName || resolveExportFileName())
    ElMessage.success('TXT 导出已开始')
    emit('exported', props.work)
    close()
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '导出 TXT 失败，请稍后重试。'
    ElMessage.error(detail)
    console.error('导出 TXT 失败:', error)
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      includeTitles.value = true
      gapLines.value = 1
    }
  }
)
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.38);
  padding: 24px;
}

.modal-panel {
  width: min(480px, 100%);
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.modal-header,
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px;
}

.modal-header {
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.modal-header p {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

.modal-body {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #111827;
}

.field-block {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.field-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 14px;
  color: #111827;
  outline: none;
}

.modal-footer {
  border-top: 1px solid #e5e7eb;
}

.ghost-button,
.primary-button {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #ffffff;
  color: #374151;
}

.primary-button {
  border-color: #2563eb;
  background: #2563eb;
  color: #ffffff;
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
</style>
