import { defineStore } from 'pinia'

export const useChapterDataStore = defineStore('workbenchChapterData', {
  state: () => ({
    chapters: [],
    activeChapterId: '',
    draftTitle: '',
    draftContent: ''
  }),
  actions: {
    reset() {
      this.chapters = []
      this.activeChapterId = ''
      this.draftTitle = ''
      this.draftContent = ''
    }
  }
})
