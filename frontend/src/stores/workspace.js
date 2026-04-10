import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    novelId: null,
    novelInfo: null,
    currentView: 'writing',
    currentChapterId: null,
    currentObject: null,
    currentTask: null,
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
  actions: {
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

      this.currentChapterId = chapterId
      this.currentView = 'writing'
      this.currentObject = {
        type: 'chapter',
        id: chapterId,
        title: chapterMeta.title || ''
      }
      this.recordOpenDocument({ type: 'chapter', id: chapterId, title: chapterMeta.title || '' })
      this.isZenMode = false
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
      } else if (object.type === 'story_model') {
        this.recordOpenDocument({ type: 'story_model', id: 'story_model', title: 'Story Model' })
      }
    },

    setCurrentTask(task) {
      this.currentTask = task || null
    },

    setContextSnapshot(snapshot) {
      this.currentContextSnapshot = snapshot || null
    },

    setStructureSection(section) {
      this.currentStructureSection = section || 'story_model'
      this.currentObject = {
        type: section || 'story_model'
      }
      this.currentView = 'structure'
    },

    setTaskFilter(filter) {
      this.currentTaskFilter = filter || 'all'
      this.currentObject = {
        type: 'task-filter',
        filter: this.currentTaskFilter
      }
      this.currentView = 'tasks'
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
      this.currentView = 'writing'
      this.currentChapterId = null
      this.currentObject = null
      this.currentTask = null
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
