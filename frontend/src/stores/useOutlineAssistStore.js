import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const DEFAULT_MODE = 'outline_polish'
const OUTLINE_ASSIST_MODES = [
  { id: 'outline_polish', label: '润色' },
  { id: 'outline_expand', label: '扩写' },
  { id: 'chapter_outline_detail', label: '章节细纲' },
  { id: 'writing_task_suggestion', label: '写作建议' }
]
const OUTLINE_APPLYABLE_SUGGESTION_TYPES = new Set(['outline_polish', 'outline_expand', 'chapter_outline_detail'])
const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

const normalizeSuggestionMode = (suggestionType) => ({
  outline_polish: 'outline_polish',
  outline_expand: 'outline_expand',
  chapter_outline_detail: 'chapter_outline_detail',
  chapter_outline_suggestion: 'chapter_outline_detail',
  writing_task_suggestion: 'writing_task_suggestion'
}[String(suggestionType || '')] || '')

export const useOutlineAssistStore = defineStore('workbenchOutlineAssist', () => {
  const workId = ref('')
  const chapterId = ref('')
  const suggestions = ref([])
  const suggestionDetails = ref({})
  const activeMode = ref(DEFAULT_MODE)
  const applyConfirmSuggestionId = ref('')
  const applySubmittingSuggestionId = ref('')
  const submittingSuggestionId = ref('')
  const submittingActionType = ref('')
  const actionError = ref('')
  const loading = ref(false)
  const conflictSectionVisible = ref(false)
  const conflictLoading = ref(false)
  const conflictItems = ref([])
  const conflictDetails = ref({})
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_outline_assist'))
  const modes = OUTLINE_ASSIST_MODES

  const isSelectionOnlySuggestion = (item) => {
    const suggestionType = String(item?.suggestion_type || '')
    if (!['outline_polish', 'outline_expand'].includes(suggestionType)) {
      return false
    }
    const payload = item?.payload_json || item?.payload || {}
    return String(payload?.target_kind || '').toLowerCase() === 'selection' && !String(payload?.target_id || '').trim()
  }

  const getSuggestionStatus = (item) => String(item?.status || '').toLowerCase()
  const isPendingLifecycleSuggestion = (item) => ['generating', 'failed'].includes(getSuggestionStatus(item))
  const isTerminalSuggestion = (item) => ['applied', 'dismissed', 'converted'].includes(getSuggestionStatus(item))
  const isAcceptedWritingTaskSuggestion = (item) => (
    String(item?.suggestion_type || '') === 'writing_task_suggestion' &&
    getSuggestionStatus(item) === 'accepted'
  )
  const isStaleSuggestion = (item) => String(item?.status || '').toLowerCase() === 'stale'
  const canAcceptSuggestion = (item) => (
    !isPendingLifecycleSuggestion(item) &&
    !isTerminalSuggestion(item) &&
    getSuggestionStatus(item) !== 'accepted'
  )
  const canResolveSuggestion = (item) => (
    !isPendingLifecycleSuggestion(item) &&
    !isTerminalSuggestion(item) &&
    !isAcceptedWritingTaskSuggestion(item)
  )
  const canConvertSuggestion = (item) => (
    canResolveSuggestion(item) &&
    getSuggestionStatus(item) !== 'accepted' &&
    !['risk_warning', 'writing_task_suggestion'].includes(String(item?.suggestion_type || ''))
  )

  const canApplySuggestion = (item) => (
    OUTLINE_APPLYABLE_SUGGESTION_TYPES.has(String(item?.suggestion_type || '')) &&
    getSuggestionStatus(item) === 'accepted' &&
    !isSelectionOnlySuggestion(item)
  )

  const filteredSuggestions = computed(() => (
    suggestions.value.filter((item) => normalizeSuggestionMode(item?.suggestion_type) === activeMode.value)
  ))

  const ensureAvailableMode = () => {
    const currentModeHasItems = suggestions.value.some((item) => normalizeSuggestionMode(item?.suggestion_type) === activeMode.value)
    if (currentModeHasItems) return
    const firstAvailableMode = modes.find((mode) => (
      suggestions.value.some((item) => normalizeSuggestionMode(item?.suggestion_type) === mode.id)
    ))?.id
    activeMode.value = firstAvailableMode || DEFAULT_MODE
  }

  const resetState = () => {
    suggestions.value = []
    suggestionDetails.value = {}
    activeMode.value = DEFAULT_MODE
    applyConfirmSuggestionId.value = ''
    applySubmittingSuggestionId.value = ''
    actionError.value = ''
    chapterId.value = ''
    clearConflictHandoff()
  }

  const initializeForWork = async (targetWorkId) => {
    const nextWorkId = String(targetWorkId || '')
    if (!featureEnabled.value) {
      workId.value = nextWorkId
      resetState()
      return
    }
    if (workId.value && workId.value !== nextWorkId) {
      resetState()
    }
    workId.value = nextWorkId
  }

  const setSuggestions = (items = []) => {
    suggestions.value = Array.isArray(items) ? [...items] : []
    ensureAvailableMode()
  }

  const loadSuggestions = async ({ workId: targetWorkId = workId.value, chapterId: targetChapterId = '' } = {}) => {
    if (!featureEnabled.value || !targetWorkId) {
      setSuggestions([])
      return []
    }
    const nextChapterId = String(targetChapterId || '')
    if (chapterId.value !== nextChapterId) {
      clearChapterScopedUiState()
      setSuggestions([])
    }
    chapterId.value = nextChapterId
    loading.value = true
    try {
      const payload = await aiApi.listAISuggestions({
        work_id: String(targetWorkId || ''),
        chapter_id: nextChapterId
      })
      const items = payload?.data?.items || payload?.items || []
      clearActionError()
      setSuggestions(items)
      return suggestions.value
    } finally {
      loading.value = false
    }
  }

  const loadSuggestionDetail = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId) return null
    const payload = await aiApi.getAISuggestion(String(suggestionId || ''))
    const detail = payload?.data ?? payload ?? {}
    suggestionDetails.value = {
      ...suggestionDetails.value,
      [String(suggestionId || '')]: detail
    }
    return detail
  }

  const refreshCurrentSuggestions = async () => {
    if (!featureEnabled.value || !workId.value) return suggestions.value
    return loadSuggestions({
      workId: workId.value,
      chapterId: chapterId.value
    })
  }

  const clearChapterScopedUiState = () => {
    clearActionError()
    applyConfirmSuggestionId.value = ''
    applySubmittingSuggestionId.value = ''
    submittingSuggestionId.value = ''
    submittingActionType.value = ''
    suggestionDetails.value = {}
    clearConflictHandoff()
  }

  const isCurrentSuggestionContext = (
    targetWorkId = workId.value,
    targetChapterId = chapterId.value
  ) => (
    String(workId.value || '') === String(targetWorkId || '') &&
    String(chapterId.value || '') === String(targetChapterId || '')
  )

  const acceptSuggestion = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId || submittingSuggestionId.value === String(suggestionId || '')) return null
    const targetSuggestion = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (targetSuggestion && !canAcceptSuggestion(targetSuggestion)) {
      setActionError('当前建议不允许采纳')
      return null
    }
    clearActionError()
    const actionWorkId = workId.value
    const actionChapterId = chapterId.value
    submittingSuggestionId.value = String(suggestionId || '')
    submittingActionType.value = 'accept'
    try {
      const payload = await aiApi.acceptAISuggestion(String(suggestionId || ''), {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        idempotency_key: buildIdempotencyKey('suggestion_accept')
      })
      const accepted = payload?.data ?? payload ?? {}
      if (!isCurrentSuggestionContext(actionWorkId, actionChapterId)) {
        return accepted
      }
      const acceptedId = String(accepted?.suggestion_id || suggestionId)
      suggestions.value = suggestions.value.map((item) => (
        String(item?.suggestion_id || '') === acceptedId
          ? { ...item, ...accepted }
          : item
      ))
      await refreshCurrentSuggestions()
      return accepted
    } finally {
      submittingSuggestionId.value = ''
      submittingActionType.value = ''
    }
  }

  const dismissSuggestion = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId || submittingSuggestionId.value === String(suggestionId || '')) return null
    const targetSuggestion = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (targetSuggestion && !canResolveSuggestion(targetSuggestion)) {
      setActionError('当前建议不允许忽略')
      return null
    }
    clearActionError()
    const actionWorkId = workId.value
    const actionChapterId = chapterId.value
    submittingSuggestionId.value = String(suggestionId || '')
    submittingActionType.value = 'dismiss'
    try {
      const payload = await aiApi.dismissAISuggestion(String(suggestionId || ''), {
        caller_type: 'user_action',
        user_action: true,
        decision_note: 'manual dismiss',
        idempotency_key: buildIdempotencyKey('suggestion_dismiss')
      })
      const dismissed = payload?.data ?? payload ?? {}
      if (!isCurrentSuggestionContext(actionWorkId, actionChapterId)) {
        return dismissed
      }
      const dismissedId = String(dismissed?.suggestion_id || suggestionId)
      suggestions.value = suggestions.value.map((item) => (
        String(item?.suggestion_id || '') === dismissedId
          ? { ...item, ...dismissed }
          : item
      ))
      await refreshCurrentSuggestions()
      return dismissed
    } finally {
      submittingSuggestionId.value = ''
      submittingActionType.value = ''
    }
  }

  const convertSuggestion = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId || submittingSuggestionId.value === String(suggestionId || '')) return null
    const targetSuggestion = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (targetSuggestion && !canConvertSuggestion(targetSuggestion)) {
      setActionError('当前建议不允许转为执行动作')
      return null
    }
    clearActionError()
    const actionWorkId = workId.value
    const actionChapterId = chapterId.value
    submittingSuggestionId.value = String(suggestionId || '')
    submittingActionType.value = 'convert'
    try {
      const payload = await aiApi.convertAISuggestion(String(suggestionId || ''), {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        idempotency_key: buildIdempotencyKey('suggestion_convert')
      })
      const converted = payload?.data ?? payload ?? {}
      if (!isCurrentSuggestionContext(actionWorkId, actionChapterId)) {
        return converted
      }
      const convertedId = String(converted?.suggestion_id || suggestionId)
      suggestions.value = suggestions.value.map((item) => (
        String(item?.suggestion_id || '') === convertedId
          ? { ...item, ...converted }
          : item
      ))
      await refreshCurrentSuggestions()
      return converted
    } finally {
      submittingSuggestionId.value = ''
      submittingActionType.value = ''
    }
  }

  const applySuggestion = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId || applySubmittingSuggestionId.value === suggestionId) {
      return null
    }
    const targetSuggestion = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (targetSuggestion && !canApplySuggestion(targetSuggestion)) {
      setActionError('当前建议不允许应用到大纲')
      return null
    }
    startApplySubmitting(suggestionId)
    const actionWorkId = workId.value
    const actionChapterId = chapterId.value
    try {
      const payload = await aiApi.applyOutlineAssistSuggestion(String(suggestionId || ''), {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        idempotency_key: buildIdempotencyKey('outline_suggestion_apply')
      })
      const applied = payload?.data ?? payload ?? {}
      if (!isCurrentSuggestionContext(actionWorkId, actionChapterId)) {
        return applied
      }
      const appliedId = String(applied?.suggestion_id || suggestionId)
      suggestions.value = suggestions.value.map((item) => (
        String(item?.suggestion_id || '') === appliedId
          ? { ...item, ...applied }
          : item
      ))
      applyConfirmSuggestionId.value = ''
      await refreshCurrentSuggestions()
      return applied
    } catch (error) {
      if (isCurrentSuggestionContext(actionWorkId, actionChapterId)) {
        setActionError(String(error?.userMessage || error?.message || '大纲应用失败，请稍后重试'))
      }
      throw error
    } finally {
      finishApplySubmitting()
    }
  }

  const clearConflictHandoff = () => {
    conflictSectionVisible.value = false
    conflictLoading.value = false
    conflictItems.value = []
    conflictDetails.value = {}
  }

  const syncConflictHandoff = async (actionPayloadRef, { workId: targetWorkId = workId.value, chapterId: targetChapterId = chapterId.value } = {}) => {
    clearConflictHandoff()
    const actionRef = String(actionPayloadRef || '')
    if (!actionRef.startsWith('conflict_guard:')) {
      return []
    }
    const recordId = actionRef.split(':').slice(1).join(':')
    if (!recordId || !targetWorkId) {
      return []
    }
    conflictSectionVisible.value = true
    conflictLoading.value = true
    try {
      const [detailPayload, listPayload] = await Promise.all([
        aiApi.getConflict(recordId),
        aiApi.listConflicts({
          work_id: String(targetWorkId || ''),
          chapter_id: String(targetChapterId || '')
        })
      ])
      const detail = detailPayload?.data ?? detailPayload ?? {}
      const items = listPayload?.data?.items || listPayload?.items || []
      conflictDetails.value = {
        ...conflictDetails.value,
        [recordId]: detail
      }
      conflictItems.value = Array.isArray(items) ? items : []
      return conflictItems.value
    } finally {
      conflictLoading.value = false
    }
  }

  const convertSuggestionWithConflictSync = async (suggestionId, { workId: targetWorkId = workId.value, chapterId: targetChapterId = chapterId.value } = {}) => {
    const converted = await convertSuggestion(suggestionId)
    if (!isCurrentSuggestionContext(targetWorkId, targetChapterId)) {
      return converted
    }
    await syncConflictHandoff(converted?.action?.action_payload_ref, {
      workId: targetWorkId,
      chapterId: targetChapterId
    })
    return converted
  }

  const setActiveMode = (modeId) => {
    activeMode.value = modes.some((mode) => mode.id === modeId) ? modeId : DEFAULT_MODE
  }

  const setActionError = (message = '') => {
    actionError.value = String(message || '')
  }

  const clearActionError = () => {
    actionError.value = ''
  }

  const openApplyConfirm = (suggestionId) => {
    clearActionError()
    applyConfirmSuggestionId.value = String(suggestionId || '')
  }

  const closeApplyConfirm = () => {
    if (applySubmittingSuggestionId.value) return
    applyConfirmSuggestionId.value = ''
  }

  const startApplySubmitting = (suggestionId) => {
    clearActionError()
    applySubmittingSuggestionId.value = String(suggestionId || '')
  }

  const finishApplySubmitting = () => {
    applySubmittingSuggestionId.value = ''
  }

  return {
    workId,
    chapterId,
    featureEnabled,
    modes,
    suggestions,
    suggestionDetails,
    activeMode,
    applyConfirmSuggestionId,
    applySubmittingSuggestionId,
    submittingSuggestionId,
    submittingActionType,
    actionError,
    loading,
    conflictSectionVisible,
    conflictLoading,
    conflictItems,
    conflictDetails,
    filteredSuggestions,
    initializeForWork,
    resetState,
    setSuggestions,
    loadSuggestions,
    loadSuggestionDetail,
    refreshCurrentSuggestions,
    acceptSuggestion,
    dismissSuggestion,
    convertSuggestion,
    applySuggestion,
    syncConflictHandoff,
    convertSuggestionWithConflictSync,
    setActiveMode,
    setActionError,
    clearActionError,
    openApplyConfirm,
    closeApplyConfirm,
    startApplySubmitting,
    finishApplySubmitting,
    clearConflictHandoff,
    clearChapterScopedUiState,
    normalizeSuggestionMode,
    getSuggestionStatus,
    isPendingLifecycleSuggestion,
    isTerminalSuggestion,
    isAcceptedWritingTaskSuggestion,
    isSelectionOnlySuggestion,
    isStaleSuggestion,
    canAcceptSuggestion,
    canResolveSuggestion,
    canConvertSuggestion,
    canApplySuggestion
  }
})
