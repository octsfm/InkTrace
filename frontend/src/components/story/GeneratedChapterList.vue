<template>
  <el-card shadow="never">
    <template #header>
      <div class="header-row">
        <span>本次生成章节</span>
        <el-tag type="info">共 {{ generatedChapters.length }} 章</el-tag>
      </div>
    </template>
    <div v-if="!generatedChapters.length" class="empty-text">暂无生成结果</div>
    <el-timeline v-else>
      <el-timeline-item
        v-for="chapter in generatedChapters"
        :key="chapter.chapter_id || `${chapter.chapter_number}-${chapter.title}`"
        :timestamp="`第${chapter.chapter_number || chapter.number}章`"
        placement="top"
      >
        <el-card shadow="hover">
          <div class="row-top">
            <div>
              <div class="chapter-title">{{ chapter.title || '未命名章节' }}</div>
              <div class="chapter-summary">{{ summaryText(chapter.content) }}</div>
              <div v-if="chapterMeta(chapter)" class="chapter-meta">{{ chapterMeta(chapter) }}</div>
            </div>
            <div class="tag-group">
              <el-tag :type="chapter.used_structural_fallback ? 'warning' : 'success'">
                {{ chapter.used_structural_fallback ? '已 fallback' : '正常生成' }}
              </el-tag>
              <el-tag :type="chapter.saved ? 'success' : 'info'">
                {{ chapter.saved ? '已保存' : '待确认' }}
              </el-tag>
            </div>
          </div>
          <div class="action-row">
            <el-button type="primary" link @click="$emit('view', chapter)">查看结果</el-button>
            <el-button type="primary" link @click="$emit('edit', chapter)">跳转章节编辑页</el-button>
          </div>
        </el-card>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<script setup>
defineProps({
  generatedChapters: {
    type: Array,
    default: () => []
  }
})

defineEmits(['view', 'edit'])

const summaryText = (content) => {
  const text = String(content || '').trim()
  return text ? `${text.slice(0, 120)}${text.length > 120 ? '...' : ''}` : '暂无内容摘要'
}

const chapterMeta = (chapter) => {
  const parts = []
  const revisionCount = Array.isArray(chapter?.revision_attempts) ? chapter.revision_attempts.length : 0
  const issueCount = Array.isArray(chapter?.integrity_check?.issue_list) ? chapter.integrity_check.issue_list.length : 0
  if (revisionCount) parts.push(`修订 ${revisionCount} 次`)
  if (issueCount) parts.push(`问题 ${issueCount} 条`)
  return parts.join('，')
}
</script>

<style scoped>
.header-row,
.row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.chapter-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.chapter-summary,
.empty-text {
  color: #606266;
}

.chapter-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

.tag-group,
.action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-row {
  margin-top: 12px;
}
</style>
