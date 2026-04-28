import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const statusValues = ['synced', 'saving', 'offline', 'error']
const normalizeTimestamp = (value) => {
  const timestamp = Number(value)
  return Number.isFinite(timestamp) ? timestamp : Date.now()
}

const resolveDraftKey = (payload) => String(payload?.chapterId || payload?.chapter_id || payload?.key || '')

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

  const isSaving = computed(() => saveStatus.value === 'saving')
  const hasPendingDrafts = computed(() => pendingQueue.value.length > 0)

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
    const item = payload && typeof payload === 'object' ? { ...payload } : null
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
      const key = resolveDraftKey(item)
      if (!key) continue
      const normalized = {
        ...(item || {}),
        chapterId: key,
        timestamp: normalizeTimestamp(item?.timestamp)
      }
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

  const replayOfflineDrafts = async ({ drafts = pendingQueue.value, replay }) => {
    const replayableDrafts = sortDraftsByTimestamp(
      (drafts || [])
        .map((item) => {
          const key = resolveDraftKey(item)
          if (!key) return null
          return {
            ...(item || {}),
            chapterId: key,
            timestamp: normalizeTimestamp(item?.timestamp)
          }
        })
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
    isSaving,
    hasPendingDrafts,
    setSaveStatus,
    markSaving,
    markSynced,
    markOffline,
    markError,
    setRetrySchedule,
    clearRetrySchedule,
    enqueueDraft,
    upsertDraft,
    replaceQueue,
    shiftDraft,
    clearQueue,
    removeDraft,
    replayOfflineDrafts
  }
})
