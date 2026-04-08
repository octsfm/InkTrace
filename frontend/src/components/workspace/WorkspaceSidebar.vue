<template>
  <aside class="workspace-sidebar">
    <!-- Writing View: Chapter Tree -->
    <section v-if="workspaceStore.activeView === 'writing' || workspaceStore.activeView === 'chapters'" class="sidebar-section chapter-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">章节目录</div>
        <button type="button" class="ghost-action" @click="createChapter">
          <el-icon><Plus /></el-icon>
        </button>
      </div>

      <div v-if="!state.chapters || !state.chapters.length" class="sidebar-empty">
        还没有章节，先从导入内容或新建章节开始。
      </div>

      <div v-else class="chapter-list">
        <button
          v-for="chapter in state.chapters"
          :key="chapter.id"
          type="button"
          class="chapter-item"
          :class="{ active: currentChapterId === chapter.id }"
          @click="openChapter(chapter.id)"
        >
          <div class="chapter-number">第 {{ chapter.chapter_number || '?' }} 章</div>
          <div class="chapter-title">{{ chapter.title || '未命名章节' }}</div>
          <div class="chapter-meta">
            <span>{{ chapter.updated_at ? formatDate(chapter.updated_at) : '未记录更新时间' }}</span>
          </div>
        </button>
      </div>
    </section>

    <!-- Structure View: Object Navigation -->
    <section v-else-if="workspaceStore.activeView === 'structure'" class="sidebar-section structure-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">结构导航</div>
      </div>
      <div class="nav-list">
        <button class="nav-item">Story Model</button>
        <button class="nav-item">剧情弧 (PlotArcs)</button>
        <button class="nav-item">角色 (Characters)</button>
        <button class="nav-item">世界观 (Worldview)</button>
      </div>
    </section>

    <!-- Tasks View: Task Filter Navigation -->
    <section v-else-if="workspaceStore.activeView === 'tasks'" class="sidebar-section tasks-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">任务视图</div>
      </div>
      <div class="nav-list">
        <button class="nav-item active">所有任务</button>
        <button class="nav-item">运行中</button>
        <button class="nav-item">失败</button>
        <button class="nav-item">已完成</button>
      </div>
    </section>
    
    <!-- Overview View: Outline/Info -->
    <section v-else-if="workspaceStore.activeView === 'overview'" class="sidebar-section overview-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">概览导航</div>
      </div>
      <div class="nav-list">
        <button class="nav-item active">项目信息</button>
        <button class="nav-item">近期动态</button>
        <button class="nav-item">统计数据</button>
      </div>
    </section>

  </aside>
</template>

<script setup>
import { useWorkspaceStore } from '@/stores/workspace'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { Plus } from '@element-plus/icons-vue'

const workspaceStore = useWorkspaceStore()
const { state, currentChapterId, openChapter, createChapter } = useWorkspaceContext()

const formatDate = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric'
    })
  } catch (error) {
    return ''
  }
}
</script>

<style scoped>
.workspace-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  width: 240px;
  padding: 20px 16px;
  background-color: #ffffff;
  border-right: 1px solid #E5E7EB;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.sidebar-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.sidebar-heading {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ghost-action {
  border: none;
  background: none;
  color: #6B7280;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.ghost-action:hover {
  background-color: #F3F4F6;
  color: #374151;
}

.chapter-list, .nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow-y: auto;
}

.chapter-item, .nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-item {
  flex-direction: row;
  align-items: center;
  color: #4B5563;
  font-size: 14px;
  font-weight: 500;
}

.chapter-item:hover, .nav-item:hover {
  background-color: #F3F4F6;
}

.chapter-item.active, .nav-item.active {
  background-color: #EFF6FF;
  color: #1D4ED8;
}

.chapter-item.active .chapter-title {
  color: #1D4ED8;
}

.chapter-item.active .chapter-number,
.chapter-item.active .chapter-meta {
  color: #60A5FA;
}

.chapter-number {
  font-size: 12px;
  color: #9CA3AF;
}

.chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  line-height: 1.4;
}

.chapter-meta {
  font-size: 12px;
  color: #9CA3AF;
}

.sidebar-empty {
  padding: 16px 12px;
  font-size: 13px;
  color: #6B7280;
  background-color: #F9FAFB;
  border-radius: 8px;
  text-align: center;
}
</style>
