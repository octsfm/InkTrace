import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'
import { useChapterDataStore } from '@/stores/useChapterDataStore'

const MIN_SELECTION_LENGTH = 2
const MAX_SELECTION_LENGTH = 3000
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

const applyPatchToDraft = (source, patch) => {
  const content = String(source || '')
  const range = Array.isArray(patch?.range) ? patch.range : []
  const start = Math.max(0, Number(range[0] || 0))
  const end = Math.max(start, Number(range[1] || 0))
  const replacement = String(patch?.replacement || '')
  return `${content.slice(0, start)}${replacement}${content.slice(end)}`
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
  const status = ref('')
  const candidate = ref(null)
  const editedText = ref('')
  const diffSummary = ref('')
  const modalVisible = ref(false)
  const loading = ref(false)
  const applying = ref(false)
  const actionError = ref('')
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_selection_rewrite'))
  const hasValidSelection = computed(() => {
    const length = String(selectionText.value || '').length
    return length >= MIN_SELECTION_LENGTH && length <= MAX_SELECTION_LENGTH && selectionEnd.value > selectionStart.value
  })

  const clearError = () => {
    actionError.value = ''
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

  const resetState = () => {
    activeRewriteId.value = ''
    status.value = ''
    candidate.value = null
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
      actionError.value = '当前选区不满足改写条件'
      return null
    }
    loading.value = true
    clearError()
    try {
      const payload = unwrapData(await aiApi.createSelectionRewrite({
        work_id: workId.value,
        chapter_id: chapterId.value,
        chapter_revision: chapterRevision.value,
        draft_revision: draftRevision.value,
        source_text: selectionText.value,
        source_hash: await sha256Hex(selectionText.value),
        start_pos: selectionStart.value,
        end_pos: selectionEnd.value,
        mode: String(mode || '')
      }))
      activeRewriteId.value = String(payload?.rewrite_id || '')
      status.value = String(payload?.status || '')
      candidate.value = payload
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
      status.value = String(payload?.status || '')
      candidate.value = payload
      diffSummary.value = String(payload?.diff_summary || '')
      if (status.value === 'pending') {
        editedText.value = String(payload?.rewritten_text || '')
        modalVisible.value = true
      }
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_load_failed')
      throw error
    } finally {
      loading.value = false
    }
  }

  const applyCurrentRewrite = async () => {
    const rewriteId = String(activeRewriteId.value || candidate.value?.rewrite_id || '')
    if (!featureEnabled.value || !rewriteId) return null
    applying.value = true
    clearError()
    try {
      const payload = unwrapData(await aiApi.applySelectionRewrite(rewriteId, {
        final_text: editedText.value || String(candidate.value?.rewritten_text || ''),
        chapter_revision: chapterRevision.value,
        draft_revision: draftRevision.value,
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: buildIdempotencyKey('selection_rewrite_apply')
      }))
      const currentDraft = chapterStore.activeChapterContent
      const nextDraft = applyPatchToDraft(currentDraft, payload?.patch)
      chapterStore.updateChapterDraft(chapterId.value, nextDraft)
      candidate.value = {
        ...(candidate.value || {}),
        ...payload
      }
      status.value = String(payload?.status || 'applied')
      clearModalState()
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_apply_failed')
      throw error
    } finally {
      applying.value = false
    }
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
      clearModalState()
      return payload
    } catch (error) {
      actionError.value = String(error?.userMessage || error?.message || 'selection_rewrite_reject_failed')
      throw error
    }
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
    status,
    candidate,
    editedText,
    diffSummary,
    modalVisible,
    loading,
    applying,
    actionError,
    featureEnabled,
    hasValidSelection,
    initializeContext,
    setSelection,
    clearSelection,
    clearModalState,
    resetState,
    createRewrite,
    loadRewriteResult,
    applyCurrentRewrite,
    rejectCurrentRewrite
  }
})
