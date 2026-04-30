import { defineStore } from 'pinia'

export const useSaveStateStore = defineStore('workbenchSaveState', {
  state: () => ({
    status: 'idle',
    pendingQueue: [],
    conflictPayload: null,
    offline: false
  }),
  actions: {
    reset() {
      this.status = 'idle'
      this.pendingQueue = []
      this.conflictPayload = null
      this.offline = false
    }
  }
})
