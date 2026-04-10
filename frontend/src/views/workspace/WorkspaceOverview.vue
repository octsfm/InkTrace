<template>
  <div class="workspace-page">
    <section class="page-hero">
      <div class="hero-copy">
        <div class="hero-eyebrow">Overview</div>
        <h1>小说工作区概览</h1>
        <p>这里不再是旧详情页，而是当前小说状态、最近进度和下一步动作的轻量总览。</p>
      </div>
      <div class="hero-chip-row">
        <div class="hero-chip">
          <span class="chip-label">当前章节</span>
          <span class="chip-value">{{ currentChapterLabel }}</span>
        </div>
        <div class="hero-chip">
          <span class="chip-label">活跃剧情弧</span>
          <span class="chip-value">{{ activeArcCount }}</span>
        </div>
      </div>
    </section>

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

    <div class="workspace-action-row">
      <button type="button" class="workspace-action-chip primary" @click="workspace.openSection('writing', chapterQuery)">
        继续写作
      </button>
      <button type="button" class="workspace-action-chip" @click="workspace.openSection('structure')">
        查看结构
      </button>
      <button type="button" class="workspace-action-chip" @click="workspace.openSection('tasks')">
        打开任务台
      </button>
      <button type="button" class="workspace-action-chip" @click="workspace.openSection('chapters')">
        查看章节
      </button>
    </div>

    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h3>建议下一步</h3>
          <p>第一阶段先把创作入口、结构入口和任务入口稳定下来。</p>
        </div>
      </div>

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
      <div class="section-header">
        <div>
          <h3>下一步入口</h3>
          <p>这里不只是状态展示，而是把你最可能马上要做的动作直接抬到前面。</p>
        </div>
      </div>

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
      <div class="section-header">
        <div>
          <h3>任务快照</h3>
          <p>这里快速提示失败任务、运行中任务和当前最建议处理的任务。</p>
        </div>
        <el-button text @click="workspace.openSection('tasks')">打开任务台</el-button>
      </div>

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
      <div class="section-header">
        <div>
          <h3>最近章节</h3>
          <p>从这里可以快速进入新写作台，而不需要先回到旧详情页。</p>
        </div>
        <el-button text @click="workspace.openSection('chapters')">查看全部</el-button>
      </div>

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

import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const workspace = useWorkspaceContext()

const currentProgress = computed(() => {
  return workspace.state.memoryView?.current_progress || '当前还没有形成稳定的结构进度，适合先从章节或结构页开始。'
})

const currentChapterLabel = computed(() => {
  const chapter = (workspace.state.chapters || []).find((item) => item.id === workspace.currentChapterId.value)
  if (!chapter) return '尚未打开'
  return chapter.title || `第 ${chapter.chapter_number || '?'} 章`
})

const overviewDecisionCards = computed(() => workspace.overviewDecisionCards?.value || [])
const taskSnapshot = computed(() => workspace.overviewTaskSnapshot?.value || { failed: 0, running: 0, audit: 0, recommendation: null })

const activeArcCount = computed(() => String((workspace.state.activeArcs || []).length || 0))

const recentChapters = computed(() => {
  return [...(workspace.state.chapters || [])]
    .sort((a, b) => (b.chapter_number || 0) - (a.chapter_number || 0))
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
  max-width: 760px;
  margin: 0;
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

.workspace-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
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
</style>
