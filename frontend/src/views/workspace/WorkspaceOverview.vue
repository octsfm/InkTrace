<template>
  <div class="workspace-page">
    <WorkspacePageHero
      eyebrow="概览"
      title="小说工作区概览"
      description="这里集中呈现当前小说状态、最近进度和下一步动作，是工作区的轻量总览入口。"
    >
      <WorkspaceHeroChips :items="heroChipItems" />
    </WorkspacePageHero>

    <section class="hero-grid">
      <article class="hero-card primary">
        <div class="eyebrow">当前状态</div>
        <h2>{{ workspace.state.novel?.title || '未命名小说' }}</h2>
        <p>{{ currentProgress }}</p>
        <div class="hero-actions">
          <el-button type="primary" @click="workspace.openSection('writing', chapterQuery)">继续写作</el-button>
          <el-button @click="workspace.openSection('structure')">查看结构</el-button>
        </div>
      </article>

      <article class="hero-card stat">
        <div class="eyebrow">章节总数</div>
        <div class="stat-value">{{ workspace.state.chapters.length }}</div>
        <div class="stat-meta">当前工作区已接入章节目录和写作入口</div>
      </article>

      <article class="hero-card stat">
        <div class="eyebrow">整理状态</div>
        <div class="stat-value">{{ organizeStatus }}</div>
        <div class="stat-meta">{{ organizeHint }}</div>
      </article>
    </section>

    <WorkspaceActionBar :items="workspaceActionItems" />

    <WorkspaceStatePanel
      v-if="overviewStatePanel"
      :tone="overviewStatePanel.tone"
      :tag="overviewStatePanel.tag"
      :title="overviewStatePanel.title"
      :description="overviewStatePanel.description"
      :caption="overviewStatePanel.caption"
      :actions="overviewStatePanel.actions"
      @action="runOverviewStateAction"
    />

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div>
            <h3>建议下一步</h3>
            <p>这里直接根据当前章节、结构焦点和任务状态给出最自然的继续入口。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <div class="suggestion-grid">
        <article v-for="item in workspace.suggestedActions.value" :key="item.key" class="suggestion-card">
          <h4>{{ item.title }}</h4>
          <p>{{ item.description }}</p>
          <el-button type="primary" plain @click="workspace.openSection(item.key, item.key === 'writing' ? chapterQuery : {})">
            {{ item.cta }}
          </el-button>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div>
            <h3>下一步入口</h3>
            <p>这里不只是状态展示，而是把你最可能马上要做的动作直接抬到前面。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <div class="decision-grid">
        <button
          v-for="item in overviewDecisionCards"
          :key="item.key"
          type="button"
          class="decision-card"
          @click="item.onClick"
        >
          <div class="decision-top">
            <span class="decision-tag">{{ item.tag }}</span>
            <span class="decision-cta">{{ item.cta }}</span>
          </div>
          <div class="decision-title">{{ item.title }}</div>
          <p class="decision-description">{{ item.description }}</p>
          <div class="decision-meta">{{ item.meta }}</div>
        </button>
      </div>
    </section>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div>
            <h3>任务快照</h3>
            <p>这里快速提示失败任务、运行中任务和当前最建议处理的任务。</p>
          </div>
        </template>
        <template #actions>
          <el-button text @click="workspace.openSection('tasks')">打开任务台</el-button>
        </template>
      </WorkspaceSectionHeader>

      <div class="task-snapshot-grid">
        <article class="snapshot-card">
          <div class="snapshot-label">失败任务</div>
          <div class="snapshot-value">{{ taskSnapshot.failed }}</div>
          <div class="snapshot-meta">建议优先处理失败链路</div>
        </article>
        <article class="snapshot-card">
          <div class="snapshot-label">运行中</div>
          <div class="snapshot-value">{{ taskSnapshot.running }}</div>
          <div class="snapshot-meta">仍在执行中的任务</div>
        </article>
        <article class="snapshot-card">
          <div class="snapshot-label">审查类</div>
          <div class="snapshot-value">{{ taskSnapshot.audit }}</div>
          <div class="snapshot-meta">结构审查与分析任务</div>
        </article>
      </div>

      <div v-if="taskSnapshot.recommendation" class="task-recommendation-card">
        <div class="task-recommendation-top">
          <span class="decision-tag">{{ taskSnapshot.recommendation.tag }}</span>
          <span class="decision-cta">{{ taskSnapshot.recommendation.meta }}</span>
        </div>
        <div class="decision-title">{{ taskSnapshot.recommendation.title }}</div>
        <p class="decision-description">{{ taskSnapshot.recommendation.description }}</p>
        <el-button type="primary" plain @click="runTaskRecommendation(taskSnapshot.recommendation)">
          {{ taskSnapshot.recommendation.actionLabel || '打开任务台' }}
        </el-button>
      </div>
    </section>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div>
            <h3>最近章节</h3>
            <p>从这里可以直接进入对应章节的工作区写作流，继续正文、结果回流和任务恢复。</p>
          </div>
        </template>
        <template #actions>
          <el-button text @click="workspace.openSection('chapters')">查看全部</el-button>
        </template>
      </WorkspaceSectionHeader>

      <div v-if="recentChapters.length" class="recent-list">
        <button
          v-for="chapter in recentChapters"
          :key="chapter.id"
          type="button"
          class="recent-item"
          @click="workspace.openChapter(chapter.id)"
        >
          <div class="recent-title">
            第 {{ chapter.chapter_number || '?' }} 章 · {{ chapter.title || '未命名章节' }}
          </div>
          <div class="recent-meta">{{ formatDate(chapter.updated_at) }}</div>
        </button>
      </div>
      <el-empty v-else description="当前还没有章节内容。" />
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar.vue'
import WorkspaceHeroChips from '@/components/workspace/WorkspaceHeroChips.vue'
import WorkspacePageHero from '@/components/workspace/WorkspacePageHero.vue'
import WorkspaceSectionHeader from '@/components/workspace/WorkspaceSectionHeader.vue'
import WorkspaceStatePanel from '@/components/workspace/WorkspaceStatePanel.vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const workspace = useWorkspaceContext()
const resourceSnapshot = computed(() => workspace.resourceSnapshot?.value || {})
const taskCenterSnapshot = computed(() => workspace.taskCenterSnapshot?.value || { failedCount: 0, runningCount: 0, auditCount: 0 })
const contextSnapshot = computed(() => workspace.contextSnapshot?.value || {})

const currentProgress = computed(() => {
  return workspace.state.memoryView?.current_progress
    || contextSnapshot.value.contextMeta?.summary
    || '当前还没有形成稳定的结构进度，适合先从章节或结构页开始。'
})

const currentChapterLabel = computed(() => {
  const chapter = (workspace.state.chapters || []).find((item) => item.id === workspace.currentChapterId.value)
  if (!chapter) return '尚未打开'
  return chapter.title || `第 ${chapter.chapter_number || '?'} 章`
})

const overviewDecisionCards = computed(() => workspace.overviewDecisionCards?.value || [])
const taskSnapshot = computed(() => workspace.overviewTaskSnapshot?.value || { failed: 0, running: 0, audit: 0, recommendation: null })

const activeArcCount = computed(() => String((workspace.state.activeArcs || []).length || 0))
const heroChipItems = computed(() => ([
  { label: '当前章节', value: currentChapterLabel.value },
  { label: '活跃剧情弧', value: activeArcCount.value },
  { label: '项目状态', value: resourceSnapshot.value.projectId ? '已绑定' : '待绑定' },
  { label: '失败任务', value: String(taskCenterSnapshot.value.failedCount || taskSnapshot.value.failed || 0) }
]))

const recentChapters = computed(() => {
  return [...(workspace.state.chapters || [])]
    .sort((a, b) => {
      const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return bTs - aTs
    })
    .slice(0, 5)
})

const organizeStatus = computed(() => {
  const status = String(workspace.state.organizeProgress?.status || '').trim()
  if (!status) return '未运行'
  if (status === 'running') return '整理中'
  if (status === 'paused') return '已暂停'
  if (status === 'success' || status === 'done') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  return status
})

const organizeHint = computed(() => {
  if (organizeStatus.value === '整理中') {
    return `当前进度 ${workspace.state.organizeProgress?.progress ?? 0}%`
  }
  if (organizeStatus.value === '失败') {
    return workspace.state.organizeProgress?.error_message || '可前往任务台查看恢复入口。'
  }
  return '任务详情统一收口到任务台。'
})

const chapterQuery = computed(() => (
  workspace.currentChapterId.value
    ? { chapterId: workspace.currentChapterId.value }
    : {}
))

const workspaceActionItems = computed(() => ([
  {
    label: '继续写作',
    primary: true,
    onClick: () => workspace.openSection('writing', chapterQuery.value)
  },
  {
    label: '查看结构',
    onClick: () => workspace.openSection('structure')
  },
  {
    label: '打开任务台',
    onClick: () => workspace.openSection('tasks')
  },
  {
    label: '查看章节',
    onClick: () => workspace.openSection('chapters')
  }
]))

const overviewStatePanel = computed(() => {
  const contextChapterTitle = String(contextSnapshot.value.chapterTitle || '').trim()
  const failedCount = Number(taskSnapshot.value.failed || 0)
  if (!resourceSnapshot.value.projectId) {
    return {
      tone: 'warning',
      tag: '前提缺失',
      title: '当前工作区还未绑定项目',
      description: '未绑定时，结构分析、任务回流和上下文拼装都可能不完整，建议先确认项目链路是否稳定。',
      caption: '项目快照',
      actions: [
        { key: 'open-settings', label: '查看设置', primary: true },
        { key: 'continue-writing', label: '回到写作' }
      ]
    }
  }
  if (!workspace.state.chapters?.length) {
    return {
      tone: 'warning',
      tag: '空状态',
      title: '当前还没有章节内容',
      description: '建议先创建第一章，之后再进入写作、结构或任务闭环。',
      caption: '章节为空',
      actions: [
        { key: 'create-chapter', label: '新建章节', primary: true },
        { key: 'open-chapters', label: '查看章节' }
      ]
    }
  }
  if (!contextChapterTitle && workspace.state.chapters?.length) {
    return {
      tone: 'info',
      tag: '上下文',
      title: '当前还没有稳定的章节上下文快照',
      description: '建议先进入一个章节，让写作、任务和结构页共享同一份上下文基线。',
      caption: resourceSnapshot.value.novelTitle || '工作区快照',
      actions: [
        { key: 'open-chapters', label: '选择章节', primary: true },
        { key: 'continue-writing', label: '回到写作' }
      ]
    }
  }
  if (failedCount > 0) {
    return {
      tone: 'danger',
      tag: '恢复',
      title: `当前有 ${failedCount} 个失败任务待恢复`,
      description: '建议先处理失败链路，再继续写作或结构推进，避免旧结果干扰当前判断。',
      caption: '任务异常',
      actions: [
        { key: 'open-failed-tasks', label: '看失败任务', primary: true },
        { key: 'continue-writing', label: '回到写作' }
      ]
    }
  }
  return null
})

const runOverviewStateAction = (key) => {
  if (key === 'create-chapter') {
    workspace.createChapter?.()
    return
  }
  if (key === 'open-chapters') {
    workspace.openSection('chapters')
    return
  }
  if (key === 'open-settings') {
    workspace.openSection('settings')
    return
  }
  if (key === 'open-failed-tasks') {
    workspace.executeWorkspaceAction?.({ type: 'task-filter', filter: 'failed' })
    return
  }
  if (key === 'continue-writing') {
    workspace.openSection('writing', chapterQuery.value)
  }
}

const runTaskRecommendation = (item) => {
  const action = item?.action || {}
  if (workspace.executeWorkspaceAction && action.type) {
    workspace.executeWorkspaceAction(action)
    return
  }
  if (action.type === 'task-filter') {
    workspace.setTaskFilter?.(action.filter || 'all')
    workspace.openSection('tasks')
    return
  }
  if (action.type === 'chapter' && action.chapterId) {
    workspace.openChapter(action.chapterId)
    return
  }
  if (action.type === 'arc') {
    workspace.openSection('structure')
    return
  }
  workspace.openSection('tasks')
}

const formatDate = (value) => {
  if (!value) return '未记录更新时间'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch (error) {
    return '未记录更新时间'
  }
}
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 32px;
  background-color: #F8FAFC;
  height: 100%;
  overflow-y: auto;
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 16px;
}

.hero-card,
.workspace-section {
  padding: 24px;
  border-radius: 20px;
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.hero-card.primary {
  background: linear-gradient(180deg, #FFFFFF 0%, #F7FAFF 100%);
  border-color: #DCE7F8;
}

.eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6B7280;
}

.hero-card.primary .eyebrow {
  color: #3B82F6;
}

.hero-card h2 {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.hero-card p,
.section-header p,
.suggestion-card p {
  margin-top: 8px;
  line-height: 1.6;
  color: #4B5563;
  font-size: 14px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.stat-value {
  margin-top: 12px;
  font-size: 32px;
  font-weight: 700;
  color: #111827;
}

.stat-meta {
  margin-top: 8px;
  color: #6B7280;
  font-size: 13px;
  line-height: 1.5;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.suggestion-card {
  padding: 16px;
  border-radius: 16px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  transition: all 0.2s ease;
}

.suggestion-card:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.suggestion-card h4 {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.decision-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.workspace-page :deep(.workspace-action-row) {
  margin-bottom: 20px;
}

.task-snapshot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.snapshot-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  transition: all 0.2s ease;
}

.snapshot-card:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.snapshot-label {
  font-size: 12px;
  color: #9CA3AF;
}

.snapshot-value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.snapshot-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #6B7280;
}

.task-recommendation-card {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.task-recommendation-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.decision-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.decision-card:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.decision-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.decision-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  border-radius: 999px;
  padding: 3px 8px;
}

.decision-cta {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
}

.decision-title {
  margin-top: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.decision-description {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.decision-meta {
  margin-top: 12px;
  font-size: 12px;
  color: #9CA3AF;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  background-color: #FFFFFF;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.recent-item:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.recent-title {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.recent-meta {
  font-size: 13px;
  color: #6B7280;
}

@media (max-width: 1200px) {
  .page-hero,
  .hero-grid,
  .suggestion-grid,
  .decision-grid,
  .task-snapshot-grid {
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

  .hero-card,
  .workspace-section {
    padding: 20px;
  }

  .hero-actions,
  .task-recommendation-top,
  .recent-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .recent-item {
    gap: 8px;
  }
}
</style>
