import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    novelId: null,
    novelInfo: null,
    activeView: 'overview', // Defaulting to overview
    activeChapterId: null,
    isCopilotOpen: true,
    activeCopilotTab: 'chat',
    isZenMode: false
  }),
  actions: {
    initWorkspace(novelId) {
      this.novelId = novelId
    },
    switchView(viewName) {
      this.activeView = viewName
      // Enforce business rule: Zen mode is only applicable in writing view
      if (viewName !== 'writing') {
        this.isZenMode = false
      }
    },
    openChapter(chapterId) {
      this.activeChapterId = chapterId
      this.activeView = 'writing'
      this.isZenMode = false
    }
  }
})
