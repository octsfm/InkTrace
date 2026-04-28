<template>
  <div v-if="modelValue" class="modal-mask" @click.self="close">
    <div class="modal-panel">
      <div class="modal-header">
        <div>
          <h3>导入 TXT</h3>
          <p>输入本地 TXT 路径后，系统会创建作品并导入章节。</p>
        </div>
        <button type="button" class="ghost-button" @click="close">关闭</button>
      </div>

      <div class="modal-body">
        <label class="field-block">
          <span class="field-label">TXT 路径</span>
          <input v-model="form.file_path" class="field-input" placeholder="例如：D:\drafts\novel.txt" />
        </label>

        <label class="field-block">
          <span class="field-label">作品标题</span>
          <input v-model="form.title" class="field-input" placeholder="可选，不填则使用文件名" />
        </label>

        <label class="field-block">
          <span class="field-label">作者</span>
          <input v-model="form.author" class="field-input" placeholder="可选" />
        </label>
      </div>

      <div class="modal-footer">
        <button type="button" class="ghost-button" @click="close">取消</button>
        <button type="button" class="primary-button" :disabled="submitting" @click="submit">
          {{ submitting ? '导入中...' : '开始导入' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { v1IOApi } from '@/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'imported'])

const form = reactive({
  file_path: '',
  title: '',
  author: ''
})

const submitting = ref(false)

const resetForm = () => {
  form.file_path = ''
  form.title = ''
  form.author = ''
}

const close = () => {
  emit('update:modelValue', false)
}

const submit = async () => {
  if (submitting.value) return
  if (!String(form.file_path || '').trim()) {
    ElMessage.warning('请输入 TXT 文件路径。')
    return
  }
  submitting.value = true
  try {
    const work = await v1IOApi.importTxt({
      file_path: form.file_path.trim(),
      title: form.title.trim(),
      author: form.author.trim()
    })
    ElMessage.success('TXT 导入成功')
    emit('imported', work)
    close()
    resetForm()
  } catch (error) {
    console.error('导入 TXT 失败:', error)
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      resetForm()
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
  width: min(560px, 100%);
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
  line-height: 1.6;
  color: #6b7280;
}

.modal-body {
  display: grid;
  gap: 16px;
  padding: 24px;
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

.field-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
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
