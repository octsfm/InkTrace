<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h2>任务与审查</h2>
          <p>这里承接整理、重试和恢复入口，不再把这些控制按钮散落到详情页和写作页里。</p>
        </div>
      </div>

      <div class="status-grid">
        <article class="status-card">
          <div class="card-title">当前状态</div>
          <div class="status-value">{{ statusText }}</div>
          <p>{{ statusHint }}</p>
        </article>
        <article class="status-card">
          <div class="card-title">最近进度</div>
          <div class="status-value">{{ progressText }}</div>
          <p>第一阶段先把任务入口收口，后续再接完整日志和 trace。</p>
        </article>
      </div>

      <div class="task-actions">
        <el-button :loading="runningAction === 'refresh'" @click="refreshStatus">刷新状态</el-button>
        <el-button :loading="runningAction === 'retry'" type="primary" @click="retryOrganize">重新整理</el-button>
        <el-button
          v-if="workspace.state.organizeProgress?.status === 'running'"
          :loading="runningAction === 'pause'"
          @click="pauseOrganize"
        >
          暂停
        </el-button>
        <el-button
          v-if="workspace.state.organizeProgress?.status === 'paused'"
          :loading="runningAction === 'resume'"
          @click="resumeOrganize"
        >
          恢复
        </el-button>
        <el-button
          v-if="['running', 'paused'].includes(workspace.state.organizeProgress?.status)"
          :loading="runningAction === 'cancel'"
          type="danger"
          plain
          @click="cancelOrganize"
        >
          取消
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

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
  gap: 24px;
}

.workspace-section {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 34px rgba(93, 72, 37, 0.07);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-header h2 {
  color: #342318;
}

.section-header p,
.status-card p {
  margin-top: 8px;
  color: #6f5641;
  line-height: 1.7;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.status-card {
  padding: 18px;
  border-radius: 18px;
  background: #fff9f1;
}

.card-title {
  font-weight: 700;
  color: #3a291c;
}

.status-value {
  margin-top: 14px;
  font-size: 30px;
  font-weight: 700;
  color: #3a291c;
}

.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

@media (max-width: 960px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
