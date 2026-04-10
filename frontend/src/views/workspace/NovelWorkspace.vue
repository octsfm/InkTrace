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
      <component :is="activeComponent" v-bind="activeComponentProps" />
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
      :memory-view="state.memoryView"
      :organize-progress="state.organizeProgress"
      :suggested-actions="suggestedActions"
      @trigger="handleCopilotTrigger"
      @update:chat-draft="workspaceStore.setCopilotChatDraft($event)"
      @chat-submit="handleCopilotChatSubmit"
      @clear-chat="handleCopilotChatClear"
      @chat-session-change="handleCopilotChatSessionChange"
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
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { novelApi, projectApi } from '@/api'
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
import WorkspaceCommandPalette from '@/components/workspace/WorkspaceCommandPalette.vue'

const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()
const state = useNovelWorkspaceStore()
const commandPaletteVisible = ref(false)
const commandPaletteQuery = ref('')

const viewMetaMap = {
  writing: {
    title: '写作',
    description: '中央区域保持写作优先，AI 结果默认回流为候选稿或审查结果。'
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
  overview: {
    eyebrow: '概览',
    title: '项目摘要',
    subtitle: '只展示最小必要信息，帮助你决定下一步。'
  }
}

const sidebarMeta = computed(() => (
  sidebarMetaMap[workspaceStore.currentView] || sidebarMetaMap.overview
))

const sidebarStructureItems = [
  { key: 'story_model', label: '故事模型' },
  { key: 'plot_arc', label: '剧情弧' },
  { key: 'character', label: '角色 Characters' },
  { key: 'worldview', label: '世界观 Worldview' },
  { key: 'risk', label: '风险点 Risks' }
]

const taskFilterOptionDefs = [
  { key: 'all', label: '全部任务' },
  { key: 'running', label: '运行中' },
  { key: 'failed', label: '失败任务' },
  { key: 'completed', label: '已完成' },
  { key: 'audit', label: '审查结果' }
]

const sidebarOverviewCards = computed(() => ([
  {
    label: '当前小说',
    value: state.novel?.title || '未命名小说'
  },
  {
    label: '最近章节',
    value: recentChapter.value?.title || '暂无章节'
  },
  {
    label: '当前任务',
    value: taskStatusText.value || '暂无任务'
  }
]))

const taskFilterOptions = computed(() => (taskFilterOptionDefs.map((item) => {
  const countMap = taskSummaryCounts.value || {}
  const count = countMap[item.key] ?? countMap.all ?? 0
  return {
    ...item,
    count,
    label: `${item.label}${item.key === 'all' ? '' : ` (${count})`}`
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
    if (taskSummaryCounts.value.failed > 0) {
      facts.push({
        label: '失败任务',
        value: String(taskSummaryCounts.value.failed)
      })
    }
  } else {
    facts.push({
      label: '最近章节',
      value: recentChapter.value?.title || '暂无章节'
    })
    facts.push({
      label: '活跃弧',
      value: String((state.activeArcs || []).length || 0)
    })
    if (taskSummaryCounts.value.failed > 0) {
      facts.push({
        label: '失败任务',
        value: String(taskSummaryCounts.value.failed)
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
  if (state.editor.aiRunning) return 'AI 处理中'
  if (taskSummaryCounts.value.failed > 0) return `${taskSummaryCounts.value.failed} 个失败任务`
  if (taskSummaryCounts.value.running > 0) return `${taskSummaryCounts.value.running} 个运行中任务`
  const organizeStatus = String(state.organizeProgress?.status || '').trim()
  if (!organizeStatus) return '暂无任务'
  if (organizeStatus === 'running') return `整理中 ${state.organizeProgress?.progress ?? 0}%`
  if (organizeStatus === 'paused') return '整理已暂停'
  if (organizeStatus === 'failed' || organizeStatus === 'error') return '整理失败'
  if (organizeStatus === 'success' || organizeStatus === 'done') return '最近任务完成'
  return organizeStatus
})

const taskSummaryCounts = computed(() => {
  const items = Array.isArray(state.chapterTasks) ? state.chapterTasks : []
  return {
    all: items.length,
    running: items.filter((item) => String(item?.status || '').trim() === 'running').length,
    failed: items.filter((item) => ['failed', 'error'].includes(String(item?.status || '').trim())).length,
    completed: items.filter((item) => ['completed', 'success', 'done'].includes(String(item?.status || '').trim())).length,
    audit: items.filter((item) => String(item?.task_type || item?.type || '').toLowerCase().includes('audit')).length
  }
})

const activeComponentProps = computed(() => {
  if (workspaceStore.currentView === 'tasks') {
    return {
      filterOptions: taskFilterOptions,
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
      historyEmptyText: taskHistoryEmptyText.value
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
  const status = String(state.organizeProgress?.status || '').trim()
  if (!status) return '未运行'
  if (status === 'running') return '整理中'
  if (status === 'paused') return '已暂停'
  if (status === 'success' || status === 'done') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  return status
})

const taskPanelProgressText = computed(() => `${state.organizeProgress?.progress ?? 0}%`)

const taskPanelStatusHint = computed(() => (
  state.organizeProgress?.error_message || '如果任务异常，可以在这里统一重试、暂停或恢复。'
))

const unifiedTaskCards = computed(() => {
  const cards = []
  const organizeStatus = String(state.organizeProgress?.status || '').trim()
  cards.push({
    id: 'organize-task',
    type: 'organize',
    typeLabel: '整理任务',
    status: organizeStatus || 'idle',
    statusLabel: buildTaskStatusLabel(organizeStatus),
    title: '全书整理任务',
    subtitle: `当前进度 ${state.organizeProgress?.progress ?? 0}%`,
    description: state.organizeProgress?.error_message || '负责导入后整理、结构分析与相关写回。',
    targetLabel: '目标对象：全书结构与章节状态',
    reasonText: state.organizeProgress?.error_message || '当前未提供更详细的失败原因。',
    nextStepText: ['failed', 'error'].includes(organizeStatus)
      ? '建议先查看失败原因，再重新整理。'
      : '可在任务控制台继续暂停、恢复或取消。',
    hint: ['failed', 'error'].includes(organizeStatus)
      ? '建议先查看失败原因，再重试整理。'
      : '可在上方任务控制台执行暂停、恢复或取消。',
    actionLabel: ['failed', 'error'].includes(organizeStatus) ? '重新整理' : '',
    action: ['failed', 'error'].includes(organizeStatus) ? { type: 'retry-organize' } : null
  })

  ;(Array.isArray(state.chapterTasks) ? state.chapterTasks : []).forEach((task, index) => {
    const taskId = String(task.id || task.task_id || `chapter-task-${index}`)
    const taskType = String(task.task_type || task.type || 'task')
    const taskStatus = String(task.status || '').trim() || 'idle'
    const chapterId = String(task.chapter_id || task.chapterId || '')
    const chapterTitle = (state.chapters || []).find((item) => item.id === chapterId)?.title || ''
    const taskTitle = task.title || task.label || task.name || `章节任务 ${index + 1}`
    const actionPayload = buildTaskActionPayload(task)
    const taskSubtitle = [
      chapterTitle || (chapterId ? `章节 ${chapterId}` : ''),
      task.target_arc_title || task.target_arc_id || '',
      buildTaskTypeLabel(task)
    ].filter(Boolean).join(' · ')

    cards.push({
      id: taskId,
      type: taskType,
      typeLabel: buildTaskTypeLabel(task),
      status: taskStatus,
      statusLabel: buildTaskStatusLabel(taskStatus),
      title: taskTitle,
      subtitle: taskSubtitle || '项目任务',
      description: task.error_message || task.error || task.description || '用于驱动章节生成、审查与结构推进的项目任务。',
      targetLabel: buildTaskTargetLabel(task, chapterTitle),
      reasonText: buildTaskReasonText(task),
      nextStepText: buildTaskNextStepText(task),
      hint: ['failed', 'error'].includes(taskStatus)
        ? '建议先回到对应对象处理后再恢复。'
        : '可切回对应章节或结构对象继续推进。',
      actionLabel: buildTaskActionLabel(task),
      action: actionPayload,
      chapterId,
      targetArcId: String(task.target_arc_id || ''),
      raw: task
    })
  })

  if (workspaceStore.currentTask?.id) {
    const task = workspaceStore.currentTask
    cards.push({
      id: task.id,
      type: task.type || 'task',
      typeLabel: buildTaskTypeLabel(task),
      status: task.status || 'idle',
      statusLabel: buildTaskStatusLabel(task.status),
      title: task.label || '当前任务',
      subtitle: task.chapterId ? `章节 ${task.chapterId}` : '当前工作区任务',
      description: task.error || '当前工作区最近一次 AI/校验任务状态。',
      targetLabel: task.chapterId ? `目标章节：${task.chapterId}` : '目标对象：当前工作区',
      reasonText: task.error || '当前未提供更详细的失败原因。',
      nextStepText: task.chapterId ? '建议先回到对应章节继续处理。' : '建议先查看失败任务筛选。', 
      hint: task.status === 'failed' ? '如需恢复，可回到写作页重新发起。' : '可切换回对应工作区继续处理。',
      actionLabel: task.chapterId ? '打开对象' : (task.status === 'failed' ? '查看失败任务' : ''),
      action: task.chapterId
        ? { type: 'chapter', chapterId: task.chapterId }
        : (task.status === 'failed' ? { type: 'task-filter', filter: 'failed' } : { type: 'section', section: 'tasks' }),
      chapterId: task.chapterId || ''
    })
  }

  const deduped = []
  const seen = new Set()
  cards.forEach((item) => {
    if (seen.has(item.id)) return
    seen.add(item.id)
    deduped.push(item)
  })
  return deduped
})

const filteredTaskCards = computed(() => {
  const filter = workspaceStore.currentTaskFilter
  const cards = unifiedTaskCards.value
  if (filter === 'all') return cards
  if (filter === 'running') return cards.filter((item) => item.status === 'running')
  if (filter === 'failed') return cards.filter((item) => ['failed', 'error'].includes(item.status))
  if (filter === 'completed') return cards.filter((item) => ['completed', 'success', 'done'].includes(item.status))
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
      items: cards.filter((item) => ['failed', 'error'].includes(item.status))
    },
    {
      key: 'running',
      title: '运行中',
      description: '这些任务仍在运行，可以先观察进度或切回对象继续处理。',
      items: cards.filter((item) => item.status === 'running')
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
  const failedTask = unifiedTaskCards.value.find((item) => ['failed', 'error'].includes(item.status) && item.id !== 'organize-task')
  const failedOrganizeTask = unifiedTaskCards.value.find((item) => item.id === 'organize-task' && ['failed', 'error'].includes(item.status))
  const runningTask = unifiedTaskCards.value.find((item) => item.status === 'running' && item.id !== 'organize-task')
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
    items.push({
      key: 'task-fallback',
      tag: '任务',
      title: '当前任务状态稳定',
      description: '没有需要立即恢复的任务，下一步可切回写作或结构页继续推进。',
      meta: `${taskSummaryCounts.value.all || 0} 个项目任务`,
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

const taskHistoryEmptyText = computed(() => (
  filteredTaskCards.value.length ? '更完整的任务历史和 trace 将在后续接入。' : '当前筛选下暂无任务记录。'
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
  const issueCount = Number(state.editor.integrityCheck?.issue_list?.length || 0)
  const failedTaskCount = Number(taskSummaryCounts.value.failed || 0)
  const runningTaskCount = Number(taskSummaryCounts.value.running || 0)
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

  if (taskSummaryCounts.value.failed > 0) {
    actions.push({
      label: `失败任务 ${taskSummaryCounts.value.failed}`,
      action: {
        type: 'task-filter',
        filter: 'failed'
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
      title: currentTargetArcText.value ? '检查活跃剧情弧' : '打开 Story Model',
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

const buildTaskStatusLabel = (status) => {
  const normalized = String(status || '').trim()
  if (!normalized) return '待命中'
  if (normalized === 'running') return '运行中'
  if (normalized === 'paused') return '已暂停'
  if (['completed', 'success', 'done'].includes(normalized)) return '已完成'
  if (['failed', 'error'].includes(normalized)) return '失败'
  return normalized
}

const buildTaskTypeLabel = (task) => {
  const type = String(task?.task_type || task?.type || '').toLowerCase()
  if (type.includes('audit') || type.includes('analyze')) return '审查任务'
  if (type.includes('organize')) return '整理任务'
  if (type.includes('write') || type.includes('draft')) return '写作任务'
  if (type.includes('arc') || type.includes('plot')) return '结构任务'
  return '项目任务'
}

const buildTaskActionPayload = (task) => {
  const chapterId = String(task?.chapter_id || task?.chapterId || '').trim()
  const targetArcId = String(task?.target_arc_id || task?.targetArcId || '').trim()
  if (chapterId) {
    return { type: 'chapter', chapterId }
  }
  if (targetArcId) {
    return {
      type: 'arc',
      arcId: targetArcId,
      title: task?.target_arc_title || targetArcId
    }
  }
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  if (taskType.includes('audit') || taskType.includes('analyze')) {
    return { type: 'task-filter', filter: 'audit' }
  }
  if (['failed', 'error'].includes(String(task?.status || '').trim())) {
    return { type: 'task-filter', filter: 'failed' }
  }
  return { type: 'section', section: 'tasks' }
}

const buildTaskActionLabel = (task) => {
  const chapterId = String(task?.chapter_id || task?.chapterId || '').trim()
  const targetArcId = String(task?.target_arc_id || task?.targetArcId || '').trim()
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  if (chapterId) return '打开章节'
  if (targetArcId) return '查看目标弧'
  if (taskType.includes('audit') || taskType.includes('analyze')) return '查看审查'
  if (['failed', 'error'].includes(String(task?.status || '').trim())) return '查看失败任务'
  return '查看任务'
}

const buildTaskTargetLabel = (task, chapterTitle) => {
  const targetArcTitle = String(task?.target_arc_title || task?.targetArcId || task?.target_arc_id || '').trim()
  if (chapterTitle) {
    return `目标章节：${chapterTitle}`
  }
  if (targetArcTitle) {
    return `目标弧：${targetArcTitle}`
  }
  return '目标对象：项目任务'
}

const buildTaskReasonText = (task) => {
  return String(task?.error_message || task?.error || task?.description || '').trim() || '当前未提供更详细的失败原因。'
}

const buildTaskNextStepText = (task) => {
  const status = String(task?.status || '').trim()
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  if (['failed', 'error'].includes(status)) {
    if (String(task?.chapter_id || task?.chapterId || '').trim()) {
      return '建议先回到对应章节修复，再重新触发任务。'
    }
    if (String(task?.target_arc_id || task?.targetArcId || '').trim()) {
      return '建议先检查目标剧情弧状态，再重新推进相关任务。'
    }
    return '建议先查看失败任务筛选，再决定是否重试。'
  }
  if (status === 'running') {
    return '任务仍在进行中，可先回到对应对象继续处理。'
  }
  if (taskType.includes('audit') || taskType.includes('analyze')) {
    return '建议先看审查结果，再回到写作或结构页处理。'
  }
  return '可切回目标对象继续推进。'
}

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
      issueIndex: index
    }
  }))
})

const recentOpenDocumentCommands = computed(() => {
  return (workspaceStore.openDocuments || [])
    .slice(0, 8)
    .map((doc, index) => ({
      id: `recent-doc-${doc.type}-${doc.id}-${index}`,
      group: '最近对象',
      title: doc.title || `${doc.type} ${doc.id}`,
      subtitle: [
        doc.type === 'chapter'
          ? '重新打开该章节'
          : doc.type === 'plot_arc'
            ? '重新打开该剧情弧'
            : doc.type === 'story_model'
              ? '重新打开结构模型'
              : '重新打开最近对象',
        formatRelativeTime(doc.lastOpenedAt)
      ].filter(Boolean).join(' · '),
      keywords: `${doc.title || ''} 最近 打开 recent ${doc.type}`,
      hint: '最近',
      action: doc.type === 'chapter'
        ? { type: 'chapter', chapterId: doc.id }
        : doc.type === 'plot_arc'
          ? { type: 'arc', arcId: doc.id, title: doc.title || '' }
          : doc.type === 'story_model'
            ? { type: 'section', section: 'structure', object: { type: 'story_model' } }
            : doc.type === 'task-filter'
              ? { type: 'task-filter', filter: doc.id }
              : { type: 'section', section: workspaceStore.currentView || 'overview' }
    }))
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
      id: 'story-model',
      group: '结构',
      title: '打开故事模型',
      subtitle: '查看整体结构模型与约束',
      keywords: 'story model 结构 模型 约束',
      hint: '结构',
      action: { type: 'section', section: 'structure', object: { type: 'story_model' } }
    },
    {
      id: 'dashboard',
      group: '视图',
      title: '返回 Dashboard',
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
      subtitle: '切到 Structure 并聚焦当前剧情弧',
      keywords: `${workspaceStore.currentObject.title || ''} 当前对象 剧情弧 structure`,
      hint: '当前',
      action: {
        type: 'arc',
        arcId: workspaceStore.currentObject.arcId,
        title: workspaceStore.currentObject.title || ''
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

  if (workspaceStore.currentTask?.id) {
    items.push({
      id: `current-task-${workspaceStore.currentTask.id}`,
      group: '任务',
      title: workspaceStore.currentTask.label || '当前任务',
      subtitle: workspaceStore.currentTask.chapterId ? `回到对应章节 ${workspaceStore.currentTask.chapterId}` : '打开当前任务上下文',
      keywords: `${workspaceStore.currentTask.label || ''} 当前任务 task`,
      hint: '当前',
      action: workspaceStore.currentTask.chapterId
        ? { type: 'chapter', chapterId: workspaceStore.currentTask.chapterId }
        : { type: 'task-filter', filter: 'all' }
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
      group: 'Copilot',
      title: '打开 Copilot Chat',
      subtitle: '切到对话页并保留当前对象上下文',
      keywords: 'copilot chat 对话 助手',
      hint: 'Copilot',
      action: { type: 'copilot-tab', tab: 'chat' }
    },
    {
      id: 'copilot-context',
      group: 'Copilot',
      title: '打开 Copilot Context',
      subtitle: '查看当前对象上下文卡片',
      keywords: 'copilot context 上下文',
      hint: 'Copilot',
      action: { type: 'copilot-tab', tab: 'context' }
    },
    {
      id: 'copilot-inspire',
      group: 'Copilot',
      title: '打开 Copilot Inspire',
      subtitle: '查看建议动作与灵感提示',
      keywords: 'copilot inspire 灵感 建议',
      hint: 'Copilot',
      action: { type: 'copilot-tab', tab: 'inspire' }
    }
  )

  copilotChatSessions.value.slice(0, 6).forEach((session) => {
    items.push({
      id: `chat-session-${session.key}`,
      group: 'Copilot 会话',
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

  return items
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
    const isCurrentView = item.action?.section === workspaceStore.currentView
      || (item.action?.type === 'task-filter' && workspaceStore.currentView === 'tasks' && item.action?.filter === workspaceStore.currentTaskFilter)

    if (isCurrentObject) score += 80
    if (isRecentCommand) score += 60
    if (isRecentOpen) score += 45
    if (isCurrentView) score += 35

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
      if (group === 'Copilot 会话') return 2
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
    if (group === 'Copilot 会话') return 2
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
      description: `回到 ${currentChapter.value.title || '当前章节'}，继续正文写作与 AI 协作。`,
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
  if (!query.section && workspaceStore.currentView) {
    query.section = workspaceStore.currentView
  }
  if (!query.chapterId && workspaceStore.currentChapterId) {
    query.chapterId = workspaceStore.currentChapterId
  }
  if (!query.chapterId) {
    delete query.chapterId
  }
  if (!query.section) {
    delete query.section
  }
  return query
}

const openSection = (section, extraQuery = {}) => {
  if (section === 'overview') {
    workspaceStore.focusOverview({ openView: true })
  } else if (section === 'structure') {
    if (!workspaceStore.currentObject || !['story_model', 'plot_arc', 'risk'].includes(workspaceStore.currentObject.type)) {
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
  } else {
    workspaceStore.switchView(section)
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
    query: buildRouteQuery({ chapterId })
  })
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
  void ensureWorkspaceEntry()
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

watch(
  () => currentCopilotSessionMeta.value,
  (sessionMeta) => {
    workspaceStore.ensureCopilotChatSession(sessionMeta)
    workspaceStore.setActiveCopilotChatSession(sessionMeta.key)
  },
  { immediate: true, deep: true }
)

watch(() => [state.loading, state.chapters], () => {
  void ensureWorkspaceEntry()
}, { deep: true })

onMounted(() => {
  // Initialize workspace with novelId from route
  if (route && route.params && route.params.id) {
    workspaceStore.initWorkspace(route.params.id)
  }
  void ensureWorkspaceEntry()
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
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
