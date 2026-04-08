<template>
  <div class="workspace-page">
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
  background-color: #ffffff;
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
  border-radius: 16px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
}

.hero-card.primary {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
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
  border-radius: 12px;
  background-color: #ffffff;
  border: 1px solid #E5E7EB;
}

.suggestion-card h4 {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
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
  border-radius: 12px;
  background-color: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.recent-item:hover {
  background-color: #F3F4F6;
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
  .hero-grid,
  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
