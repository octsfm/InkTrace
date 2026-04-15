<template>
  <NodeViewWrapper class="workspace-candidate-node">
    <div class="candidate-node-shell">
      <div class="candidate-node-top">
        <div>
          <div class="candidate-node-tag">{{ node.attrs.resultLabel || '候选稿' }}</div>
          <h4>{{ node.attrs.title || '行内候选块' }}</h4>
        </div>
        <div v-if="node.attrs.hint" class="candidate-node-hint">{{ node.attrs.hint }}</div>
      </div>
      <div class="candidate-node-meta">
        <span>候选 {{ node.attrs.candidateIndex || 1 }} / {{ node.attrs.candidateTotal || 1 }}</span>
        <span v-if="node.attrs.createdAtLabel">{{ node.attrs.createdAtLabel }}</span>
      </div>

      <p v-if="node.attrs.description" class="candidate-node-description">{{ node.attrs.description }}</p>

      <div class="candidate-node-body">
        <div class="candidate-node-label">候选内容</div>
        <pre class="candidate-node-content">{{ node.attrs.resultText || '暂无候选内容' }}</pre>
        <div v-if="candidateSegments.length > 1" class="candidate-node-segments">
          <span class="candidate-node-segment-title">局部采纳</span>
          <button
            v-for="(segment, index) in candidateSegments.slice(0, 3)"
            :key="`segment-${index}`"
            type="button"
            class="candidate-node-segment-action"
            @click="triggerAction('candidate-adopt-segment', { segmentText: segment })"
          >
            采纳片段 {{ index + 1 }}
          </button>
        </div>
      </div>

      <div class="candidate-node-actions">
        <button type="button" class="candidate-node-action" @click="triggerAction('candidate-prev')">
          上一个候选
        </button>
        <button type="button" class="candidate-node-action" @click="triggerAction('candidate-next')">
          下一个候选
        </button>
        <button type="button" class="candidate-node-action primary" @click="triggerAction('apply-structural-append')">
          采纳并插入
        </button>
        <button type="button" class="candidate-node-action" @click="triggerAction('save-structural')">
          保存草稿
        </button>
        <button type="button" class="candidate-node-action" @click="triggerAction('open-draft-panel')">
          查看右侧结果区
        </button>
        <button type="button" class="candidate-node-action subtle" @click="triggerAction('candidate-dismiss')">
          忽略当前候选
        </button>
      </div>
    </div>
  </NodeViewWrapper>
</template>

<script setup>
import { computed } from 'vue'
import { NodeViewWrapper } from '@tiptap/vue-3'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  extension: {
    type: Object,
    required: true
  }
})

const candidateSegments = computed(() => {
  const text = String(props.node?.attrs?.resultText || '')
  return text
    .split(/\r?\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
})

const triggerAction = (key, payload = {}) => {
  props.extension.options.onAction?.(key, {
    ...(props.node?.attrs || {}),
    ...payload
  })
}
</script>

<style scoped>
.workspace-candidate-node {
  margin: 20px 0;
}

.candidate-node-shell {
  border: 1px solid #93C5FD;
  border-radius: 20px;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.10);
  padding: 18px;
}

.candidate-node-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.candidate-node-tag {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6B7280;
}

.candidate-node-top h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.candidate-node-hint {
  font-size: 12px;
  color: #6B7280;
}

.candidate-node-description {
  margin: 10px 0 0;
  color: #4B5563;
  font-size: 13px;
  line-height: 1.7;
}

.candidate-node-meta {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #6B7280;
}

.candidate-node-body {
  margin-top: 14px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #DBEAFE;
  background: #F8FBFF;
}

.candidate-node-segments {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.candidate-node-segment-title {
  font-size: 12px;
  color: #6B7280;
}

.candidate-node-segment-action {
  border: 1px solid #BFDBFE;
  background: #EFF6FF;
  color: #1D4ED8;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}

.candidate-node-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #374151;
}

.candidate-node-content {
  margin: 0;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  color: #1F2937;
}

.candidate-node-actions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.candidate-node-action {
  border: 1px solid #D1D5DB;
  background: #FFFFFF;
  color: #374151;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.candidate-node-action.primary {
  border-color: #2563EB;
  background: #2563EB;
  color: #FFFFFF;
}

.candidate-node-action.subtle {
  color: #6B7280;
}
</style>
