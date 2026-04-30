import { defineStore } from 'pinia'

export const useWritingAssetStore = defineStore('workbenchWritingAsset', {
  state: () => ({
    activeDrawer: '',
    assets: {
      outline: null,
      timeline: [],
      foreshadow: [],
      character: []
    },
    assetDrafts: {},
    dirtyAssetKeys: []
  }),
  actions: {
    reset() {
      this.activeDrawer = ''
      this.assets = {
        outline: null,
        timeline: [],
        foreshadow: [],
        character: []
      }
      this.assetDrafts = {}
      this.dirtyAssetKeys = []
    }
  }
})
