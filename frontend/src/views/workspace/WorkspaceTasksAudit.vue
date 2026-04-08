<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h2>任务与审查</h2>
          <p>查看后台运行的结构整理、内容审查和导入分析任务状态，并在此处理异常或重试。</p>
        </div>
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
    </section>

    <!-- Placeholder for future task list -->
    <section class="workspace-section mt-6">
      <div class="section-header">
        <div class="header-left">
          <h3>任务历史</h3>
        </div>
      </div>
      <el-empty description="暂无任务历史记录，近期完成的任务将会显示在这里。" />
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Timer, Refresh, VideoPlay, VideoPause, Close } from '@element-plus/icons-vue'

import { contentApi } from '@/api'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const workspace = useWorkspaceContext()
const runningAction = ref('')

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
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  padding: 32px;
  background-color: #ffffff;
  height: 100%;
  overflow-y: auto;
  gap: 24px;
}

.workspace-section {
  display: flex;
  flex-direction: column;
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
  border-radius: 16px;
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
  border-radius: 16px;
  background-color: #ffffff;
  border: 1px solid #E5E7EB;
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
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
