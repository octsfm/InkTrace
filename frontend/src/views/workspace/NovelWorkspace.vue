<template>
  <div class="novel-workspace-layout" :class="{ 'zen-mode': workspaceStore.isZenMode }">
    <!-- 最左：主视图导航栏 -->
    <nav class="workspace-nav-bar" :class="{ 'hidden-in-zen': workspaceStore.isZenMode }">
      <div class="nav-top">
        <el-tooltip content="概览" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'overview' }" @click="openSection('overview')">
            <el-icon><Monitor /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="写作" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'writing' }" @click="openSection('writing')">
            <el-icon><Edit /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="结构" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'structure' }" @click="openSection('structure')">
            <el-icon><DataBoard /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="章节" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'chapters' }" @click="openSection('chapters')">
            <el-icon><Notebook /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="任务" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'tasks' }" @click="openSection('tasks')">
            <el-icon><List /></el-icon>
          </div>
        </el-tooltip>
        <el-tooltip content="设置" placement="right">
          <div class="nav-item" :class="{ active: workspaceStore.currentView === 'settings' }" @click="openSection('settings')">
            <el-icon><Setting /></el-icon>
          </div>
        </el-tooltip>
      </div>
      <div class="nav-bottom">
        <el-tooltip content="返回主页" placement="right">
          <div class="nav-item" @click="goToDashboard">
            <el-icon><House /></el-icon>
          </div>
        </el-tooltip>
      </div>
    </nav>

    <!-- 左二：目录与对象导航区 -->
    <WorkspaceSidebar
      v-show="!workspaceStore.isZenMode"
      :current-view="workspaceStore.currentView"
      :current-chapter-id="currentChapterId"
      :current-structure-section="workspaceStore.currentStructureSection"
      :current-task-filter="workspaceStore.currentTaskFilter"
      :chapters="state.chapters"
      :sidebar-meta="sidebarMeta"
      :structure-items="sidebarStructureItems"
      :task-filters="sidebarTaskFilters"
      :overview-cards="sidebarOverviewCards"
      @open-chapter="openChapter"
      @create-chapter="createChapter"
      @change-structure="workspaceStore.setStructureSection($event)"
      @change-task-filter="workspaceStore.setTaskFilter($event)"
      @run-action="handleWorkspaceAction"
    />

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
        :quick-facts="resolvedTopbarQuickFacts"
        :status-cards="resolvedTopbarStatusCards"
        :object-actions="resolvedTopbarObjectActions"
        :copilot-open="workspaceStore.isCopilotOpen"
        @toggle-copilot="workspaceStore.toggleCopilot()"
        @action="handleWorkspaceAction"
        @open-command-palette="openCommandPalette"
      />
      <div v-if="mainViewError" class="workspace-main-fallback">
        <h3>当前视图加载失败</h3>
        <p>{{ mainViewError }}</p>
        <div class="fallback-actions">
          <el-button type="primary" @click="recoverMainView">恢复到概览</el-button>
          <el-button plain @click="clearMainViewError">重试当前视图</el-button>
        </div>
      </div>
      <component v-else :is="activeComponent" v-bind="activeComponentProps" />
    </main>

    <!-- 右侧：AI Copilot 区 -->
    <WorkspaceCopilotPanel
      v-show="workspaceStore.isCopilotOpen && !workspaceStore.isZenMode"
      v-model="workspaceStore.currentCopilotTab"
      :active-arcs="state.activeArcs"
      :current-view="workspaceStore.currentView"
      :current-object="workspaceStore.currentObject"
      :current-chapter-title="currentChapter?.title || ''"
      :chat-draft="workspaceStore.copilotChatDraft"
      :chat-messages="workspaceStore.copilotChatMessages"
      :chat-pending="workspaceStore.copilotChatPending"
      :chat-sessions="copilotChatSessions"
      :current-chat-session-key="workspaceStore.currentCopilotChatSessionKey"
      :recent-prompts="workspaceStore.copilotRecentPrompts"
      :context-summary="copilotContextSummary"
      :current-object-action="copilotCurrentObjectAction"
      :structure-action="copilotStructureAction"
      :story-model-action="copilotStoryModelAction"
      :chat-prompts="copilotChatPrompts"
      :object-prompt-cards="copilotObjectPromptCards"
      :inspire-items="copilotInspireItems"
      :inspire-pending="copilotInspirePending"
      :memory-view="state.memoryView"
      :organize-progress="state.organizeProgress"
      :suggested-actions="suggestedActions"
      @trigger="handleCopilotTrigger"
      @update:chat-draft="workspaceStore.setCopilotChatDraft($event)"
      @chat-submit="handleCopilotChatSubmit"
      @clear-chat="handleCopilotChatClear"
      @chat-session-change="handleCopilotChatSessionChange"
      @inspire-feedback="handleInspireFeedback"
    />

    <WorkspaceCommandPalette
      :visible="commandPaletteVisible"
      :query="commandPaletteQuery"
      :grouped-items="groupedCommandPaletteItems"
      @update:query="commandPaletteQuery = $event"
      @execute="handleCommandExecute"
      @close="closeCommandPalette"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, provide, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { novelApi, projectApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useNovelWorkspaceStore } from '@/stores/novelWorkspace'
import { WORKSPACE_CONTEXT_KEY } from '@/composables/useWorkspaceContext'
import {
  Monitor, Edit, DataBoard, Notebook, List, House, Setting
} from '@element-plus/icons-vue'

// Import views
import WorkspaceOverview from './WorkspaceOverview.vue'
import WorkspaceWritingStudio from './WorkspaceWritingStudio.vue'
import WorkspaceStructureStudio from './WorkspaceStructureStudio.vue'
import WorkspaceChapterManager from './WorkspaceChapterManager.vue'
import WorkspaceTasksAudit from './WorkspaceTasksAudit.vue'
import WorkspaceSettingsPanel from './WorkspaceSettingsPanel.vue'
import {
  buildWorkspaceResultLabel,
  buildWorkspaceTaskCenter,
  isWorkspaceTaskCompleted,
  isWorkspaceTaskFailed,
  isWorkspaceTaskRunning,
  normalizeWorkspaceTaskStatus
} from './workspaceTaskModel'
import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import WorkspaceCopilotPanel from '@/components/workspace/WorkspaceCopilotPanel.vue'
import WorkspaceTopBar from '@/components/workspace/WorkspaceTopBar.vue'
import WorkspaceCommandPalette from '@/components/workspace/WorkspaceCommandPalette.vue'

const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()
const state = useNovelWorkspaceStore()
const commandPaletteVisible = ref(false)
const commandPaletteQuery = ref('')
const mainViewError = ref('')

const viewMetaMap = {
  writing: {
    title: '写作',
    description: '中央区域保持写作优先，智能结果默认回流为候选稿或审查结果。'
  },
  overview: {
    title: '概览',
    description: '用最小信息集理解当前小说状态，再决定下一步动作。'
  },
  structure: {
    title: '结构',
    description: '集中查看剧情弧、主线进度和结构摘要，不打断写作主流程。'
  },
  chapters: {
    title: '章节管理',
    description: '统一管理章节顺序、状态和批量操作，正文编辑仍回到写作。'
  },
  tasks: {
    title: '任务与审查',
    description: '查看运行状态、失败原因和恢复入口，而不是浏览原始日志。'
  },
  settings: {
    title: '设置',
    description: '集中查看当前工作区前提、项目绑定、任务状态与编辑器诊断。'
  }
}

// Map activeView string to component
const activeComponent = computed(() => {
  switch (workspaceStore.currentView) {
    case 'writing': return WorkspaceWritingStudio
    case 'structure': return WorkspaceStructureStudio
    case 'chapters': return WorkspaceChapterManager
    case 'tasks': return WorkspaceTasksAudit
    case 'settings': return WorkspaceSettingsPanel
    case 'overview':
    default:
      return WorkspaceOverview
  }
})

const goToDashboard = () => {
  state.cancelPendingRequests?.()
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

const getWritingResultLabel = (resultType) => buildWorkspaceResultLabel(resultType, { noneLabel: '候选稿' })

const currentObjectLabel = computed(() => {
  if (workspaceStore.currentObject?.type === 'writing-result') {
    const resultLabel = getWritingResultLabel(workspaceStore.currentObject.resultType)
    if (currentChapter.value?.title) {
      return `${resultLabel} · ${currentChapter.value.title}`
    }
    return resultLabel
  }
  if (workspaceStore.currentView === 'writing' && currentChapter.value) {
    return currentChapter.value.title || `第 ${currentChapter.value.chapter_number || '?'} 章`
  }
  if (workspaceStore.currentView === 'structure') {
    if (workspaceStore.currentObject?.type === 'plot_arc' && workspaceStore.currentObject?.title) {
      return workspaceStore.currentObject.title
    }
    const labelMap = {
      story_model: '故事模型',
      plot_arc: '剧情弧',
      character: '角色',
      worldview: '世界观',
      risk: '风险点'
    }
    return labelMap[workspaceStore.currentStructureSection] || '结构'
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
    return labelMap[workspaceStore.currentTaskFilter] || '任务'
  }
  if (workspaceStore.currentView === 'chapters') {
    if (workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.title) {
      return workspaceStore.currentObject.title
    }
    return currentChapter.value?.title || '章节管理'
  }
  return ''
})

const currentWordCount = computed(() => {
  const content = state.editor.chapter?.content || ''
  return content ? content.replace(/\s+/g, '').length : 0
})

const sidebarMetaMap = {
  writing: {
    eyebrow: '写作',
    title: '章节与对象导航',
    subtitle: '当前以章节为主对象，切换章节不会离开工作区。'
  },
  chapters: {
    eyebrow: '章节',
    title: '章节导航',
    subtitle: '统一查看章节对象，再按需进入写作或管理视图。'
  },
  structure: {
    eyebrow: '结构',
    title: '结构导航',
    subtitle: '在剧情弧、角色与世界观对象之间切换。'
  },
  tasks: {
    eyebrow: '任务',
    title: '任务筛选',
    subtitle: '优先处理失败任务和审查结果。'
  },
  settings: {
    eyebrow: '设置',
    title: '工作区设置',
    subtitle: '集中查看当前工作区前提、任务状态与模型上下文。'
  },
  overview: {
    eyebrow: '概览',
    title: '项目摘要',
    subtitle: '只展示最小必要信息，帮助你决定下一步。'
  }
}

const sidebarMeta = computed(() => (
  sidebarMetaMap[workspaceStore.currentView] || sidebarMetaMap.overview
))

const sidebarStructureItems = computed(() => {
  const issueCount = Number(state.editor?.integrityCheck?.issue_list?.length || 0)
  return [
    { key: 'story_model', label: '故事模型', hint: '全局结构约束与主设定' },
    { key: 'plot_arc', label: '剧情弧', count: Number((state.activeArcs || []).length || 0), hint: currentTargetArcText.value || '当前主线推进视角' },
    { key: 'character', label: '角色', hint: '人物关系、动机与角色弧' },
    { key: 'worldview', label: '世界观', hint: '设定规则与边界条件' },
    { key: 'risk', label: '风险点', count: issueCount, hint: issueCount > 0 ? '优先检查结构与一致性风险' : '当前未发现明显风险阻塞' }
  ]
})

const taskFilterOptionDefs = [
  { key: 'all', label: '全部任务' },
  { key: 'running', label: '运行中' },
  { key: 'failed', label: '失败任务' },
  { key: 'completed', label: '已完成' },
  { key: 'audit', label: '审查结果' }
]

const sidebarOverviewCards = computed(() => {
  if (workspaceStore.currentView === 'settings') {
    return [
      {
        key: 'settings-project-id',
        label: '项目编号',
        value: resourceSnapshot.value.projectId || '未绑定项目',
        hint: resourceSnapshot.value.projectId ? '当前工作区已绑定项目。' : '未绑定时部分结构与任务链路可能不完整。'
      },
      {
        key: 'settings-failed-tasks',
        label: '失败任务',
        value: `${taskCenterSnapshot.value.failedCount || 0} 个`,
        hint: taskCenterSnapshot.value.failedCount > 0 ? '建议先恢复失败链路。' : '当前没有失败任务。',
        actionLabel: taskCenterSnapshot.value.failedCount > 0 ? '去处理' : '',
        action: taskCenterSnapshot.value.failedCount > 0 ? { type: 'task-filter', filter: 'failed' } : null
      },
      {
        key: 'settings-issues',
        label: '问题单',
        value: `${Number(contextSnapshot.value.contextMeta?.issueCount || state.editor?.integrityCheck?.issue_list?.length || 0)} 个`,
        hint: (contextSnapshot.value.chapterTitle || currentChapter.value?.title)
          ? `当前章节：${contextSnapshot.value.chapterTitle || currentChapter.value?.title}`
          : '回到写作页可查看问题详情。',
        actionLabel: Number(contextSnapshot.value.contextMeta?.issueCount || state.editor?.integrityCheck?.issue_list?.length || 0) > 0 ? '去写作' : '',
        action: Number(contextSnapshot.value.contextMeta?.issueCount || state.editor?.integrityCheck?.issue_list?.length || 0) > 0 && (contextSnapshot.value.chapterId || currentChapter.value?.id)
          ? { type: 'chapter', chapterId: contextSnapshot.value.chapterId || currentChapter.value?.id }
          : null
      }
    ]
  }

  return [
    {
      key: 'overview-novel',
      label: '当前小说',
      value: state.novel?.title || '未命名小说',
      hint: '工作区主对象',
      actionLabel: '概览',
      action: { type: 'section', section: 'overview' }
    },
    {
      key: 'overview-recent-chapter',
      label: '最近章节',
      value: recentChapter.value?.title || '暂无章节',
      hint: recentChapter.value?.chapter_number ? `第 ${recentChapter.value.chapter_number} 章` : '尚未创建章节',
      actionLabel: recentChapter.value?.id ? '去写作' : '',
      action: recentChapter.value?.id ? { type: 'chapter', chapterId: recentChapter.value.id } : null
    },
    {
      key: 'overview-current-task',
      label: '当前任务',
      value: taskStatusText.value || '暂无任务',
      hint: taskCenterSnapshot.value.failedCount > 0
        ? `失败 ${taskCenterSnapshot.value.failedCount} 个`
        : taskCenterSnapshot.value.runningCount > 0
          ? `运行中 ${taskCenterSnapshot.value.runningCount} 个`
          : '当前任务状态稳定',
      actionLabel: '任务台',
      action: { type: 'section', section: 'tasks' }
    },
    {
      key: 'overview-structure',
      label: '结构焦点',
      value: currentTargetArcText.value || '查看故事模型',
      hint: currentTargetArcText.value ? '当前写作目标弧' : '当前还没有明显结构焦点',
      actionLabel: '去结构',
      action: { type: 'section', section: 'structure' }
    }
  ]
})

const taskFilterOptions = computed(() => (taskFilterOptionDefs.map((item) => {
  const countMap = taskSummaryCounts.value || {}
  const count = countMap[item.key] ?? countMap.all ?? 0
  const hintMap = {
    all: '查看全部任务动态',
    running: '优先观察仍在执行的任务',
    failed: '优先恢复失败链路',
    completed: '查看最近完成结果',
    audit: '集中处理审查与分析任务'
  }
  return {
    ...item,
    count,
    label: item.label,
    hint: hintMap[item.key] || ''
  }
})))

const sidebarTaskFilters = computed(() => taskFilterOptions.value)

const currentTargetArcText = computed(() => {
  const taskArcId = String(state.editor.chapterTask?.target_arc_id || '').trim()
  const taskArc = (state.editor.chapterArcs || []).find((item) => item.arc_id === taskArcId)
  if (taskArc) return taskArc.title || taskArc.arc_title || taskArc.arc_id
  const activeArc = (state.activeArcs || [])[0]
  if (activeArc) return activeArc.title || activeArc.arc_id
  return ''
})

const resourceSnapshot = computed(() => workspaceStore.resourceSnapshot || {
  novelId: route.params.id || '',
  novelTitle: state.novel?.title || '',
  projectId: state.projectId || '',
  chapterCount: (state.chapters || []).length,
  activeChapterId: currentChapter.value?.id || workspaceStore.currentChapterId || '',
  hasStructure: Boolean((state.activeArcs || []).length)
})

const taskCenterSnapshot = computed(() => {
  const snapshot = workspaceStore.taskCenterSnapshot
  const hasUsableSnapshot = Boolean(
    snapshot && (
      (Array.isArray(snapshot.tasks) && snapshot.tasks.length > 0)
      || snapshot.failedCount
      || snapshot.runningCount
      || snapshot.completedCount
      || snapshot.auditCount
      || snapshot.organizeTask
    )
  )

  if (hasUsableSnapshot) {
    return snapshot
  }

  return {
    tasks: [],
    failedCount: taskSummaryCounts.value.failed || 0,
    runningCount: taskSummaryCounts.value.running || 0,
    completedCount: taskSummaryCounts.value.completed || 0,
    auditCount: taskSummaryCounts.value.audit || 0
  }
})

const contextSnapshot = computed(() => workspaceStore.currentContextSnapshot || {
  chapterId: currentChapter.value?.id || '',
  chapterTitle: currentChapter.value?.title || '',
  contextMeta: {
    issueCount: Number(state.editor?.integrityCheck?.issue_list?.length || 0)
  }
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
      value: currentObjectLabel.value || '结构'
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
    if (taskCenterSnapshot.value.failedCount > 0) {
      facts.push({
        label: '失败任务',
        value: String(taskCenterSnapshot.value.failedCount)
      })
    }
  } else {
    facts.push({
      label: '最近章节',
      value: recentChapter.value?.title || '暂无章节'
    })
    facts.push({
      label: '项目状态',
      value: resourceSnapshot.value.projectId ? '已绑定' : '待绑定'
    })
    facts.push({
      label: '活跃弧',
      value: String((state.activeArcs || []).length || 0)
    })
    if (taskCenterSnapshot.value.failedCount > 0) {
      facts.push({
        label: '失败任务',
        value: String(taskCenterSnapshot.value.failedCount)
      })
    }
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
  if (state.editor.aiRunning) return '智能处理中'
  if (taskCenterSnapshot.value.failedCount > 0) return `${taskCenterSnapshot.value.failedCount} 个失败任务`
  if (taskCenterSnapshot.value.runningCount > 0) return `${taskCenterSnapshot.value.runningCount} 个运行中任务`
  const organizeStatus = normalizeWorkspaceTaskStatus(state.organizeProgress?.status)
  if (!organizeStatus || organizeStatus === 'idle') return '暂无任务'
  if (isWorkspaceTaskRunning(organizeStatus)) return `整理中 ${state.organizeProgress?.progress ?? 0}%`
  if (organizeStatus === 'paused') return '整理已暂停'
  if (isWorkspaceTaskFailed(organizeStatus)) return '整理失败'
  if (isWorkspaceTaskCompleted(organizeStatus)) return '最近任务完成'
  return organizeStatus
})

const taskSummaryCounts = computed(() => {
  if (state.taskCenter?.counts) {
    return state.taskCenter.counts
  }

  const items = Array.isArray(state.chapterTasks) ? state.chapterTasks : []
  return {
    all: items.length,
    running: items.filter((item) => isWorkspaceTaskRunning(item?.status)).length,
    failed: items.filter((item) => isWorkspaceTaskFailed(item?.status)).length,
    completed: items.filter((item) => isWorkspaceTaskCompleted(item?.status)).length,
    audit: items.filter((item) => String(item?.task_type || item?.type || '').toLowerCase().includes('audit')).length
  }
})

const activeComponentProps = computed(() => {
  if (workspaceStore.currentView === 'tasks') {
    return {
      filterOptions: taskFilterOptions.value,
      statusText: taskPanelStatusText.value,
      progressText: taskPanelProgressText.value,
      statusHint: taskPanelStatusHint.value,
      statusCards: taskStatusCards.value,
      summaryChips: taskSummaryChips.value,
      taskCards: unifiedTaskCards.value,
      filteredTaskCards: filteredTaskCards.value,
      groupedTaskSections: groupedTaskSections.value,
      recommendationItems: taskRecommendationItems.value,
      focusBannerText: taskFocusBannerText.value,
      historyEmptyText: taskHistoryEmptyText.value,
      historyTitle: taskHistoryTitle.value,
      historyDescription: taskHistoryDescription.value,
      timelineItems: taskTimelineItems.value
    }
  }
  if (workspaceStore.currentView === 'settings') {
    return {
      novelTitle: state.novel?.title || '',
      projectId: state.projectId || '',
      resourceSnapshot: workspaceStore.resourceSnapshot,
      taskCenterSnapshot: workspaceStore.taskCenterSnapshot,
      contextSnapshot: workspaceStore.currentContextSnapshot,
      chapterCount: (state.chapters || []).length,
      currentView: workspaceStore.currentView,
      currentChapterTitle: currentChapter.value?.title || '',
      saveStatusText: saveStatusText.value,
      taskStatusText: taskStatusText.value,
      failedTaskCount: taskSummaryCounts.value.failed,
      runningTaskCount: taskSummaryCounts.value.running,
      auditTaskCount: taskSummaryCounts.value.audit,
      issueCount: Number(state.editor?.integrityCheck?.issue_list?.length || 0),
      copilotOpen: workspaceStore.isCopilotOpen,
      recentPromptCount: (workspaceStore.copilotRecentPrompts || []).length,
      sessionCount: (workspaceStore.copilotChatSessions || []).length,
      zenMode: workspaceStore.isZenMode,
      currentObjectTitle: currentObjectLabel.value || '',
      actionItems: [
        {
          key: 'settings-open-writing',
          label: '回到写作',
          onClick: () => openSection('writing', currentChapterId.value ? { chapterId: currentChapterId.value } : {})
        },
        {
          key: 'settings-open-tasks',
          label: '查看任务',
          onClick: () => openSection('tasks')
        },
        {
          key: 'settings-open-structure',
          label: '查看结构',
          onClick: () => openSection('structure')
        },
        {
          key: 'settings-open-chapters',
          label: '查看章节',
          onClick: () => openSection('chapters')
        }
      ]
    }
  }
  return {}
})

const overviewTaskSnapshot = computed(() => ({
  failed: taskSummaryCounts.value.failed || 0,
  running: taskSummaryCounts.value.running || 0,
  audit: taskSummaryCounts.value.audit || 0,
  recommendation: taskRecommendationItems.value[0] || null
}))

const taskPanelStatusText = computed(() => {
  const status = normalizeWorkspaceTaskStatus(state.organizeProgress?.status)
  if (!status || status === 'idle') return '未运行'
  if (status === 'running') return '整理中'
  if (status === 'paused') return '已暂停'
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  return status
})

const taskPanelProgressText = computed(() => `${state.organizeProgress?.progress ?? 0}%`)

const taskPanelStatusHint = computed(() => (
  state.organizeProgress?.error_message || '如果任务异常，可以在这里统一重试、暂停或恢复。'
))

const formatTaskTimestampText = (value) => {
  const timestamp = Number(value || 0)
  if (!timestamp) {
    return '未记录时间'
  }

  const diff = Math.max(0, Date.now() - timestamp)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  return `${Math.floor(diff / day)} 天前`
}

const unifiedTaskCards = computed(() => {
  const taskCenter = state.taskCenter || buildWorkspaceTaskCenter({
    organizeProgress: state.organizeProgress,
    chapterTasks: state.chapterTasks,
    sessionTasks: state.sessionTasks,
    currentTask: workspaceStore.currentTask,
    chapters: state.chapters
  })

  return (taskCenter.tasks || []).map((item) => ({
    ...item,
    timestampText: item.timestamp ? formatTaskTimestampText(item.timestamp) : '当前会话'
  }))
})

const filteredTaskCards = computed(() => {
  const filter = workspaceStore.currentTaskFilter
  const cards = unifiedTaskCards.value
  if (filter === 'all') return cards
  if (filter === 'running') return cards.filter((item) => isWorkspaceTaskRunning(item.status))
  if (filter === 'failed') return cards.filter((item) => isWorkspaceTaskFailed(item.status))
  if (filter === 'completed') return cards.filter((item) => isWorkspaceTaskCompleted(item.status))
  if (filter === 'audit') return cards.filter((item) => item.type === 'audit')
  return cards
})

const taskSummaryChips = computed(() => ([
  { label: '全部', value: String(taskSummaryCounts.value.all || 0) },
  { label: '失败', value: String(taskSummaryCounts.value.failed || 0) },
  { label: '运行中', value: String(taskSummaryCounts.value.running || 0) },
  { label: '审查', value: String(taskSummaryCounts.value.audit || 0) }
]))

const groupedTaskSections = computed(() => {
  const cards = filteredTaskCards.value
  const sections = [
    {
      key: 'failed',
      title: '优先恢复',
      description: '这些任务当前失败或异常，建议优先定位并恢复。',
      items: cards.filter((item) => isWorkspaceTaskFailed(item.status))
    },
    {
      key: 'running',
      title: '运行中',
      description: '这些任务仍在运行，可以先观察进度或切回对象继续处理。',
      items: cards.filter((item) => isWorkspaceTaskRunning(item.status))
    },
    {
      key: 'audit',
      title: '审查与分析',
      description: '这些任务更偏结构审查、分析和一致性判断。',
      items: cards.filter((item) => String(item.type || '').toLowerCase().includes('audit') || String(item.type || '').toLowerCase().includes('analyze'))
    },
    {
      key: 'others',
      title: '其他任务',
      description: '其余项目任务和当前工作区任务。',
      items: cards.filter((item) => !['failed', 'error', 'running'].includes(item.status)
        && !String(item.type || '').toLowerCase().includes('audit')
        && !String(item.type || '').toLowerCase().includes('analyze'))
    }
  ]

  return sections.filter((section) => section.items.length)
})

const taskRecommendationItems = computed(() => {
  const items = []
  const failedTask = unifiedTaskCards.value.find((item) => isWorkspaceTaskFailed(item.status) && item.id !== 'organize-task')
  const failedOrganizeTask = unifiedTaskCards.value.find((item) => item.id === 'organize-task' && isWorkspaceTaskFailed(item.status))
  const runningTask = unifiedTaskCards.value.find((item) => isWorkspaceTaskRunning(item.status) && item.id !== 'organize-task')
  const auditTask = unifiedTaskCards.value.find((item) => String(item.type || '').toLowerCase().includes('audit'))

  if (failedTask) {
    items.push({
      key: 'failed-task',
      tag: '优先',
      title: `先恢复：${failedTask.title}`,
      description: failedTask.description || failedTask.hint,
      meta: failedTask.subtitle || failedTask.statusLabel,
      actionLabel: failedTask.actionLabel || '查看任务',
      action: failedTask.action || { type: 'task-filter', filter: 'failed' }
    })
  }

  if (failedOrganizeTask) {
    items.push({
      key: 'organize-retry',
      tag: '整理',
      title: '全书整理任务需要恢复',
      description: failedOrganizeTask.description || failedOrganizeTask.hint,
      meta: failedOrganizeTask.subtitle || failedOrganizeTask.statusLabel,
      actionLabel: failedOrganizeTask.actionLabel || '重新整理',
      action: failedOrganizeTask.action || { type: 'retry-organize' }
    })
  }

  if (auditTask) {
    items.push({
      key: 'audit-check',
      tag: '审查',
      title: `查看：${auditTask.title}`,
      description: auditTask.hint || '先确认审查结果，再决定是否回到写作或结构页处理。',
      meta: auditTask.subtitle || auditTask.statusLabel,
      actionLabel: auditTask.actionLabel || '查看审查',
      action: auditTask.action || { type: 'task-filter', filter: 'audit' }
    })
  }

  if (runningTask) {
    items.push({
      key: 'running-task',
      tag: '进行中',
      title: `跟进：${runningTask.title}`,
      description: runningTask.hint || '该任务仍在执行中，可回到对应对象继续处理。',
      meta: runningTask.subtitle || runningTask.statusLabel,
      actionLabel: runningTask.actionLabel || '查看任务',
      action: runningTask.action || { type: 'section', section: 'tasks' }
    })
  }

  if (!items.length) {
    const totalTaskCount = Array.isArray(taskCenterSnapshot.value.tasks) && taskCenterSnapshot.value.tasks.length
      ? taskCenterSnapshot.value.tasks.length
      : (taskSummaryCounts.value.all || 0)
    items.push({
      key: 'task-fallback',
      tag: '任务',
      title: '当前任务状态稳定',
      description: '没有需要立即恢复的任务，下一步可切回写作或结构页继续推进。',
      meta: `${totalTaskCount} 个项目任务`,
      actionLabel: '回到概览',
      action: { type: 'section', section: 'overview' }
    })
  }

  return items.slice(0, 3)
})

const taskFocusBannerText = computed(() => {
  if (workspaceStore.currentObject?.type === 'task' && workspaceStore.currentObject?.title) {
    return `当前聚焦：${workspaceStore.currentObject.title}`
  }
  const filter = taskFilterOptions.value.find((item) => item.key === workspaceStore.currentTaskFilter)
  return filter ? `当前筛选：${filter.label}` : ''
})

const taskHistoryTitle = computed(() => {
  const filter = taskFilterOptions.value.find((item) => item.key === workspaceStore.currentTaskFilter)
  return filter ? `${filter.label} · 最近动态` : '最近任务动态'
})

const taskHistoryDescription = computed(() => {
  if (workspaceStore.currentTaskFilter === 'failed') {
    return '把失败原因、最近状态和恢复入口串成一条历史线，便于快速定位。'
  }
  if (workspaceStore.currentTaskFilter === 'running') {
    return '优先观察仍在运行的任务，确认进度、阶段和当前处理对象。'
  }
  if (workspaceStore.currentTaskFilter === 'audit') {
    return '集中查看审查与分析任务，确认结果应该回流到哪个对象处理。'
  }
  return '按时间查看最近任务动态，快速决定下一步应该恢复、观察还是回到对象处理。'
})

const taskTimelineItems = computed(() => {
  return [...filteredTaskCards.value]
    .sort((a, b) => {
      const timestampDiff = Number(b.timestamp || 0) - Number(a.timestamp || 0)
      if (timestampDiff !== 0) {
        return timestampDiff
      }
      return String(a.title || '').localeCompare(String(b.title || ''), 'zh-CN')
    })
    .map((item) => ({
      id: item.id,
      title: item.title,
      status: item.status,
      statusLabel: item.statusLabel,
      typeLabel: item.typeLabel,
      resultTypeLabel: item.resultTypeLabel || '',
      meta: item.subtitle || item.targetLabel,
      timestampText: item.timestampText || '当前会话',
      summary: item.reasonText || item.description || item.hint,
      traceItems: Array.isArray(item.traceItems) ? item.traceItems.slice(0, 3) : [],
      actionLabel: item.actionLabel,
      action: item.action,
      chapterId: item.chapterId || ''
    }))
    .slice(0, 8)
})

const taskHistoryEmptyText = computed(() => (
  workspaceStore.currentTaskFilter === 'all'
    ? '当前工作区还没有可展示的任务动态。'
    : '当前筛选下暂无任务动态。'
))

const taskStatusCards = computed(() => ([
  {
    label: '当前状态',
    value: taskPanelStatusText.value,
    hint: taskPanelStatusHint.value
  },
  {
    label: '最近进度',
    value: taskPanelProgressText.value,
    hint: `项目任务 ${taskSummaryCounts.value.all} 个`
  },
  {
    label: '失败任务',
    value: String(taskSummaryCounts.value.failed || 0),
    hint: taskSummaryCounts.value.failed ? '建议优先处理' : '当前无失败项'
  }
]))

const topbarStatusCards = computed(() => {
  const issueCount = Number(contextSnapshot.value.contextMeta?.issueCount || state.editor.integrityCheck?.issue_list?.length || 0)
  const failedTaskCount = Number(taskCenterSnapshot.value.failedCount || 0)
  const runningTaskCount = Number(taskCenterSnapshot.value.runningCount || 0)
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
      tone: issueCount > 0 || failedTaskCount > 0 ? 'warning' : 'primary',
      hint: issueCount > 0
        ? `含 ${issueCount} 条问题`
        : failedTaskCount > 0
          ? `${failedTaskCount} 个失败任务`
          : runningTaskCount > 0
            ? `${runningTaskCount} 个运行中任务`
            : '状态正常'
    }
  ]
})

const topbarObjectActions = computed(() => {
  const actions = []

  if (taskCenterSnapshot.value.failedCount > 0) {
    actions.push({
      label: `失败任务 ${taskCenterSnapshot.value.failedCount}`,
      action: {
        type: 'task-filter',
        filter: 'failed'
      }
    })
  }

  if (workspaceStore.currentObject?.type === 'writing-result') {
    actions.push({
      label: `查看${getWritingResultLabel(workspaceStore.currentObject.resultType)}`,
      action: {
        type: 'writing-result',
        chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
        resultType: workspaceStore.currentObject.resultType || 'candidate',
        taskId: workspaceStore.currentObject.taskId || '',
        title: workspaceStore.currentObject.title || getWritingResultLabel(workspaceStore.currentObject.resultType)
      }
    })
  }

  if (workspaceStore.currentView === 'writing' && currentChapter.value?.id) {
    actions.push({
      label: '章节管理',
      action: {
        type: 'chapter-manager',
        chapterId: currentChapter.value.id,
        title: currentChapter.value.title || ''
      }
    })

    const taskArcId = String(state.editor.chapterTask?.target_arc_id || '').trim()
    const taskArc = (state.editor.chapterArcs || []).find((item) => item.arc_id === taskArcId)
    if (taskArc?.arc_id) {
      actions.push({
        label: '查看目标弧',
        action: {
          type: 'arc',
          arcId: taskArc.arc_id,
          title: taskArc.title || taskArc.arc_title || taskArc.arc_id
        }
      })
    }
  }

  if (workspaceStore.currentView === 'chapters' && workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.id) {
    actions.push({
      label: '进入写作',
      action: {
        type: 'chapter',
        chapterId: workspaceStore.currentObject.id
      }
    })
  }

  if (workspaceStore.currentView === 'tasks') {
    if (workspaceStore.currentObject?.type === 'task' && workspaceStore.currentTask?.chapterId) {
      actions.push({
        label: '回到写作',
        action: {
          type: 'chapter',
          chapterId: workspaceStore.currentTask.chapterId
        }
      })
    }

    if (workspaceStore.currentTaskFilter !== 'failed') {
      actions.push({
        label: '看失败任务',
        action: {
          type: 'task-filter',
          filter: 'failed'
        }
      })
    }
  }

  if (workspaceStore.currentView === 'structure' && workspaceStore.currentObject?.type === 'plot_arc' && currentChapter.value?.id) {
    actions.push({
      label: '回到当前章节',
      action: {
        type: 'chapter',
        chapterId: currentChapter.value.id
      }
    })
  }

  if (workspaceStore.currentView === 'overview') {
    actions.push({
      label: '继续写作',
      action: currentChapter.value?.id
        ? { type: 'chapter', chapterId: currentChapter.value.id }
        : { type: 'section', section: 'writing' }
    })
    actions.push({
      label: '看结构',
      action: { type: 'section', section: 'structure' }
    })
  }

  if (workspaceStore.currentView === 'settings') {
    actions.push({
      label: '回到写作',
      action: currentChapter.value?.id
        ? { type: 'chapter', chapterId: currentChapter.value.id }
        : { type: 'section', section: 'writing' }
    })
    if (taskSummaryCounts.value.failed > 0) {
      actions.push({
        label: '恢复失败链路',
        action: {
          type: 'task-filter',
          filter: 'failed'
        }
      })
    } else {
      actions.push({
        label: '查看任务',
        action: { type: 'section', section: 'tasks' }
      })
    }
  }

  return actions
})

const resolvedTopbarQuickFacts = computed(() => (
  Array.isArray(topbarQuickFacts.value)
    ? topbarQuickFacts.value.filter((item) => item?.label && item?.value !== undefined && item?.value !== '')
    : []
))

const resolvedTopbarStatusCards = computed(() => (
  Array.isArray(topbarStatusCards.value)
    ? topbarStatusCards.value.filter((item) => item?.label && item?.value !== undefined && item?.value !== '')
    : []
))

const resolvedTopbarObjectActions = computed(() => (
  Array.isArray(topbarObjectActions.value)
    ? topbarObjectActions.value.filter((item) => item?.label && item?.action)
    : []
))

const copilotProgressText = computed(() => {
  const status = String(state.organizeProgress?.status || '').trim()
  if (!status) return '系统待命中，可随时开始写作。'
  if (status === 'running') {
    return `正在整理中，进度 ${state.organizeProgress?.progress ?? 0}%`
  }
  if (status === 'success' || status === 'done') {
    return '最近一次整理已完成。'
  }
  if (status === 'failed' || status === 'error') {
    return state.organizeProgress?.error_message || '最近一次整理失败。'
  }
  return `当前状态：${status}`
})

const copilotMemorySummaryText = computed(() => {
  const summary = String(state.memoryView?.current_progress || '').trim()
  if (summary) {
    return summary
  }
  const stageCount = Array.isArray(state.activeArcs) ? state.activeArcs.length : 0
  if (stageCount) {
    return `当前有 ${stageCount} 条可推进剧情弧，可直接进入结构页查看。`
  }
  return '写作过程中提及的人物、世界观与主线约束会逐步汇总在这里。'
})

const copilotMainPlotLines = computed(() => {
  const lines = Array.isArray(state.memoryView?.main_plot_lines) ? state.memoryView.main_plot_lines : []
  return lines.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
})

const copilotCurrentStateText = computed(() => {
  const stateText = String(state.memoryView?.current_state || '').trim()
  if (stateText) {
    return stateText
  }
  return '当前对象相关的阶段状态、角色压力和上下文摘要会汇总在这里。'
})

const copilotCurrentObjectTitle = computed(() => {
  if (workspaceStore.currentObject?.type === 'writing-result') {
    const resultLabel = getWritingResultLabel(workspaceStore.currentObject.resultType)
    return currentChapter.value?.title
      ? `${resultLabel} · ${currentChapter.value.title}`
      : resultLabel
  }
  if (workspaceStore.currentView === 'writing') {
    return currentChapter.value?.title || '当前章节'
  }
  if (workspaceStore.currentObject?.title) {
    return workspaceStore.currentObject.title
  }
  if (workspaceStore.currentObject?.type === 'task-filter') {
    return `任务筛选：${workspaceStore.currentObject.filter || 'all'}`
  }
  return '当前工作对象'
})

const copilotCurrentObjectMeta = computed(() => {
  const objectType = String(workspaceStore.currentObject?.type || '').trim()
  if (objectType === 'writing-result') {
    return `${getWritingResultLabel(workspaceStore.currentObject?.resultType)}对象`
  }
  if (workspaceStore.currentView === 'writing') {
    return '正文写作对象'
  }
  if (workspaceStore.currentView === 'structure') {
    return objectType === 'plot_arc' ? '剧情弧对象' : '结构对象'
  }
  if (workspaceStore.currentView === 'chapters') {
    return '章节管理对象'
  }
  if (workspaceStore.currentView === 'tasks') {
    return objectType === 'task' ? '任务对象' : '任务筛选对象'
  }
  return '当前工作区对象'
})

const copilotCurrentObjectAction = computed(() => {
  if (workspaceStore.currentObject?.type === 'writing-result') {
    return {
      type: 'writing-result',
      chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
      resultType: workspaceStore.currentObject.resultType || 'candidate',
      taskId: workspaceStore.currentObject.taskId || '',
      title: workspaceStore.currentObject.title || getWritingResultLabel(workspaceStore.currentObject.resultType)
    }
  }
  if (workspaceStore.currentView === 'writing' && workspaceStore.currentObject?.id) {
    return {
      type: 'chapter-manager',
      chapterId: workspaceStore.currentObject.id,
      title: workspaceStore.currentObject.title || currentChapter.value?.title || ''
    }
  }
  if (workspaceStore.currentView === 'structure' && workspaceStore.currentObject?.type === 'plot_arc') {
    return {
      type: 'arc',
      arcId: workspaceStore.currentObject.arcId || '',
      title: workspaceStore.currentObject.title || ''
    }
  }
  if (workspaceStore.currentView === 'chapters' && workspaceStore.currentObject?.type === 'chapter') {
    return {
      type: 'chapter',
      chapterId: workspaceStore.currentObject.id,
      title: workspaceStore.currentObject.title || ''
    }
  }
  if (workspaceStore.currentView === 'tasks' && workspaceStore.currentObject?.type === 'task-filter') {
    return {
      type: 'task-filter',
      filter: workspaceStore.currentObject.filter || 'all'
    }
  }
  return null
})

const copilotStructureAction = {
  type: 'section',
  section: 'structure',
  object: {
    type: 'plot_arc'
  }
}

const copilotStoryModelAction = {
  type: 'section',
  section: 'structure',
  object: {
    type: 'story_model'
  }
}

const copilotContextSummary = computed(() => ({
  progressText: copilotProgressText.value,
  memorySummaryText: copilotMemorySummaryText.value,
  mainPlotLines: copilotMainPlotLines.value,
  currentStateText: copilotCurrentStateText.value,
  currentObjectTitle: copilotCurrentObjectTitle.value,
  currentObjectMeta: copilotCurrentObjectMeta.value
}))

const copilotChatPrompts = computed(() => {
  if (workspaceStore.currentView === 'writing') {
    if (workspaceStore.currentObject?.type === 'writing-result') {
      const resultType = workspaceStore.currentObject.resultType || 'candidate'
      if (resultType === 'issues') {
        return [
          '这些问题单应该先处理哪几个？',
          '当前问题结果里最可能影响后续剧情的风险是什么？',
          '我应该先回正文修复，还是先看结构约束？'
        ]
      }
      if (resultType === 'diff') {
        return [
          '这份改写稿最值得保留的变化是什么？',
          '当前改写稿和正文相比，最大的收益与风险分别是什么？',
          '我应该整体采用这份改写稿，还是只吸收部分段落？'
        ]
      }
      return [
        '这份候选稿最适合如何并入正文？',
        '当前候选稿还缺少哪种情绪或信息落点？',
        '我应该直接采纳、局部吸收，还是继续改写这一稿？'
      ]
    }
    return [
      '下一章最适合推进哪条剧情弧？',
      '当前章节还有哪些一致性风险？',
      '这章结尾最适合留下什么悬念？'
    ]
  }
  if (workspaceStore.currentView === 'structure') {
    return [
      '这条剧情弧下一步应该推进到哪个阶段？',
      '当前结构里最大的风险点是什么？',
      '哪些设定还缺少落地章节？'
    ]
  }
  if (workspaceStore.currentView === 'tasks') {
    return [
      '当前失败任务优先应该恢复哪一个？',
      '这个任务失败最可能是什么原因？',
      '我下一步应该先回到哪个对象处理？'
    ]
  }
  return [
    '我应该从哪里继续创作？',
    '最近最值得关注的对象是什么？',
    '下一步最适合进入哪个工作区？'
  ]
})

const copilotObjectPromptCards = computed(() => {
  if (workspaceStore.currentView === 'writing') {
    if (workspaceStore.currentObject?.type === 'writing-result') {
      const resultType = workspaceStore.currentObject.resultType || 'candidate'
      if (resultType === 'issues') {
        return [
          {
            title: '排序问题优先级',
            tag: '问题',
            description: '判断哪些问题会最先影响结构、人物或信息一致性。',
            prompt: `请根据当前问题结果「${copilotCurrentObjectTitle.value}」，帮我按优先级排序这些问题，并说明先修哪几个最划算。`
          },
          {
            title: '规划修复路径',
            tag: '恢复',
            description: '决定先回正文、结构还是任务台处理。',
            prompt: `围绕当前问题结果「${copilotCurrentObjectTitle.value}」，我下一步应该先回正文修复、先看结构约束，还是先处理相关任务？请给出顺序。`
          }
        ]
      }
      if (resultType === 'diff') {
        return [
          {
            title: '评估改写价值',
            tag: '改写',
            description: '比较当前改写稿和原正文，找出最值得保留的变化。',
            prompt: `请评估当前改写结果「${copilotCurrentObjectTitle.value}」，指出最值得采纳的三处变化，以及各自的风险。`
          },
          {
            title: '制定采纳策略',
            tag: '写作',
            description: '判断整体采用还是局部吸收更合适。',
            prompt: `对于当前改写结果「${copilotCurrentObjectTitle.value}」，我更适合整体替换、局部吸收，还是继续改写？请说明依据。`
          }
        ]
      }
      return [
        {
          title: '评估候选稿可用性',
          tag: '候选',
          description: '快速判断当前候选稿是否适合直接并入正文。',
          prompt: `请评估当前候选稿「${copilotCurrentObjectTitle.value}」的可用性，指出最该保留和最该修改的部分。`
        },
        {
          title: '规划合并方式',
          tag: '写作',
          description: '决定是追加、覆盖还是局部吸收。',
          prompt: `围绕当前候选稿「${copilotCurrentObjectTitle.value}」，我更适合追加到正文、覆盖当前段落，还是只局部吸收？`
        }
      ]
    }
    return [
      {
        title: '评估当前章节风险',
        tag: '审查',
        description: '快速检查当前章节是否存在一致性、节奏或信息落点问题。',
        prompt: `请检查当前章节「${copilotCurrentObjectTitle.value}」还有哪些一致性风险，并按优先级给出处理建议。`
      },
      {
        title: '规划下一步剧情弧',
        tag: '结构',
        description: '围绕当前章节和结构约束，决定下一步最该推进的剧情弧。',
        prompt: `围绕当前章节「${copilotCurrentObjectTitle.value}」，下一步最适合推进哪条剧情弧？请结合当前结构约束给出理由。`
      },
      {
        title: '生成结尾方案',
        tag: '写作',
        description: '给当前章节生成更具悬念感的收束方向。',
        prompt: `请为当前章节「${copilotCurrentObjectTitle.value}」提供三个结尾悬念方案，并说明各自适合的情绪强度。`
      }
    ]
  }
  if (workspaceStore.currentView === 'structure') {
    return [
      {
        title: '推进当前结构对象',
        tag: '结构',
        description: '判断当前结构对象下一步应该推进到哪个阶段。',
        prompt: `对于当前结构对象「${copilotCurrentObjectTitle.value}」，下一步应该推进到哪个阶段？请说明原因。`
      },
      {
        title: '找缺口章节',
        tag: '落地',
        description: '从结构约束反推还缺哪些章节落地。',
        prompt: '根据当前结构约束，哪些设定或剧情弧还缺少对应章节来承接？'
      }
    ]
  }
  if (workspaceStore.currentView === 'tasks') {
    return [
      {
        title: '恢复失败任务',
        tag: '恢复',
        description: '优先判断当前失败任务是否应该立刻恢复。',
        prompt: `请分析当前任务对象「${copilotCurrentObjectTitle.value}」，下一步最适合先恢复、重试还是回到对应对象处理？`
      },
      {
        title: '排序处理优先级',
        tag: '任务',
        description: '给出当前任务页的处理顺序建议。',
        prompt: '请根据当前任务状态，给我一个失败任务、审查任务和整理任务的处理优先级。'
      }
    ]
  }
  if (workspaceStore.currentView === 'chapters') {
    return [
      {
        title: '判断章节功能',
        tag: '章节',
        description: '评估当前章节在全书中的位置是否清晰。',
        prompt: `请评估当前章节「${copilotCurrentObjectTitle.value}」在整本书中的功能是否清晰，并给出修改建议。`
      },
      {
        title: '安排下一章',
        tag: '规划',
        description: '围绕当前章节推导下一章应该承接什么。',
        prompt: `基于当前章节「${copilotCurrentObjectTitle.value}」，下一章最应该承接什么信息或冲突？`
      }
    ]
  }
  return [
    {
      title: '决定下一步',
      tag: '概览',
      description: '围绕当前工作区状态决定下一步最合适的入口。',
      prompt: '请根据当前工作区状态，告诉我下一步最适合进入哪个对象继续处理。'
    }
  ]
})

const copilotInspireRemoteItems = ref([])
const copilotInspirePending = ref(false)
const copilotInspireLastSignature = ref('')
const inspireFeedbackMap = ref({})

const inspireFeedbackStorageKey = computed(() => {
  const projectId = state.projectId || state.project?.id || ''
  return projectId ? `inktrace:workspace:inspire-feedback:${projectId}` : ''
})

const loadInspireFeedback = () => {
  const storageKey = inspireFeedbackStorageKey.value
  if (!storageKey) return
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) {
      inspireFeedbackMap.value = {}
      return
    }
    const parsed = JSON.parse(raw)
    inspireFeedbackMap.value = parsed && typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    inspireFeedbackMap.value = {}
  }
}

const persistInspireFeedback = () => {
  const storageKey = inspireFeedbackStorageKey.value
  if (!storageKey) return
  try {
    localStorage.setItem(storageKey, JSON.stringify(inspireFeedbackMap.value || {}))
  } catch (error) {
    // ignore storage failures in private mode
  }
}

const getInspireSourcePriority = (item = {}) => {
  const key = String(item.key || '')
  if (key.startsWith('remote-plan-')) return 42
  if (key.startsWith('remote-branch-')) return 36
  if (item.tag === '修复') return 34
  if (item.tag === '恢复') return 32
  if (item.tag === '候选') return 30
  if (item.tag === '改写') return 28
  if (item.tag === '续写') return 26
  if (item.tag === '结构') return 24
  if (item.tag === '规划') return 22
  return 18
}

const scoreInspireItem = (item = {}, index = 0) => {
  const feedback = inspireFeedbackMap.value[String(item.key || '')] || {}
  const accepted = Number(feedback.accepted || 0)
  const dismissed = Number(feedback.dismissed || 0)
  const sourcePriority = getInspireSourcePriority(item)
  const freshness = Math.max(0, 8 - index)
  return sourcePriority + freshness + accepted * 6 - dismissed * 4
}

const handleInspireFeedback = (payload = {}) => {
  const key = String(payload.key || '').trim()
  if (!key) return
  const signal = String(payload.signal || '').trim()
  if (!signal) return

  const previous = inspireFeedbackMap.value[key] || { accepted: 0, dismissed: 0 }
  inspireFeedbackMap.value = {
    ...inspireFeedbackMap.value,
    [key]: {
      accepted: Number(previous.accepted || 0) + (signal === 'accept' ? 1 : 0),
      dismissed: Number(previous.dismissed || 0) + (signal === 'dismiss' ? 1 : 0),
      updatedAt: Date.now()
    }
  }
  persistInspireFeedback()

  if (signal === 'accept') {
    ElMessage.success('已记录采纳偏好，后续会优先推荐类似灵感')
  } else {
    ElMessage.info('已记录忽略偏好，后续会降低类似灵感权重')
  }
}

const buildCopilotInspireSignature = () => JSON.stringify({
  tab: workspaceStore.currentCopilotTab,
  view: workspaceStore.currentView,
  chapterId: currentChapter.value?.id || '',
  objectType: workspaceStore.currentObject?.type || '',
  objectId: workspaceStore.currentObject?.id || workspaceStore.currentObject?.taskId || workspaceStore.currentObject?.arcId || '',
  resultType: workspaceStore.currentObject?.resultType || '',
  failedCount: taskCenterSnapshot.value.failedCount || 0,
  projectId: state.projectId || state.project?.id || ''
})

const buildCopilotInspireDirectionHint = () => {
  if (workspaceStore.currentObject?.type === 'writing-result') {
    return `${copilotCurrentObjectTitle.value}，请给出更适合当前结果状态的推进方向`
  }
  if (workspaceStore.currentView === 'writing') {
    return `${currentChapter.value?.title || '当前章节'}，请围绕下一段推进和冲突升级提供分支灵感`
  }
  if (workspaceStore.currentView === 'structure') {
    return `${currentTargetArcText.value || '当前结构对象'}，请围绕剧情弧落地章节提供分支灵感`
  }
  if (workspaceStore.currentView === 'tasks') {
    return `当前有 ${taskCenterSnapshot.value.failedCount || 0} 个失败任务，请围绕恢复顺序和对象切换提供灵感`
  }
  return `${copilotCurrentObjectTitle.value}，请给出下一步最值得推进的创作分支`
}

const buildRemoteBranchInspireItems = (branches = []) => {
  return branches
    .map((branch, index) => {
      const title = String(branch?.title || '').trim()
      const summary = String(branch?.summary || '').trim()
      const conflict = String(branch?.core_conflict || '').trim()
      const progressions = Array.isArray(branch?.key_progressions) ? branch.key_progressions.filter(Boolean) : []
      if (!title && !summary && !conflict) return null

      const focus = progressions[0] || (Array.isArray(branch?.related_characters) && branch.related_characters[0]) || ''
      return {
        key: `remote-branch-${branch?.id || index}`,
        tag: '分支',
        focus,
        title: title || `剧情分支 ${index + 1}`,
        description: summary || conflict || '来自项目分支仓库的当前候选方向。',
        rationale: [
          conflict ? `核心冲突：${conflict}` : '',
          branch?.consistency_note ? `一致性提醒：${branch.consistency_note}` : '',
          branch?.risk_note ? `风险提醒：${branch.risk_note}` : ''
        ].filter(Boolean).join(' · '),
        prompt: `请围绕这个剧情分支「${title || `剧情分支 ${index + 1}`}」继续展开，重点说明它与当前工作区对象的关系、最大收益和最大风险。`,
        cta: '打开结构',
        action: copilotStructureAction
      }
    })
    .filter(Boolean)
    .slice(0, 2)
}

const buildRemotePlanInspireItems = (plans = [], branchTitle = '') => {
  return plans
    .map((plan, index) => {
      const title = String(plan?.title || '').trim()
      const goal = String(plan?.goal || '').trim()
      const hook = String(plan?.ending_hook || '').trim()
      const taskSeed = plan?.chapter_task_seed || {}
      const chapterFunction = String(taskSeed?.chapter_function || '').trim()
      const mustContinuePoints = Array.isArray(taskSeed?.must_continue_points) ? taskSeed.must_continue_points.filter(Boolean) : []
      if (!title && !goal && !hook) return null

      return {
        key: `remote-plan-${plan?.id || index}`,
        tag: '规划',
        focus: branchTitle || `第 ${index + 1} 章规划`,
        title: title || `章节规划 ${index + 1}`,
        description: goal || hook || '来自章节规划服务的落地建议。',
        rationale: [
          chapterFunction ? `章节功能：${chapterFunction}` : '',
          mustContinuePoints[0] ? `必须承接：${mustContinuePoints[0]}` : '',
          hook ? `结尾钩子：${hook}` : ''
        ].filter(Boolean).join(' · '),
        prompt: `请围绕这个章节规划「${title || `章节规划 ${index + 1}`}」继续展开，说明这一章最适合如何承接当前对象、如何制造推进，以及结尾钩子该怎么落。`,
        cta: '打开章节',
        action: {
          type: 'section',
          section: 'chapters'
        }
      }
    })
    .filter(Boolean)
    .slice(0, 2)
}

const loadCopilotInspireRemoteItems = async () => {
  if (workspaceStore.currentCopilotTab !== 'inspire') {
    return
  }

  const projectId = state.projectId || state.project?.id || ''
  if (!projectId) {
    copilotInspireRemoteItems.value = []
    return
  }

  const signature = buildCopilotInspireSignature()
  if (copilotInspireLastSignature.value === signature) {
    return
  }

  copilotInspireLastSignature.value = signature
  copilotInspirePending.value = true

  try {
    const response = await projectApi.branchesV2(projectId, {
      direction_hint: buildCopilotInspireDirectionHint(),
      branch_count: 3
    })
    const branches = response?.branches || []
    const branchItems = buildRemoteBranchInspireItems(branches)
    const primaryBranch = branches[0] || null

    let planItems = []
    if (primaryBranch?.id) {
      try {
        const planResponse = await projectApi.chapterPlanV2(projectId, {
          branch_id: primaryBranch.id,
          chapter_count: 2,
          target_words_per_chapter: 1800
        })
        planItems = buildRemotePlanInspireItems(planResponse?.plans || [], String(primaryBranch.title || '').trim())
      } catch (error) {
        planItems = []
      }
    }

    copilotInspireRemoteItems.value = [...branchItems, ...planItems]
  } catch (error) {
    copilotInspireRemoteItems.value = []
  } finally {
    copilotInspirePending.value = false
  }
}

const copilotInspireItems = computed(() => {
  const items = [...copilotInspireRemoteItems.value]
  const chapterTitle = currentChapter.value?.title || '当前章节'
  const focusTitle = copilotCurrentObjectTitle.value

  if (workspaceStore.currentObject?.type === 'writing-result') {
    const resultType = workspaceStore.currentObject.resultType || 'candidate'
    const resultLabel = getWritingResultLabel(resultType)

    if (resultType === 'issues') {
      items.push({
        key: 'inspire-issues-repair',
        tag: '修复',
        focus: resultLabel,
        title: `先规划 ${resultLabel} 的修复顺序`,
        description: '先判断哪些问题最先影响剧情、信息一致性和人物状态，再决定回正文还是回结构页。',
        rationale: '这类结果最适合先做优先级排序，而不是立即整体重写。',
        prompt: `请围绕当前${resultLabel}「${focusTitle}」给我一个修复优先级列表，并说明每一项更适合在正文、结构还是任务台处理。`,
        cta: '查看结果',
        action: {
          type: 'writing-result',
          chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
          resultType,
          taskId: workspaceStore.currentObject.taskId || '',
          title: workspaceStore.currentObject.title || resultLabel
        }
      })
    } else if (resultType === 'diff') {
      items.push({
        key: 'inspire-diff-merge',
        tag: '改写',
        focus: resultLabel,
        title: '评估哪些改写值得吸收',
        description: '对照当前正文与改写结果，先找高收益改动，再决定整体替换还是局部吸收。',
        rationale: '改写结果更适合先筛价值点，而不是直接整段覆盖。',
        prompt: `请围绕当前${resultLabel}「${focusTitle}」指出最值得采纳的三处变化，并说明各自应该整体替换还是局部吸收。`,
        cta: '查看结果',
        action: {
          type: 'writing-result',
          chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
          resultType,
          taskId: workspaceStore.currentObject.taskId || '',
          title: workspaceStore.currentObject.title || resultLabel
        }
      })
    } else {
      items.push({
        key: 'inspire-candidate-landing',
        tag: '候选',
        focus: resultLabel,
        title: '判断候选稿如何并入正文',
        description: '先决定是追加、覆盖还是局部吸收，再回正文落地会更稳。',
        rationale: '候选稿的风险通常不在内容缺失，而在并入方式不合适。',
        prompt: `请围绕当前${resultLabel}「${focusTitle}」给我一个并入正文的建议：追加、覆盖还是局部吸收？并说明原因。`,
        cta: '查看结果',
        action: {
          type: 'writing-result',
          chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
          resultType,
          taskId: workspaceStore.currentObject.taskId || '',
          title: workspaceStore.currentObject.title || resultLabel
        }
      })
    }
  }

  if (workspaceStore.currentView === 'writing' && currentChapter.value?.id) {
    items.push({
      key: 'inspire-next-scene',
      tag: '续写',
      focus: chapterTitle,
      title: '生成下一段推进方案',
      description: '给当前章节生成更具体的下一段承接方向，而不是只给抽象建议。',
      rationale: '当前在写作视图时，最有价值的灵感通常是“下一段怎么写”。',
      prompt: `请围绕当前章节「${chapterTitle}」给我三个下一段推进方案，分别偏向冲突升级、情绪沉淀和信息揭示。`,
      cta: '打开写作',
      action: {
        type: 'chapter',
        chapterId: currentChapter.value.id
      }
    })
  }

  if (workspaceStore.currentView === 'structure' || currentTargetArcText.value) {
    items.push({
      key: 'inspire-structure-landing',
      tag: '结构',
      focus: currentTargetArcText.value || '活跃剧情弧',
      title: '反推还缺哪一章落地',
      description: '从当前结构对象反推还缺哪些章节承接，避免结构停留在概念层。',
      rationale: '结构灵感最有用的形式不是再抽象一次，而是给出落地章节方向。',
      prompt: `请根据当前结构对象「${currentTargetArcText.value || focusTitle}」判断还缺哪些章节来落地，并给出优先顺序。`,
      cta: '打开结构',
      action: copilotStructureAction
    })
  }

  if (taskCenterSnapshot.value.failedCount > 0) {
    items.push({
      key: 'inspire-failed-task-recovery',
      tag: '恢复',
      focus: `${taskCenterSnapshot.value.failedCount} 个失败任务`,
      title: '先决定失败任务恢复顺序',
      description: '失败任务会污染写作、结构和章节判断，先确定恢复顺序更稳。',
      rationale: '任务恢复顺序明确后，后续对象切换和结果回流会更顺。',
      prompt: `当前有 ${taskCenterSnapshot.value.failedCount} 个失败任务，请给我一个恢复顺序，并说明每个任务更适合回哪个对象处理。`,
      cta: '打开任务',
      action: {
        type: 'task-filter',
        filter: 'failed'
      }
    })
  }

  if (!items.length) {
    items.push({
      key: 'inspire-default-next-step',
      tag: '概览',
      focus: focusTitle,
      title: '决定下一步最值得推进的对象',
      description: '当没有明显失败项或结果对象时，直接让 Inspire 给出下一个最值得进入的对象。',
      rationale: '概览态最适合做“下一步去哪”的决策，而不是继续堆信息。',
      prompt: '请根据当前工作区状态，给我三个下一步最值得进入的对象或视图，并说明各自收益。',
      cta: '打开概览',
      action: {
        type: 'section',
        section: 'overview'
      }
    })
  }

  const seen = new Set()
  const dedupedItems = items.filter((item) => {
    const key = String(item?.key || '')
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })

  const rankedItems = dedupedItems
    .map((item, index) => ({
      ...item,
      score: scoreInspireItem(item, index)
    }))
    .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))

  return rankedItems.slice(0, 4)
})

const overviewDecisionCards = computed(() => {
  const issueCount = Number(state.editor?.integrityCheck?.issue_list?.length || 0)
  const cards = [
    {
      key: 'continue-writing',
      tag: '写作',
      cta: '继续',
      title: currentChapter.value?.title ? `继续章节：${currentChapter.value.title}` : '从最新章节开始写作',
      description: '优先回到正文工作区，继续当前章节或最近章节的写作与修订。',
      meta: currentChapter.value?.title || recentChapter.value?.title || '将自动打开最近章节',
      onClick: () => openSection('writing', currentChapterId.value ? { chapterId: currentChapterId.value } : {})
    },
    {
      key: 'structure-focus',
      tag: '结构',
      cta: '查看',
      title: currentTargetArcText.value ? '检查活跃剧情弧' : '打开故事模型',
      description: currentTargetArcText.value
        ? '先确认主线和当前推进阶段，避免写作脱离结构目标。'
        : '当前缺少明显活跃剧情弧，先回到结构工作台确定主线推进。',
      meta: currentTargetArcText.value || `活跃弧 ${(state.activeArcs || []).length || 0} 条`,
      onClick: () => openSection('structure')
    },
    {
      key: 'chapter-manager',
      tag: '章节',
      cta: '进入',
      title: '整理章节与落点',
      description: '快速检查章节顺序、标题与最近更新情况，决定下一章承接位置。',
      meta: `${(state.chapters || []).length || 0} 个章节入口`,
      onClick: () => openSection('chapters')
    }
  ]

  if (issueCount > 0) {
    cards.unshift({
      key: 'issue-review',
      tag: '问题单',
      cta: '处理',
      title: '先处理当前问题单',
      description: '当前章节已有待处理问题，先解决一致性和结构风险，再继续写作更稳妥。',
      meta: `${issueCount} 个问题待处理`,
      onClick: () => openSection('writing', currentChapterId.value ? { chapterId: currentChapterId.value } : {})
    })
  } else if (taskSummaryCounts.value.failed > 0) {
    cards.unshift({
      key: 'failed-task-review',
      tag: '任务',
      cta: '处理',
      title: '先处理失败任务',
      description: '当前存在失败任务，建议先恢复失败链路，再继续写作或结构推进。',
      meta: `${taskSummaryCounts.value.failed} 个失败任务`,
      onClick: () => openSection('tasks')
    })
  } else {
    cards.push({
      key: 'tasks-audit',
      tag: '任务',
      cta: '查看',
      title: '检查任务台与整理状态',
      description: '如果当前没有明显问题单，下一步适合回到任务台确认整理和审查状态。',
      meta: taskStatusText.value,
      onClick: () => openSection('tasks')
    })
  }

  return cards.slice(0, 4)
})

const currentCopilotSessionMeta = computed(() => {
  const currentObject = workspaceStore.currentObject || {}
  const view = workspaceStore.currentView || 'overview'
  const baseTitle = currentObject.title || currentObjectLabel.value || currentChapter.value?.title || currentViewMeta.value.title
  let discriminator = 'default'

  if (currentObject.type === 'chapter' && currentObject.id) {
    discriminator = `chapter:${currentObject.id}`
  } else if (currentObject.type === 'plot_arc' && currentObject.arcId) {
    discriminator = `arc:${currentObject.arcId}`
  } else if (currentObject.type === 'task' && currentObject.taskId) {
    discriminator = `task:${currentObject.taskId}`
  } else if (currentObject.type === 'writing-result') {
    discriminator = `writing-result:${currentObject.chapterId || 'chapter'}:${currentObject.resultType || 'candidate'}`
  } else if (currentObject.type === 'task-filter' && currentObject.filter) {
    discriminator = `task-filter:${currentObject.filter}`
  } else if (view === 'writing' && currentChapter.value?.id) {
    discriminator = `chapter:${currentChapter.value.id}`
  } else {
    discriminator = `${currentObject.type || 'default'}:${baseTitle || 'default'}`
  }

  return {
    key: `${view}::${discriminator}`,
    label: baseTitle || currentViewMeta.value.title,
    view,
    objectTitle: baseTitle || ''
  }
})

const formatRelativeTime = (timestamp) => {
  const value = Number(timestamp || 0)
  if (!value) {
    return ''
  }
  const diff = Math.max(0, Date.now() - value)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  return `${Math.floor(diff / day)} 天前`
}

const copilotChatSessions = computed(() => {
  return [...workspaceStore.copilotChatSessions]
    .sort((a, b) => {
      const aActive = a.key === workspaceStore.currentCopilotChatSessionKey ? 1 : 0
      const bActive = b.key === workspaceStore.currentCopilotChatSessionKey ? 1 : 0
      if (aActive !== bActive) {
        return bActive - aActive
      }
      return Number(b.updatedAt || 0) - Number(a.updatedAt || 0)
    })
    .map((session) => ({
      key: session.key,
      label: session.label,
      summary: session.summary || '',
      messageCount: session.messageCount || 0,
      relativeLabel: formatRelativeTime(session.updatedAt),
      metaText: [session.messageCount ? `${session.messageCount} 条消息` : '', formatRelativeTime(session.updatedAt)]
        .filter(Boolean)
        .join(' · ')
    }))
})

const currentIssueCommands = computed(() => {
  const issues = Array.isArray(state.editor?.integrityCheck?.issue_list) ? state.editor.integrityCheck.issue_list : []
  return issues.slice(0, 6).map((issue, index) => ({
    id: `issue-${index}`,
    group: '问题单',
    title: issue.title || issue.code || `问题 ${index + 1}`,
    subtitle: issue.detail || '在写作页中定位该问题',
    keywords: `${issue.title || ''} ${issue.detail || ''} issue 审查 问题`,
    hint: issue.severity === 'high' ? '高优先级' : '问题',
    action: {
      type: 'issue',
      issueIndex: index,
      issueTitle: issue.title || issue.code || `问题 ${index + 1}`,
      issueCode: issue.code || '',
      chapterId: currentChapter.value?.id || ''
    }
  }))
})

const buildRecentDocumentAction = (doc) => {
  if (doc.type === 'chapter') {
    return { type: 'chapter', chapterId: doc.id }
  }
  if (doc.type === 'plot_arc') {
    return { type: 'arc', arcId: doc.id, title: doc.title || '' }
  }
  if (doc.type === 'story_model') {
    return { type: 'section', section: 'structure', object: { type: 'story_model' } }
  }
  if (doc.type === 'character') {
    return { type: 'section', section: 'structure', object: { type: 'character' } }
  }
  if (doc.type === 'worldview') {
    return { type: 'section', section: 'structure', object: { type: 'worldview' } }
  }
  if (doc.type === 'risk') {
    return { type: 'section', section: 'structure', object: { type: 'risk' } }
  }
  if (doc.type === 'task-filter') {
    return { type: 'task-filter', filter: doc.id }
  }
  if (doc.type === 'task') {
    return {
      type: 'task',
      taskId: doc.id,
      title: doc.title || '',
      chapterId: doc.chapterId || '',
      status: doc.status || '',
      targetArcId: doc.targetArcId || ''
    }
  }
  if (doc.type === 'issue') {
    return {
      type: 'issue',
      issueId: doc.id,
      issueIndex: typeof doc.index === 'number' ? doc.index : Number(doc.index ?? -1),
      issueTitle: doc.title || '',
      issueCode: doc.code || '',
      chapterId: doc.chapterId || ''
    }
  }
  if (doc.type === 'writing-result') {
    return {
      type: 'writing-result',
      chapterId: doc.chapterId || '',
      resultType: doc.resultType || 'candidate',
      taskId: doc.taskId || '',
      title: doc.title || ''
    }
  }
  return { type: 'section', section: workspaceStore.currentView || 'overview' }
}

const getTaskStatusLabel = (status) => {
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  if (status === 'completed') return '已完成'
  if (status === 'paused') return '已暂停'
  return ''
}

const getChapterLabelById = (chapterId) => {
  const chapter = (state.chapters || []).find((item) => item.id === chapterId)
  if (!chapter) {
    return ''
  }
  return chapter.title || `第 ${chapter.chapter_number || '?'} 章`
}

const getRecentDocumentPresentation = (doc) => {
  const relativeTime = formatRelativeTime(doc.lastOpenedAt)
  const chapterLabel = getChapterLabelById(doc.chapterId)
  const taskStatusLabel = getTaskStatusLabel(doc.status)

  if (doc.type === 'chapter') {
    return {
      subtitle: ['重新打开该章节', relativeTime].filter(Boolean).join(' · '),
      hint: '最近',
      priority: 55
    }
  }

  if (doc.type === 'plot_arc') {
    return {
      subtitle: ['重新打开该剧情弧', relativeTime].filter(Boolean).join(' · '),
      hint: '结构',
      priority: 45
    }
  }

  if (doc.type === 'story_model') {
    return {
      subtitle: ['重新打开结构模型', relativeTime].filter(Boolean).join(' · '),
      hint: '结构',
      priority: 40
    }
  }

  if (doc.type === 'character') {
    return {
      subtitle: ['恢复角色视角', relativeTime].filter(Boolean).join(' · '),
      hint: '结构',
      priority: 41
    }
  }

  if (doc.type === 'worldview') {
    return {
      subtitle: ['恢复世界观视角', relativeTime].filter(Boolean).join(' · '),
      hint: '结构',
      priority: 41
    }
  }

  if (doc.type === 'risk') {
    return {
      subtitle: ['恢复风险点视角', relativeTime].filter(Boolean).join(' · '),
      hint: '结构',
      priority: 42
    }
  }

  if (doc.type === 'task') {
    return {
      subtitle: ['恢复该任务对象', chapterLabel, relativeTime].filter(Boolean).join(' · '),
      hint: taskStatusLabel || '任务',
      priority: doc.status === 'failed' ? 72 : doc.status === 'running' ? 68 : 58
    }
  }

  if (doc.type === 'issue') {
    return {
      subtitle: ['恢复该问题定位', chapterLabel, relativeTime].filter(Boolean).join(' · '),
      hint: '问题',
      priority: 70
    }
  }

  if (doc.type === 'writing-result') {
    const resultLabel = buildWorkspaceResultLabel(doc.resultType, { noneLabel: '候选稿' })
    return {
      subtitle: ['恢复该结果回流', resultLabel, chapterLabel, relativeTime].filter(Boolean).join(' · '),
      hint: '结果',
      priority: doc.resultType === 'issues' ? 71 : 66
    }
  }

  if (doc.type === 'task-filter') {
    return {
      subtitle: ['恢复该任务筛选', relativeTime].filter(Boolean).join(' · '),
      hint: '任务',
      priority: 38
    }
  }

  return {
    subtitle: ['重新打开最近对象', relativeTime].filter(Boolean).join(' · '),
    hint: '最近',
    priority: 30
  }
}

const getCommandObjectRestoreKey = (item) => {
  const action = item?.action || {}
  if (action.type === 'chapter' && action.chapterId) {
    return `chapter:${action.chapterId}`
  }
  if (action.type === 'chapter-manager' && action.chapterId) {
    return `chapter:${action.chapterId}`
  }
  if (action.type === 'arc' && action.arcId) {
    return `plot_arc:${action.arcId}`
  }
  if (action.type === 'task-filter' && action.filter) {
    return `task-filter:${action.filter}`
  }
  if (action.type === 'task' && action.taskId) {
    return `task:${action.taskId}`
  }
  if (action.type === 'issue') {
    const chapterId = action.chapterId || currentChapter.value?.id || 'chapter'
    const issueIndex = Number(action.issueIndex ?? -1)
    return `issue:${action.issueId || `${chapterId}::issue-${issueIndex}`}`
  }
  if (action.type === 'writing-result') {
    const chapterId = action.chapterId || currentChapter.value?.id || 'chapter'
    return `writing-result:${chapterId}:${action.resultType || 'candidate'}`
  }
  if (action.type === 'section' && action.section === 'structure' && action.object?.type) {
    return `${action.object.type}:${action.object.type}`
  }
  if (action.type === 'section' && action.section === 'overview') {
    return 'overview:overview'
  }
  if (action.type === 'section' && action.section === 'settings') {
    return 'settings:settings'
  }
  return ''
}

const recentOpenDocumentCommands = computed(() => {
  return (workspaceStore.openDocuments || [])
    .slice(0, 8)
    .map((doc, index) => {
      const presentation = getRecentDocumentPresentation(doc)
      return {
        id: `recent-doc-${doc.type}-${doc.id}-${index}`,
        group: '最近对象',
        title: doc.title || `${doc.type} ${doc.id}`,
        subtitle: presentation.subtitle,
        keywords: `${doc.title || ''} 最近 打开 recent ${doc.type} ${doc.status || ''} ${doc.code || ''} ${getChapterLabelById(doc.chapterId)}`,
        hint: presentation.hint,
        priority: presentation.priority,
        action: buildRecentDocumentAction(doc)
      }
    })
})

const recentCommandIdSet = computed(() => (
  new Set((workspaceStore.recentCommandItems || []).map((item) => item.id))
))

const recentOpenDocumentIdSet = computed(() => (
  new Set((recentOpenDocumentCommands.value || []).map((item) => item.id))
))

const commandPaletteItems = computed(() => {
  const items = [
    {
      id: 'view-overview',
      group: '视图',
      title: '打开概览',
      subtitle: '回到小说整体概览',
      keywords: 'overview 概览 dashboard 总览',
      action: { type: 'section', section: 'overview' }
    },
    {
      id: 'view-writing',
      group: '视图',
      title: '打开写作',
      subtitle: '进入正文写作工作区',
      keywords: 'writing 写作 正文',
      action: recentChapter.value?.id
        ? { type: 'chapter', chapterId: recentChapter.value.id }
        : { type: 'section', section: 'writing' }
    },
    {
      id: 'view-structure',
      group: '视图',
      title: '打开结构',
      subtitle: '查看结构摘要和剧情弧',
      keywords: 'structure 结构 剧情弧',
      action: { type: 'section', section: 'structure', object: { type: 'plot_arc' } }
    },
    {
      id: 'view-chapters',
      group: '视图',
      title: '打开章节',
      subtitle: '进入章节管理工作区',
      keywords: 'chapters 章节 管理',
      action: { type: 'section', section: 'chapters' }
    },
    {
      id: 'view-tasks',
      group: '视图',
      title: '打开任务',
      subtitle: '查看任务与审查结果',
      keywords: 'tasks 任务 审查',
      action: { type: 'task-filter', filter: 'all' }
    },
    {
      id: 'view-settings',
      group: '视图',
      title: '打开设置',
      subtitle: '查看工作区设置与运行诊断',
      keywords: 'settings 设置 配置 诊断',
      action: { type: 'section', section: 'settings' }
    },
    {
      id: 'story-model',
      group: '结构',
      title: '打开故事模型',
      subtitle: '查看整体结构模型与约束',
      keywords: 'story model 结构 模型 约束',
      hint: '结构',
      action: { type: 'section', section: 'structure', object: { type: 'story_model' } }
    },
    {
      id: 'structure-character',
      group: '结构',
      title: '打开角色视角',
      subtitle: '查看角色关系、人物弧和冲突承载',
      keywords: 'character 角色 人物弧 结构',
      hint: '结构',
      action: { type: 'section', section: 'structure', object: { type: 'character' } }
    },
    {
      id: 'structure-worldview',
      group: '结构',
      title: '打开世界观视角',
      subtitle: '查看设定规则和世界观支撑',
      keywords: 'worldview 世界观 设定 结构',
      hint: '结构',
      action: { type: 'section', section: 'structure', object: { type: 'worldview' } }
    },
    {
      id: 'structure-risk',
      group: '结构',
      title: '打开风险点视角',
      subtitle: '查看结构风险、断层与约束缺口',
      keywords: 'risk 风险点 结构 断层',
      hint: '结构',
      action: { type: 'section', section: 'structure', object: { type: 'risk' } }
    },
    {
      id: 'dashboard',
      group: '视图',
      title: '返回主页',
      subtitle: '离开当前工作区回到首页',
      keywords: 'dashboard 首页 返回',
      action: { type: 'dashboard' }
    }
  ]

  if (workspaceStore.currentObject?.type === 'chapter' && workspaceStore.currentObject?.id) {
    items.unshift({
      id: `current-object-chapter-${workspaceStore.currentObject.id}`,
      group: '当前对象',
      title: `继续当前章节：${workspaceStore.currentObject.title || currentObjectLabel.value || '未命名章节'}`,
      subtitle: '回到当前章节正文写作',
      keywords: `${workspaceStore.currentObject.title || ''} 当前对象 当前章节 writing`,
      hint: '当前',
      action: { type: 'chapter', chapterId: workspaceStore.currentObject.id }
    })
  }

  if (workspaceStore.currentObject?.type === 'plot_arc' && workspaceStore.currentObject?.arcId) {
    items.unshift({
      id: `current-object-arc-${workspaceStore.currentObject.arcId}`,
      group: '当前对象',
      title: `打开当前剧情弧：${workspaceStore.currentObject.title || workspaceStore.currentObject.arcId}`,
      subtitle: '切到结构页并聚焦当前剧情弧',
      keywords: `${workspaceStore.currentObject.title || ''} 当前对象 剧情弧 structure`,
      hint: '当前',
      action: {
        type: 'arc',
        arcId: workspaceStore.currentObject.arcId,
        title: workspaceStore.currentObject.title || ''
      }
    })
  }

  if (['story_model', 'character', 'worldview', 'risk'].includes(workspaceStore.currentObject?.type)) {
    const structureType = workspaceStore.currentObject.type
    const label = {
      story_model: '故事模型',
      character: '角色',
      worldview: '世界观',
      risk: '风险点'
    }[structureType] || structureType
    items.unshift({
      id: `current-object-structure-${structureType}`,
      group: '当前对象',
      title: `打开当前结构视角：${label}`,
      subtitle: '切到结构页并恢复当前结构视角',
      keywords: `${label} 当前对象 结构 structure`,
      hint: '当前',
      action: {
        type: 'section',
        section: 'structure',
        object: { type: structureType }
      }
    })
  }

  if (workspaceStore.currentObject?.type === 'task-filter') {
    items.unshift({
      id: `current-task-filter-${workspaceStore.currentObject.filter || 'all'}`,
      group: '当前对象',
      title: `当前任务筛选：${workspaceStore.currentObject.filter || 'all'}`,
      subtitle: '回到当前任务筛选视图',
      keywords: `${workspaceStore.currentObject.filter || 'all'} 当前对象 任务 筛选`,
      hint: '当前',
      action: {
        type: 'task-filter',
        filter: workspaceStore.currentObject.filter || 'all'
      }
    })
  }

  if (workspaceStore.currentObject?.type === 'task' && workspaceStore.currentObject?.id) {
    items.unshift({
      id: `current-object-task-${workspaceStore.currentObject.id}`,
      group: '当前对象',
      title: `打开当前任务：${workspaceStore.currentObject.title || workspaceStore.currentTask?.label || '当前任务'}`,
      subtitle: '切到任务台并恢复当前任务焦点',
      keywords: `${workspaceStore.currentObject.title || ''} 当前对象 任务 task`,
      hint: '当前',
      action: {
        type: 'task',
        taskId: workspaceStore.currentObject.id,
        title: workspaceStore.currentObject.title || workspaceStore.currentTask?.label || '',
        chapterId: workspaceStore.currentObject.chapterId || '',
        status: workspaceStore.currentObject.status || ''
      }
    })
  }

  if (workspaceStore.currentObject?.type === 'issue') {
    items.unshift({
      id: `current-object-issue-${workspaceStore.currentObject.id || workspaceStore.currentObject.issueId || workspaceStore.currentObject.index}`,
      group: '当前对象',
      title: `回到当前问题：${workspaceStore.currentObject.title || workspaceStore.currentObject.code || '问题单'}`,
      subtitle: '回到写作页并恢复当前问题定位',
      keywords: `${workspaceStore.currentObject.title || ''} 当前对象 问题 issue`,
      hint: '当前',
      action: {
        type: 'issue',
        issueId: workspaceStore.currentObject.id || workspaceStore.currentObject.issueId || '',
        issueIndex: Number(workspaceStore.currentObject.index ?? -1),
        issueTitle: workspaceStore.currentObject.title || '',
        issueCode: workspaceStore.currentObject.code || '',
        chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || ''
      }
    })
  }

  if (workspaceStore.currentObject?.type === 'writing-result') {
    const resultType = workspaceStore.currentObject.resultType || 'candidate'
    const resultLabel = buildWorkspaceResultLabel(resultType, { noneLabel: '候选稿' })
    items.unshift({
      id: `current-object-writing-result-${workspaceStore.currentObject.id || `${workspaceStore.currentObject.chapterId || 'chapter'}-${resultType}`}`,
      group: '当前对象',
      title: `回到当前结果：${resultLabel}`,
      subtitle: '回到写作页并恢复当前结果区域',
      keywords: `${resultLabel} 当前对象 writing result`,
      hint: '当前',
      action: {
        type: 'writing-result',
        chapterId: workspaceStore.currentObject.chapterId || currentChapter.value?.id || '',
        resultType,
        taskId: workspaceStore.currentObject.taskId || '',
        title: workspaceStore.currentObject.title || resultLabel
      }
    })
  }

  const currentTaskIsFocusedObject = (
    workspaceStore.currentObject?.type === 'task'
    && workspaceStore.currentObject?.id
    && workspaceStore.currentTask?.id
    && String(workspaceStore.currentObject.id) === String(workspaceStore.currentTask.id)
  )

  if (workspaceStore.currentTask?.id && !currentTaskIsFocusedObject) {
    const currentTaskChapterLabel = getChapterLabelById(workspaceStore.currentTask.chapterId)
    const currentTaskStatusLabel = getTaskStatusLabel(workspaceStore.currentTask.status)
    items.push({
      id: `current-task-${workspaceStore.currentTask.id}`,
      group: '任务',
      title: workspaceStore.currentTask.label || '当前任务',
      subtitle: ['恢复当前任务上下文', currentTaskChapterLabel, currentTaskStatusLabel].filter(Boolean).join(' · '),
      keywords: `${workspaceStore.currentTask.label || ''} 当前任务 task`,
      hint: currentTaskStatusLabel || '当前',
      action: {
        type: 'task',
        taskId: workspaceStore.currentTask.id,
        title: workspaceStore.currentTask.label || '',
        chapterId: workspaceStore.currentTask.chapterId || '',
        status: workspaceStore.currentTask.status || '',
        targetArcId: workspaceStore.currentTask.targetArcId || ''
      }
    })
  }

  ;(state.chapters || []).forEach((chapter) => {
    items.push({
      id: `chapter-${chapter.id}`,
      group: '章节',
      title: chapter.title || `第 ${chapter.chapter_number || '?'} 章`,
      subtitle: `打开章节写作 · 第 ${chapter.chapter_number || '?'} 章`,
      keywords: `${chapter.title || ''} 章节 chapter writing`,
      hint: '写作',
      action: { type: 'chapter', chapterId: chapter.id }
    })
    items.push({
      id: `chapter-manage-${chapter.id}`,
      group: '章节',
      title: `在章节管理中定位：${chapter.title || `第 ${chapter.chapter_number || '?'} 章`}`,
      subtitle: '切到章节管理并聚焦当前章节',
      keywords: `${chapter.title || ''} 章节 管理 定位`,
      hint: '管理',
      action: {
        type: 'chapter-manager',
        chapterId: chapter.id,
        title: chapter.title || ''
      }
    })
  })

  ;(state.activeArcs || []).slice(0, 8).forEach((arc) => {
    items.push({
      id: `arc-${arc.arc_id}`,
      group: '剧情弧',
      title: arc.title || arc.arc_id,
      subtitle: `打开剧情弧对象 · ${arc.current_stage || arc.stage || '未标注阶段'}`,
      keywords: `${arc.title || ''} 剧情弧 structure arc`,
      hint: '结构',
      action: {
        type: 'arc',
        arcId: arc.arc_id,
        title: arc.title || arc.arc_id
      }
    })
  })

  ;[
    { key: 'all', title: '全部任务' },
    { key: 'running', title: '运行中任务' },
    { key: 'failed', title: '失败任务' },
    { key: 'completed', title: '已完成任务' },
    { key: 'audit', title: '审查结果' }
  ].forEach((filter) => {
    items.push({
      id: `task-filter-${filter.key}`,
      group: '任务',
      title: filter.title,
      subtitle: '切换任务筛选',
      keywords: `${filter.title} task filter`,
      hint: '任务',
      action: { type: 'task-filter', filter: filter.key }
    })
  })

  if (taskSummaryCounts.value.failed > 0) {
    items.push({
      id: 'task-failed-shortcut',
      group: '任务',
      title: `处理失败任务 (${taskSummaryCounts.value.failed})`,
      subtitle: '直接切到失败任务筛选并优先处理异常链路',
      keywords: '失败任务 failed task 风险 恢复',
      hint: '优先',
      action: { type: 'task-filter', filter: 'failed' }
    })
  }

  if (taskSummaryCounts.value.audit > 0) {
    items.push({
      id: 'task-audit-shortcut',
      group: '任务',
      title: `查看审查任务 (${taskSummaryCounts.value.audit})`,
      subtitle: '直接切到审查结果与分析任务筛选',
      keywords: '审查任务 audit analyze 审查结果',
      hint: '审查',
      action: { type: 'task-filter', filter: 'audit' }
    })
  }

  if (taskRecommendationItems.value[0]) {
    const item = taskRecommendationItems.value[0]
    items.push({
      id: `task-recommendation-${item.key}`,
      group: '任务',
      title: item.title,
      subtitle: item.description || '根据当前任务状态给出的推荐处理入口',
      keywords: `${item.title} ${item.description || ''} 推荐 任务`,
      hint: item.tag || '推荐',
      action: item.action || { type: 'task-filter', filter: 'all' }
    })
  }

  items.push(
    {
      id: 'copilot-chat',
      group: '助手',
      title: '打开助手对话',
      subtitle: '切到对话页并保留当前对象上下文',
      keywords: 'copilot chat 对话 助手',
      hint: '助手',
      action: { type: 'copilot-tab', tab: 'chat' }
    },
    {
      id: 'copilot-context',
      group: '助手',
      title: '打开助手上下文',
      subtitle: '查看当前对象上下文卡片',
      keywords: 'copilot context 上下文',
      hint: '助手',
      action: { type: 'copilot-tab', tab: 'context' }
    },
    {
      id: 'copilot-inspire',
      group: '助手',
      title: '打开助手灵感',
      subtitle: '查看建议动作与灵感提示',
      keywords: 'copilot inspire 灵感 建议',
      hint: '助手',
      action: { type: 'copilot-tab', tab: 'inspire' }
    }
  )

  copilotChatSessions.value.slice(0, 6).forEach((session) => {
    items.push({
      id: `chat-session-${session.key}`,
      group: '助手会话',
      title: session.label,
      subtitle: session.summary || `切到该对象的聊天会话${session.metaText ? ` · ${session.metaText}` : ''}`,
      keywords: `${session.label} chat session 会话`,
      hint: '会话',
      action: {
        type: 'chat-session',
        sessionKey: session.key
      }
    })
  })

  items.push(...recentOpenDocumentCommands.value)
  items.push(...currentIssueCommands.value)

  const currentObjectRestoreKeys = new Set(
    items
      .filter((item) => item.group === '当前对象')
      .map((item) => getCommandObjectRestoreKey(item))
      .filter(Boolean)
  )

  return items.filter((item) => {
    if (item.group !== '最近对象') {
      return true
    }
    const restoreKey = getCommandObjectRestoreKey(item)
    if (!restoreKey) {
      return true
    }
    return !currentObjectRestoreKeys.has(restoreKey)
  })
})

const filteredCommandPaletteItems = computed(() => {
  const query = String(commandPaletteQuery.value || '').trim().toLowerCase()
  const filtered = (!query ? commandPaletteItems.value : commandPaletteItems.value.filter((item) => {
    const haystack = [
      item.title,
      item.subtitle,
      item.group,
      item.keywords
    ].join(' ').toLowerCase()
    return haystack.includes(query)
  }))

  const scoreCommandItem = (item) => {
    let score = 0
    const title = String(item.title || '').toLowerCase()
    const subtitle = String(item.subtitle || '').toLowerCase()
    const keywords = String(item.keywords || '').toLowerCase()
    const group = String(item.group || '').toLowerCase()
    const isCurrentObject = group.includes('当前对象')
    const isRecentCommand = recentCommandIdSet.value.has(item.id)
    const isRecentOpen = recentOpenDocumentIdSet.value.has(item.id)
    const isTaskGroup = group === '任务'
    const isViewGroup = group === '视图'
    const isCurrentView = item.action?.section === workspaceStore.currentView
      || (item.action?.type === 'task-filter' && workspaceStore.currentView === 'tasks' && item.action?.filter === workspaceStore.currentTaskFilter)
    const commandPriority = Number(item.priority || 0)

    if (isCurrentObject) score += 80
    if (isRecentCommand) score += 60
    if (isRecentOpen) score += 45
    if (isCurrentView) score += 35
    if (!query && isTaskGroup) score += 10
    if (!query && isViewGroup) score += 5
    if (!query) score += commandPriority

    if (!query) {
      return score
    }

    if (title === query) score += 220
    else if (title.startsWith(query)) score += 170
    else if (title.includes(query)) score += 130

    if (subtitle.startsWith(query)) score += 80
    else if (subtitle.includes(query)) score += 50

    if (keywords.includes(query)) score += 40
    if (group.includes(query)) score += 30

    return score
  }

  return [...filtered].sort((a, b) => {
    const scoreDiff = scoreCommandItem(b) - scoreCommandItem(a)
    if (scoreDiff !== 0) {
      return scoreDiff
    }
    const groupPriority = (group) => {
      if (group === '最近对象') return 4
      if (group === '当前对象') return 3
      if (group === '助手会话') return 2
      return 1
    }
    const groupDiff = groupPriority(b.group) - groupPriority(a.group)
    if (groupDiff !== 0) {
      return groupDiff
    }
    return String(a.title || '').localeCompare(String(b.title || ''), 'zh-CN')
  })
})

const groupedCommandPaletteItems = computed(() => {
  const groups = new Map()
  const isEmptyQuery = !String(commandPaletteQuery.value || '').trim()

  if (isEmptyQuery && Array.isArray(workspaceStore.recentCommandItems) && workspaceStore.recentCommandItems.length) {
    groups.set('最近命令', workspaceStore.recentCommandItems)
  }

  filteredCommandPaletteItems.value.forEach((item) => {
    const groupName = item.group || '命令'
    if (!groups.has(groupName)) {
      groups.set(groupName, [])
    }
    groups.get(groupName).push(item)
  })

  const groupPriority = (group) => {
    if (isEmptyQuery && group === '最近对象') return 5
    if (isEmptyQuery && group === '最近命令') return 4
    if (group === '当前对象') return 3
    if (group === '助手会话') return 2
    return 1
  }

  return Array.from(groups.entries())
    .sort((a, b) => groupPriority(b[0]) - groupPriority(a[0]))
    .map(([group, items]) => ({ group, items }))
})

const buildCopilotReply = (prompt, remoteContext = {}) => {
  const promptText = String(prompt || '').trim()
  const memoryView = remoteContext.memoryView || state.memoryView || {}
  const continuationContext = remoteContext.continuationContext || {}
  const plotHint = currentTargetArcText.value
    || memoryView?.main_plot_lines?.[0]
    || continuationContext?.target_arc?.title
    || '当前还没有明确的主线约束摘要。'
  const stateHint = String(memoryView?.current_state || '').trim() || currentViewMeta.value.description
  const recentTail = String(continuationContext?.last_chapter_tail || '').trim()
  const relevantForeshadowing = Array.isArray(continuationContext?.relevant_foreshadowing)
    ? continuationContext.relevant_foreshadowing.filter(Boolean).slice(0, 2).join('；')
    : ''

  if (!promptText) {
    return '我已准备好，你可以继续围绕当前对象发问。'
  }

  if (promptText.includes('剧情弧') || promptText.includes('目标弧')) {
    return `建议优先回看「${currentObjectLabel.value || currentChapter.value?.title || '当前对象'}」相关的目标弧。当前可见约束是：${plotHint}${relevantForeshadowing ? `；还需留意伏笔：${relevantForeshadowing}` : ''}`
  }

  if (promptText.includes('风险') || promptText.includes('问题')) {
    return `当前最该关注的是一致性与结构约束是否对齐。上下文摘要：${stateHint}${recentTail ? `；最近章节尾部语气是：${recentTail.slice(-80)}` : ''}`
  }

  if (promptText.includes('下一步') || promptText.includes('继续')) {
    return `下一步建议围绕「${currentObjectLabel.value || currentChapter.value?.title || '当前对象'}」继续推进，并优先检查：${plotHint}${relevantForeshadowing ? `；同时别遗失：${relevantForeshadowing}` : ''}`
  }

  return `我会优先参考当前对象「${currentObjectLabel.value || currentChapter.value?.title || '当前对象'}」。目前可见的上下文摘要是：${stateHint}${recentTail ? `；最近承接段尾部是：${recentTail.slice(-80)}` : ''}`
}

const loadCopilotRemoteContext = async () => {
  const projectId = state.projectId || state.project?.id || ''
  if (!projectId) {
    return {}
  }

  const chapterId = currentChapter.value?.id || workspaceStore.currentObject?.id || ''
  const chapterNumber = Number(currentChapter.value?.chapter_number || 0)

  const [memoryView, continuationContext] = await Promise.all([
    projectApi.memoryViewV2(projectId).catch(() => state.memoryView || {}),
    chapterId
      ? projectApi.continuationContextV2(projectId, { chapter_id: chapterId, chapter_number: chapterNumber || undefined }).catch(() => null)
      : Promise.resolve(null)
  ])

  return {
    memoryView: memoryView || state.memoryView || {},
    continuationContext: continuationContext || null
  }
}

const suggestedActions = computed(() => {
  const actions = []
  if (currentChapter.value?.id) {
    actions.push({
      key: 'writing',
      title: '继续当前章节',
      description: `回到 ${currentChapter.value.title || '当前章节'}，继续正文写作与智能协作。`,
      cta: '打开写作',
      action: {
        type: 'chapter',
        chapterId: currentChapter.value.id
      }
    })
    actions.push({
      key: 'chapters',
      title: '在章节管理中定位',
      description: `切到章节管理页，并聚焦 ${currentChapter.value.title || '当前章节'}。`,
      cta: '打开章节',
      action: {
        type: 'chapter-manager',
        chapterId: currentChapter.value.id,
        title: currentChapter.value.title || ''
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
    cta: '打开结构',
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
    cta: '打开任务',
    action: {
      type: 'task-filter',
      filter: 'all'
    }
  })
  return actions
})

const buildRouteQuery = (extraQuery = {}) => {
  const query = { ...route.query, ...extraQuery }
  if (Object.prototype.hasOwnProperty.call(extraQuery, 'section')) {
    query.section = String(extraQuery.section || '').trim()
  } else if (!query.section && workspaceStore.currentView) {
    query.section = workspaceStore.currentView
  }
  if (!query.chapterId && workspaceStore.currentChapterId) {
    query.chapterId = workspaceStore.currentChapterId
  }
  if (!query.chapterId) {
    delete query.chapterId
  }
  if (!['overview', 'writing', 'structure', 'chapters', 'tasks', 'settings'].includes(String(query.section || ''))) {
    delete query.section
  }
  return query
}

const openSection = (section, extraQuery = {}) => {
  if (section === 'overview') {
    workspaceStore.focusOverview({ openView: true })
  } else if (section === 'structure') {
    if (!workspaceStore.currentObject || !['story_model', 'plot_arc', 'character', 'worldview', 'risk'].includes(workspaceStore.currentObject.type)) {
      workspaceStore.focusStructureSection(workspaceStore.currentStructureSection, { openView: true })
    } else {
      workspaceStore.switchView(section)
    }
  } else if (section === 'tasks') {
    if (!workspaceStore.currentObject || !['task', 'task-filter'].includes(workspaceStore.currentObject.type)) {
      workspaceStore.focusTaskFilter(workspaceStore.currentTaskFilter, { openView: true })
    } else {
      workspaceStore.switchView(section)
    }
  } else if (section === 'settings') {
    workspaceStore.switchView(section)
  } else {
    workspaceStore.switchView(section)
  }
  router.replace({
    path: route.path,
    query: buildRouteQuery({ ...extraQuery, section })
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

  if (payload.type === 'chapter-manager' && payload.chapterId) {
    const chapterMeta = (state.chapters || []).find((item) => item.id === payload.chapterId) || {}
    workspaceStore.focusChapterObject({
      id: payload.chapterId,
      title: payload.title || chapterMeta.title || ''
    }, { openView: false })
    openSection('chapters')
    return
  }

  if (payload.type === 'arc') {
    workspaceStore.focusPlotArc({
      arcId: payload.arcId || '',
      title: payload.title || ''
    }, { openView: false, section: 'plot_arc' })
    openSection('structure')
    return
  }

  if (payload.type === 'task-filter') {
    workspaceStore.focusTaskFilter(payload.filter || 'all', { openView: false })
    openSection('tasks')
    return
  }

  if (payload.type === 'go_task_filter') {
    workspaceStore.focusTaskFilter(payload.task_filter || payload.filter || 'all', { openView: false })
    openSection('tasks')
    return
  }

  if (payload.type === 'go_chapter') {
    const chapterId = payload.chapter_id || payload.chapterId || ''
    if (chapterId) {
      await openChapter(chapterId, 'writing')
      return
    }
  }

  if (payload.type === 'focus_arc') {
    workspaceStore.focusPlotArc({
      arcId: payload.arc_id || payload.arcId || '',
      title: payload.title || ''
    }, { openView: false, section: 'plot_arc' })
    openSection('structure')
    return
  }

  if (payload.type === 'task' && payload.taskId) {
    workspaceStore.focusTask({
      id: payload.taskId,
      label: payload.title || '',
      chapterId: payload.chapterId || '',
      status: payload.status || '',
      targetArcId: payload.targetArcId || ''
    }, { openView: false })
    openSection('tasks')
    return
  }

  if (payload.type === 'writing-result') {
    const chapterId = String(payload.chapterId || currentChapter.value?.id || '')
    if (chapterId) {
      await openChapter(chapterId, 'writing')
    } else {
      openSection('writing')
    }
    workspaceStore.focusWritingResult({
      chapterId,
      resultType: payload.resultType || 'candidate',
      taskId: payload.taskId || '',
      title: payload.title || ''
    }, { openView: false })
    return
  }

  if (payload.type === 'section') {
    if (payload.section === 'structure' && payload.object?.type) {
      workspaceStore.setStructureSection(payload.object.type)
      workspaceStore.focusObject(payload.object, { openView: false })
    }
    if (payload.section === 'tasks' && payload.filter) {
      workspaceStore.focusTaskFilter(payload.filter, { openView: false })
    }
    openSection(payload.section || 'overview', payload.query || {})
    return
  }
}

const handleWorkspaceAction = async (payload) => {
  await handleCopilotTrigger(payload)
}

const handleCopilotChatSubmit = async (prompt) => {
  const content = String(prompt || '').trim()
  if (!content || workspaceStore.copilotChatPending) {
    return
  }

  workspaceStore.recordCopilotPrompt(content)
  workspaceStore.appendCopilotChatMessage({
    role: 'user',
    content
  })
  workspaceStore.setCopilotChatPending(true)
  try {
    const remoteContext = await loadCopilotRemoteContext()
    workspaceStore.appendCopilotChatMessage({
      role: 'assistant',
      content: buildCopilotReply(content, remoteContext)
    })
    workspaceStore.setCopilotChatDraft('')
  } catch (error) {
    workspaceStore.appendCopilotChatMessage({
      role: 'assistant',
      content: buildCopilotReply(content)
    })
  } finally {
    workspaceStore.setCopilotChatPending(false)
  }
}

const handleCopilotChatClear = () => {
  workspaceStore.clearCopilotChatMessages()
  workspaceStore.setCopilotChatDraft('')
  workspaceStore.setCopilotChatPending(false)
}

const handleCopilotChatSessionChange = (key) => {
  workspaceStore.setActiveCopilotChatSession(key)
}

const openCommandPalette = () => {
  commandPaletteVisible.value = true
}

const closeCommandPalette = () => {
  commandPaletteVisible.value = false
  commandPaletteQuery.value = ''
}

const handleCommandExecute = async (item) => {
  if (!item?.action) {
    return
  }
  workspaceStore.recordRecentCommand(item)
  if (item.action.type === 'copilot-tab') {
    workspaceStore.toggleCopilot(true)
    workspaceStore.setCopilotTab(item.action.tab || 'context')
    closeCommandPalette()
    return
  }
  if (item.action.type === 'chat-session') {
    workspaceStore.toggleCopilot(true)
    workspaceStore.setCopilotTab('chat')
    workspaceStore.setActiveCopilotChatSession(item.action.sessionKey)
    closeCommandPalette()
    return
  }
  if (item.action.type === 'issue') {
    if (currentChapter.value?.id) {
      await openChapter(currentChapter.value.id, 'writing')
    } else {
      openSection('writing')
    }
    workspaceStore.focusIssue({
      index: item.action.issueIndex,
      title: item.action.issueTitle || item.title || '',
      code: item.action.issueCode || '',
      chapterId: item.action.chapterId || currentChapter.value?.id || ''
    }, { openView: false })
    closeCommandPalette()
    return
  }
  if (item.action.type === 'dashboard') {
    closeCommandPalette()
    goToDashboard()
    return
  }
  await handleCopilotTrigger(item.action)
  closeCommandPalette()
}

const handleGlobalKeydown = (event) => {
  const isOpenShortcut = (event.ctrlKey || event.metaKey) && String(event.key || '').toLowerCase() === 'k'
  if (isOpenShortcut) {
    event.preventDefault()
    commandPaletteVisible.value = !commandPaletteVisible.value
    if (!commandPaletteVisible.value) {
      commandPaletteQuery.value = ''
    }
    return
  }

  if (event.key === 'Escape' && commandPaletteVisible.value) {
    closeCommandPalette()
  }
}

const openChapter = async (chapterId, section = 'writing') => {
  const chapterMeta = (state.chapters || []).find((item) => item.id === chapterId) || {}
  workspaceStore.focusChapterObject({
    id: chapterId,
    title: chapterMeta.title || ''
  }, {
    openView: true,
    view: section,
    exitZen: section === 'writing'
  })
  if (section === 'writing') {
    await state.loadEditorChapter(chapterId)
  }
  await router.replace({
    path: route.path,
    query: buildRouteQuery({ chapterId, section })
  })
}

const clearMainViewError = () => {
  mainViewError.value = ''
}

const recoverMainView = () => {
  mainViewError.value = ''
  workspaceStore.switchView('overview')
  router.replace({
    path: route.path,
    query: buildRouteQuery({ section: 'overview' })
  })
}

onErrorCaptured((error) => {
  mainViewError.value = error?.message || '视图渲染时发生异常'
  return false
})

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

const resolveRequestedSection = () => {
  const nextSection = String(route.query.section || '').trim()
  if (['overview', 'writing', 'structure', 'chapters', 'tasks'].includes(nextSection)) {
    return nextSection
  }
  return ''
}

const ensureWorkspaceEntry = async () => {
  if (state.loading) return
  if (!route.params.id) return
  const requestedSection = resolveRequestedSection()
  const targetChapterId = resolveDefaultChapterId()

  if (requestedSection && requestedSection !== 'writing') {
    if (requestedSection === 'chapters' && targetChapterId) {
      const chapterMeta = (state.chapters || []).find((item) => item.id === targetChapterId) || {}
      workspaceStore.focusChapterObject({
        id: targetChapterId,
        title: chapterMeta.title || ''
      }, { openView: true, view: 'chapters' })
      return
    }
    workspaceStore.switchView(requestedSection)
    return
  }

  if (targetChapterId) {
    if (targetChapterId !== workspaceStore.currentChapterId || !state.editor.chapter?.id) {
      await openChapter(targetChapterId, 'writing')
      return
    }

    workspaceStore.switchView('writing')
    return
  }

  workspaceStore.switchView(requestedSection || 'overview')
}

// Provide context for child components
provide(WORKSPACE_CONTEXT_KEY, {
  state,
  resourceSnapshot: computed(() => workspaceStore.resourceSnapshot),
  taskCenterSnapshot: computed(() => workspaceStore.taskCenterSnapshot),
  contextSnapshot: computed(() => workspaceStore.currentContextSnapshot),
  currentSection: computed(() => workspaceStore.currentView),
  currentChapterId,
  latestChapter,
  suggestedActions,
  overviewDecisionCards,
  overviewTaskSnapshot,
  openSection,
  openChapter,
  setTaskFilter: (filter) => workspaceStore.setTaskFilter(filter),
  executeWorkspaceAction: (action) => handleWorkspaceAction(action),
  createChapter,
  refreshBase: () => state.loadBase(route.params.id),
  refreshStructure: state.loadStructure,
  syncChapterSnapshot: state.syncChapterSnapshot,
  loadEditorChapter: state.loadEditorChapter,
  organizeSingleChapter: state.organizeSingleChapter,
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

  const requestedSection = resolveRequestedSection() || workspaceStore.currentView
  if (requestedSection === 'writing') {
    void openChapter(nextChapterId, 'writing')
    return
  }

  const chapterMeta = (state.chapters || []).find((item) => item.id === nextChapterId) || {}
  workspaceStore.focusChapterObject({
    id: nextChapterId,
    title: chapterMeta.title || ''
  }, { openView: false })
})

watch(() => route.query.section, () => {
  mainViewError.value = ''
  void ensureWorkspaceEntry()
})

watch(() => [state.editor.contextMeta, state.memoryView], ([contextMeta, memoryView]) => {
  workspaceStore.syncShellState({
    novelId: route.params.id,
    novelInfo: state.novel,
    projectId: state.projectId,
    chapterCount: state.chapters?.length || 0,
    activeChapterId: state.editor.chapter?.id || workspaceStore.currentChapterId || '',
    hasStructure: Boolean((state.activeArcs || []).length || Object.keys(memoryView || {}).length)
  })
  workspaceStore.setContextSnapshot({
    chapterId: state.editor.chapter?.id || '',
    chapterTitle: state.editor.chapter?.title || '',
    activeArcs: state.activeArcs || [],
    memoryView: memoryView || {},
    contextMeta: contextMeta || {}
  })
}, { deep: true, immediate: true })

watch(() => state.taskCenter, (taskCenter) => {
  workspaceStore.syncTaskCenterSnapshot({
    organizeTask: state.organizeProgress || {},
    tasks: taskCenter?.tasks || [],
    failedCount: taskCenter?.counts?.failed || 0,
    runningCount: taskCenter?.counts?.running || 0,
    completedCount: taskCenter?.counts?.completed || 0,
    auditCount: taskCenter?.counts?.audit || 0
  })
}, { deep: true, immediate: true })

watch(
  () => currentCopilotSessionMeta.value,
  (sessionMeta) => {
    workspaceStore.ensureCopilotChatSession(sessionMeta)
    workspaceStore.setActiveCopilotChatSession(sessionMeta.key)
  },
  { immediate: true, deep: true }
)

watch(
  () => [
    workspaceStore.currentCopilotTab,
    workspaceStore.currentView,
    workspaceStore.currentObject?.type,
    workspaceStore.currentObject?.id,
    workspaceStore.currentObject?.taskId,
    workspaceStore.currentObject?.arcId,
    workspaceStore.currentObject?.resultType,
    currentChapter.value?.id,
    state.projectId,
    taskCenterSnapshot.value.failedCount
  ],
  () => {
    void loadCopilotInspireRemoteItems()
  },
  { immediate: true }
)

watch(
  () => inspireFeedbackStorageKey.value,
  () => {
    loadInspireFeedback()
  },
  { immediate: true }
)

watch(() => [state.loading, state.chapters], () => {
  void ensureWorkspaceEntry()
}, { deep: true })

onMounted(() => {
  // Initialize workspace with novelId from route
  if (route && route.params && route.params.id) {
    workspaceStore.initWorkspace(route.params.id)
    workspaceStore.syncShellState({
      novelId: route.params.id,
      novelInfo: state.novel,
      projectId: state.projectId,
      chapterCount: state.chapters?.length || 0,
      activeChapterId: state.editor.chapter?.id || workspaceStore.currentChapterId || '',
      hasStructure: Boolean((state.activeArcs || []).length || Object.keys(state.memoryView || {}).length)
    })
  }
  loadInspireFeedback()
  void ensureWorkspaceEntry()
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  state.cancelPendingRequests?.()
  window.removeEventListener('keydown', handleGlobalKeydown)
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

.workspace-main-fallback {
  margin: 20px;
  padding: 16px;
  border: 1px solid #FECACA;
  background: #FEF2F2;
  border-radius: 12px;
  color: #991B1B;
}

.fallback-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
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
