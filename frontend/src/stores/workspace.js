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
    isZenMode: false
  }),
  actions: {
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
      this.openDocuments = [
        { type: 'chapter', id: chapterId, title: chapterMeta.title || '' },
        ...this.openDocuments.filter((item) => !(item.type === 'chapter' && item.id === chapterId))
      ].slice(0, 10)
      this.isZenMode = false
    },

    setCurrentObject(object) {
      this.currentObject = object || null
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
      this.isCopilotOpen = true
      this.isZenMode = false
    }
  }
})
