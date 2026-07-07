﻿﻿﻿﻿﻿<template>
  <div v-if="modelValue" class="modal-mask">
    <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="asset-conflict-title">
      <div class="modal-header">
        <div>
          <h3 id="asset-conflict-title">资料版本冲突</h3>
          <p>{{ description }}</p>
        </div>
      </div>

      <div class="modal-body">
        <p>在你明确做出选择之前，本地资料草稿会一直保留。</p>
        <p>选择“覆盖云端”会再次提交本地草稿；选择“放弃本地”会重新加载服务器版本。</p>

        <details class="compare-panel">
          <summary>展开查看本地版本与服务器版本对比</summary>
          <div class="compare-grid">
            <section class="compare-column">
              <h4>本地版本</h4>
              <pre>{{ localContent || '无本地内容' }}</pre>
            </section>
            <section class="compare-column">
              <h4>服务器版本</h4>
              <pre>{{ serverContent || '无服务器内容' }}</pre>
            </section>
          </div>
        </details>
      </div>

      <div class="modal-footer">
        <button type="button" class="ink-button ink-button--ghost ghost-button" @click="$emit('cancel')">取消</button>
        <button type="button" class="ink-button ink-button--ghost ghost-button" @click="$emit('discard')">放弃本地</button>
        <button type="button" class="ink-button ink-button--danger danger-button" @click="$emit('override')">覆盖云端</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  description: {
    type: String,
    default: '当前资料已在其他位置被修改，请选择冲突处理方式。'
  },
  localContent: {
    type: String,
    default: ''
  },
  serverContent: {
    type: String,
    default: ''
  }
})

defineEmits(['cancel', 'discard', 'override'])
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.45);
}

.modal-panel {
  width: min(760px, 100%);
  border: 1px solid var(--ink-border);
  border-radius: 24px;
  background: var(--ink-surface-1);
  box-shadow: 0 32px 80px rgba(15, 23, 42, 0.18);
}

.modal-header,
.modal-footer {
  padding: 20px 24px;
}

.modal-header {
  border-bottom: 1px solid var(--ink-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--ink-text-primary);
}

.modal-header p {
  margin: 8px 0 0;
  color: var(--ink-text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.modal-body {
  display: grid;
  gap: 12px;
  padding: 24px;
  color: var(--ink-text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.modal-body p {
  margin: 0;
}

.compare-panel {
  border: 1px solid var(--ink-border);
  border-radius: 16px;
  padding: 12px 14px;
  background: var(--ink-surface-2);
}

.compare-panel summary {
  cursor: pointer;
  font-weight: 700;
  color: var(--ink-text-primary);
}

.compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.compare-column {
  min-width: 0;
}

.compare-column h4 {
  margin: 0 0 8px;
  color: var(--ink-text-secondary);
  font-size: 13px;
}

.compare-column pre {
  min-height: 96px;
  max-height: 220px;
  overflow: auto;
  margin: 0;
  border: 1px solid var(--ink-border);
  border-radius: 12px;
  background: var(--ink-surface-1);
  padding: 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
}

.modal-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--ink-border);
}

.ghost-button,
.danger-button {
  min-width: 96px;
}

@media (max-width: 760px) {
  .compare-grid {
    grid-template-columns: 1fr;
  }
}
</style>
