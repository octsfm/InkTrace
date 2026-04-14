<template>
  <div class="workspace-page">
    <WorkspacePageHero
      eyebrow="任务"
      title="任务与恢复工作台"
      description="这里展示运行状态、异常恢复和操作入口，不再把任务页做成原始日志堆。"
    >
      <WorkspaceHeroChips :items="heroChipItems" />
    </WorkspacePageHero>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h2>任务与审查</h2>
            <p>查看后台运行的结构整理、内容审查和导入分析任务状态，并在此处理异常或重试。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <WorkspaceSelectableChips :items="filterChipItems" :selected-key="workspaceStore.currentTaskFilter" />

      <WorkspaceSummaryChips :items="props.summaryChips" />

      <WorkspaceActionBar :items="workspaceActionItems" />

      <WorkspaceInfoBanner v-if="focusBannerText" :text="focusBannerText" tone="primary" />
      <WorkspaceStatePanel
        v-if="taskStatePanel"
        :tone="taskStatePanel.tone"
        :tag="taskStatePanel.tag"
        :title="taskStatePanel.title"
        :description="taskStatePanel.description"
        :caption="taskStatePanel.caption"
        :actions="taskStatePanel.actions"
        @action="runTaskStateAction"
      />

      <div class="status-grid">
        <article
          v-for="item in props.statusCards"
          :key="item.label"
          class="status-card"
          :class="getStatusCardClass(item.label === '当前状态' ? item.value : '')"
        >
          <div class="card-header">
            <el-icon class="card-icon"><Monitor v-if="item.label === '当前状态'" /><Timer v-else /></el-icon>
            <div class="card-title">{{ item.label }}</div>
          </div>
          <div class="status-value">{{ item.value }}</div>
          <el-progress
            v-if="item.label === '最近进度'"
            :percentage="workspace.state.organizeProgress?.progress || 0"
            :status="getProgressStatus(props.statusText)"
            :show-text="false"
            class="progress-bar"
          />
          <p class="status-hint">{{ item.hint }}</p>
        </article>
      </div>

      <div class="action-panel">
        <h3>任务控制台</h3>
        <div class="task-actions">
          <el-button :loading="runningAction === 'refresh'" @click="refreshStatus">
            <el-icon><Refresh /></el-icon>刷新状态
          </el-button>
          <el-button :loading="runningAction === 'retry'" type="primary" @click="retryOrganize">
            <el-icon><VideoPlay /></el-icon>重新整理
          </el-button>
          
          <template v-if="workspace.state.organizeProgress?.status === 'running'">
            <el-button :loading="runningAction === 'pause'" type="warning" plain @click="pauseOrganize">
              <el-icon><VideoPause /></el-icon>暂停任务
            </el-button>
          </template>
          
          <template v-if="workspace.state.organizeProgress?.status === 'paused'">
            <el-button :loading="runningAction === 'resume'" type="success" plain @click="resumeOrganize">
              <el-icon><VideoPlay /></el-icon>恢复任务
            </el-button>
          </template>
          
          <template v-if="['running', 'paused'].includes(workspace.state.organizeProgress?.status)">
            <el-button :loading="runningAction === 'cancel'" type="danger" plain @click="cancelOrganize">
              <el-icon><Close /></el-icon>取消任务
            </el-button>
          </template>
        </div>
      </div>

      <div v-if="props.recommendationItems.length" class="recommendation-panel">
        <div class="recommendation-heading">
          <h3>优先处理建议</h3>
          <p>根据当前任务状态，先把最值得你立即处理的任务抬到前面。</p>
        </div>
        <div class="recommendation-grid">
          <article
            v-for="item in props.recommendationItems"
            :key="item.key"
            class="recommendation-card"
          >
            <div class="recommendation-top">
              <span class="recommendation-tag">{{ item.tag }}</span>
              <span class="recommendation-meta">{{ item.meta }}</span>
            </div>
            <div class="recommendation-title">{{ item.title }}</div>
            <p class="recommendation-desc">{{ item.description }}</p>
            <el-button size="small" type="primary" plain @click="runTaskAction({ ...item, action: item.action })">
              {{ item.actionLabel }}
            </el-button>
          </article>
        </div>
      </div>

      <div v-if="props.groupedTaskSections.length" class="task-section-stack">
        <section
          v-for="section in props.groupedTaskSections"
          :key="section.key"
          class="task-subsection"
        >
          <div class="task-subsection-header">
            <div>
              <h3>{{ section.title }} <span class="section-count">{{ section.items.length }}</span></h3>
              <p>{{ section.description }}</p>
            </div>
          </div>
          <div class="history-grid">
            <article
              v-for="task in section.items"
              :key="task.id"
              :ref="(el) => setTaskCardRef(task.id, el)"
              class="history-card"
              :class="taskCardClassMap(task)"
              :data-task-id="task.id"
              @click="focusTask(task)"
            >
              <div class="history-top">
                <div>
                  <div class="history-title">{{ task.title }}</div>
                  <div class="history-meta">
                    <span>{{ task.subtitle }}</span>
                    <span v-if="task.timestampText">· {{ task.timestampText }}</span>
                  </div>
                </div>
                <el-tag size="small" :type="getTaskTagType(task.status)" effect="plain">
                  {{ task.statusLabel }}
                </el-tag>
              </div>
              <div class="history-chip-row">
                <span class="history-chip type">{{ task.typeLabel }}</span>
                <span v-if="task.resultTypeLabel" class="history-chip result">{{ task.resultTypeLabel }}</span>
                <span class="history-chip">{{ task.targetLabel }}</span>
              </div>
              <p class="history-desc">{{ task.description }}</p>
              <div v-if="task.traceItems?.length" class="trace-list">
                <div
                  v-for="trace in task.traceItems"
                  :key="`${task.id}-${trace.label}`"
                  class="trace-item"
                  :class="getTraceToneClass(trace.tone)"
                >
                  <span class="trace-label">{{ trace.label }}</span>
                  <span class="trace-value">{{ trace.value }}</span>
                </div>
              </div>
              <div class="history-note">
                <div class="note-label">失败原因</div>
                <div class="note-value">{{ task.reasonText }}</div>
              </div>
              <div class="history-note">
                <div class="note-label">下一步建议</div>
                <div class="note-value">{{ task.nextStepText }}</div>
              </div>
              <div class="history-footer">
                <span>{{ task.hint }}</span>
                <el-button v-if="task.actionLabel" size="small" plain @click.stop="runTaskAction(task)">
                  {{ task.actionLabel }}
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </div>
    </section>

    <section class="workspace-section mt-6">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h3>{{ props.historyTitle }}</h3>
            <p>{{ props.historyDescription }}</p>
          </div>
        </template>
      </WorkspaceSectionHeader>
      <div v-if="props.timelineItems.length" class="timeline-list">
        <article
          v-for="item in props.timelineItems"
          :key="item.id"
          class="timeline-card"
          :class="getTimelineCardClass(item.status)"
        >
          <div class="timeline-top">
            <div>
              <div class="timeline-title">{{ item.title }}</div>
              <div class="timeline-meta">{{ item.typeLabel }} · {{ item.meta }}</div>
            </div>
            <div class="timeline-side">
              <span class="timeline-time">{{ item.timestampText }}</span>
              <el-tag size="small" :type="getTaskTagType(item.status)" effect="plain">
                {{ item.statusLabel }}
              </el-tag>
            </div>
          </div>
          <p class="timeline-summary">{{ item.summary }}</p>
          <div v-if="item.traceItems?.length" class="timeline-trace-row">
            <span
              v-for="trace in item.traceItems"
              :key="`${item.id}-${trace.label}`"
              class="timeline-trace-chip"
              :class="getTraceToneClass(trace.tone)"
            >
              {{ trace.label }}：{{ trace.value }}
            </span>
          </div>
          <div class="timeline-footer">
            <span>{{ item.resultTypeLabel ? `${item.resultTypeLabel} · ${item.meta}` : item.meta }}</span>
            <el-button v-if="item.actionLabel" size="small" plain @click="runTaskAction(item)">
              {{ item.actionLabel }}
            </el-button>
          </div>
        </article>
      </div>
      <el-empty v-else :description="props.historyEmptyText" />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Timer, Refresh, VideoPlay, VideoPause, Close } from '@element-plus/icons-vue'

import { contentApi } from '@/api'
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

const props = defineProps({
  filterOptions: {
    type: Array,
    default: () => []
  },
  statusText: {
    type: String,
    default: '未运行'
  },
  progressText: {
    type: String,
    default: '0%'
  },
  statusHint: {
    type: String,
    default: ''
  },
  statusCards: {
    type: Array,
    default: () => []
  },
  summaryChips: {
    type: Array,
    default: () => []
  },
  taskCards: {
    type: Array,
    default: () => []
  },
  filteredTaskCards: {
    type: Array,
    default: () => []
  },
  groupedTaskSections: {
    type: Array,
    default: () => []
  },
  recommendationItems: {
    type: Array,
    default: () => []
  },
  focusBannerText: {
    type: String,
    default: ''
  },
  historyEmptyText: {
    type: String,
    default: ''
  },
  historyTitle: {
    type: String,
    default: '最近任务动态'
  },
  historyDescription: {
    type: String,
    default: ''
  },
  timelineItems: {
    type: Array,
    default: () => []
  }
})

const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const runningAction = ref('')
const taskCardRefs = ref({})
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
  {
    label: '查看章节',
    onClick: () => workspace.openSection?.('chapters')
  }
]))
const filterChipItems = computed(() => (
  props.filterOptions.map((item) => ({
    ...item,
    onClick: () => workspaceStore.setTaskFilter(item.key)
  }))
))
const heroChipItems = computed(() => ([
  { label: '当前状态', value: props.statusText },
  { label: '最近进度', value: props.progressText }
]))
const taskStatePanel = computed(() => {
  const hasTasks = Array.isArray(props.taskCards) && props.taskCards.length > 0
  const organizeStatus = String(workspace.state.organizeProgress?.status || '').trim()
  if (!hasTasks && !organizeStatus) {
    return {
      tone: 'info',
      tag: '空状态',
      title: '当前还没有可展示的任务动态',
      description: '适合先回到写作或结构页继续推进；当整理、审查或 AI 任务开始后，这里会形成统一恢复中心。',
      caption: '任务中心',
      actions: [
        { key: 'open-writing', label: '回到写作', primary: true },
        { key: 'open-structure', label: '查看结构' }
      ]
    }
  }
  if (props.statusText === '整理失败' || props.statusText === '失败') {
    return {
      tone: 'danger',
      tag: '恢复',
      title: '最近一次整理失败',
      description: props.statusHint || '建议先恢复整理任务，再继续处理章节或结构工作。',
      caption: '整理异常',
      actions: [
        { key: 'retry-organize', label: '重新整理', primary: true },
        { key: 'focus-failed', label: '看失败任务' }
      ]
    }
  }
  if (props.statusText === '整理已暂停' || props.statusText === '已暂停') {
    return {
      tone: 'warning',
      tag: '恢复',
      title: '整理任务当前已暂停',
      description: '你可以先恢复任务，或保持暂停状态先回到对象页处理。',
      caption: '任务暂停',
      actions: [
        { key: 'resume-organize', label: '恢复任务', primary: true },
        { key: 'open-writing', label: '回到写作' }
      ]
    }
  }
  return null
})

const getStatusCardClass = (status) => {
  if (status === '失败') return 'is-error'
  if (status === '整理中') return 'is-running'
  if (status === '已完成') return 'is-success'
  if (status === '已暂停') return 'is-warning'
  return ''
}

const getProgressStatus = (status) => {
  if (status === '失败') return 'exception'
  if (status === '已完成') return 'success'
  if (status === '已暂停') return 'warning'
  return ''
}


const focusedTaskId = computed(() => workspaceStore.currentTaskFocusId || '')

const setTaskCardRef = (taskId, el) => {
  if (!taskId) return
  if (!el) {
    delete taskCardRefs.value[taskId]
    return
  }
  taskCardRefs.value[taskId] = el
}

const focusTask = (task) => {
  workspaceStore.focusTask({
    id: task.id,
    type: task.type,
    label: task.title,
    status: task.status,
    chapterId: task.chapterId || '',
    targetArcId: task.targetArcId || ''
  }, { openView: false })
}

const scrollToFocusedTask = async (taskId) => {
  if (!taskId) return
  await nextTick()
  const element = taskCardRefs.value[taskId]
  if (element?.scrollIntoView) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

const getTaskTagType = (status) => {
  if (status === 'running') return 'primary'
  if (status === 'failed' || status === 'error') return 'danger'
  if (status === 'completed' || status === 'success' || status === 'done') return 'success'
  if (status === 'paused') return 'warning'
  return 'info'
}

const taskCardClassMap = (task) => ({
  focused: focusedTaskId.value === task.id,
  'is-failed': ['failed', 'error'].includes(task.status),
  'is-running': task.status === 'running',
  'is-audit': String(task.type || '').toLowerCase().includes('audit') || String(task.type || '').toLowerCase().includes('analyze')
})

const getTraceToneClass = (tone) => {
  if (tone === 'danger') return 'is-danger'
  if (tone === 'primary') return 'is-primary'
  return ''
}

const getTimelineCardClass = (status) => ({
  'is-failed': ['failed', 'error'].includes(status),
  'is-running': status === 'running'
})

const runAction = async (name, executor) => {
  runningAction.value = name
  try {
    await executor()
    workspace.state.organizeProgress = await contentApi.organizeProgress(workspace.state.novel?.id)
    await workspace.refreshStructure()
  } finally {
    runningAction.value = ''
  }
}

const refreshStatus = async () => {
  await runAction('refresh', async () => {})
}

const retryOrganize = async () => {
  await runAction('retry', async () => {
    await contentApi.retryOrganize(workspace.state.novel?.id, 'rebuild_global')
    ElMessage.success('已重新发起整理任务')
  })
}

const pauseOrganize = async () => {
  await runAction('pause', async () => {
    await contentApi.pauseOrganize(workspace.state.novel?.id)
    ElMessage.success('已暂停整理任务')
  })
}

const resumeOrganize = async () => {
  await runAction('resume', async () => {
    await contentApi.resumeOrganize(workspace.state.novel?.id, 'rebuild_global')
    ElMessage.success('已恢复整理任务')
  })
}

const cancelOrganize = async () => {
  await runAction('cancel', async () => {
    await contentApi.cancelOrganize(workspace.state.novel?.id)
    ElMessage.success('已取消整理任务')
  })
}

const runTaskStateAction = async (key) => {
  if (key === 'retry-organize') {
    await retryOrganize()
    return
  }
  if (key === 'resume-organize') {
    await resumeOrganize()
    return
  }
  if (key === 'focus-failed') {
    workspaceStore.focusTaskFilter('failed')
    workspace.openSection?.('tasks')
    return
  }
  if (key === 'open-writing') {
    workspace.openSection?.('writing')
    return
  }
  if (key === 'open-structure') {
    workspace.openSection?.('structure')
  }
}

const runTaskAction = async (task) => {
  focusTask(task)

  if (task.action?.type === 'retry-organize') {
    await retryOrganize()
    return
  }

  if (task.action?.type === 'chapter' && task.action.chapterId) {
    await workspace.openChapter?.(task.action.chapterId, 'writing')
    return
  }

  if (task.action?.type === 'writing-result') {
    await workspace.executeWorkspaceAction?.({
      type: 'writing-result',
      chapterId: task.action.chapterId,
      resultType: task.action.resultType,
      taskId: task.action.taskId || task.id,
      title: task.title
    })
    return
  }

  if (task.action?.type === 'arc' && task.action.arcId) {
    workspaceStore.focusPlotArc({
      arcId: task.action.arcId,
      title: task.action.title || task.title
    })
    workspace.openSection?.('structure')
    return
  }

  if (task.action?.type === 'task-filter') {
    workspaceStore.focusTaskFilter(task.action.filter || 'all')
    workspace.openSection?.('tasks')
    return
  }

  if (task.action?.type === 'section') {
    workspace.openSection?.(task.action.section || 'tasks')
    return
  }

  if (task.status === 'failed') {
    workspace.openSection?.('tasks')
  }
}

watch(
  () => focusedTaskId.value,
  (taskId) => {
    if (!taskId) return
    void scrollToFocusedTask(taskId)
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
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.workspace-page :deep(.workspace-selectable-row) {
  margin-bottom: 16px;
}

.workspace-page :deep(.workspace-info-banner) {
  margin-bottom: 16px;
}

.workspace-page :deep(.workspace-action-row) {
  margin-bottom: 16px;
}

.workspace-page :deep(.workspace-summary-row) {
  margin-bottom: 16px;
}

.mt-6 {
  margin-top: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-left h2, .header-left h3 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.header-left h3 {
  font-size: 18px;
}

.header-left p {
  font-size: 14px;
  color: #6B7280;
  margin: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.status-card {
  padding: 24px;
  border-radius: 18px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.status-card:hover,
.recommendation-card:hover,
.timeline-card:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.status-card.is-error {
  background-color: #FEF2F2;
  border-color: #FEE2E2;
}
.status-card.is-error .status-value, .status-card.is-error .card-icon { color: #DC2626; }

.status-card.is-running {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
}
.status-card.is-running .status-value, .status-card.is-running .card-icon { color: #2563EB; }

.status-card.is-success {
  background-color: #F0FDF4;
  border-color: #DCFCE7;
}
.status-card.is-success .status-value, .status-card.is-success .card-icon { color: #16A34A; }

.status-card.is-warning {
  background-color: #FFFBEB;
  border-color: #FEF3C7;
}
.status-card.is-warning .status-value, .status-card.is-warning .card-icon { color: #D97706; }

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 18px;
  color: #6B7280;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

.status-value {
  font-size: 36px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.status-hint {
  font-size: 14px;
  color: #6B7280;
  line-height: 1.5;
  margin: 0;
}

.progress-bar {
  margin: 8px 0;
}

.action-panel {
  padding: 24px;
  border-radius: 18px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
}

.recommendation-panel {
  margin-top: 20px;
  padding: 20px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
}

.recommendation-heading h3,
.task-subsection-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.section-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  margin-left: 8px;
  padding: 0 6px;
  border-radius: 999px;
  background-color: #F3F4F6;
  color: #6B7280;
  font-size: 12px;
  font-weight: 600;
}

.recommendation-heading p,
.task-subsection-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6B7280;
}

.recommendation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.recommendation-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
}

.recommendation-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.recommendation-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  border-radius: 999px;
  padding: 3px 8px;
}

.recommendation-meta {
  font-size: 12px;
  color: #9CA3AF;
}

.recommendation-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.recommendation-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4B5563;
}

.task-section-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 20px;
}

.task-subsection {
  padding-top: 4px;
}

.task-subsection-header {
  margin-bottom: 14px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.history-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-card.is-failed {
  border-color: #FECACA;
  background: linear-gradient(180deg, #FFFFFF 0%, #FEF2F2 100%);
}

.history-card.is-running {
  border-color: #BFDBFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
}

.history-card.is-audit .history-chip.type {
  color: #7C3AED;
  border-color: #DDD6FE;
  background-color: #F5F3FF;
}

.history-card:hover {
  border-color: #D1D5DB;
  transform: translateY(-1px);
}

.history-card.focused {
  border-color: #93C5FD;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
  box-shadow: 0 14px 26px rgba(59, 130, 246, 0.10);
}

.history-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.history-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.history-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #6B7280;
}

.history-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4B5563;
}

.trace-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trace-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  font-size: 11px;
  color: #6B7280;
}

.trace-item.is-primary,
.timeline-trace-chip.is-primary {
  color: #1D4ED8;
  border-color: #DBEAFE;
  background-color: #EFF6FF;
}

.trace-item.is-danger,
.timeline-trace-chip.is-danger {
  color: #B91C1C;
  border-color: #FECACA;
  background-color: #FEF2F2;
}

.trace-label {
  font-weight: 600;
}

.trace-value {
  color: inherit;
}

.history-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  font-size: 11px;
  color: #6B7280;
}

.history-chip.type {
  color: #1D4ED8;
  border-color: #DBEAFE;
  background-color: #EFF6FF;
}

.history-note {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background-color: #FFFFFF;
  border: 1px solid #F3F4F6;
}

.note-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
}

.note-value {
  font-size: 12px;
  line-height: 1.6;
  color: #4B5563;
}

.history-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #9CA3AF;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.timeline-card.is-failed {
  border-color: #FECACA;
  background: linear-gradient(180deg, #FFFFFF 0%, #FEF2F2 100%);
}

.timeline-card.is-running {
  border-color: #BFDBFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
}

.timeline-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.timeline-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.timeline-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #6B7280;
}

.timeline-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.timeline-time {
  font-size: 12px;
  color: #9CA3AF;
}

.timeline-summary {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.timeline-trace-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.timeline-trace-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  font-size: 11px;
  color: #6B7280;
}

.timeline-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #9CA3AF;
}

.action-panel h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.task-actions .el-button {
  display: flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 960px) {
  .page-hero,
  .status-grid,
  .recommendation-grid {
    grid-template-columns: 1fr;
  }

  .page-hero {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .workspace-page {
    padding: 20px;
    gap: 20px;
  }

  .action-panel,
  .recommendation-panel,
  .timeline-card,
  .history-card,
  .status-card {
    padding: 18px;
  }

  .history-top,
  .history-footer,
  .timeline-top,
  .timeline-footer,
  .timeline-side,
  .recommendation-top {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
