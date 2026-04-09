<template>
  <div class="novel-workspace-layout" :class="{ 'zen-mode': workspaceStore.isZenMode }">
    <!-- 最左：主视图导航栏 -->
    <nav class="workspace-nav-bar" :class="{ 'hidden-in-zen': workspaceStore.isZenMode }">
      <div class="nav-top">
        <el-tooltip content="概览 Overview" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'overview' }" @click="openSection('overview')">
            <el-icon><Monitor /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="写作 Writing" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'writing' }" @click="openSection('writing')">
            <el-icon><Edit /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="结构 Structure" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'structure' }" @click="openSection('structure')">
            <el-icon><DataBoard /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="章节 Chapters" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'chapters' }" @click="openSection('chapters')">
            <el-icon><Notebook /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="任务 Tasks" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'tasks' }" @click="openSection('tasks')">
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
      <WorkspaceTopBar
        :novel-title="state.novel?.title || '未命名小说'"
        :object-label="currentObjectLabel"
        :view-title="currentViewMeta.title"
        :view-description="currentViewMeta.description"
        :save-status-text="saveStatusText"
        :task-status-text="taskStatusText"
        :word-count="currentWordCount"
        :quick-facts="topbarQuickFacts"
        :status-cards="topbarStatusCards"
        :copilot-open="workspaceStore.isCopilotOpen"
        @toggle-copilot="workspaceStore.toggleCopilot()"
      />
      <component :is="activeComponent" />
    </main>

    <!-- 右侧：AI Copilot 区 -->
    <WorkspaceCopilotPanel
      v-show="workspaceStore.isCopilotOpen && !workspaceStore.isZenMode"
      v-model="workspaceStore.currentCopilotTab"
      :active-arcs="state.activeArcs"
      :memory-view="state.memoryView"
      :organize-progress="state.organizeProgress"
      :suggested-actions="suggestedActions"
      @trigger="handleCopilotTrigger"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, provide, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { novelApi } from '@/api'
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
import WorkspaceTopBar from '@/components/workspace/WorkspaceTopBar.vue'

const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()
const state = useNovelWorkspaceStore()

const viewMetaMap = {
  writing: {
    title: 'Writing',
    description: '中央区域保持写作优先，AI 结果默认回流为候选稿或审查结果。'
  },
  overview: {
    title: 'Overview',
    description: '用最小信息集理解当前小说状态，再决定下一步动作。'
  },
  structure: {
    title: 'Structure',
    description: '集中查看剧情弧、主线进度和结构摘要，不打断写作主流程。'
  },
  chapters: {
    title: 'Chapter Manager',
    description: '统一管理章节顺序、状态和批量操作，正文编辑仍回到 Writing。'
  },
  tasks: {
    title: 'Tasks & Audit',
    description: '查看运行状态、失败原因和恢复入口，而不是浏览原始日志。'
  }
}

// Map activeView string to component
const activeComponent = computed(() => {
  switch (workspaceStore.currentView) {
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
  return queryChapterId || workspaceStore.currentChapterId || ''
})

const latestChapter = computed(() => {
  const chapters = Array.isArray(state.chapters) ? [...state.chapters] : []
  return chapters.sort((a, b) => (b.chapter_number || 0) - (a.chapter_number || 0))[0] || null
})

const recentChapter = computed(() => {
  const chapters = Array.isArray(state.chapters) ? [...state.chapters] : []
  return chapters.sort((a, b) => {
    const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
    const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
    return bTs - aTs
  })[0] || latestChapter.value || null
})

const currentChapter = computed(() => (
  (state.chapters || []).find((item) => item.id === currentChapterId.value)
  || (state.editor.chapter?.id === currentChapterId.value ? state.editor.chapter : null)
  || null
))

const currentViewMeta = computed(() => (
  viewMetaMap[workspaceStore.currentView] || viewMetaMap.overview
))

const currentObjectLabel = computed(() => {
  if (workspaceStore.currentView === 'writing' && currentChapter.value) {
    return currentChapter.value.title || `第 ${currentChapter.value.chapter_number || '?'} 章`
  }
  if (workspaceStore.currentView === 'structure') {
    if (workspaceStore.currentObject?.type === 'plot_arc' && workspaceStore.currentObject?.title) {
      return workspaceStore.currentObject.title
    }
    const labelMap = {
      story_model: 'Story Model',
      plot_arc: 'PlotArc',
      character: '角色',
      worldview: '世界观',
      risk: '风险点'
    }
    return labelMap[workspaceStore.currentStructureSection] || 'Structure'
  }
  if (workspaceStore.currentView === 'tasks') {
    if (workspaceStore.currentObject?.type === 'task' && workspaceStore.currentObject?.title) {
      return workspaceStore.currentObject.title
    }
    const labelMap = {
      all: '全部任务',
      running: '运行中',
      failed: '失败任务',
      completed: '已完成',
      audit: '审查结果'
    }
    return labelMap[workspaceStore.currentTaskFilter] || 'Tasks'
  }
  if (workspaceStore.currentView === 'chapters') {
    if (workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.title) {
      return workspaceStore.currentObject.title
    }
    return currentChapter.value?.title || 'Chapter Manager'
  }
  return ''
})

const currentWordCount = computed(() => {
  const content = state.editor.chapter?.content || ''
  return content ? content.replace(/\s+/g, '').length : 0
})

const currentTargetArcText = computed(() => {
  const taskArcId = String(state.editor.chapterTask?.target_arc_id || '').trim()
  const taskArc = (state.editor.chapterArcs || []).find((item) => item.arc_id === taskArcId)
  if (taskArc) return taskArc.title || taskArc.arc_title || taskArc.arc_id
  const activeArc = (state.activeArcs || [])[0]
  if (activeArc) return activeArc.title || activeArc.arc_id
  return ''
})

const topbarQuickFacts = computed(() => {
  const facts = []

  if (workspaceStore.currentView === 'writing') {
    facts.push({
      label: '当前章节',
      value: currentChapter.value?.title || (currentChapter.value ? `第 ${currentChapter.value.chapter_number || '?'} 章` : '未打开')
    })
    if (currentTargetArcText.value) {
      facts.push({
        label: '目标弧',
        value: currentTargetArcText.value
      })
    }
    facts.push({
      label: '问题单',
      value: String(state.editor.integrityCheck?.issue_list?.length || 0)
    })
  } else if (workspaceStore.currentView === 'structure') {
    facts.push({
      label: '活跃弧',
      value: String((state.activeArcs || []).length || 0)
    })
    facts.push({
      label: '当前对象',
      value: currentObjectLabel.value || 'Structure'
    })
  } else if (workspaceStore.currentView === 'chapters') {
    facts.push({
      label: '章节总数',
      value: String((state.chapters || []).length || 0)
    })
    if (currentChapter.value?.title) {
      facts.push({
        label: '当前章节',
        value: currentChapter.value.title
      })
    }
  } else if (workspaceStore.currentView === 'tasks') {
    facts.push({
      label: '当前筛选',
      value: currentObjectLabel.value || '全部任务'
    })
  } else {
    facts.push({
      label: '最近章节',
      value: recentChapter.value?.title || '暂无章节'
    })
    facts.push({
      label: '活跃弧',
      value: String((state.activeArcs || []).length || 0)
    })
  }

  return facts.filter((item) => item.value !== '')
})

const saveStatusText = computed(() => {
  if (state.editor.saving) return '保存中'
  if (state.editor.dirty) return '未保存'
  if (state.editor.chapter?.id) return '已保存'
  return '待命中'
})

const taskStatusText = computed(() => {
  if (state.editor.aiRunning) return 'AI 处理中'
  const organizeStatus = String(state.organizeProgress?.status || '').trim()
  if (!organizeStatus) return '暂无任务'
  if (organizeStatus === 'running') return `整理中 ${state.organizeProgress?.progress ?? 0}%`
  if (organizeStatus === 'paused') return '整理已暂停'
  if (organizeStatus === 'failed' || organizeStatus === 'error') return '整理失败'
  if (organizeStatus === 'success' || organizeStatus === 'done') return '最近任务完成'
  return organizeStatus
})

const topbarStatusCards = computed(() => {
  const issueCount = Number(state.editor.integrityCheck?.issue_list?.length || 0)
  return [
    {
      label: '保存',
      value: saveStatusText.value,
      tone: state.editor.saving ? 'primary' : (state.editor.dirty ? 'warning' : 'success')
    },
    {
      label: '字数',
      value: String(currentWordCount.value || 0),
      hint: workspaceStore.currentView === 'writing' ? '当前正文' : '当前对象'
    },
    {
      label: '任务',
      value: taskStatusText.value,
      tone: issueCount > 0 ? 'warning' : 'primary',
      hint: issueCount > 0 ? `含 ${issueCount} 条问题` : '状态正常'
    }
  ]
})

const suggestedActions = computed(() => {
  const actions = []
  if (currentChapter.value?.id) {
    actions.push({
      key: 'writing',
      title: '继续当前章节',
      description: `回到 ${currentChapter.value.title || '当前章节'}，继续正文写作与 AI 协作。`,
      cta: '打开 Writing',
      action: {
        type: 'chapter',
        chapterId: currentChapter.value.id
      }
    })
  } else if (recentChapter.value?.id) {
    actions.push({
      key: 'writing',
      title: '打开最近章节',
      description: `从 ${recentChapter.value.title || '最近章节'} 恢复写作。`,
      cta: '继续写作',
      action: {
        type: 'chapter',
        chapterId: recentChapter.value.id
      }
    })
  }

  actions.push({
    key: 'structure',
    title: '查看活跃剧情弧',
    description: '检查主线、当前进度和活跃剧情弧，避免写作脱离结构。 ',
    cta: '打开 Structure',
    action: {
      type: 'section',
      section: 'structure',
      object: {
        type: 'plot_arc'
      }
    }
  })
  actions.push({
    key: 'tasks',
    title: '检查任务状态',
    description: '集中查看整理、审查和失败任务的恢复入口。',
    cta: '打开 Tasks',
    action: {
      type: 'task-filter',
      filter: 'all'
    }
  })
  return actions
})

const buildRouteQuery = (extraQuery = {}) => {
  const query = { ...route.query, ...extraQuery }
  if (!query.chapterId && workspaceStore.currentChapterId) {
    query.chapterId = workspaceStore.currentChapterId
  }
  if (!query.chapterId) {
    delete query.chapterId
  }
  return query
}

const openSection = (section, extraQuery = {}) => {
  workspaceStore.switchView(section)
  if (section === 'structure' && !workspaceStore.currentObject) {
    workspaceStore.setStructureSection(workspaceStore.currentStructureSection)
  }
  if (section === 'tasks' && !workspaceStore.currentObject) {
    workspaceStore.setTaskFilter(workspaceStore.currentTaskFilter)
  }
  router.replace({
    path: route.path,
    query: buildRouteQuery(extraQuery)
  })
}

const handleCopilotTrigger = async (payload) => {
  if (typeof payload === 'string') {
    openSection(payload)
    return
  }

  if (!payload || typeof payload !== 'object') {
    return
  }

  if (payload.type === 'chapter' && payload.chapterId) {
    await openChapter(payload.chapterId, 'writing')
    return
  }

  if (payload.type === 'arc') {
    workspaceStore.setStructureSection('plot_arc')
    workspaceStore.setCurrentObject({
      type: 'plot_arc',
      arcId: payload.arcId || '',
      title: payload.title || ''
    })
    openSection('structure')
    return
  }

  if (payload.type === 'task-filter') {
    workspaceStore.setTaskFilter(payload.filter || 'all')
    openSection('tasks')
    return
  }

  if (payload.type === 'section') {
    if (payload.section === 'structure' && payload.object?.type) {
      workspaceStore.setStructureSection(payload.object.type)
      workspaceStore.setCurrentObject(payload.object)
    }
    if (payload.section === 'tasks' && payload.filter) {
      workspaceStore.setTaskFilter(payload.filter)
    }
    openSection(payload.section || 'overview', payload.query || {})
    return
  }
}

const openChapter = async (chapterId, section = 'writing') => {
  const chapterMeta = (state.chapters || []).find((item) => item.id === chapterId) || {}
  workspaceStore.openChapter(chapterId, chapterMeta)
  await state.loadEditorChapter(chapterId)
  await router.replace({
    path: route.path,
    query: buildRouteQuery({ chapterId })
  })
  if (section !== 'writing') {
    workspaceStore.switchView(section)
  }
}

const createChapter = async () => {
  if (!route.params.id) return
  const defaultTitle = `第${(state.chapters?.length || 0) + 1}章`
  const result = await novelApi.createChapter(route.params.id, { title: defaultTitle, content: '' })
  await state.loadBase(route.params.id)
  const chapterId = result?.id || ''
  if (chapterId) {
    await openChapter(chapterId)
  }
  ElMessage.success('已创建新章节')
}

const resolveDefaultChapterId = () => {
  const queryChapterId = String(route.query.chapterId || '').trim()
  if (queryChapterId) return queryChapterId
  if (workspaceStore.currentChapterId) return workspaceStore.currentChapterId
  if (recentChapter.value?.id) return recentChapter.value.id
  if (latestChapter.value?.id) return latestChapter.value.id
  return ''
}

const ensureWorkspaceEntry = async () => {
  if (state.loading) return
  if (!route.params.id) return

  const targetChapterId = resolveDefaultChapterId()
  if (targetChapterId) {
    if (targetChapterId !== workspaceStore.currentChapterId || !state.editor.chapter?.id) {
      await openChapter(targetChapterId)
      return
    }

    workspaceStore.switchView('writing')
    return
  }

  workspaceStore.switchView('overview')
}

// Provide context for child components
provide(WORKSPACE_CONTEXT_KEY, {
  state,
  currentSection: computed(() => workspaceStore.currentView),
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

watch(() => route.query.chapterId, (chapterId) => {
  const nextChapterId = String(chapterId || '').trim()
  if (!nextChapterId || nextChapterId === workspaceStore.currentChapterId) {
    return
  }

  void openChapter(nextChapterId)
})

watch(() => [state.editor.contextMeta, state.memoryView], ([contextMeta, memoryView]) => {
  workspaceStore.setContextSnapshot({
    chapterId: state.editor.chapter?.id || '',
    chapterTitle: state.editor.chapter?.title || '',
    activeArcs: state.activeArcs || [],
    memoryView: memoryView || {},
    contextMeta: contextMeta || {}
  })
}, { deep: true, immediate: true })

watch(() => [state.loading, state.chapters], () => {
  void ensureWorkspaceEntry()
}, { deep: true })

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
  background-color: #F8FAFC;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 8px;
  z-index: 10;
  transition: transform 0.3s ease;
}

.nav-item {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 48px;
  height: 48px;
  margin: 0 auto 10px;
  border-radius: 16px;
  color: #6B7280;
  cursor: pointer;
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.03);
  transition: all 0.2s ease;
}

.nav-item:hover {
  background-color: #F9FAFB;
  color: #374151;
  transform: translateY(-1px);
}

.nav-item.active {
  background-color: #EFF6FF;
  color: #3B82F6;
  border-color: #DBEAFE;
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.10);
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
  min-width: 0;
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
