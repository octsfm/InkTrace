import { defineStore } from 'pinia'

import { v1WritingAssetsApi } from '@/api'
import { localCache } from '@/utils/localCache'

const OUTLINE_WORK_ID = 'work'
const TIMELINE_REORDER_ID = '__reorder__'
const ASSET_TYPES = ['work_outline', 'chapter_outline', 'timeline', 'foreshadow', 'character']

const normalizeAssetType = (assetType) => String(assetType || '').trim()

const buildAssetKey = (assetType, assetId = OUTLINE_WORK_ID) => {
  const type = normalizeAssetType(assetType)
  const id = String(assetId || OUTLINE_WORK_ID).trim()
  if (!type || !ASSET_TYPES.includes(type)) return ''
  return `${type}:${id || OUTLINE_WORK_ID}`
}

const buildAssetDraftCacheKey = (assetType, assetId = OUTLINE_WORK_ID) => {
  const key = buildAssetKey(assetType, assetId)
  return key ? `asset_draft:${key}` : ''
}

const clonePayload = (payload) => (
  payload && typeof payload === 'object'
    ? JSON.parse(JSON.stringify(payload))
    : payload
)

const isAssetConflictError = (error) => (
  error?.is_version_conflict ||
  (
    error?.response?.status === 409 &&
    error?.response?.data?.detail === 'asset_version_conflict'
  )
)

const resolveConflictPayload = (error, draft) => ({
  ...(draft || {}),
  ...(error?.conflict_payload || error?.response?.data || {})
})

export const useWritingAssetStore = defineStore('workbenchWritingAsset', {
  state: () => ({
    activeDrawer: '',
    workId: '',
    workOutline: null,
    chapterOutlines: {},
    timeline: [],
    foreshadows: [],
    characters: [],
    assets: {
      outline: null,
      timeline: [],
      foreshadow: [],
      character: []
    },
    assetDrafts: {},
    assetSaveStatus: {},
    assetConflictPayload: null,
    dirtyAssetKeys: [],
    loading: false,
    lastError: ''
  }),

  getters: {
    hasAssetConflict: (state) => Boolean(state.assetConflictPayload),
    dirtyAssets: (state) => state.dirtyAssetKeys,
    getAssetDraft: (state) => (assetType, assetId = OUTLINE_WORK_ID) => {
      const key = buildAssetKey(assetType, assetId)
      return key ? state.assetDrafts[key] || null : null
    },
    getAssetSaveStatus: (state) => (assetType, assetId = OUTLINE_WORK_ID) => {
      const key = buildAssetKey(assetType, assetId)
      return key ? state.assetSaveStatus[key] || 'idle' : 'idle'
    }
  },

  actions: {
    reset() {
      this.activeDrawer = ''
      this.workId = ''
      this.workOutline = null
      this.chapterOutlines = {}
      this.timeline = []
      this.foreshadows = []
      this.characters = []
      this.assets = {
        outline: null,
        timeline: [],
        foreshadow: [],
        character: []
      }
      this.assetDrafts = {}
      this.assetSaveStatus = {}
      this.assetConflictPayload = null
      this.dirtyAssetKeys = []
      this.loading = false
      this.lastError = ''
    },

    setWorkContext(workId) {
      const nextWorkId = String(workId || '')
      if (this.workId && this.workId !== nextWorkId) {
        this.reset()
      }
      this.workId = nextWorkId
    },

    setActiveDrawer(tabName = '') {
      this.activeDrawer = String(tabName || '')
    },

    setAssetStatus(assetType, assetId, status) {
      const key = buildAssetKey(assetType, assetId)
      if (!key) return
      this.assetSaveStatus = {
        ...this.assetSaveStatus,
        [key]: String(status || 'idle')
      }
    },

    markDirty(assetKey) {
      const key = String(assetKey || '')
      if (!key || this.dirtyAssetKeys.includes(key)) return
      this.dirtyAssetKeys = [...this.dirtyAssetKeys, key]
    },

    markClean(assetKey) {
      const key = String(assetKey || '')
      if (!key) return
      this.dirtyAssetKeys = this.dirtyAssetKeys.filter((item) => item !== key)
    },

    writeAssetDraft(assetType, assetId = OUTLINE_WORK_ID, draft = {}) {
      const key = buildAssetKey(assetType, assetId)
      if (!key) return null
      const cacheKey = buildAssetDraftCacheKey(assetType, assetId)
      const payload = {
        asset_type: normalizeAssetType(assetType),
        asset_id: String(assetId || OUTLINE_WORK_ID),
        payload: clonePayload(draft || {}),
        timestamp: Date.now()
      }
      this.assetDrafts = {
        ...this.assetDrafts,
        [key]: payload
      }
      this.markDirty(key)
      this.setAssetStatus(assetType, assetId, 'dirty')
      localCache.set(cacheKey, payload, {
        protectedKeys: this.resolveProtectedAssetDraftKeys(cacheKey)
      })
      return payload
    },

    readAssetDraft(assetType, assetId = OUTLINE_WORK_ID) {
      const key = buildAssetKey(assetType, assetId)
      const cacheKey = buildAssetDraftCacheKey(assetType, assetId)
      if (!key || !cacheKey) return null
      const cached = localCache.get(cacheKey, null)
      if (!cached) return null
      this.assetDrafts = {
        ...this.assetDrafts,
        [key]: cached
      }
      this.markDirty(key)
      this.setAssetStatus(assetType, assetId, 'dirty')
      return cached
    },

    resolveProtectedAssetDraftKeys(currentCacheKey = '') {
      const protectedKeys = [String(currentCacheKey || '')].filter(Boolean)
      if (this.assetConflictPayload?.asset_type) {
        const conflictKey = buildAssetDraftCacheKey(
          this.assetConflictPayload.asset_type,
          this.assetConflictPayload.asset_id
        )
        if (conflictKey && !protectedKeys.includes(conflictKey)) {
          protectedKeys.push(conflictKey)
        }
      }
      return protectedKeys
    },

    discardAssetDraft(assetType, assetId = OUTLINE_WORK_ID) {
      const key = buildAssetKey(assetType, assetId)
      if (!key) return
      const nextDrafts = { ...this.assetDrafts }
      delete nextDrafts[key]
      this.assetDrafts = nextDrafts
      localCache.remove(buildAssetDraftCacheKey(assetType, assetId))
      this.markClean(key)
      this.setAssetStatus(assetType, assetId, 'idle')
    },

    clearAssetConflict() {
      this.assetConflictPayload = null
    },

    markAssetConflict(assetType, assetId, payload = {}) {
      this.assetConflictPayload = {
        asset_type: normalizeAssetType(assetType),
        asset_id: String(assetId || OUTLINE_WORK_ID),
        ...payload
      }
      this.setAssetStatus(assetType, assetId, 'conflict')
    },

    async loadWorkOutline(workId = this.workId) {
      this.setWorkContext(workId)
      this.loading = true
      this.lastError = ''
      try {
        const outline = await v1WritingAssetsApi.getWorkOutline(this.workId)
        this.workOutline = outline
        this.assets.outline = outline
        return outline
      } finally {
        this.loading = false
      }
    },

    async loadChapterOutline(chapterId) {
      const id = String(chapterId || '')
      if (!id) return null
      const outline = await v1WritingAssetsApi.getChapterOutline(id)
      this.chapterOutlines = {
        ...this.chapterOutlines,
        [id]: outline
      }
      return outline
    },

    async loadTimeline(workId = this.workId) {
      this.setWorkContext(workId)
      const items = await v1WritingAssetsApi.listTimeline(this.workId)
      this.timeline = items
      this.assets.timeline = items
      return items
    },

    async loadForeshadows(workId = this.workId, status = 'open') {
      this.setWorkContext(workId)
      const items = await v1WritingAssetsApi.listForeshadows(this.workId, status)
      this.foreshadows = items
      this.assets.foreshadow = items
      return items
    },

    async createForeshadow(payload = {}) {
      const created = await v1WritingAssetsApi.createForeshadow(this.workId, payload)
      this.foreshadows = [created, ...this.foreshadows]
      this.assets.foreshadow = this.foreshadows
      return created
    },

    async updateForeshadow(foreshadowId, payload = {}) {
      const id = String(foreshadowId || '')
      return this.saveAsset('foreshadow', id, payload, async (draft) => {
        const saved = await v1WritingAssetsApi.updateForeshadow(id, draft)
        this.foreshadows = this.foreshadows.map((item) => (item.id === id ? saved : item))
        this.assets.foreshadow = this.foreshadows
        return saved
      })
    },

    async deleteForeshadow(foreshadowId) {
      const id = String(foreshadowId || '')
      if (!id) return null
      const result = await v1WritingAssetsApi.deleteForeshadow(id)
      this.foreshadows = this.foreshadows.filter((item) => item.id !== id)
      this.assets.foreshadow = this.foreshadows
      this.discardAssetDraft('foreshadow', id)
      return result
    },

    async loadCharacters(workId = this.workId, keyword = '') {
      this.setWorkContext(workId)
      const items = await v1WritingAssetsApi.listCharacters(this.workId, keyword)
      this.characters = items
      this.assets.character = items
      return items
    },

    async createCharacter(payload = {}) {
      const created = await v1WritingAssetsApi.createCharacter(this.workId, payload)
      this.characters = [created, ...this.characters]
      this.assets.character = this.characters
      return created
    },

    async updateCharacter(characterId, payload = {}) {
      const id = String(characterId || '')
      return this.saveAsset('character', id, payload, async (draft) => {
        const saved = await v1WritingAssetsApi.updateCharacter(id, draft)
        this.characters = this.characters.map((item) => (item.id === id ? saved : item))
        this.assets.character = this.characters
        return saved
      })
    },

    async deleteCharacter(characterId) {
      const id = String(characterId || '')
      if (!id) return null
      const result = await v1WritingAssetsApi.deleteCharacter(id)
      this.characters = this.characters.filter((item) => item.id !== id)
      this.assets.character = this.characters
      this.discardAssetDraft('character', id)
      return result
    },

    async loadAllAssets(workId) {
      this.setWorkContext(workId)
      const [workOutline, timeline, foreshadows, characters] = await Promise.all([
        this.loadWorkOutline(this.workId),
        this.loadTimeline(this.workId),
        this.loadForeshadows(this.workId, 'open'),
        this.loadCharacters(this.workId)
      ])
      return { workOutline, timeline, foreshadows, characters }
    },

    async saveWorkOutline(payload = {}) {
      return this.saveAsset('work_outline', OUTLINE_WORK_ID, payload, (draft) => (
        v1WritingAssetsApi.saveWorkOutline(this.workId, draft)
      ))
    },

    async saveChapterOutline(chapterId, payload = {}) {
      const id = String(chapterId || '')
      return this.saveAsset('chapter_outline', id, payload, (draft) => (
        v1WritingAssetsApi.saveChapterOutline(id, draft)
      ))
    },

    async createTimelineEvent(payload = {}) {
      const created = await v1WritingAssetsApi.createTimeline(this.workId, payload)
      this.timeline = [...this.timeline, created].sort((left, right) => Number(left.order_index) - Number(right.order_index))
      this.assets.timeline = this.timeline
      return created
    },

    async updateTimelineEvent(eventId, payload = {}) {
      const id = String(eventId || '')
      return this.saveAsset('timeline', id, payload, async (draft) => {
        const saved = await v1WritingAssetsApi.updateTimeline(id, draft)
        this.timeline = this.timeline
          .map((item) => item.id === id ? saved : item)
          .sort((left, right) => Number(left.order_index) - Number(right.order_index))
        this.assets.timeline = this.timeline
        return saved
      })
    },

    async deleteTimelineEvent(eventId) {
      const id = String(eventId || '')
      if (!id) return null
      const result = await v1WritingAssetsApi.deleteTimeline(id)
      this.timeline = this.timeline.filter((item) => item.id !== id)
      this.assets.timeline = this.timeline
      this.discardAssetDraft('timeline', id)
      return result
    },

    stageTimelineReorder(items = []) {
      const normalized = [...items]
        .map((item, index) => ({
          ...item,
          order_index: index + 1
        }))
      this.timeline = normalized
      this.assets.timeline = normalized
      this.writeAssetDraft('timeline', TIMELINE_REORDER_ID, {
        items: normalized.map((item) => ({
          id: item.id,
          order_index: item.order_index
        }))
      })
      return normalized
    },

    async reorderTimelineEvents(items = null) {
      const reorderDraft = this.assetDrafts[buildAssetKey('timeline', TIMELINE_REORDER_ID)]?.payload
      const mappings = Array.isArray(items)
        ? items
        : Array.isArray(reorderDraft?.items)
          ? reorderDraft.items
          : []
      if (!this.workId || !mappings.length) return []
      this.setAssetStatus('timeline', TIMELINE_REORDER_ID, 'saving')
      try {
        const reordered = await v1WritingAssetsApi.reorderTimeline(this.workId, clonePayload(mappings))
        this.timeline = [...reordered].sort((left, right) => Number(left.order_index) - Number(right.order_index))
        this.assets.timeline = this.timeline
        this.discardAssetDraft('timeline', TIMELINE_REORDER_ID)
        this.setAssetStatus('timeline', TIMELINE_REORDER_ID, 'synced')
        return this.timeline
      } catch (error) {
        this.setAssetStatus('timeline', TIMELINE_REORDER_ID, 'error')
        this.lastError = String(error?.message || 'timeline_reorder_failed')
        throw error
      }
    },

    async prepareChapterOutlineSwitch({
      currentChapterId = '',
      nextChapterId = '',
      decision = 'cancel'
    } = {}) {
      const currentId = String(currentChapterId || '')
      const nextId = String(nextChapterId || '')
      const currentKey = buildAssetKey('chapter_outline', currentId)
      const hasDirtyOutline = Boolean(currentKey && this.assetDrafts[currentKey])
      if (!nextId) return false
      if (!hasDirtyOutline) {
        this.readAssetDraft('chapter_outline', nextId)
        await this.loadChapterOutline(nextId)
        return true
      }
      const normalizedDecision = String(decision || 'cancel')
      if (normalizedDecision === 'cancel') {
        return false
      }
      if (normalizedDecision === 'save') {
        await this.saveChapterOutline(currentId)
      }
      if (normalizedDecision === 'discard') {
        this.discardAssetDraft('chapter_outline', currentId)
      }
      this.readAssetDraft('chapter_outline', nextId)
      await this.loadChapterOutline(nextId)
      return true
    },

    async saveAsset(assetType, assetId = OUTLINE_WORK_ID, payload = {}, saveFn) {
      const key = buildAssetKey(assetType, assetId)
      if (!key || typeof saveFn !== 'function') return null
      const draft = this.assetDrafts[key]?.payload || payload || {}
      this.setAssetStatus(assetType, assetId, 'saving')
      try {
        const saved = await saveFn(clonePayload(draft))
        if (assetType === 'work_outline') {
          this.workOutline = saved
          this.assets.outline = saved
        } else if (assetType === 'chapter_outline') {
          this.chapterOutlines = {
            ...this.chapterOutlines,
            [String(assetId)]: saved
          }
        }
        this.discardAssetDraft(assetType, assetId)
        this.setAssetStatus(assetType, assetId, 'synced')
        return saved
      } catch (error) {
        if (isAssetConflictError(error)) {
          this.markAssetConflict(assetType, assetId, resolveConflictPayload(error, this.assetDrafts[key]))
        } else {
          this.setAssetStatus(assetType, assetId, 'error')
          this.lastError = String(error?.message || 'asset_save_failed')
        }
        throw error
      }
    }
  }
})

export { buildAssetKey }
export { buildAssetDraftCacheKey }
