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
        <p>当前章节在服务端已经存在更新版本。处理前，本地草稿会继续保留。</p>
        <p>继续覆盖会使用本地内容重新提交；放弃本地会重新加载服务端内容。</p>

        <details class="compare-panel">
          <summary>查看本地版本 vs 服务端版本</summary>
          <div class="compare-grid">
            <section class="compare-column">
              <h4>本地版本</h4>
              <pre>{{ localContent || '暂无本地内容' }}</pre>
            </section>
            <section class="compare-column">
              <h4>服务端版本</h4>
              <pre>{{ serverContent || '暂无服务端内容' }}</pre>
            </section>
          </div>
        </details>
      </div>

      <div class="modal-footer">
        <button type="button" class="ink-button ink-button--ghost ghost-button" @click="$emit('cancel')">取消</button>
        <button type="button" class="ink-button ink-button--ghost ghost-button" @click="$emit('discard')">放弃本地，重新加载服务端</button>
        <button type="button" class="ink-button ink-button--danger danger-button" @click="$emit('override')">覆盖服务端</button>
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
    default: '检测到远端已存在新版本，请先决定是否覆盖。'
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
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-panel {
  width: min(760px, 100%);
  border-radius: 24px;
  background: var(--ink-surface-1);
  border: 1px solid var(--ink-border);
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
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink-text-secondary);
}

.modal-body {
  display: grid;
  gap: 12px;
  padding: 24px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-text-secondary);
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
  font-size: 13px;
  color: var(--ink-text-secondary);
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

