import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workbenchWorkspace', {
  state: () => ({
    workId: '',
    lastOpenChapterId: '',
    cursorPosition: 0,
    scrollTop: 0,
    hydrated: false
  }),
  actions: {
    reset() {
      this.workId = ''
      this.lastOpenChapterId = ''
      this.cursorPosition = 0
      this.scrollTop = 0
      this.hydrated = false
    }
  }
})
