<template>
  <div class="workspace-shell" v-loading="state.loading">
    <el-alert
      v-if="state.errorMessage"
      class="workspace-alert"
      :title="state.errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <div class="workspace-header">
      <div>
        <div class="workspace-kicker">Author Workspace</div>
        <h1>{{ state.novel?.title || '小说工作区' }}</h1>
        <p class="workspace-subtitle">
          {{ state.novel?.author ? `作者：${state.novel.author}` : '正在为这部作品准备新的写作工作区。' }}
        </p>
      </div>
      <div class="workspace-header-actions">
        <el-button @click="openLegacyDetail">旧版详情</el-button>
        <el-button type="primary" @click="openSection('writing', currentChapterId ? { chapterId: currentChapterId } : {})">
          进入写作台
        </el-button>
      </div>
    </div>

    <div class="workspace-grid">
      <WorkspaceSidebar
        :section-items="sectionItems"
        :current-section="currentSection"
        :chapters="state.chapters"
        :selected-chapter-id="currentChapterId"
        @navigate="openSection"
        @open-chapter="openChapter"
        @create-chapter="createChapter"
      />

      <main class="workspace-main">
        <router-view />
      </main>

      <WorkspaceCopilotPanel
        v-model="state.copilotTab"
        :active-arcs="state.activeArcs"
        :memory-view="state.memoryView"
        :organize-progress="state.organizeProgress"
        :suggested-actions="suggestedActions"
        @trigger="handleCopilotAction"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, provide, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import WorkspaceCopilotPanel from '@/components/workspace/WorkspaceCopilotPanel.vue'
import { WORKSPACE_CONTEXT_KEY } from '@/composables/useWorkspaceContext'
import { useNovelWorkspaceStore } from '@/stores/novelWorkspace'

const route = useRoute()
const router = useRouter()
const state = useNovelWorkspaceStore()

const sectionRouteMap = {
  overview: 'WorkspaceOverview',
  structure: 'WorkspaceStructure',
  chapters: 'WorkspaceChapters',
  writing: 'WorkspaceWriting',
  tasks: 'WorkspaceTasks'
}

const sectionItems = computed(() => [
  { key: 'overview', label: '概览' },
  { key: 'structure', label: '结构台', badge: state.activeArcs.length || '' },
  { key: 'chapters', label: '章节台', badge: state.chapters.length || '' },
  { key: 'writing', label: '写作台' },
  {
    key: 'tasks',
    label: '任务台',
    badge: ['running', 'paused'].includes(state.organizeProgress?.status) ? '!' : ''
  }
])

const currentSection = computed(() => {
  const name = String(route.name || '')
  if (name === 'WorkspaceOverview') return 'overview'
  if (name === 'WorkspaceStructure') return 'structure'
  if (name === 'WorkspaceChapters') return 'chapters'
  if (name === 'WorkspaceWriting') return 'writing'
  if (name === 'WorkspaceTasks') return 'tasks'
  return 'overview'
})

const latestChapter = computed(() => {
  const chapters = Array.isArray(state.chapters) ? [...state.chapters] : []
  return chapters.sort((a, b) => (b.chapter_number || 0) - (a.chapter_number || 0))[0] || null
})

const currentChapterId = computed(() => {
  const queryChapterId = String(route.query.chapterId || '').trim()
  return queryChapterId || latestChapter.value?.id || state.chapters[0]?.id || ''
})

const suggestedActions = computed(() => {
  const actions = []
  if (latestChapter.value) {
    actions.push({
      key: 'writing',
      title: `继续第 ${latestChapter.value.chapter_number || '?'} 章之后的写作`,
      description: latestChapter.value.title || '进入当前章节继续创作。',
      cta: '继续写作'
    })
  }
  if (state.activeArcs[0]) {
    actions.push({
      key: 'structure',
      title: `检查当前主推进：${state.activeArcs[0].title || state.activeArcs[0].arc_id}`,
      description: '进入结构台，查看当前剧情弧和阶段状态。',
      cta: '查看结构'
    })
  }
  actions.push({
    key: 'tasks',
    title: '查看整理与分析任务',
    description: '进入任务台，查看最近的整理状态和失败恢复入口。',
    cta: '查看任务'
  })
  return actions
})

const openSection = (section, extraQuery = {}) => {
  const routeName = sectionRouteMap[section] || sectionRouteMap.overview
  const nextQuery = { ...extraQuery }
  if (section === 'writing' && !nextQuery.chapterId && currentChapterId.value) {
    nextQuery.chapterId = currentChapterId.value
  }
  router.push({
    name: routeName,
    params: { id: route.params.id },
    query: nextQuery
  })
}

const openChapter = (chapterId, section = 'writing') => {
  openSection(section, { chapterId })
}

const handleCopilotAction = (actionKey) => {
  if (actionKey === 'writing') {
    openSection('writing', currentChapterId.value ? { chapterId: currentChapterId.value } : {})
    return
  }
  if (actionKey === 'structure') {
    openSection('structure')
    return
  }
  if (actionKey === 'tasks') {
    openSection('tasks')
  }
}

const createChapter = () => {
  router.push(`/novel/${route.params.id}/chapters/new`)
}

const openLegacyDetail = () => {
  router.push(`/novel/${route.params.id}`)
}

provide(WORKSPACE_CONTEXT_KEY, {
  state,
  currentSection,
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
  void state.loadBase(route.params.id)
}, { immediate: true })
</script>

<style scoped>
.workspace-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: calc(100vh - 120px);
}

.workspace-alert {
  margin-bottom: 4px;
}

.workspace-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
  border-radius: 24px;
  background:
    radial-gradient(circle at left top, rgba(214, 150, 89, 0.24), transparent 28%),
    linear-gradient(135deg, #f7ede0 0%, #fdfaf5 52%, #efe7db 100%);
  border: 1px solid rgba(106, 77, 42, 0.08);
}

.workspace-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a86c3b;
}

.workspace-header h1 {
  margin-top: 8px;
  font-size: 32px;
  color: #322318;
}

.workspace-subtitle {
  margin-top: 8px;
  color: #725944;
}

.workspace-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  gap: 0;
  min-height: calc(100vh - 270px);
  border-radius: 28px;
  overflow: hidden;
  border: 1px solid rgba(96, 70, 38, 0.08);
  background: #fffaf2;
  box-shadow: 0 24px 60px rgba(93, 72, 37, 0.08);
}

.workspace-main {
  min-width: 0;
  padding: 24px 26px;
  background:
    radial-gradient(circle at top, rgba(235, 209, 174, 0.2), transparent 24%),
    linear-gradient(180deg, #fffdf9 0%, #fffaf2 100%);
}

@media (max-width: 1280px) {
  .workspace-grid {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .workspace-grid :deep(.copilot-panel) {
    display: none;
  }
}

@media (max-width: 960px) {
  .workspace-header {
    flex-direction: column;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .workspace-grid :deep(.workspace-sidebar) {
    display: none;
  }
}
</style>
