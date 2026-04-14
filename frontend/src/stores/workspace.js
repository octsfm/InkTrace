import { defineStore } from 'pinia'
import { buildWorkspaceResultLabel, normalizeWorkspaceTaskStatus } from '@/views/workspace/workspaceTaskModel'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    novelId: null,
    novelInfo: null,
    resourceSnapshot: null,
    currentView: 'writing',
    currentChapterId: null,
    currentObject: null,
    currentTask: null,
    taskCenterSnapshot: null,
    currentContextSnapshot: null,
    openDocuments: [],
    currentStructureSection: 'story_model',
    currentTaskFilter: 'all',
    isCopilotOpen: true,
    currentCopilotTab: 'context',
    currentCopilotChatSessionKey: 'overview::default',
    copilotChatSessions: [],
    copilotChatDraft: '',
    copilotChatMessages: [],
    copilotRecentPrompts: [],
    recentCommandItems: [],
    copilotChatPending: false,
    isZenMode: false
  }),
  getters: {
    currentTaskFocusId(state) {
      if (state.currentObject?.type === 'task') {
        return String(state.currentObject?.taskId || state.currentObject?.id || '')
      }
      return String(state.currentTask?.id || '')
    }
  },
  actions: {
    normalizeTask(task) {
      if (!task?.id) {
        return null
      }

      return {
        id: String(task.id),
        type: task.type || 'task',
        label: task.label || task.title || '当前任务',
        status: normalizeWorkspaceTaskStatus(task.status || 'idle'),
        chapterId: task.chapterId || task.chapter_id || '',
        resultType: task.resultType || '',
        error: task.error || '',
        targetArcId: task.targetArcId || task.target_arc_id || ''
      }
    },

    buildTaskObject(task) {
      const normalized = this.normalizeTask(task)
      if (!normalized) {
        return null
      }

      return {
        type: 'task',
        id: normalized.id,
        taskId: normalized.id,
        title: normalized.label,
        status: normalized.status,
        chapterId: normalized.chapterId,
        targetArcId: normalized.targetArcId,
        resultType: normalized.resultType
      }
    },

    buildWritingResultObject(result = {}) {
      const chapterId = String(result.chapterId || result.chapter_id || this.currentChapterId || '')
      const resultType = String(result.resultType || 'none')
      const taskId = String(result.taskId || result.id || '')
      return {
        type: 'writing-result',
        id: `${chapterId || 'chapter'}::${resultType || 'result'}`,
        taskId,
        chapterId,
        resultType,
        title: result.title || ''
      }
    },

    recordOpenDocument(document) {
      if (!document?.type) {
        return
      }

      const docId = document.id || document.arcId || document.taskId || document.filter || document.type
      const normalized = {
        ...document,
        id: docId,
        title: document.title || document.label || '',
        lastOpenedAt: Date.now()
      }

      this.openDocuments = [
        normalized,
        ...this.openDocuments.filter((item) => !(item.type === normalized.type && item.id === normalized.id))
      ].slice(0, 10)
    },

    summarizeCopilotChatMessage(message) {
      const content = String(message?.content || '').trim()
      if (!content) return ''
      return content.length > 56 ? `${content.slice(0, 56)}...` : content
    },

    initWorkspace(novelId) {
      this.novelId = novelId
    },

    syncShellState(payload = {}) {
      const novelId = String(payload.novelId || this.novelId || '')
      const novelInfo = payload.novelInfo || this.novelInfo || null
      this.novelId = novelId || null
      this.novelInfo = novelInfo
      this.resourceSnapshot = {
        novelId,
        novelTitle: novelInfo?.title || '',
        projectId: String(payload.projectId || ''),
        chapterCount: Number(payload.chapterCount || 0),
        activeChapterId: String(payload.activeChapterId || this.currentChapterId || ''),
        hasStructure: Boolean(payload.hasStructure)
      }
    },

    switchView(viewName) {
      this.currentView = viewName
      if (viewName !== 'writing') {
        this.isZenMode = false
      }

      if (viewName === 'overview' && !this.currentObject) {
        this.currentObject = { type: 'overview' }
      }
    },

    openChapter(chapterId, chapterMeta = {}) {
      if (!chapterId) {
        return
      }

      this.focusChapterObject({
        id: chapterId,
        title: chapterMeta.title || ''
      }, {
        openView: true,
        view: 'writing',
        exitZen: true
      })
    },

    focusChapterObject(chapter, options = {}) {
      const chapterId = String(chapter?.id || chapter?.chapterId || '')
      if (!chapterId) {
        return
      }

      const nextObject = {
        type: 'chapter',
        id: chapterId,
        title: chapter?.title || ''
      }
      this.currentChapterId = chapterId
      this.currentObject = nextObject
      this.recordOpenDocument({ type: 'chapter', id: chapterId, title: nextObject.title })
      if (options.exitZen) {
        this.isZenMode = false
      }
      if (options.openView) {
        this.currentView = options.view || 'chapters'
      }
    },

    setCurrentObject(object) {
      this.currentObject = object || null
      if (!object?.type) {
        return
      }

      if (object.type === 'chapter' && object.id) {
        this.recordOpenDocument({ type: 'chapter', id: object.id, title: object.title || '' })
      } else if (object.type === 'plot_arc' && object.arcId) {
        this.recordOpenDocument({ type: 'plot_arc', id: object.arcId, title: object.title || '' })
      } else if (object.type === 'task' && (object.taskId || object.id)) {
        this.recordOpenDocument({ type: 'task', id: object.taskId || object.id, title: object.title || object.label || '' })
      } else if (object.type === 'task-filter' && object.filter) {
        this.recordOpenDocument({ type: 'task-filter', id: object.filter, title: `任务筛选：${object.filter}` })
      } else if (object.type === 'issue') {
        const issueId = object.id || object.issueId || `${object.chapterId || 'chapter'}::${object.index ?? 'issue'}`
        this.recordOpenDocument({ type: 'issue', id: issueId, title: object.title || object.code || '问题单' })
      } else if (object.type === 'writing-result') {
        const resultId = object.id || `${object.chapterId || 'chapter'}::${object.resultType || 'result'}`
        this.recordOpenDocument({
          type: 'writing-result',
          id: resultId,
          title: object.title || buildWorkspaceResultLabel(object.resultType, { noneLabel: '候选稿' }),
          chapterId: object.chapterId || ''
        })
      } else if (['story_model', 'character', 'worldview', 'risk'].includes(object.type)) {
        const structureTitleMap = {
          story_model: '故事模型',
          character: '角色',
          worldview: '世界观',
          risk: '风险点'
        }
        this.recordOpenDocument({
          type: object.type,
          id: object.type,
          title: structureTitleMap[object.type] || object.type
        })
      }
    },

    focusOverview(options = {}) {
      this.currentObject = { type: 'overview' }
      if (options.openView !== false) {
        this.currentView = 'overview'
      }
    },

    focusStructureSection(section, options = {}) {
      const nextSection = section || 'story_model'
      this.currentStructureSection = nextSection
      this.currentObject = {
        type: nextSection
      }
      this.recordOpenDocument({
        type: nextSection,
        id: nextSection,
        title: nextSection === 'story_model'
          ? '故事模型'
          : nextSection === 'character'
            ? '角色'
            : nextSection === 'worldview'
              ? '世界观'
          : nextSection === 'plot_arc'
            ? '剧情弧'
            : nextSection === 'risk'
              ? '风险点'
              : nextSection
      })
      if (options.openView !== false) {
        this.currentView = 'structure'
      }
    },

    setCurrentTask(task) {
      const normalized = this.normalizeTask(task)
      this.currentTask = normalized

      if (!normalized) {
        return
      }

      this.recordOpenDocument({
        type: 'task',
        id: normalized.id,
        title: normalized.label,
        chapterId: normalized.chapterId,
        status: normalized.status,
        targetArcId: normalized.targetArcId
      })

      if (this.currentObject?.type === 'task') {
        this.currentObject = this.buildTaskObject(normalized)
      }
    },

    focusTask(task, options = {}) {
      const normalized = this.normalizeTask(task)
      if (!normalized) {
        return
      }

      this.currentTask = normalized
      this.currentObject = this.buildTaskObject(normalized)
      this.recordOpenDocument({
        type: 'task',
        id: normalized.id,
        title: normalized.label,
        chapterId: normalized.chapterId,
        status: normalized.status,
        targetArcId: normalized.targetArcId
      })

      if (options.openView !== false) {
        this.currentView = 'tasks'
      }
    },

    focusPlotArc(arc, options = {}) {
      const arcId = String(arc?.arcId || arc?.arc_id || '')
      this.currentStructureSection = options.section || 'plot_arc'
      this.currentObject = {
        type: 'plot_arc',
        arcId,
        title: arc?.title || arc?.label || arcId
      }
      this.recordOpenDocument({
        type: 'plot_arc',
        id: arcId || 'plot_arc',
        title: arc?.title || arc?.label || arcId
      })
      if (options.openView !== false) {
        this.currentView = 'structure'
      }
    },

    focusTaskFilter(filter, options = {}) {
      this.currentTaskFilter = filter || 'all'
      this.currentObject = {
        type: 'task-filter',
        filter: this.currentTaskFilter
      }
      this.recordOpenDocument({
        type: 'task-filter',
        id: this.currentTaskFilter,
        title: `任务筛选：${this.currentTaskFilter}`
      })
      if (options.openView !== false) {
        this.currentView = 'tasks'
      }
    },

    focusIssue(issue, options = {}) {
      const issueIndex = Number(issue?.index ?? -1)
      const chapterId = String(issue?.chapterId || issue?.chapter_id || this.currentChapterId || '')
      const issueId = String(issue?.id || `${chapterId || 'chapter'}::issue-${issueIndex >= 0 ? issueIndex : 'current'}`)
      this.currentObject = {
        type: 'issue',
        id: issueId,
        issueId,
        index: issueIndex,
        code: issue?.code || '',
        title: issue?.title || '',
        chapterId
      }
      this.recordOpenDocument({
        type: 'issue',
        id: issueId,
        title: issue?.title || issue?.code || '问题单',
        chapterId,
        index: issueIndex,
        code: issue?.code || ''
      })
      if (options.openView !== false) {
        this.currentView = options.view || 'writing'
      }
    },

    focusWritingResult(result, options = {}) {
      const normalized = this.buildWritingResultObject(result)
      this.currentObject = normalized
      if (normalized.chapterId) {
        this.currentChapterId = normalized.chapterId
      }
      this.recordOpenDocument({
        type: 'writing-result',
        id: normalized.id,
        title: normalized.title || buildWorkspaceResultLabel(normalized.resultType, { noneLabel: '候选稿' }),
        chapterId: normalized.chapterId
      })
      if (options.openView !== false) {
        this.currentView = options.view || 'writing'
      }
    },

    focusObject(object, options = {}) {
      if (!object?.type) {
        this.currentObject = null
        return
      }

      if (object.type === 'overview') {
        this.focusOverview(options)
        return
      }

      if (object.type === 'chapter') {
        this.focusChapterObject(object, options)
        return
      }

      if (object.type === 'plot_arc') {
        this.focusPlotArc(object, options)
        return
      }

      if (['story_model', 'character', 'worldview', 'risk'].includes(object.type)) {
        this.focusStructureSection(object.type, options)
        return
      }

      if (object.type === 'task-filter') {
        this.focusTaskFilter(object.filter, options)
        return
      }

      if (object.type === 'task') {
        this.focusTask(object, options)
        return
      }

      if (object.type === 'issue') {
        this.focusIssue(object, options)
        return
      }

      if (object.type === 'writing-result') {
        this.focusWritingResult(object, options)
        return
      }

      this.setCurrentObject(object)
      if (options.openView && options.view) {
        this.currentView = options.view
      }
    },

    setContextSnapshot(snapshot) {
      this.currentContextSnapshot = snapshot || null
    },

    syncTaskCenterSnapshot(snapshot = {}) {
      const tasks = Array.isArray(snapshot.tasks)
        ? snapshot.tasks.map((task) => this.normalizeTask(task)).filter(Boolean)
        : []

      const organizeTask = snapshot.organizeTask && typeof snapshot.organizeTask === 'object'
        ? {
            id: String(snapshot.organizeTask.id || 'organize-task'),
            status: normalizeWorkspaceTaskStatus(snapshot.organizeTask.status),
            stage: snapshot.organizeTask.stage || '',
            current: Number(snapshot.organizeTask.current || 0),
            total: Number(snapshot.organizeTask.total || 0),
            percent: Number(snapshot.organizeTask.percent || snapshot.organizeTask.progress || 0),
            chapterTitle: snapshot.organizeTask.current_chapter_title || ''
          }
        : null

      this.taskCenterSnapshot = {
        tasks,
        organizeTask,
        failedCount: Number(snapshot.failedCount || 0),
        runningCount: Number(snapshot.runningCount || 0),
        completedCount: Number(snapshot.completedCount || 0),
        auditCount: Number(snapshot.auditCount || 0)
      }
    },

    setStructureSection(section) {
      this.focusStructureSection(section, { openView: true })
    },

    setTaskFilter(filter) {
      this.focusTaskFilter(filter, { openView: true })
    },

    setCopilotTab(tab) {
      this.currentCopilotTab = tab || 'context'
    },

    ensureCopilotChatSession(session) {
      if (!session?.key) {
        return
      }

      const nextSession = {
        key: session.key,
        label: session.label || '当前对象',
        view: session.view || 'overview',
        objectTitle: session.objectTitle || '',
        draft: '',
        messages: [],
        summary: session.summary || '',
        messageCount: 0,
        updatedAt: Date.now()
      }

      const index = this.copilotChatSessions.findIndex((item) => item.key === session.key)
      if (index === -1) {
        this.copilotChatSessions = [nextSession, ...this.copilotChatSessions].slice(0, 8)
        return
      }

      const previous = this.copilotChatSessions[index]
      const merged = {
        ...previous,
        ...nextSession,
        draft: previous.draft,
        messages: previous.messages,
        summary: previous.summary,
        messageCount: previous.messageCount,
        updatedAt: previous.updatedAt
      }
      this.copilotChatSessions.splice(index, 1, merged)
    },

    setActiveCopilotChatSession(key) {
      if (!key) {
        return
      }

      const target = this.copilotChatSessions.find((item) => item.key === key)
      if (!target) {
        return
      }

      this.currentCopilotChatSessionKey = key
      this.copilotChatDraft = target.draft || ''
      this.copilotChatMessages = Array.isArray(target.messages) ? [...target.messages] : []
    },

    setCopilotChatDraft(value) {
      const nextDraft = String(value || '')
      this.copilotChatDraft = nextDraft

      const index = this.copilotChatSessions.findIndex((item) => item.key === this.currentCopilotChatSessionKey)
      if (index >= 0) {
        this.copilotChatSessions[index] = {
          ...this.copilotChatSessions[index],
          draft: nextDraft,
          updatedAt: Date.now()
        }
      }
    },

    appendCopilotChatMessage(message) {
      if (!message || !message.role || !message.content) {
        return
      }

      const nextMessages = [
        ...this.copilotChatMessages,
        {
          role: message.role,
          content: String(message.content || '')
        }
      ].slice(-30)
      this.copilotChatMessages = nextMessages

      const index = this.copilotChatSessions.findIndex((item) => item.key === this.currentCopilotChatSessionKey)
      if (index >= 0) {
        const latestMessage = nextMessages[nextMessages.length - 1]
        this.copilotChatSessions[index] = {
          ...this.copilotChatSessions[index],
          messages: nextMessages,
          summary: this.summarizeCopilotChatMessage(latestMessage),
          messageCount: nextMessages.length,
          updatedAt: Date.now()
        }
      }
    },

    clearCopilotChatMessages() {
      this.copilotChatMessages = []
      const index = this.copilotChatSessions.findIndex((item) => item.key === this.currentCopilotChatSessionKey)
      if (index >= 0) {
        this.copilotChatSessions[index] = {
          ...this.copilotChatSessions[index],
          messages: [],
          summary: '',
          messageCount: 0,
          updatedAt: Date.now()
        }
      }
    },

    recordCopilotPrompt(prompt) {
      const content = String(prompt || '').trim()
      if (!content) {
        return
      }

      this.copilotRecentPrompts = [
        content,
        ...this.copilotRecentPrompts.filter((item) => item !== content)
      ].slice(0, 8)
    },

    recordRecentCommand(command) {
      if (!command?.id || !command?.title) {
        return
      }

      const normalized = {
        id: command.id,
        title: command.title,
        subtitle: command.subtitle || '',
        group: command.group || '命令',
        hint: command.hint || '',
        action: command.action || null
      }

      this.recentCommandItems = [
        normalized,
        ...this.recentCommandItems.filter((item) => item.id !== normalized.id)
      ].slice(0, 8)
    },

    setCopilotChatPending(value) {
      this.copilotChatPending = Boolean(value)
    },

    toggleCopilot(forceValue) {
      this.isCopilotOpen = typeof forceValue === 'boolean'
        ? forceValue
        : !this.isCopilotOpen
    },

    toggleZenMode(forceValue) {
      if (this.currentView !== 'writing') {
        this.isZenMode = false
        return
      }

      this.isZenMode = typeof forceValue === 'boolean'
        ? forceValue
        : !this.isZenMode
    },

    resetWorkspaceState() {
      this.novelId = null
      this.novelInfo = null
      this.resourceSnapshot = null
      this.currentView = 'writing'
      this.currentChapterId = null
      this.currentObject = null
      this.currentTask = null
      this.taskCenterSnapshot = null
      this.currentContextSnapshot = null
      this.openDocuments = []
      this.currentStructureSection = 'story_model'
      this.currentTaskFilter = 'all'
      this.currentCopilotTab = 'context'
      this.currentCopilotChatSessionKey = 'overview::default'
      this.copilotChatSessions = []
      this.copilotChatDraft = ''
      this.copilotChatMessages = []
      this.copilotRecentPrompts = []
      this.recentCommandItems = []
      this.copilotChatPending = false
      this.isCopilotOpen = true
      this.isZenMode = false
    }
  }
})
