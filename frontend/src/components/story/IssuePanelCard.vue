<template>
  <div class="issue-panel-card">
    <div class="header-row">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ subtitle }}</p>
      </div>
      <el-tag size="small" :type="issueCount ? 'warning' : 'success'" effect="plain">
        {{ issueCount ? `${issueCount} 个问题` : '无问题' }}
      </el-tag>
    </div>

    <div v-if="!issueCount" class="empty-copy">
      当前没有问题单，可以继续写作或再次发起审查。
    </div>

    <div v-else class="issue-list">
      <article
        v-for="(issue, index) in issues"
        :key="`${issue.code || 'issue'}-${index}`"
        class="issue-item"
        :class="{ active: activeIssueIndex === index }"
        @mouseenter="$emit('preview', { issue, index })"
        @mouseleave="$emit('preview-leave', { issue, index })"
      >
        <div class="issue-top">
          <div class="issue-main">
            <div class="issue-title-row">
              <span class="issue-title">{{ issue.title || '未命名问题' }}</span>
              <el-tag size="small" :type="severityType(issue.severity)" effect="plain">
                {{ severityLabel(issue.severity) }}
              </el-tag>
            </div>
            <div class="issue-detail">{{ issue.detail || '暂无详细说明。' }}</div>
          </div>
        </div>

        <div class="issue-actions">
          <el-button size="small" type="primary" plain @click="$emit('locate', { issue, index })">
            定位正文
          </el-button>
        </div>
      </article>
    </div>

    <div class="footer-row">
      <el-button size="small" @click="$emit('reanalyze')">重新审查</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '问题单'
  },
  subtitle: {
    type: String,
    default: '优先处理高优先级问题，再重新审查。'
  },
  issues: {
    type: Array,
    default: () => []
  },
  activeIssueIndex: {
    type: Number,
    default: -1
  }
})

defineEmits(['locate', 'reanalyze', 'preview', 'preview-leave'])

const issueCount = computed(() => props.issues.length)

const severityType = (severity) => {
  if (severity === 'high') return 'danger'
  if (severity === 'medium') return 'warning'
  return 'info'
}

const severityLabel = (severity) => {
  if (severity === 'high') return '高'
  if (severity === 'medium') return '中'
  if (severity === 'low') return '低'
  return '信息'
}
</script>

<style scoped>
.issue-panel-card {
  padding: 18px;
  border: 1px solid #E5E7EB;
  border-radius: 18px;
  background-color: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-row h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.header-row p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #6B7280;
}

.empty-copy {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #9CA3AF;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.issue-item {
  padding: 14px;
  border-radius: 14px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  transition: all 0.2s ease;
}

.issue-item.active {
  border-color: #C4B5FD;
  background-color: #F5F3FF;
  box-shadow: 0 8px 18px rgba(124, 58, 237, 0.08);
}

.issue-item:hover {
  border-color: #D1D5DB;
}

.issue-top {
  display: flex;
}

.issue-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.issue-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.issue-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.issue-detail {
  font-size: 13px;
  line-height: 1.6;
  color: #4B5563;
}

.issue-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.footer-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
