<template>
  <div class="workspace-page">
    <WorkspacePageHero
      eyebrow="章节"
      title="章节管理工作台"
      description="统一处理章节顺序、状态和批量查看，正文编辑仍然回到写作视图。"
    >
      <WorkspaceHeroChips :items="heroChipItems" />
    </WorkspacePageHero>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <div>
              <h2>{{ sectionTitle }}</h2>
              <p>{{ sectionDescription }}</p>
            </div>
            <div class="view-switch">
              <el-radio-group v-model="viewMode" size="small">
                <el-radio-button label="list">列表视图</el-radio-button>
                <el-radio-button label="kanban">看板视图</el-radio-button>
              </el-radio-group>
            </div>
          </div>
        </template>
        <template #actions>
          <div class="header-actions">
            <el-button type="primary" @click="workspace.createChapter">
              <el-icon><Plus /></el-icon>新建章节
            </el-button>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <WorkspaceSummaryChips :items="chapterSummaryItems" />

      <WorkspaceSelectableChips :items="quickChapterItems" :selected-key="focusedChapterId" />

      <WorkspaceSelectableChips :items="statusFilterItems" :selected-key="selectedStatusFilter" />

      <WorkspaceActionBar :items="workspaceActionItems" />

      <WorkspaceInfoBanner :text="modeBannerText" />
      <WorkspaceStatePanel
        v-if="chapterStatePanel"
        :tone="chapterStatePanel.tone"
        :tag="chapterStatePanel.tag"
        :title="chapterStatePanel.title"
        :description="chapterStatePanel.description"
        :caption="chapterStatePanel.caption"
        :actions="chapterStatePanel.actions"
        @action="runChapterStateAction"
      />

      <WorkspaceInfoBanner
        v-if="focusedChapter"
        :text="`当前聚焦：${focusedChapter.title || `第 ${focusedChapter.chapter_number || '?'} 章`}`"
        tone="primary"
      />

      <div v-if="focusedChapter" class="focus-grid">
        <article class="focus-card">
          <div class="focus-label">当前章节</div>
          <h3>{{ focusedChapter.title || `第 ${focusedChapter.chapter_number || '?'} 章` }}</h3>
          <p>第 {{ focusedChapter.chapter_number || '?' }} 章 · {{ formatStatus(focusedChapter.normalizedStatus) }}</p>
        </article>
        <article class="focus-card">
          <div class="focus-label">内容体量</div>
          <h3>{{ formatWordCount(focusedChapter.word_count || (focusedChapter.content ? focusedChapter.content.length : 0)) }}</h3>
          <p>最近更新：{{ formatDate(focusedChapter.updated_at) }}</p>
        </article>
        <article class="focus-card">
          <div class="focus-label">下一步建议</div>
          <h3>{{ focusedChapterNextStep.title }}</h3>
          <p>{{ focusedChapterNextStep.description }}</p>
        </article>
      </div>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'" class="list-view">
        <el-table
          ref="tableRef"
          :data="filteredChapters"
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
                <el-tag size="small" :type="getStatusType(row.normalizedStatus)" class="status-tag" effect="plain">
                  {{ formatStatus(row.normalizedStatus) }}
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
              <el-button size="small" text @click.stop="openChapterWorkspace(row.id)">章节编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else class="kanban-view">
        <div class="kanban-columns">
          <div
            v-for="col in kanbanColumns"
            :key="col.status"
            class="kanban-column"
            :class="{ 'kanban-column-drop-active': dragOverStatus === col.status }"
          >
            <div class="column-header">
              <span class="column-title">{{ col.label }}</span>
              <span class="column-count">{{ getFilteredChaptersByStatus(col.status).length }}</span>
            </div>
            <div
              class="column-body"
              @dragover.prevent="handleDragOver(col.status)"
              @dragenter.prevent="handleDragOver(col.status)"
              @dragleave="handleDragLeave(col.status)"
              @drop.prevent="handleDrop(col.status)"
            >
              <div 
                v-for="chapter in getFilteredChaptersByStatus(col.status)" 
                :key="chapter.id" 
                class="kanban-card"
                :class="{ focused: focusedChapterId === chapter.id, dragging: draggingChapterId === chapter.id }"
                :ref="(el) => setChapterCardRef(chapter.id, el)"
                :data-chapter-id="chapter.id"
                draggable="true"
                @dragstart="handleDragStart(chapter)"
                @dragend="handleDragEnd"
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
              <div v-if="!getFilteredChaptersByStatus(col.status).length" class="kanban-empty">
                当前筛选下没有{{ col.label }}章节
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
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { novelApi } from '@/api'
import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar.vue'
import WorkspaceHeroChips from '@/components/workspace/WorkspaceHeroChips.vue'
import WorkspaceInfoBanner from '@/components/workspace/WorkspaceInfoBanner.vue'
import WorkspacePageHero from '@/components/workspace/WorkspacePageHero.vue'
import WorkspaceSelectableChips from '@/components/workspace/WorkspaceSelectableChips.vue'
import WorkspaceSectionHeader from '@/components/workspace/WorkspaceSectionHeader.vue'
import WorkspaceStatePanel from '@/components/workspace/WorkspaceStatePanel.vue'
import WorkspaceSummaryChips from '@/components/workspace/WorkspaceSummaryChips.vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { useWorkspaceStore } from '@/stores/workspace'
import { buildWorkspaceResultLabel } from './workspaceTaskModel'

const router = useRouter()
const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()

const viewMode = ref('list') // 'list' | 'kanban'
const selectedStatusFilter = ref('all')
const tableRef = ref(null)
const chapterCardRefs = ref({})
const draggingChapterId = ref('')
const dragOverStatus = ref('')
const workspaceActionItems = computed(() => ([
  {
    label: '回到概览',
    primary: true,
    onClick: () => workspace.openSection?.('overview')
  },
  {
    label: '查看结构',
    onClick: () => workspace.openSection?.('structure')
  },
  ...(focusedChapterId.value ? [{
    label: '进入当前章节写作',
    onClick: () => workspace.openChapter?.(focusedChapterId.value)
  }] : [])
]))
const statusFilterItems = computed(() => (
  statusFilters.value.map((item) => ({
    ...item,
    onClick: () => {
      selectedStatusFilter.value = item.key
    }
  }))
))
const quickChapterItems = computed(() => (
  topUpdatedChapters.value.map((chapter) => ({
    key: chapter.id,
    label: chapter.title || `第 ${chapter.chapter_number || '?'} 章`,
    onClick: () => focusChapter(chapter)
  }))
))
const heroChipItems = computed(() => ([
  { label: '章节总数', value: String(workspace.state.chapters?.length || 0) },
  { label: '当前视图', value: viewMode.value === 'list' ? '列表' : '看板' },
  { label: '当前筛选', value: currentFilterLabel.value.replace(/\s+\(\d+\)$/, '') }
]))
const sectionTitle = computed(() => (
  viewMode.value === 'list' ? '章节列表管理' : '章节看板管理'
))
const sectionDescription = computed(() => (
  viewMode.value === 'list'
    ? '按更新时间、字数和状态快速核对章节对象，再决定进入写作或继续整理。'
    : '按章节状态统一巡视推进节奏，优先定位还未完成收口的章节。'
))
const chapterSummaryItems = computed(() => ([
  { label: '草稿', value: String(getChaptersByStatus('draft').length) },
  { label: '已校验', value: String(getChaptersByStatus('reviewed').length) },
  { label: '最近更新', value: latestUpdatedLabel.value }
]))

const statusFilters = computed(() => ([
  { key: 'all', label: `全部 (${(workspace.state.chapters || []).length || 0})` },
  { key: 'drafting', label: `构思中 (${getChaptersByStatus('drafting').length})` },
  { key: 'draft', label: `草稿 (${getChaptersByStatus('draft').length})` },
  { key: 'reviewed', label: `已校验 (${getChaptersByStatus('reviewed').length})` },
  { key: 'confirmed', label: `已确认 (${getChaptersByStatus('confirmed').length})` }
]))

const kanbanColumns = [
  { label: '构思中', status: 'drafting' },
  { label: '草稿', status: 'draft' },
  { label: '已校验', status: 'reviewed' },
  { label: '已确认', status: 'confirmed' }
]

const chapterStatusMap = {
  idea: 'drafting',
  outline: 'drafting',
  drafting: 'drafting',
  planned: 'drafting',
  saved: 'draft',
  writing: 'draft',
  draft: 'draft',
  reviewed: 'reviewed',
  checked: 'reviewed',
  analyzed: 'reviewed',
  confirmed: 'confirmed',
  completed: 'confirmed',
  done: 'confirmed',
  final: 'confirmed',
  published: 'confirmed'
}

const resolveChapterStatus = (chapter = {}) => {
  const rawStatus = String(chapter.status || '').trim().toLowerCase()
  if (chapterStatusMap[rawStatus]) {
    return chapterStatusMap[rawStatus]
  }

  const issueCount = Number(chapter.integrity_check?.issue_list?.length || 0)
  if (issueCount > 0 || chapter.integrity_check) {
    return 'reviewed'
  }

  if (chapter.detemplated_draft || chapter.structural_draft) {
    return 'draft'
  }

  if (chapter.outline?.goal && !String(chapter.content || '').trim()) {
    return 'drafting'
  }

  if (String(chapter.content || '').trim() || chapter.updated_at) {
    return 'draft'
  }

  return 'drafting'
}

const normalizedChapters = computed(() => (
  (workspace.state.chapters || []).map((chapter) => ({
    ...chapter,
    normalizedStatus: resolveChapterStatus(chapter)
  }))
))

const getChaptersByStatus = (status) => {
  return normalizedChapters.value.filter((chapter) => chapter.normalizedStatus === status)
}

const filteredChapters = computed(() => {
  if (selectedStatusFilter.value === 'all') {
    return normalizedChapters.value
  }
  return getChaptersByStatus(selectedStatusFilter.value)
})

const currentFilterLabel = computed(() => (
  statusFilters.value.find((item) => item.key === selectedStatusFilter.value)?.label || '全部'
))
const modeBannerText = computed(() => {
  if (viewMode.value === 'kanban') {
    return `当前筛选：${currentFilterLabel.value}；看板视图更适合按状态巡视章节流转。`
  }
  return `当前筛选：${currentFilterLabel.value}；列表视图更适合核对字数、更新时间和当前对象。`
})

const getFilteredChaptersByStatus = (status) => (
  filteredChapters.value.filter((chapter) => chapter.normalizedStatus === status)
)

const focusedChapterId = computed(() => {
  if (workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.id) {
    return String(workspaceStore.currentObject.id)
  }
  return String(workspaceStore.currentChapterId || '')
})

const focusedChapter = computed(() => (
  normalizedChapters.value.find((chapter) => chapter.id === focusedChapterId.value) || null
))
const taskCenterSnapshot = computed(() => workspaceStore.taskCenterSnapshot || { tasks: [], failedCount: 0 })
const focusedChapterTasks = computed(() => {
  const chapterId = String(focusedChapter.value?.id || '')
  if (!chapterId) return []
  return (taskCenterSnapshot.value.tasks || []).filter((task) => String(task.chapterId || '') === chapterId)
})
const focusedChapterPrimaryTask = computed(() => (
  focusedChapterTasks.value.find((task) => task.status === 'failed')
  || focusedChapterTasks.value.find((task) => task.resultType === 'issues')
  || focusedChapterTasks.value.find((task) => ['candidate', 'diff'].includes(String(task.resultType || '')))
  || focusedChapterTasks.value[0]
  || null
))
const chapterStatePanel = computed(() => {
  if (!normalizedChapters.value.length) {
    return {
      tone: 'warning',
      tag: '空状态',
      title: '当前还没有章节对象',
      description: '建议先创建第一章，之后再通过写作、任务和结构页继续闭环。',
      caption: '章节为空',
      actions: [
        { key: 'create-chapter', label: '新建章节', primary: true },
        { key: 'open-overview', label: '回到概览' }
      ]
    }
  }
  if (!focusedChapter.value && normalizedChapters.value.length) {
    return {
      tone: 'info',
      tag: '聚焦',
      title: '当前还没有聚焦章节',
      description: '先聚焦一个章节，再决定进入写作、结构或查看任务闭环。',
      caption: viewMode.value === 'list' ? '列表视图' : '看板视图',
      actions: [
        { key: 'focus-latest', label: '聚焦最近章节', primary: true },
        { key: 'open-writing', label: '进入写作' }
      ]
    }
  }
  if (focusedChapter.value && focusedChapterPrimaryTask.value) {
    const task = focusedChapterPrimaryTask.value
    const resultLabel = task.resultType
      ? buildWorkspaceResultLabel(task.resultType, { noneLabel: '章节任务', rewriteVariant: 'draft' })
      : '章节任务'
    return {
      tone: task.status === 'failed' ? 'danger' : 'info',
      tag: task.status === 'failed' ? '恢复' : '结果',
      title: task.status === 'failed'
        ? `当前章节存在失败任务：${task.label}`
        : `当前章节最近回流：${resultLabel}`,
      description: task.status === 'failed'
        ? '建议先恢复这个章节关联任务，再继续正文或结构推进。'
        : '可以直接跳转到当前章节的对应结果区域，继续完成写作闭环。',
      caption: focusedChapter.value.title,
      actions: [
        {
          key: task.status === 'failed' ? 'open-failed-tasks' : 'open-focused-result',
          label: task.status === 'failed' ? '看失败任务' : `查看${resultLabel}`,
          primary: true
        },
        { key: 'open-writing', label: '进入写作' }
      ]
    }
  }
  return null
})
const focusedChapterNextStep = computed(() => {
  const status = focusedChapter.value?.normalizedStatus || 'draft'
  const map = {
    drafting: {
      title: '先补结构与目标',
      description: '当前章节仍在构思中，适合先回到结构或继续补全章节目标。'
    },
    draft: {
      title: '继续正文写作',
      description: '当前章节仍是草稿状态，适合回到写作台继续推进正文。'
    },
    reviewed: {
      title: '处理审查结果',
      description: '当前章节已校验，适合先处理问题单或补全需要修复的片段。'
    },
    confirmed: {
      title: '准备推进下一章',
      description: '当前章节已确认，可转向下一章或回到结构台确认后续推进。'
    }
  }
  return map[status] || map.draft
})

const sortedByUpdated = computed(() => {
  return [...normalizedChapters.value].sort((a, b) => {
    const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
    const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
    return bTs - aTs
  })
})

const latestUpdatedLabel = computed(() => {
  const chapter = sortedByUpdated.value[0]
  if (!chapter) return '未记录'
  return chapter.title || `第 ${chapter.chapter_number || '?'} 章`
})

const topUpdatedChapters = computed(() => sortedByUpdated.value.slice(0, 4))

const setChapterCardRef = (chapterId, el) => {
  if (!chapterId) return
  if (!el) {
    delete chapterCardRefs.value[chapterId]
    return
  }
  chapterCardRefs.value[chapterId] = el
}

const patchChapterStatusLocally = (chapterId, nextStatus) => {
  const chapterList = Array.isArray(workspace.state.chapters) ? workspace.state.chapters : []
  const target = chapterList.find((item) => String(item.id) === String(chapterId))
  if (!target) return null

  const previousStatus = target.status
  target.status = nextStatus
  target.updated_at = new Date().toISOString()
  return previousStatus
}

const persistChapterStatus = async (chapterId, nextStatus) => {
  const novelId = workspace.state.novel?.id
  if (!novelId || !chapterId) return
  await novelApi.updateChapter(novelId, chapterId, { status: nextStatus })
}

const focusChapter = (chapter) => {
  if (!chapter?.id) return
  workspaceStore.focusChapterObject({
    id: chapter.id,
    title: chapter.title || ''
  }, { openView: false })
}

const handleDragStart = (chapter) => {
  if (!chapter?.id) return
  draggingChapterId.value = String(chapter.id)
}

const handleDragOver = (status) => {
  dragOverStatus.value = String(status || '')
}

const handleDragLeave = (status) => {
  if (dragOverStatus.value === String(status || '')) {
    dragOverStatus.value = ''
  }
}

const handleDragEnd = () => {
  draggingChapterId.value = ''
  dragOverStatus.value = ''
}

const handleDrop = async (status) => {
  const chapterId = String(draggingChapterId.value || '')
  const nextStatus = String(status || '')
  if (!chapterId || !nextStatus) {
    handleDragEnd()
    return
  }

  const chapter = normalizedChapters.value.find((item) => String(item.id) === chapterId) || null
  if (!chapter || chapter.normalizedStatus === nextStatus) {
    handleDragEnd()
    return
  }

  const previousStatus = patchChapterStatusLocally(chapterId, nextStatus)
  focusChapter({
    ...chapter,
    status: nextStatus,
    normalizedStatus: nextStatus
  })
  handleDragEnd()

  try {
    await persistChapterStatus(chapterId, nextStatus)
    ElMessage.success(`已移动到${formatStatus(nextStatus)}`)
  } catch (error) {
    if (previousStatus !== null) {
      patchChapterStatusLocally(chapterId, previousStatus)
    }
    ElMessage.error(error?.message || '章节状态更新失败')
  }
}

const runChapterStateAction = (key) => {
  if (key === 'create-chapter') {
    workspace.createChapter?.()
    return
  }
  if (key === 'open-overview') {
    workspace.openSection?.('overview')
    return
  }
  if (key === 'focus-latest' && sortedByUpdated.value[0]) {
    focusChapter(sortedByUpdated.value[0])
    return
  }
  if (key === 'open-failed-tasks') {
    workspaceStore.focusTaskFilter('failed', { openView: false })
    workspace.openSection?.('tasks')
    return
  }
  if (key === 'open-focused-result' && focusedChapterPrimaryTask.value) {
    workspace.executeWorkspaceAction?.({
      type: 'writing-result',
      chapterId: focusedChapter.value?.id || '',
      resultType: focusedChapterPrimaryTask.value.resultType || 'candidate',
      taskId: focusedChapterPrimaryTask.value.id,
      title: focusedChapterPrimaryTask.value.label || focusedChapter.value?.title || ''
    })
    return
  }
  if (key === 'open-writing' && sortedByUpdated.value[0]) {
    workspace.openChapter?.((focusedChapter.value?.id || sortedByUpdated.value[0].id))
  }
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

const openChapterWorkspace = (chapterId) => {
  router.push({
    path: `/novel/${workspace.state.novel?.id}`,
    query: {
      section: 'writing',
      chapterId
    }
  })
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

.workspace-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.workspace-page :deep(.workspace-summary-row) {
  margin-bottom: 18px;
}

.workspace-page :deep(.workspace-action-row) {
  margin-bottom: 18px;
}

.workspace-page :deep(.workspace-selectable-row) {
  margin-bottom: 18px;
}

.workspace-page :deep(.workspace-info-banner) {
  margin-bottom: 16px;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.focus-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.focus-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
}

.focus-card h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #111827;
}

.focus-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
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

.list-view {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-bottom: 8px;
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
  min-height: 0;
  overflow-x: auto;
  overflow-y: auto;
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

.kanban-column-drop-active {
  border-color: #93C5FD;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.18);
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
  min-height: 220px;
}

.kanban-empty {
  padding: 16px 12px;
  border: 1px dashed #D1D5DB;
  border-radius: 12px;
  background-color: #FFFFFF;
  font-size: 12px;
  line-height: 1.6;
  color: #9CA3AF;
  text-align: center;
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

.kanban-card.dragging {
  opacity: 0.56;
  transform: rotate(1deg);
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

  .focus-grid {
    grid-template-columns: 1fr;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
