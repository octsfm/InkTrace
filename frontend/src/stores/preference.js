import { defineStore } from 'pinia'

export const usePreferenceStore = defineStore('workbenchPreference', {
  state: () => ({
    drawerWidth: 360,
    sidebarWidth: 280,
    editorFontSize: 18
  }),
  actions: {
    reset() {
      this.drawerWidth = 360
      this.sidebarWidth = 280
      this.editorFontSize = 18
    }
  }
})
