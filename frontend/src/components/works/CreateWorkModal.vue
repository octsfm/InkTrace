<template>
  <div v-if="modelValue" class="modal-mask" @click.self="close">
    <div class="modal-panel">
      <div class="modal-header">
        <div>
          <h3>新建作品</h3>
          <p>填写作品标题和作者，创建后将直接进入写作页。</p>
        </div>
        <button type="button" class="ghost-button" @click="close">关闭</button>
      </div>

      <div class="modal-body">
        <label class="field-block">
          <span class="field-label">作品标题</span>
          <input v-model="form.title" class="field-input" placeholder="请输入作品标题" />
        </label>

        <label class="field-block">
          <span class="field-label">作者</span>
          <input v-model="form.author" class="field-input" placeholder="可选" />
        </label>
      </div>

      <div class="modal-footer">
        <button type="button" class="ghost-button" @click="close">取消</button>
        <button type="button" class="primary-button" :disabled="submitting" @click="submit">
          {{ submitting ? '创建中...' : '创建并进入写作' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { v1WorksApi } from '@/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  defaultTitle: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'created'])

const form = reactive({
  title: '',
  author: ''
})

const submitting = ref(false)

const syncDefaultTitle = () => {
  form.title = String(props.defaultTitle || '').trim()
  form.author = ''
}

const close = () => {
  emit('update:modelValue', false)
}

const submit = async () => {
  if (submitting.value) return
  if (!String(form.title || '').trim()) {
    ElMessage.warning('请输入作品标题')
    return
  }
  submitting.value = true
  try {
    const work = await v1WorksApi.create({
      title: form.title.trim(),
      author: form.author.trim()
    })
    ElMessage.success('已创建新作品')
    emit('created', work)
    close()
  } catch (error) {
    console.error('创建作品失败:', error)
    ElMessage.error('创建作品失败，请稍后重试。')
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      syncDefaultTitle()
      return
    }
    if (!submitting.value) {
      syncDefaultTitle()
    }
  },
  { immediate: true }
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
