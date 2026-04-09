<template>
  <div class="workspace-page">
    <section class="page-hero">
      <div class="hero-copy">
        <div class="hero-eyebrow">Chapters</div>
        <h1>章节管理工作台</h1>
        <p>统一处理章节顺序、状态和批量查看，正文编辑仍然回到 Writing 视图。</p>
      </div>
      <div class="hero-chip-row">
        <div class="hero-chip">
          <span class="chip-label">章节总数</span>
          <span class="chip-value">{{ workspace.state.chapters?.length || 0 }}</span>
        </div>
        <div class="hero-chip">
          <span class="chip-label">当前视图</span>
          <span class="chip-value">{{ viewMode === 'list' ? '列表' : '看板' }}</span>
        </div>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <div>
            <h2>章节管理</h2>
            <p>章节树、章节表和看板应共享同一份章节对象状态。</p>
          </div>
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

      <div v-if="focusedChapter" class="focus-banner">
        当前聚焦：{{ focusedChapter.title || `第 ${focusedChapter.chapter_number || '?'} 章` }}
      </div>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'" class="list-view">
        <el-table
          ref="tableRef"
          :data="workspace.state.chapters"
          row-key="id"
          style="width: 100%"
          class="custom-table"
          :show-header="true"
          :row-class-name="getRowClassName"
          @row-click="focusChapter"
        >
          <el-table-column prop="chapter_number" label="序号" width="80" align="center" />
          <el-table-column prop="title" label="章节标题" min-width="250">
            <template #default="{ row }">
              <div class="chapter-title-cell">
                <span class="title-text">{{ row.title || '未命名章节' }}</span>
                <el-tag v-if="focusedChapterId === row.id" size="small" type="primary" effect="plain">
                  当前对象
                </el-tag>
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
              <el-button size="small" @click.stop="focusChapter(row)">聚焦</el-button>
              <el-button size="small" type="primary" plain @click.stop="workspace.openChapter(row.id)">进入写作</el-button>
              <el-button size="small" text @click.stop="openLegacyEditor(row.id)">旧版</el-button>
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
                :class="{ focused: focusedChapterId === chapter.id }"
                :ref="(el) => setChapterCardRef(chapter.id, el)"
                :data-chapter-id="chapter.id"
                @click="focusChapter(chapter)"
              >
                <div class="card-number">第 {{ chapter.chapter_number }} 章</div>
                <div class="card-title">{{ chapter.title || '未命名' }}</div>
                <div class="card-meta">
                  <span>{{ formatWordCount(chapter.word_count || (chapter.content ? chapter.content.length : 0)) }} 字</span>
                  <span>{{ formatDateShort(chapter.updated_at) }}</span>
                </div>
                <div class="card-actions">
                  <el-button size="small" type="primary" plain @click.stop="workspace.openChapter(chapter.id)">进入写作</el-button>
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
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { useWorkspaceStore } from '@/stores/workspace'

const router = useRouter()
const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()

const viewMode = ref('list') // 'list' | 'kanban'
const tableRef = ref(null)
const chapterCardRefs = ref({})

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

const focusedChapterId = computed(() => {
  if (workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.id) {
    return String(workspaceStore.currentObject.id)
  }
  return String(workspaceStore.currentChapterId || '')
})

const focusedChapter = computed(() => (
  (workspace.state.chapters || []).find((chapter) => chapter.id === focusedChapterId.value) || null
))

const setChapterCardRef = (chapterId, el) => {
  if (!chapterId) return
  if (!el) {
    delete chapterCardRefs.value[chapterId]
    return
  }
  chapterCardRefs.value[chapterId] = el
}

const focusChapter = (chapter) => {
  if (!chapter?.id) return
  workspaceStore.currentChapterId = chapter.id
  workspaceStore.setCurrentObject({
    type: 'chapter',
    id: chapter.id,
    title: chapter.title || ''
  })
}

const getRowClassName = ({ row }) => (
  row?.id && row.id === focusedChapterId.value ? 'chapter-row-focused' : ''
)

const scrollToFocusedChapter = async (chapterId) => {
  if (!chapterId) return
  await nextTick()

  if (viewMode.value === 'kanban') {
    const element = chapterCardRefs.value[chapterId]
    if (element?.scrollIntoView) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
    return
  }

  const tableEl = tableRef.value?.$el
  const targetRow = tableEl?.querySelector('.chapter-row-focused')
  if (targetRow?.scrollIntoView) {
    targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
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

watch(
  () => [focusedChapterId.value, viewMode.value],
  ([chapterId]) => {
    if (!chapterId) return
    void scrollToFocusedChapter(chapterId)
  },
  { immediate: true }
)
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  padding: 32px;
  background-color: #F8FAFC;
  height: 100%;
  overflow-y: auto;
  gap: 24px;
}

.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border-radius: 24px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.page-hero h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #111827;
}

.page-hero p {
  margin: 0;
  max-width: 760px;
  font-size: 14px;
  line-height: 1.7;
  color: #4B5563;
}

.hero-chip-row {
  display: flex;
  gap: 12px;
}

.hero-chip {
  min-width: 120px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
}

.chip-label {
  display: block;
  font-size: 12px;
  color: #9CA3AF;
}

.chip-value {
  display: block;
  margin-top: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.workspace-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.focus-banner {
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #DBEAFE;
  background-color: #EFF6FF;
  color: #1D4ED8;
  font-size: 13px;
  font-weight: 600;
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

.header-left p {
  margin-top: 6px;
  font-size: 14px;
  color: #6B7280;
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

.custom-table :deep(.chapter-row-focused td) {
  background-color: #EFF6FF !important;
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
  border-radius: 16px;
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
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
}

.kanban-card:hover {
  transform: translateY(-2px);
  border-color: #D1D5DB;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.kanban-card.focused {
  border-color: #93C5FD;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
  box-shadow: 0 14px 26px rgba(59, 130, 246, 0.10);
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

.card-actions {
  margin-top: 12px;
}

@media (max-width: 1100px) {
  .page-hero {
    flex-direction: column;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
