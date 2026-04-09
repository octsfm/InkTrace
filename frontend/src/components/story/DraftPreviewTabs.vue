<template>
  <el-card shadow="never" class="draft-preview-tabs">
    <template #header>
      <div class="header-row">
        <div>
          <div class="eyebrow">Drafts</div>
          <span class="panel-title">{{ title }}</span>
        </div>
        <el-tag v-if="usedStructuralFallback" type="warning" effect="plain">当前默认展示结构稿</el-tag>
      </div>
    </template>
    <el-tabs :model-value="activeTab" @update:model-value="$emit('update:activeTab', $event)">
      <el-tab-pane label="结构稿" name="structural">
        <div v-if="!structuralDraft" class="empty-text">暂无结构稿</div>
        <template v-else>
          <div class="draft-title">{{ structuralDraft.title || '未命名章节' }}</div>
          <pre class="draft-content">{{ structuralDraft.content || '暂无正文' }}</pre>
          <div class="action-row">
            <el-button type="primary" @click="$emit('apply', { type: 'structural', mode: 'replace' })">覆盖正文</el-button>
            <el-button @click="$emit('apply', { type: 'structural', mode: 'append' })">插入正文末尾</el-button>
            <el-button @click="$emit('save-draft', { type: 'structural' })">保存为草稿</el-button>
            <el-button @click="$emit('discard', { type: 'structural' })">放弃</el-button>
          </div>
        </template>
      </el-tab-pane>
      <el-tab-pane label="去模板化稿" name="detemplated">
        <div v-if="!detemplatedDraft" class="empty-text">暂无去模板化稿</div>
        <template v-else>
          <el-alert
            v-if="detemplatedDraft.display_fallback_to_structural"
            type="warning"
            show-icon
            :closable="false"
            title="当前默认展示结构稿，改写稿存在一致性风险，可查看但请谨慎采纳"
          />
          <div class="draft-title">{{ detemplatedDraft.title || '未命名章节' }}</div>
          <pre class="draft-content">{{ detemplatedDraft.content || '暂无正文' }}</pre>
          <div class="action-row">
            <el-button type="primary" @click="$emit('apply', { type: 'detemplated', mode: 'replace' })">覆盖正文</el-button>
            <el-button @click="$emit('apply', { type: 'detemplated', mode: 'append' })">插入正文末尾</el-button>
            <el-button @click="$emit('save-draft', { type: 'detemplated' })">保存为草稿</el-button>
            <el-button @click="$emit('discard', { type: 'detemplated' })">放弃</el-button>
          </div>
        </template>
      </el-tab-pane>
      <el-tab-pane label="校验结果" name="integrity">
        <div v-if="!integrityCheck" class="empty-text">暂无校验结果</div>
        <template v-else>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="事件一致性">{{ yesNo(integrityCheck.event_integrity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="动机一致性">{{ yesNo(integrityCheck.motivation_integrity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="伏笔一致性">{{ yesNo(integrityCheck.foreshadowing_integrity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="钩子一致性">{{ yesNo(integrityCheck.hook_integrity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="承接一致性">{{ yesNo(integrityCheck.continuity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="剧情弧一致性">{{ yesNo(integrityCheck.arc_consistency_ok) }}</el-descriptions-item>
            <el-descriptions-item label="标题一致性">{{ yesNo(integrityCheck.title_alignment_ok) }}</el-descriptions-item>
            <el-descriptions-item label="推进性一致性">{{ yesNo(integrityCheck.progression_integrity_ok) }}</el-descriptions-item>
            <el-descriptions-item label="修订状态">
              <span>{{ revisionSummary }}</span>
              <el-tag v-if="integrityCheck.revision_succeeded" type="success" size="small" class="inline-tag">修订成功</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="integrityCheck.revision_suggestion" label="修订建议">
              {{ integrityCheck.revision_suggestion }}
            </el-descriptions-item>
            <el-descriptions-item label="风险说明">
              {{ riskNotesText }}
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="issueList.length" class="issue-block">
            <div class="issue-title">问题单</div>
            <div class="issue-list">
              <el-alert
                v-for="(item, index) in issueList"
                :key="`${item.code || 'issue'}-${index}`"
                :title="item.title || '未命名问题'"
                :type="severityType(item.severity)"
                :description="item.detail || ''"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </template>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'AI 结果区'
  },
  activeTab: {
    type: String,
    default: 'structural'
  },
  structuralDraft: {
    type: Object,
    default: null
  },
  detemplatedDraft: {
    type: Object,
    default: null
  },
  integrityCheck: {
    type: Object,
    default: null
  },
  revisionAttempts: {
    type: Array,
    default: () => []
  },
  usedStructuralFallback: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:activeTab', 'apply', 'save-draft', 'discard'])

const yesNo = (value) => (value === false ? '否' : '是')
const issueList = computed(() => (Array.isArray(props.integrityCheck?.issue_list) ? props.integrityCheck.issue_list : []))
const riskNotesText = computed(() => {
  const notes = Array.isArray(props.integrityCheck?.risk_notes) ? props.integrityCheck.risk_notes : []
  return notes.length ? notes.join('；') : '无'
})
const revisionSummary = computed(() => {
  if (Array.isArray(props.revisionAttempts) && props.revisionAttempts.length) {
    return `已尝试 ${props.revisionAttempts.length} 次`
  }
  return props.integrityCheck?.revision_attempted ? '已尝试修订' : '未尝试修订'
})
const severityType = (severity) => {
  if (severity === 'high') return 'error'
  if (severity === 'medium') return 'warning'
  return 'info'
}
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9CA3AF;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.draft-preview-tabs {
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.draft-title {
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.draft-content {
  white-space: pre-wrap;
  line-height: 1.75;
  max-height: 420px;
  overflow: auto;
  padding: 18px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  color: #374151;
}

.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.empty-text {
  color: #9CA3AF;
}

.issue-block {
  margin-top: 16px;
}

.issue-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.issue-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.inline-tag {
  margin-left: 8px;
}
</style>
