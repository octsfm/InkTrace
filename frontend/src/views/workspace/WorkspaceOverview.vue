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
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 18px;
}

.hero-card,
.workspace-section {
  padding: 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 16px 34px rgba(93, 72, 37, 0.07);
}

.hero-card.primary {
  background:
    radial-gradient(circle at top right, rgba(207, 122, 60, 0.14), transparent 28%),
    linear-gradient(135deg, #fff8ee 0%, #fffdf9 100%);
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a86c3b;
}

.hero-card h2 {
  margin-top: 10px;
  font-size: 28px;
  color: #342318;
}

.hero-card p,
.section-header p,
.suggestion-card p {
  margin-top: 8px;
  line-height: 1.7;
  color: #6f5641;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.stat-value {
  margin-top: 16px;
  font-size: 34px;
  font-weight: 700;
  color: #39271b;
}

.stat-meta {
  margin-top: 10px;
  color: #8b6f54;
  line-height: 1.6;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-header h3 {
  font-size: 20px;
  color: #342318;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.suggestion-card {
  padding: 18px;
  border-radius: 18px;
  background: #fff9f1;
}

.suggestion-card h4 {
  font-size: 16px;
  color: #3a291c;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: none;
  border-radius: 18px;
  background: #fff9f1;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.recent-title {
  font-weight: 600;
  color: #3a291c;
}

.recent-meta {
  color: #8b6f54;
  white-space: nowrap;
}

@media (max-width: 1200px) {
  .hero-grid,
  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
