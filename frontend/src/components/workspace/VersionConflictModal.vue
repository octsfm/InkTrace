<template>
  <div v-if="modelValue" class="modal-mask">
    <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="version-conflict-title">
      <div class="modal-header">
        <div>
          <h3 id="version-conflict-title">检测到版本冲突</h3>
          <p>{{ description }}</p>
        </div>
      </div>

      <div class="modal-body">
        <p>您当前编辑的章节，在云端已经被其他设备或标签页更新过。</p>
        <p>如果继续保存，将会覆盖云端的最新内容。</p>
      </div>

      <div class="modal-footer">
        <button type="button" class="ghost-button" @click="$emit('discard')">放弃本地修改，重新加载云端</button>
        <button type="button" class="danger-button" @click="$emit('override')">强制覆盖云端</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  description: {
    type: String,
    default: '检测到远端已存在新版本，请先决定是否覆盖。'
  }
})

defineEmits(['discard', 'override'])
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-panel {
  width: min(640px, 100%);
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 32px 80px rgba(15, 23, 42, 0.18);
}

.modal-header,
.modal-footer {
  padding: 20px 24px;
}

.modal-header {
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.modal-header p {
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
}

.modal-body {
  display: grid;
  gap: 12px;
  padding: 24px;
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
}

.modal-body p {
  margin: 0;
}

.modal-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid #e5e7eb;
}

.ghost-button,
.danger-button {
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.ghost-button {
  background: #f3f4f6;
  color: #111827;
}

.danger-button {
  background: #dc2626;
  color: #ffffff;
}
</style>
