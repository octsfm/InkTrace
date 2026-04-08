<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h2>章节管理</h2>
          <div class="view-switch">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button label="list">列表视图</el-radio-button>
              <el-radio-button label="kanban">看板视图</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="workspace.createChapter">
            <el-icon><Plus /></el-icon>新建章节
          </el-button>
        </div>
      </div>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'" class="list-view">
        <el-table :data="workspace.state.chapters" style="width: 100%" class="custom-table" :show-header="true">
          <el-table-column prop="chapter_number" label="序号" width="80" align="center" />
          <el-table-column prop="title" label="章节标题" min-width="250">
            <template #default="{ row }">
              <div class="chapter-title-cell">
                <span class="title-text">{{ row.title || '未命名章节' }}</span>
                <el-tag size="small" :type="getStatusType(row.status)" class="status-tag" effect="plain">
                  {{ formatStatus(row.status) }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="字数" width="120" align="right">
            <template #default="{ row }">
              {{ formatWordCount(row.word_count || (row.content ? row.content.length : 0)) }}
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="180">
            <template #default="{ row }">
              <span class="time-text">{{ formatDate(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" plain @click="workspace.openChapter(row.id)">进入写作</el-button>
              <el-button size="small" text @click="openLegacyEditor(row.id)">旧版</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 看板视图 (Placeholder) -->
      <div v-else class="kanban-view">
        <div class="kanban-columns">
          <div v-for="col in kanbanColumns" :key="col.status" class="kanban-column">
            <div class="column-header">
              <span class="column-title">{{ col.label }}</span>
              <span class="column-count">{{ getChaptersByStatus(col.status).length }}</span>
            </div>
            <div class="column-body">
              <div 
                v-for="chapter in getChaptersByStatus(col.status)" 
                :key="chapter.id" 
                class="kanban-card"
                @click="workspace.openChapter(chapter.id)"
              >
                <div class="card-number">第 {{ chapter.chapter_number }} 章</div>
                <div class="card-title">{{ chapter.title || '未命名' }}</div>
                <div class="card-meta">
                  <span>{{ formatWordCount(chapter.word_count || (chapter.content ? chapter.content.length : 0)) }} 字</span>
                  <span>{{ formatDateShort(chapter.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const router = useRouter()
const workspace = useWorkspaceContext()

const viewMode = ref('list') // 'list' | 'kanban'

const kanbanColumns = [
  { label: '构思中', status: 'drafting' },
  { label: '草稿', status: 'draft' },
  { label: '已校验', status: 'reviewed' },
  { label: '已确认', status: 'confirmed' }
]

const getChaptersByStatus = (status) => {
  // If chapters don't have explicit status yet, put them all in 'draft' for now
  if (!workspace.state.chapters) return []
  return workspace.state.chapters.filter(c => {
    const cStatus = c.status || 'draft'
    return cStatus === status
  })
}

const getStatusType = (status) => {
  switch (status || 'draft') {
    case 'drafting': return 'info'
    case 'draft': return 'warning'
    case 'reviewed': return 'primary'
    case 'confirmed': return 'success'
    default: return 'info'
  }
}

const formatStatus = (status) => {
  const map = {
    drafting: '构思中',
    draft: '草稿',
    reviewed: '已校验',
    confirmed: '已确认'
  }
  return map[status || 'draft'] || '未知'
}

const formatWordCount = (count) => {
  if (!count) return '0'
  return count > 10000 ? (count / 10000).toFixed(1) + '万' : count
}

const formatDate = (value) => {
  if (!value) return '未记录'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    })
  } catch (error) {
    return '未记录'
  }
}

const formatDateShort = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
  } catch (error) {
    return ''
  }
}

const openLegacyEditor = (chapterId) => {
  router.push(`/novel/${workspace.state.novel?.id}/chapters/${chapterId}/edit`)
}
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  padding: 32px;
  background-color: #ffffff;
  height: 100%;
  overflow-y: auto;
}

.workspace-section {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.header-left h2 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.custom-table {
  --el-table-border-color: #F3F4F6;
  --el-table-header-bg-color: #F9FAFB;
  --el-table-header-text-color: #6B7280;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #E5E7EB;
}

.chapter-title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-text {
  font-weight: 500;
  color: #111827;
}

.time-text {
  color: #6B7280;
  font-size: 13px;
}

/* Kanban Styles */
.kanban-view {
  flex: 1;
  overflow-x: auto;
  padding-bottom: 16px;
}

.kanban-columns {
  display: flex;
  gap: 20px;
  height: 100%;
  min-width: max-content;
}

.kanban-column {
  width: 280px;
  display: flex;
  flex-direction: column;
  background-color: #F9FAFB;
  border-radius: 12px;
  border: 1px solid #E5E7EB;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #E5E7EB;
}

.column-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.column-count {
  background-color: #E5E7EB;
  color: #4B5563;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.column-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.kanban-card {
  background-color: #ffffff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.kanban-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  border-color: #D1D5DB;
}

.card-number {
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 4px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9CA3AF;
}
</style>
