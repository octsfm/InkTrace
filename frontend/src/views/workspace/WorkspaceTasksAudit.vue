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
          v-for="item in filterOptions"
          :key="item.key"
          type="button"
          class="filter-chip"
          :class="{ active: workspaceStore.currentTaskFilter === item.key }"
          @click="workspaceStore.setTaskFilter(item.key)"
        >
          {{ item.label }}
        </button>
      </div>

      <div v-if="focusBannerText" class="focus-banner">
        {{ focusBannerText }}
      </div>

      <div class="status-grid">
        <article class="status-card" :class="getStatusCardClass(statusText)">
          <div class="card-header">
            <el-icon class="card-icon"><Monitor /></el-icon>
            <div class="card-title">当前状态</div>
          </div>
          <div class="status-value">{{ statusText }}</div>
          <p class="status-hint">{{ statusHint }}</p>
        </article>
        
        <article class="status-card">
          <div class="card-header">
            <el-icon class="card-icon"><Timer /></el-icon>
            <div class="card-title">最近进度</div>
          </div>
          <div class="status-value">{{ progressText }}</div>
          <el-progress 
            :percentage="workspace.state.organizeProgress?.progress || 0" 
            :status="getProgressStatus(statusText)"
            :show-text="false"
            class="progress-bar"
          />
          <p class="status-hint">第一阶段先把任务入口收口，后续再接完整日志和 trace。</p>
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

      <div v-if="filteredTaskCards.length" class="history-grid">
        <article
          v-for="task in filteredTaskCards"
          :key="task.id"
          :ref="(el) => setTaskCardRef(task.id, el)"
          class="history-card"
          :class="{ focused: focusedTaskId === task.id }"
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
          <p class="history-desc">{{ task.description }}</p>
          <div class="history-footer">
            <span>{{ task.hint }}</span>
            <el-button v-if="task.actionLabel" size="small" plain @click.stop="runTaskAction(task)">
              {{ task.actionLabel }}
            </el-button>
          </div>
        </article>
      </div>
    </section>

    <!-- Placeholder for future task list -->
    <section class="workspace-section mt-6">
      <div class="section-header">
        <div class="header-left">
          <h3>任务历史</h3>
        </div>
      </div>
      <el-empty :description="historyEmptyText" />
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

const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const runningAction = ref('')
const taskCardRefs = ref({})

const filterOptions = [
  { key: 'all', label: '全部任务' },
  { key: 'running', label: '运行中' },
  { key: 'failed', label: '失败任务' },
  { key: 'completed', label: '已完成' },
  { key: 'audit', label: '审查结果' }
]

const statusText = computed(() => {
  const status = String(workspace.state.organizeProgress?.status || '').trim()
  if (!status) return '未运行'
  if (status === 'running') return '整理中'
  if (status === 'paused') return '已暂停'
  if (status === 'success' || status === 'done') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  return status
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

const progressText = computed(() => `${workspace.state.organizeProgress?.progress ?? 0}%`)

const statusHint = computed(() => {
  return workspace.state.organizeProgress?.error_message || '如果任务异常，可以在这里统一重试、暂停或恢复。'
})

const virtualTaskCards = computed(() => {
  const cards = []
  const organizeStatus = String(workspace.state.organizeProgress?.status || '').trim()
  const organizeStatusLabelMap = {
    running: '运行中',
    paused: '已暂停',
    success: '已完成',
    done: '已完成',
    failed: '失败',
    error: '失败'
  }
  cards.push({
    id: 'organize-task',
    type: 'organize',
    status: organizeStatus || 'idle',
    statusLabel: organizeStatusLabelMap[organizeStatus] || '未运行',
    title: '全书整理任务',
    subtitle: `当前进度 ${workspace.state.organizeProgress?.progress ?? 0}%`,
    description: workspace.state.organizeProgress?.error_message || '负责导入后整理、结构分析与相关写回。',
    hint: organizeStatus === 'failed' || organizeStatus === 'error' ? '建议先查看失败原因，再重试整理。' : '可在上方任务控制台执行暂停、恢复或取消。',
    actionLabel: (organizeStatus === 'failed' || organizeStatus === 'error') ? '重新整理' : ''
  })

  if (workspaceStore.currentTask?.id) {
    const task = workspaceStore.currentTask
    const labelMap = {
      running: '运行中',
      completed: '已完成',
      failed: '失败'
    }
    cards.push({
      id: task.id,
      type: task.type || 'task',
      status: task.status || 'idle',
      statusLabel: labelMap[task.status] || task.status || '待命中',
      title: task.label || '当前任务',
      subtitle: task.chapterId ? `章节 ${task.chapterId}` : '当前工作区任务',
      description: task.error || '当前工作区最近一次 AI/校验任务状态。',
      hint: task.status === 'failed' ? '如需恢复，可回到写作页重新发起。' : '可切换回对应工作区继续处理。',
      actionLabel: task.status === 'failed' ? '回到写作' : ''
    })
  }

  return cards
})

const filteredTaskCards = computed(() => {
  const filter = workspaceStore.currentTaskFilter
  const cards = virtualTaskCards.value
  if (filter === 'all') return cards
  if (filter === 'running') return cards.filter((item) => item.status === 'running')
  if (filter === 'failed') return cards.filter((item) => ['failed', 'error'].includes(item.status))
  if (filter === 'completed') return cards.filter((item) => ['completed', 'success', 'done'].includes(item.status))
  if (filter === 'audit') return cards.filter((item) => item.type === 'audit')
  return cards
})

const focusedTaskId = computed(() => (
  workspaceStore.currentObject?.type === 'task' ? String(workspaceStore.currentObject?.taskId || '') : ''
))

const focusBannerText = computed(() => {
  if (workspaceStore.currentObject?.type === 'task' && workspaceStore.currentObject?.title) {
    return `当前聚焦：${workspaceStore.currentObject.title}`
  }
  const filter = filterOptions.find((item) => item.key === workspaceStore.currentTaskFilter)
  return filter ? `当前筛选：${filter.label}` : ''
})

const historyEmptyText = computed(() => (
  filteredTaskCards.value.length ? '更完整的任务历史和 trace 将在后续接入。' : '当前筛选下暂无任务记录。'
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
    status: task.status
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
  if (task.id === 'organize-task' && task.actionLabel === '重新整理') {
    await retryOrganize()
    return
  }

  if (task.status === 'failed') {
    workspace.openSection?.('writing')
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
  .status-grid {
    grid-template-columns: 1fr;
  }

  .page-hero {
    flex-direction: column;
  }
}
</style>
