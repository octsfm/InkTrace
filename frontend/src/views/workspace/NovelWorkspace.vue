<template>
  <div class="novel-workspace-layout" :class="{ 'zen-mode': workspaceStore.isZenMode }">
    <!-- 最左：主视图导航栏 -->
    <nav class="workspace-nav-bar" :class="{ 'hidden-in-zen': workspaceStore.isZenMode }">
      <div class="nav-top">
        <el-tooltip content="概览 Overview" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.activeView === 'overview' }" @click="workspaceStore.switchView('overview')">
            <el-icon><Monitor /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="写作 Writing" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.activeView === 'writing' }" @click="workspaceStore.switchView('writing')">
            <el-icon><Edit /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="结构 Structure" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.activeView === 'structure' }" @click="workspaceStore.switchView('structure')">
            <el-icon><DataBoard /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="章节 Chapters" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.activeView === 'chapters' }" @click="workspaceStore.switchView('chapters')">
            <el-icon><Notebook /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="任务 Tasks" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.activeView === 'tasks' }" @click="workspaceStore.switchView('tasks')">
            <el-icon><List /></el-icon>
          </div>
        </el-tooltip>
      </div>
      <div class="nav-bottom">
        <el-tooltip content="返回主页 Dashboard" placement="right">
          <div class="nav-item" @click="goToDashboard">
            <el-icon><House /></el-icon>
          </div>
        </el-tooltip>
      </div>
    </nav>

    <!-- 左二：目录与对象导航区 -->
    <WorkspaceSidebar v-show="!workspaceStore.isZenMode" />

    <!-- 中间：核心内容区 (动态渲染不同视图) -->
    <main class="workspace-main-content">
      <component :is="activeComponent" />
    </main>

    <!-- 右侧：AI Copilot 区 -->
    <WorkspaceCopilotPanel
      v-show="workspaceStore.isCopilotOpen && !workspaceStore.isZenMode"
      v-model="workspaceStore.activeCopilotTab"
      :active-arcs="state.activeArcs"
      :memory-view="state.memoryView"
      :organize-progress="state.organizeProgress"
      :suggested-actions="suggestedActions"
      @trigger="openSection"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, provide, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspace'
import { useNovelWorkspaceStore } from '@/stores/novelWorkspace'
import { WORKSPACE_CONTEXT_KEY } from '@/composables/useWorkspaceContext'
import {
  Monitor, Edit, DataBoard, Notebook, List, House
} from '@element-plus/icons-vue'

// Import views
import WorkspaceOverview from './WorkspaceOverview.vue'
import WorkspaceWritingStudio from './WorkspaceWritingStudio.vue'
import WorkspaceStructureStudio from './WorkspaceStructureStudio.vue'
import WorkspaceChapterManager from './WorkspaceChapterManager.vue'
import WorkspaceTasksAudit from './WorkspaceTasksAudit.vue'
import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import WorkspaceCopilotPanel from '@/components/workspace/WorkspaceCopilotPanel.vue'

const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()
const state = useNovelWorkspaceStore()

// Map activeView string to component
const activeComponent = computed(() => {
  switch (workspaceStore.activeView) {
    case 'writing': return WorkspaceWritingStudio
    case 'structure': return WorkspaceStructureStudio
    case 'chapters': return WorkspaceChapterManager
    case 'tasks': return WorkspaceTasksAudit
    case 'overview':
    default:
      return WorkspaceOverview
  }
})

const goToDashboard = () => {
  router.push('/')
}

const currentChapterId = computed(() => {
  const queryChapterId = String(route.query.chapterId || '').trim()
  return queryChapterId || state.chapters?.[0]?.id || ''
})

const latestChapter = computed(() => {
  const chapters = Array.isArray(state.chapters) ? [...state.chapters] : []
  return chapters.sort((a, b) => (b.chapter_number || 0) - (a.chapter_number || 0))[0] || null
})

const suggestedActions = computed(() => [])

const openSection = (section, extraQuery = {}) => {
  workspaceStore.switchView(section)
}

const openChapter = (chapterId, section = 'writing') => {
  workspaceStore.openChapter(chapterId)
  // Also load it in novel store
  state.loadEditorChapter(chapterId)
}

const createChapter = () => {
  router.push(`/novel/${route.params.id}/chapters/new`)
}

// Provide context for child components
provide(WORKSPACE_CONTEXT_KEY, {
  state,
  currentSection: computed(() => workspaceStore.activeView),
  currentChapterId,
  latestChapter,
  suggestedActions,
  openSection,
  openChapter,
  createChapter,
  refreshBase: () => state.loadBase(route.params.id),
  refreshStructure: state.loadStructure,
  syncChapterSnapshot: state.syncChapterSnapshot,
  loadEditorChapter: state.loadEditorChapter,
  saveEditorChapter: state.saveEditorChapter,
  runEditorAiAction: state.runEditorAiAction,
  applyDraftToEditor: state.applyDraftToEditor,
  saveDraftResult: state.saveDraftResult,
  discardDraft: state.discardDraft
})

watch(() => route.params.id, () => {
  if (route.params.id) {
    void state.loadBase(route.params.id)
  }
}, { immediate: true })

onMounted(() => {
  // Initialize workspace with novelId from route
  if (route && route.params && route.params.id) {
    workspaceStore.initWorkspace(route.params.id)
  }
})
</script>

<style scoped>
.novel-workspace-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #F8FAFC;
}

.workspace-nav-bar {
  width: 64px;
  background-color: #ffffff;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 0;
  z-index: 10;
  transition: transform 0.3s ease;
}

.nav-item {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 48px;
  height: 48px;
  margin: 0 auto 8px;
  border-radius: 8px;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-item:hover {
  background-color: #F3F4F6;
  color: #374151;
}

.nav-item.active {
  background-color: #EFF6FF;
  color: #3B82F6;
}

.nav-item .el-icon {
  font-size: 24px;
}

.workspace-main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.workspace-copilot {
  width: 320px;
  background-color: #ffffff;
  border-left: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
}

.copilot-placeholder {
  padding: 20px;
  color: #9CA3AF;
  text-align: center;
}

/* Zen Mode hides sidebars */
.hidden-in-zen {
  display: none !important;
}
</style>
