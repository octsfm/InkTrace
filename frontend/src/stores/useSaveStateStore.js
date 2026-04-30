import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { v1ChaptersApi } from '@/api'
import { localCache } from '@/utils/localCache'

const statusValues = ['synced', 'saving', 'offline', 'conflict', 'error']
const normalizeTimestamp = (value) => {
  const timestamp = Number(value)
  return Number.isFinite(timestamp) ? timestamp : Date.now()
}

const resolveDraftKey = (payload) => String(payload?.chapterId || payload?.chapter_id || payload?.key || '')
const resolveWorkId = (payload) => String(payload?.workId || payload?.work_id || '')

const buildDraftCacheKey = ({ workId, chapterId }) => {
  const normalizedWorkId = String(workId || '').trim()
  const normalizedChapterId = String(chapterId || '').trim()
  if (!normalizedWorkId || !normalizedChapterId) return ''
  return `draft:${normalizedWorkId}:${normalizedChapterId}`
}

const normalizeDraftPayload = (payload = {}) => {
  const chapterId = resolveDraftKey(payload)
  const workId = resolveWorkId(payload)
  if (!chapterId) return null

  return {
    ...payload,
    workId,
    chapterId,
    title: String(payload.title ?? ''),
    content: String(payload.content ?? ''),
    version: Number.isInteger(Number(payload.version)) ? Number(payload.version) : 1,
    cursorPosition: Number(payload.cursorPosition ?? payload.cursor_position ?? 0) || 0,
    scrollTop: Number(payload.scrollTop ?? payload.scroll_top ?? 0) || 0,
    timestamp: normalizeTimestamp(payload.timestamp)
  }
}

const isVersionConflictError = (error) => {
  return Boolean(
    error?.is_version_conflict ||
    (
      error?.response?.status === 409 &&
      ['version_conflict', 'asset_version_conflict'].includes(String(error?.response?.data?.detail || ''))
    )
  )
}

const resolveConflictPayload = (error, draft) => ({
  ...(draft || {}),
  ...(error?.conflict_payload || error?.response?.data || {})
})

const sortDraftsByTimestamp = (drafts) => {
  return [...drafts].sort((left, right) => {
    const leftTs = normalizeTimestamp(left?.timestamp)
    const rightTs = normalizeTimestamp(right?.timestamp)
    return leftTs - rightTs
  })
}

export const useSaveStateStore = defineStore('saveState', () => {
  const saveStatus = ref('synced')
  const pendingQueue = ref([])
  const lastSyncedAt = ref('')
  const lastError = ref('')
  const retryCount = ref(0)
  const nextRetryAt = ref('')
  const conflictPayload = ref(null)

  const isSaving = computed(() => saveStatus.value === 'saving')
  const hasPendingDrafts = computed(() => pendingQueue.value.length > 0)
  const hasConflict = computed(() => Boolean(conflictPayload.value))

  const setSaveStatus = (status) => {
    const next = String(status || '')
    saveStatus.value = statusValues.includes(next) ? next : 'synced'
  }

  const markSaving = () => {
    setSaveStatus('saving')
    lastError.value = ''
  }

  const markSynced = (syncedAt = new Date().toISOString()) => {
    setSaveStatus('synced')
    lastSyncedAt.value = String(syncedAt || '')
    lastError.value = ''
    retryCount.value = 0
    nextRetryAt.value = ''
  }

  const markOffline = () => {
    setSaveStatus('offline')
    nextRetryAt.value = ''
  }

  const markError = (message) => {
    setSaveStatus('error')
    lastError.value = String(message || '')
  }

  const markConflict = (payload, message = '') => {
    conflictPayload.value = payload && typeof payload === 'object'
      ? { ...payload }
      : null
    setSaveStatus('conflict')
    lastError.value = String(message || '')
    nextRetryAt.value = ''
  }

  const clearConflict = () => {
    conflictPayload.value = null
    if (saveStatus.value === 'conflict') {
      setSaveStatus(pendingQueue.value.length ? 'offline' : 'synced')
    }
  }

  const setRetrySchedule = ({ retryCount: nextRetryCount = 0, nextRetryAt: scheduledAt = '' } = {}) => {
    retryCount.value = Math.max(0, Number(nextRetryCount) || 0)
    nextRetryAt.value = String(scheduledAt || '')
  }

  const clearRetrySchedule = () => {
    retryCount.value = 0
    nextRetryAt.value = ''
  }

  const enqueueDraft = (payload) => {
    const item = payload && typeof payload === 'object' ? { ...payload } : null
    if (!item) return
    pendingQueue.value = sortDraftsByTimestamp([
      ...pendingQueue.value,
      {
        ...item,
        timestamp: normalizeTimestamp(item.timestamp)
      }
    ])
  }

  const upsertDraft = (payload) => {
    const item = normalizeDraftPayload(payload)
    const key = resolveDraftKey(item)
    if (!item || !key) return
    pendingQueue.value = sortDraftsByTimestamp([
      ...pendingQueue.value.filter((draft) => {
        const draftKey = resolveDraftKey(draft)
        return draftKey !== key
      }),
      {
        ...item,
        timestamp: normalizeTimestamp(item.timestamp)
      }
    ])
  }

  const replaceQueue = (drafts) => {
    const deduped = new Map()
    for (const item of drafts || []) {
      const normalized = normalizeDraftPayload(item)
      const key = resolveDraftKey(normalized)
      if (!normalized || !key) continue
      const existing = deduped.get(key)
      if (!existing || normalized.timestamp >= existing.timestamp) {
        deduped.set(key, normalized)
      }
    }
    pendingQueue.value = sortDraftsByTimestamp(Array.from(deduped.values()))
  }

  const shiftDraft = () => {
    if (!pendingQueue.value.length) return null
    const [head, ...rest] = pendingQueue.value
    pendingQueue.value = rest
    return head
  }

  const clearQueue = () => {
    pendingQueue.value = []
  }

  const removeDraft = (chapterId) => {
    const key = String(chapterId || '')
    if (!key) return
    pendingQueue.value = pendingQueue.value.filter((draft) => {
      const draftKey = resolveDraftKey(draft)
      return draftKey !== key
    })
  }

  const writeLocalDraft = (payload) => {
    const draft = normalizeDraftPayload(payload)
    if (!draft?.workId || !draft?.chapterId) return null

    const cacheKey = buildDraftCacheKey(draft)
    const protectedKeys = [cacheKey]
    if (conflictPayload.value) {
      const conflictKey = buildDraftCacheKey({
        workId: conflictPayload.value.workId || draft.workId,
        chapterId: conflictPayload.value.chapterId || conflictPayload.value.chapter_id
      })
      if (conflictKey) protectedKeys.push(conflictKey)
    }

    localCache.set(cacheKey, draft, { protectedKeys })
    upsertDraft(draft)
    if (typeof window !== 'undefined' && window.navigator?.onLine === false) {
      markOffline()
    } else if (!hasConflict.value) {
      markSaving()
    }
    return draft
  }

  const readLocalDraft = ({ workId, chapterId }) => {
    const cacheKey = buildDraftCacheKey({ workId, chapterId })
    if (!cacheKey) return null
    return localCache.get(cacheKey, null)
  }

  const clearLocalDraft = ({ workId, chapterId }) => {
    const cacheKey = buildDraftCacheKey({ workId, chapterId })
    if (!cacheKey) return
    localCache.remove(cacheKey)
    removeDraft(chapterId)
  }

  const collectLocalDrafts = (workId) => {
    const prefix = `draft:${String(workId || '').trim()}:`
    if (!prefix || prefix === 'draft::') return []
    return localCache.keys()
      .filter((key) => key.startsWith(prefix))
      .map((key) => localCache.get(key, null))
      .map((draft) => normalizeDraftPayload(draft))
      .filter(Boolean)
  }

  const saveDraftToRemote = (draft, save) => {
    if (typeof save === 'function') {
      return save(draft)
    }
    return v1ChaptersApi.update(draft.chapterId, {
      title: draft.title,
      content: draft.content,
      expected_version: draft.version
    })
  }

  const flushDraft = async ({ workId = '', draft, save } = {}) => {
    const normalizedDraft = normalizeDraftPayload({
      ...(draft || {}),
      workId: draft?.workId || draft?.work_id || workId
    })
    if (!normalizedDraft?.workId || !normalizedDraft?.chapterId) return null

    markSaving()
    try {
      const result = await saveDraftToRemote(normalizedDraft, save)
      clearLocalDraft({
        workId: normalizedDraft.workId,
        chapterId: normalizedDraft.chapterId
      })
      markSynced()
      return result
    } catch (error) {
      if (isVersionConflictError(error)) {
        markConflict(
          resolveConflictPayload(error, normalizedDraft),
          'version_conflict'
        )
      } else if (typeof window !== 'undefined' && window.navigator?.onLine === false) {
        markOffline()
      } else {
        markError(error?.message || 'save_failed')
      }
      throw error
    }
  }

  const flushPendingDrafts = async ({ workId = '', save } = {}) => {
    const localDrafts = collectLocalDrafts(workId)
    replaceQueue([
      ...pendingQueue.value,
      ...localDrafts
    ])

    return replayOfflineDrafts({
      drafts: pendingQueue.value,
      replay: (draft) => flushDraft({
        workId: draft.workId || workId,
        draft,
        save
      })
    })
  }

  const handleNetworkOnline = ({ workId = '', save } = {}) => {
    return flushPendingDrafts({ workId, save })
  }

  const replayOfflineDrafts = async ({ drafts = pendingQueue.value, replay }) => {
    const replayableDrafts = sortDraftsByTimestamp(
      (drafts || [])
        .map((item) => normalizeDraftPayload(item))
        .filter(Boolean)
    )

    replaceQueue(replayableDrafts)

    let successCount = 0
    for (let index = 0; index < replayableDrafts.length; index += 1) {
      const draft = replayableDrafts[index]
      try {
        await replay(draft)
        successCount += 1
      } catch (error) {
        const remainingDrafts = replayableDrafts.slice(index)
        replaceQueue(remainingDrafts)
        error.failedDraft = draft
        error.remainingDrafts = remainingDrafts
        error.successCount = successCount
        throw error
      }
    }

    clearQueue()
    return {
      successCount,
      remainingDrafts: []
    }
  }

  return {
    saveStatus,
    pendingQueue,
    lastSyncedAt,
    lastError,
    retryCount,
    nextRetryAt,
    conflictPayload,
    isSaving,
    hasPendingDrafts,
    hasConflict,
    setSaveStatus,
    markSaving,
    markSynced,
    markOffline,
    markError,
    markConflict,
    clearConflict,
    setRetrySchedule,
    clearRetrySchedule,
    enqueueDraft,
    upsertDraft,
    replaceQueue,
    shiftDraft,
    clearQueue,
    removeDraft,
    buildDraftCacheKey,
    writeLocalDraft,
    readLocalDraft,
    clearLocalDraft,
    collectLocalDrafts,
    flushDraft,
    flushPendingDrafts,
    handleNetworkOnline,
    replayOfflineDrafts
  }
})
