import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'
import { useChapterDataStore } from '@/stores/useChapterDataStore'

const MIN_SELECTION_LENGTH = 2
const MAX_SELECTION_LENGTH = 3000
const REWRITE_POLL_INTERVAL_MS = 1200
const PROMPT_CONTEXT_WINDOW_CHARS = 500
const REWRITE_UNDO_WINDOW_MS = 5000
const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

const toHex = (buffer) => Array
  .from(new Uint8Array(buffer))
  .map((byte) => byte.toString(16).padStart(2, '0'))
  .join('')

const sha256Hex = async (value) => {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) {
    throw new Error('crypto_subtle_unavailable')
  }
  const encoded = new TextEncoder().encode(String(value || ''))
  return toHex(await subtle.digest('SHA-256', encoded))
}

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const getTerminalRewriteErrorMessage = (payload = {}) => {
  const status = String(payload?.status || '')
  const explicitMessage = String(payload?.error_message || '').trim()
  if (explicitMessage) return explicitMessage
  if (status === 'failed') return '选区改写生成失败,请稍后重试。'
  if (status === 'conflicted') return '原文已变化,请重新选择。'
  if (status === 'expired') return '当前选区改写结果已过期,请重新生成。'
  return ''
}

const getSelectionRangeText = (content, start, end) => String(content || '').slice(
  Math.max(0, Number(start || 0)),
  Math.max(0, Number(end || 0))
)

const getSelectionPromptContext = (content, start, end) => {
  const normalizedContent = String(content || '')
  const normalizedStart = Math.max(0, Number(start || 0))
  const normalizedEnd = Math.max(normalizedStart, Number(end || 0))
  return {
    contextBefore: normalizedContent.slice(
      Math.max(0, normalizedStart - PROMPT_CONTEXT_WINDOW_CHARS),
      normalizedStart
    ),
    contextAfter: normalizedContent.slice(
      normalizedEnd,
      normalizedEnd + PROMPT_CONTEXT_WINDOW_CHARS
    )
  }
}

const applyPatchToDraft = (source, patch) => {
  const content = String(source || '')
  const range = Array.isArray(patch?.range) ? patch.range : []
  const start = Math.max(0, Number(range[0] || 0))
  const end = Math.max(start, Number(range[1] || 0))
  const replacement = String(patch?.replacement || '')
  return `${content.slice(0, start)}${replacement}${content.slice(end)}`
}

const canApplyPatchToDraft = (source, patch, expectedSourceText) => {
  const content = String(source || '')
  const range = Array.isArray(patch?.range) ? patch.range : []
  const start = Number(range[0])
  const end = Number(range[1])
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > content.length) {
    return false
  }
  const expected = String(expectedSourceText || '')
  if (!expected) return true
  return content.slice(start, end) === expected
}

export const useSelectionRewriteStore = defineStore('workbenchSelectionRewrite', () => {
  const chapterStore = useChapterDataStore()

  const workId = ref('')
  const chapterId = ref('')
  const chapterRevision = ref(0)
  const draftRevision = ref(0)
  const selectionText = ref('')
  const selectionStart = ref(0)
  const selectionEnd = ref(0)
  const activeRewriteId = ref('')
  const requestId = ref('')
  const lastRequestedMode = ref('')
  const status = ref('')
  const candidate = ref(null)
  const editedText = ref('')
  const diffSummary = ref('')
  const modalVisible = ref(false)
  const loading = ref(false)
  const applying = ref(false)
  const actionError = ref('')
  const pollingTimerId = ref(null)
  const historyItems = ref([])
  const undoSnapshot = ref(null)
  const undoTimerId = ref(null)
  const canUndoLastApply = computed(() => Boolean(undoSnapshot.value))
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_selection_rewrite'))
  const hasValidSelection = computed(() => {
    const length = String(selectionText.value || '').length
    return length >= MIN_SELECTION_LENGTH && length <= MAX_SELECTION_LENGTH && selectionEnd.value > selectionStart.value
  })

  const clearError = () => {
    actionError.value = ''
  }

  const stopPolling = () => {
    if (pollingTimerId.value !== null) {
      clearTimeout(pollingTimerId.value)
      pollingTimerId.value = null
    }
  }

  const clearSelection = () => {
    selectionText.value = ''
    selectionStart.value = 0
    selectionEnd.value = 0
  }

  const clearModalState = () => {
    modalVisible.value = false
    editedText.value = ''
    diffSummary.value = ''
  }

  const clearUndoSnapshot = () => {
    if (undoTimerId.value) {
      clearTimeout(undoTimerId.value)
      undoTimerId.value = null
    }
    undoSnapshot.value = null
  }

  const resetState = () => {
    stopPolling()
    clearUndoSnapshot()
    activeRewriteId.value = ''
    requestId.value = ''
    status.value = ''
    candidate.value = null
    historyItems.value = []
    clearSelection()
    clearModalState()
    clearError()
    loading.value = false
    applying.value = false
  }

  const initializeContext = ({
    workId: nextWorkId = '',
    chapterId: nextChapterId = '',
    chapterRevision: nextChapterRevision = 0,
    draftRevision: nextDraftRevision = 0
  } = {}) => {
    const normalizedWorkId = String(nextWorkId || '')
    const normalizedChapterId = String(nextChapterId || '')
    if (
      workId.value &&
      chapterId.value &&
      (workId.value !== normalizedWorkId || chapterId.value !== normalizedChapterId)
    ) {
      resetState()
    }
    workId.value = normalizedWorkId
    chapterId.value = normalizedChapterId
    chapterRevision.value = Number(nextChapterRevision || 0)
    draftRevision.value = Number(nextDraftRevision || 0)
  }

  const setSelection = ({
    text = '',
    start = 0,
    end = 0
  } = {}) => {
    selectionText.value = String(text || '')
    selectionStart.value = Math.max(0, Number(start || 0))
    selectionEnd.value = Math.max(selectionStart.value, Number(end || 0))
    clearError()
  }

  const createRewrite = async (mode) => {
    if (!featureEnabled.value) return null
    if (!hasValidSelection.value) {
      actionError.value = '当前选区不满足改写条件。'
      return null
    }
    loading.value = true
    clearError()
    try {
      const currentDraft = String(chapterStore.activeChapterContent || '')
      const promptContext = getSelectionPromptContext(currentDraft, selectionStart.value, selectionEnd.value)
      lastRequestedMode.value = String(mode || lastRequestedMode.value || '')
      const payload = unwrapData(await aiApi.createSelectionRewrite({
        work_id: workId.value,
        chapter_id: chapterId.value,
        chapter_revision: chapterRevision.value,
        draft_revision: draftRevision.value,
        draft_text_hash: await sha256Hex(currentDraft),
        draft_length: currentDraft.length,
        source_text: selectionText.value,
        source_hash: await sha256Hex(selectionText.value),
        start_pos: selectionStart.value,
        end_pos: selectionEnd.value,
        context_before: promptContext.contextBefore,
        context_after: promptContext.contextAfter,
        mode: String(mode || '')
      }))
      activeRewriteId.value = String(payload?.rewrite_id || '')
      requestId.value = String(payload?.request_id || requestId.value || '')
      status.value = String(payload?.status || '')
      candidate.value = payload
      if (status.value === 'generating' && activeRewriteId.value) {
        queueMicrotask(() => {
          loadRewriteResult(activeRewriteId.value).catch(() => {})
        })
        schedulePoll(activeRewriteId.value)
      }
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_create_failed')
      throw error
    } finally {
      loading.value = false
    }
  }

  const loadRewriteResult = async (rewriteId = activeRewriteId.value) => {
    const targetRewriteId = String(rewriteId || '')
    if (!featureEnabled.value || !targetRewriteId) return null
    loading.value = true
    clearError()
    try {
      const payload = unwrapData(await aiApi.getSelectionRewrite(targetRewriteId))
      activeRewriteId.value = String(payload?.rewrite_id || targetRewriteId)
      requestId.value = String(payload?.request_id || requestId.value || '')
      status.value = String(payload?.status || '')
      candidate.value = payload
      diffSummary.value = String(payload?.diff_summary || '')
      if (status.value === 'pending') {
        stopPolling()
        editedText.value = String(payload?.rewritten_text || '')
        modalVisible.value = true
      } else if (status.value === 'generating') {
        schedulePoll(activeRewriteId.value)
      } else {
        stopPolling()
        actionError.value = getTerminalRewriteErrorMessage(payload)
      }
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_load_failed')
      throw error
    } finally {
      loading.value = false
    }
  }

  const loadChapterHistory = async (targetChapterId = chapterId.value) => {
    const normalizedChapterId = String(targetChapterId || '')
    if (!featureEnabled.value || !normalizedChapterId) {
      historyItems.value = []
      return []
    }
    const payload = unwrapData(await aiApi.listSelectionRewriteHistory(normalizedChapterId))
    historyItems.value = Array.isArray(payload?.items) ? payload.items : []
    return historyItems.value
  }

  const applyCurrentRewrite = async () => {
    const rewriteId = String(activeRewriteId.value || candidate.value?.rewrite_id || '')
    if (!featureEnabled.value || !rewriteId) return null
    applying.value = true
    clearError()
    try {
      const currentDraft = String(chapterStore.activeChapterContent || '')
      const rangeStart = Number(candidate.value?.source_start_pos ?? selectionStart.value ?? 0)
      const rangeEnd = Number(candidate.value?.source_end_pos ?? selectionEnd.value ?? 0)
      const payload = unwrapData(await aiApi.applySelectionRewrite(rewriteId, {
        final_text: editedText.value || String(candidate.value?.rewritten_text || ''),
        chapter_revision: chapterRevision.value,
        draft_revision: draftRevision.value,
        draft_text_hash: await sha256Hex(currentDraft),
        draft_length: currentDraft.length,
        range_text: getSelectionRangeText(currentDraft, rangeStart, rangeEnd),
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: buildIdempotencyKey('selection_rewrite_apply')
      }))
      if (!canApplyPatchToDraft(currentDraft, payload?.patch, candidate.value?.source_text || selectionText.value)) {
        actionError.value = '改写结果已确认,但本地草稿应用失败,请手动重试。'
        throw new Error('selection_rewrite_patch_apply_failed')
      }
      clearUndoSnapshot()
      const nextDraft = applyPatchToDraft(currentDraft, payload?.patch)
      chapterStore.updateChapterDraft(chapterId.value, nextDraft)
      undoSnapshot.value = {
        chapterId: chapterId.value,
        previousDraft: currentDraft,
        nextDraft,
        rewriteId,
        expiresAt: Date.now() + REWRITE_UNDO_WINDOW_MS
      }
      undoTimerId.value = setTimeout(() => {
        undoTimerId.value = null
        undoSnapshot.value = null
      }, REWRITE_UNDO_WINDOW_MS)
      candidate.value = {
        ...(candidate.value || {}),
        ...payload
      }
      status.value = String(payload?.status || 'applied')
      clearModalState()
      return payload
    } catch (error) {
      actionError.value = String(
        actionError.value
        || error?.userMessage
        || error?.message
        || 'selection_rewrite_apply_failed'
      )
      throw error
    } finally {
      applying.value = false
    }
  }

  const undoLastApply = () => {
    const snapshot = undoSnapshot.value
    if (!snapshot) return false
    if (Date.now() > Number(snapshot.expiresAt || 0)) {
      clearUndoSnapshot()
      return false
    }
    chapterStore.updateChapterDraft(String(snapshot.chapterId || chapterId.value || ''), String(snapshot.previousDraft || ''))
    clearUndoSnapshot()
    return true
  }

  const retryLastRewrite = async () => {
    const mode = String(lastRequestedMode.value || candidate.value?.rewrite_mode || '')
    if (!mode) return null
    return createRewrite(mode)
  }

  const clearChapterHistory = async (targetChapterId = chapterId.value) => {
    const normalizedChapterId = String(targetChapterId || '')
    if (!featureEnabled.value || !normalizedChapterId) return { chapter_id: normalizedChapterId, cleared_count: 0 }
    const payload = unwrapData(await aiApi.clearSelectionRewriteHistory(normalizedChapterId))
    historyItems.value = []
    activeRewriteId.value = ''
    requestId.value = ''
    status.value = ''
    candidate.value = null
    clearModalState()
    clearError()
    stopPolling()
    return payload
  }

  const rejectCurrentRewrite = async () => {
    const rewriteId = String(activeRewriteId.value || candidate.value?.rewrite_id || '')
    if (!featureEnabled.value || !rewriteId) return null
    clearError()
    try {
      const payload = unwrapData(await aiApi.rejectSelectionRewrite(rewriteId))
      candidate.value = {
        ...(candidate.value || {}),
        ...payload
      }
      status.value = String(payload?.status || 'rejected')
      stopPolling()
      clearModalState()
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_reject_failed')
      throw error
    }
  }

  const schedulePoll = (rewriteId = activeRewriteId.value) => {
    const targetRewriteId = String(rewriteId || '')
    if (!targetRewriteId) return
    stopPolling()
    pollingTimerId.value = setTimeout(() => {
      loadRewriteResult(targetRewriteId).catch(() => {})
    }, REWRITE_POLL_INTERVAL_MS)
  }

  return {
    workId,
    chapterId,
    chapterRevision,
    draftRevision,
    selectionText,
    selectionStart,
    selectionEnd,
    activeRewriteId,
    requestId,
    lastRequestedMode,
    status,
    candidate,
    editedText,
    diffSummary,
    modalVisible,
    loading,
    applying,
    actionError,
    pollingTimerId,
    historyItems,
    canUndoLastApply,
    featureEnabled,
    hasValidSelection,
    initializeContext,
    setSelection,
    clearSelection,
    clearModalState,
    resetState,
    createRewrite,
    loadRewriteResult,
    loadChapterHistory,
    applyCurrentRewrite,
    rejectCurrentRewrite,
    undoLastApply,
    retryLastRewrite,
    clearError,
    clearChapterHistory
  }
})

