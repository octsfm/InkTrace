<template>
  <div class="workspace-page">
    <section class="page-hero">
      <div class="hero-copy">
        <div class="hero-eyebrow">Tasks</div>
        <h1>任务与恢复工作台</h1>
        <p>这里展示运行状态、异常恢复和操作入口，不再把任务页做成原始日志堆。</p>
      </div>
      <div class="hero-chip-row">
        <div class="hero-chip">
          <span class="chip-label">当前状态</span>
          <span class="chip-value">{{ statusText }}</span>
        </div>
        <div class="hero-chip">
          <span class="chip-label">最近进度</span>
          <span class="chip-value">{{ progressText }}</span>
        </div>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h2>任务与审查</h2>
          <p>查看后台运行的结构整理、内容审查和导入分析任务状态，并在此处理异常或重试。</p>
        </div>
      </div>

      <div class="filter-row">
        <button
          v-for="item in props.filterOptions"
          :key="item.key"
          type="button"
          class="filter-chip"
          :class="{ active: workspaceStore.currentTaskFilter === item.key }"
          @click="workspaceStore.setTaskFilter(item.key)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="summary-chip-row">
        <div v-for="item in props.summaryChips" :key="item.label" class="summary-chip">
          <span class="summary-chip-label">{{ item.label }}</span>
          <span class="summary-chip-value">{{ item.value }}</span>
        </div>
      </div>

      <div class="workspace-action-row">
        <button type="button" class="workspace-action-chip primary" @click="workspace.openSection?.('overview')">
          回到概览
        </button>
        <button type="button" class="workspace-action-chip" @click="workspace.openSection?.('structure')">
          查看结构
        </button>
        <button type="button" class="workspace-action-chip" @click="workspace.openSection?.('chapters')">
          查看章节
        </button>
      </div>

      <div v-if="focusBannerText" class="focus-banner">
        {{ focusBannerText }}
      </div>

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
            <el-button size="small" type="primary" plain @click="runTaskAction({ action: item.action })">
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
                  <div class="history-meta">{{ task.subtitle }}</div>
                </div>
                <el-tag size="small" :type="getTaskTagType(task.status)" effect="plain">
                  {{ task.statusLabel }}
                </el-tag>
              </div>
              <div class="history-chip-row">
                <span class="history-chip type">{{ task.typeLabel }}</span>
                <span class="history-chip">{{ task.targetLabel }}</span>
              </div>
              <p class="history-desc">{{ task.description }}</p>
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

    <!-- Placeholder for future task list -->
    <section class="workspace-section mt-6">
      <div class="section-header">
        <div class="header-left">
          <h3>任务历史</h3>
        </div>
      </div>
      <el-empty :description="props.historyEmptyText" />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Timer, Refresh, VideoPlay, VideoPause, Close } from '@element-plus/icons-vue'

import { contentApi } from '@/api'
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
  }
})

const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const runningAction = ref('')
const taskCardRefs = ref({})

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


const focusedTaskId = computed(() => (
  workspaceStore.currentObject?.type === 'task' ? String(workspaceStore.currentObject?.taskId || '') : ''
))

const setTaskCardRef = (taskId, el) => {
  if (!taskId) return
  if (!el) {
    delete taskCardRefs.value[taskId]
    return
  }
  taskCardRefs.value[taskId] = el
}

const focusTask = (task) => {
  workspaceStore.setCurrentObject({
    type: 'task',
    taskId: task.id,
    title: task.title,
    status: task.status,
    chapterId: task.chapterId || '',
    targetArcId: task.targetArcId || ''
  })
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

const runTaskAction = async (task) => {
  if (task.action?.type === 'retry-organize') {
    await retryOrganize()
    return
  }

  if (task.action?.type === 'chapter' && task.action.chapterId) {
    await workspace.openChapter?.(task.action.chapterId, 'writing')
    return
  }

  if (task.action?.type === 'arc' && task.action.arcId) {
    workspaceStore.setCurrentObject({
      type: 'plot_arc',
      arcId: task.action.arcId,
      title: task.action.title || task.title
    })
    workspace.openSection?.('structure')
    return
  }

  if (task.action?.type === 'task-filter') {
    workspaceStore.setTaskFilter(task.action.filter || 'all')
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
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.filter-chip {
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #6B7280;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-chip:hover {
  background-color: #F9FAFB;
  border-color: #D1D5DB;
}

.filter-chip.active {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
  color: #1D4ED8;
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

.summary-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.workspace-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.workspace-action-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #4B5563;
  font-size: 12px;
  cursor: pointer;
}

.workspace-action-chip.primary {
  border-color: #BFDBFE;
  background-color: #EFF6FF;
  color: #1D4ED8;
}

.summary-chip {
  min-width: 96px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.summary-chip-label {
  display: block;
  font-size: 11px;
  color: #9CA3AF;
}

.summary-chip-value {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
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
</style>
