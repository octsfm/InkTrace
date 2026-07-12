import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { v1WritingAssetsApi } from '@/api/works'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const DEFAULT_MODE = 'outline_polish'
const POLL_INTERVAL_MS = 1500
const OUTLINE_ASSIST_MODES = [
  { id: 'outline_polish', label: '把这段写顺', help: '理清表达和顺序，不改变故事本意。' },
  { id: 'outline_expand', label: '把这段补完整', help: '补足动机、转折、线索或场景安排。' },
  { id: 'chapter_outline_detail', label: '生成本章细纲', help: '整理本章目标、场景节拍、冲突和结尾钩子。', chapterOnly: true },
  { id: 'writing_task_suggestion', label: '整理本章写作要点', help: '整理这一章该怎么写，不会生成正文。', chapterOnly: true }
]
const GENERATION_APIS = {
  outline_polish: 'polishOutline',
  outline_expand: 'expandOutline',
  chapter_outline_detail: 'generateChapterOutline',
  writing_task_suggestion: 'suggestWritingTask'
}
const OUTLINE_APPLYABLE_SUGGESTION_TYPES = new Set([
  'outline_polish',
  'outline_expand',
  'chapter_outline_detail'
])
const RESULT_STATUSES = new Set(['generated', 'shown'])
const POLL_TERMINAL_STATUSES = new Set(['generated', 'shown', 'failed'])
const DECISION_TERMINAL_STATUSES = new Set(['dismissed', 'converted'])

const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const textFingerprint = (value) => {
  const text = String(value || '')
  let hash = 0
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0
  }
  return Math.abs(hash).toString(36)
}
const unwrapData = (payload) => payload?.data ?? payload ?? {}
const normalizeRevision = (value) => {
  const revision = Number(value)
  return Number.isFinite(revision) && revision >= 0 ? revision : 0
}
const normalizeSuggestionMode = (suggestionType) => ({
  outline_polish: 'outline_polish',
  outline_expand: 'outline_expand',
  chapter_outline_detail: 'chapter_outline_detail',
  chapter_outline_suggestion: 'chapter_outline_detail',
  writing_task_suggestion: 'writing_task_suggestion'
}[String(suggestionType || '')] || '')
const normalizeSuggestion = (value = {}) => {
  const suggestion = unwrapData(value)
  const rawPayload = suggestion?.payload ?? suggestion?.payload_json ?? {}
  const payload = Object.keys(rawPayload || {}).length
    ? {
        ...rawPayload,
        target_content_text: rawPayload?.target_content_text ?? rawPayload?.base_content_text ?? '',
        target_content_tree_json: rawPayload?.target_content_tree_json ?? rawPayload?.base_content_tree_json ?? []
      }
    : {}
  return {
    ...suggestion,
    payload,
    payload_json: suggestion?.payload_json ?? payload
  }
}
const getApiErrorDetail = (error) => (
  error?.response?.data?.error ||
  error?.response?.data?.detail ||
  error?.data?.error ||
  error?.data ||
  {}
)
const getApiErrorCode = (error) => String(
  getApiErrorDetail(error)?.error_code || getApiErrorDetail(error)?.code || error?.code || ''
)
const getApiErrorRecordRefs = (error) => {
  const detail = getApiErrorDetail(error)
  const refs = detail?.data?.record_refs ?? detail?.record_refs ?? []
  return Array.isArray(refs) ? refs.map((item) => String(item || '')).filter(Boolean) : []
}

export const useOutlineAssistStore = defineStore('workbenchOutlineAssist', () => {
  const workId = ref('')
  const chapterId = ref('')
  const targetKind = ref('work_outline')
  const targetId = ref('')
  const baselineText = ref('')
  const baselineRevision = ref(0)
  const sourceText = ref('')
  const targetLoading = ref(false)
  const targetReady = ref(false)
  const generating = ref(false)
  const activeSuggestionId = ref('')
  const suggestions = ref([])
  const suggestionDetails = ref({})
  const activeMode = ref(DEFAULT_MODE)
  const applyConfirmSuggestionId = ref('')
  const applySubmittingSuggestionId = ref('')
  const applyConflictReasons = ref({})
  const submittingSuggestionId = ref('')
  const submittingActionType = ref('')
  const actionError = ref('')
  const actionNotice = ref('')
  const pendingWritingTaskId = ref('')
  const confirmingWritingTask = ref(false)
  const confirmedWritingTaskIds = ref([])
  const loading = ref(false)
  const conflictSectionVisible = ref(false)
  const conflictLoading = ref(false)
  const conflictItems = ref([])
  const conflictDetails = ref({})
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_outline_assist'))
  const modes = OUTLINE_ASSIST_MODES
  let contextToken = 0
  let pollTimer = null
  const idempotencyKeys = new Map()

  const operationKey = (scope) => {
    const key = String(scope || '')
    if (!idempotencyKeys.has(key)) idempotencyKeys.set(key, buildIdempotencyKey(key || 'outline_action'))
    return idempotencyKeys.get(key)
  }

  const targetLabel = computed(() => ({
    work_outline: '整本故事大纲',
    chapter_outline: '章节细纲',
    selection: '一段临时文字'
  }[targetKind.value] || '整本故事大纲'))
  const targetSelection = computed(() => {
    if (targetKind.value === 'selection') return 'selection'
    if (targetKind.value === 'chapter_outline') return `chapter:${targetId.value}`
    return 'work'
  })
  const matchesCurrentTarget = (item) => {
    const payload = item?.payload ?? item?.payload_json ?? {}
    const target = item?.target ?? {}
    const kind = String(
      payload?.target_kind || target?.target_kind || target?.target_type || ''
    )
    const id = String(
      payload?.target_id ?? payload?.chapter_id ?? target?.target_id ?? target?.target_ref_id ?? ''
    )
    if (targetKind.value === 'selection') return kind === 'selection'
    if (targetKind.value === 'work_outline') {
      return kind === 'work_outline' && (!id || id === workId.value)
    }
    if (String(item?.suggestion_type || '') === 'writing_task_suggestion') {
      return id === targetId.value
    }
    return kind === 'chapter_outline' && id === targetId.value
  }
  const filteredSuggestions = computed(() => suggestions.value.filter(
    (item) => normalizeSuggestionMode(item?.suggestion_type) === activeMode.value && matchesCurrentTarget(item)
  ))

  const cancelPolling = () => {
    if (pollTimer) clearTimeout(pollTimer)
    pollTimer = null
    activeSuggestionId.value = ''
    generating.value = false
  }

  const clearConflictHandoff = () => {
    conflictSectionVisible.value = false
    conflictLoading.value = false
    conflictItems.value = []
    conflictDetails.value = {}
  }

  const clearActionError = () => { actionError.value = '' }
  const setActionError = (message = '') => { actionError.value = String(message || '') }
  const clearActionNotice = () => { actionNotice.value = '' }
  const setSourceText = (value = '') => { sourceText.value = String(value ?? '') }

  const clearChapterScopedUiState = () => {
    contextToken += 1
    cancelPolling()
    clearActionError()
    clearActionNotice()
    pendingWritingTaskId.value = ''
    confirmingWritingTask.value = false
    applyConfirmSuggestionId.value = ''
    applySubmittingSuggestionId.value = ''
    applyConflictReasons.value = {}
    submittingSuggestionId.value = ''
    submittingActionType.value = ''
    suggestionDetails.value = {}
    clearConflictHandoff()
  }

  const resetState = () => {
    clearChapterScopedUiState()
    suggestions.value = []
    activeMode.value = DEFAULT_MODE
    chapterId.value = ''
    targetKind.value = 'work_outline'
    targetId.value = ''
    baselineText.value = ''
    baselineRevision.value = 0
    sourceText.value = ''
    targetLoading.value = false
    targetReady.value = false
    confirmedWritingTaskIds.value = []
    idempotencyKeys.clear()
  }

  const initializeForWork = async (targetWorkId) => {
    const nextWorkId = String(targetWorkId || '')
    if (workId.value && workId.value !== nextWorkId) resetState()
    workId.value = nextWorkId
    if (!featureEnabled.value) resetState()
  }

  const initializeForTarget = async (targetWorkId, targetChapterId = '') => {
    const nextWorkId = String(targetWorkId || '')
    const nextChapterId = String(targetChapterId || '')
    const contextChanged = workId.value !== nextWorkId || chapterId.value !== nextChapterId
    if (contextChanged) {
      clearChapterScopedUiState()
      suggestions.value = []
    }
    workId.value = nextWorkId
    chapterId.value = nextChapterId
    targetKind.value = nextChapterId ? 'chapter_outline' : 'work_outline'
    targetId.value = nextChapterId || nextWorkId
    targetReady.value = false
    baselineText.value = ''
    baselineRevision.value = 0
    sourceText.value = ''
    if (!nextWorkId || !featureEnabled.value) {
      baselineText.value = ''
      baselineRevision.value = 0
      sourceText.value = ''
      return null
    }
    if (!nextChapterId && modes.find((mode) => mode.id === activeMode.value)?.chapterOnly) {
      activeMode.value = DEFAULT_MODE
    }

    const requestToken = contextToken
    targetLoading.value = true
    clearActionError()
    try {
      const response = nextChapterId
        ? await v1WritingAssetsApi.getChapterOutline(nextChapterId)
        : await v1WritingAssetsApi.getWorkOutline(nextWorkId)
      if (requestToken !== contextToken) return null
      const outline = unwrapData(response)
      baselineText.value = String(outline?.content_text ?? '')
      baselineRevision.value = normalizeRevision(outline?.version ?? outline?.revision)
      sourceText.value = baselineText.value
      targetReady.value = true
      return outline
    } catch (error) {
      if (requestToken === contextToken) {
        setActionError(nextChapterId
          ? '暂时没能读到本章细纲，请稍后重试。'
          : '暂时没能读到作品大纲，请稍后重试。')
      }
      throw error
    } finally {
      if (requestToken === contextToken) targetLoading.value = false
    }
  }

  const selectTarget = async (nextTargetKind, nextTargetId = '') => {
    const kind = String(nextTargetKind || 'work_outline')
    if (kind === 'selection') {
      clearChapterScopedUiState()
      suggestions.value = []
      chapterId.value = ''
      targetKind.value = 'selection'
      targetId.value = ''
      baselineText.value = ''
      baselineRevision.value = 0
      sourceText.value = ''
      targetReady.value = true
      activeMode.value = ['outline_polish', 'outline_expand'].includes(activeMode.value)
        ? activeMode.value
        : DEFAULT_MODE
      return { target_kind: 'selection' }
    }
    if (kind === 'chapter_outline') {
      return initializeForTarget(workId.value, String(nextTargetId || ''))
    }
    return initializeForTarget(workId.value, '')
  }

  const reloadTarget = async () => {
    if (targetKind.value === 'selection') return { target_kind: 'selection' }
    return initializeForTarget(
      workId.value,
      targetKind.value === 'chapter_outline' ? targetId.value : ''
    )
  }

  const isModeDisabled = (modeId) => Boolean(
    modes.find((mode) => mode.id === String(modeId || ''))?.chapterOnly && targetKind.value !== 'chapter_outline'
  )

  const ensureAvailableMode = () => {
    const currentModeHasItems = suggestions.value.some(
      (item) => normalizeSuggestionMode(item?.suggestion_type) === activeMode.value && matchesCurrentTarget(item)
    )
    if (!isModeDisabled(activeMode.value) && currentModeHasItems) return
    const firstAvailableMode = modes.find((mode) => (
      !isModeDisabled(mode.id) && suggestions.value.some(
        (item) => normalizeSuggestionMode(item?.suggestion_type) === mode.id && matchesCurrentTarget(item)
      )
    ))?.id
    activeMode.value = firstAvailableMode || DEFAULT_MODE
  }

  const setSuggestions = (items = []) => {
    suggestions.value = Array.isArray(items) ? items.map(normalizeSuggestion) : []
    const convertedWritingPlan = suggestions.value.find((item) => (
      String(item?.suggestion_type || '') === 'writing_task_suggestion' &&
      String(item?.status || '') === 'converted' &&
      matchesCurrentTarget(item)
    ))
    if (convertedWritingPlan) {
      const actionRef = String(
        convertedWritingPlan?.action?.action_payload_ref || convertedWritingPlan?.result_ref || ''
      )
      const taskId = String(
        convertedWritingPlan?.writing_task_id ||
        convertedWritingPlan?.action?.writing_task_id ||
        (actionRef.startsWith('writing_task:') ? actionRef.slice('writing_task:'.length) : '')
      )
      if (taskId && !confirmedWritingTaskIds.value.includes(taskId)) pendingWritingTaskId.value = taskId
    }
    ensureAvailableMode()
  }

  const verifyRecoveredWritingPlan = async () => {
    const taskId = String(pendingWritingTaskId.value || '')
    if (!taskId || typeof aiApi.getWritingTask !== 'function') return
    try {
      const task = unwrapData(await aiApi.getWritingTask(taskId))
      if (String(task?.status || '') !== 'pending') {
        pendingWritingTaskId.value = ''
        if (!confirmedWritingTaskIds.value.includes(taskId)) {
          confirmedWritingTaskIds.value = [...confirmedWritingTaskIds.value, taskId]
        }
      }
    } catch {
      // Keep the recoverable confirmation visible when status lookup is temporarily unavailable.
    }
  }

  const upsertSuggestion = (item) => {
    const normalized = normalizeSuggestion(item)
    const suggestionId = String(normalized?.suggestion_id || '')
    if (!suggestionId) return normalized
    const existingIndex = suggestions.value.findIndex(
      (suggestion) => String(suggestion?.suggestion_id || '') === suggestionId
    )
    if (existingIndex < 0) {
      suggestions.value = [normalized, ...suggestions.value]
    } else {
      suggestions.value = suggestions.value.map((suggestion, index) => (
        index === existingIndex
          ? {
              ...suggestion,
              ...normalized,
              payload: { ...(suggestion?.payload || {}), ...(normalized?.payload || {}) },
              payload_json: { ...(suggestion?.payload_json || {}), ...(normalized?.payload_json || {}) }
            }
          : suggestion
      ))
    }
    return normalized
  }

  const isCurrentSuggestionContext = (
    targetWorkId = workId.value,
    targetChapterId = chapterId.value
  ) => String(workId.value || '') === String(targetWorkId || '') &&
    String(chapterId.value || '') === String(targetChapterId || '')

  const loadSuggestions = async ({
    workId: targetWorkId = workId.value,
    chapterId: targetChapterId = chapterId.value
  } = {}) => {
    const nextWorkId = String(targetWorkId || '')
    const nextChapterId = String(targetChapterId || '')
    if (!featureEnabled.value || !nextWorkId) {
      setSuggestions([])
      return []
    }
    if (!isCurrentSuggestionContext(nextWorkId, nextChapterId)) {
      clearChapterScopedUiState()
      suggestions.value = []
      workId.value = nextWorkId
      chapterId.value = nextChapterId
      targetKind.value = nextChapterId ? 'chapter_outline' : 'work_outline'
      targetId.value = nextChapterId || nextWorkId
    }
    const requestToken = contextToken
    loading.value = true
    try {
      const payload = await aiApi.listAISuggestions({
        work_id: nextWorkId,
        chapter_id: nextChapterId
      })
      if (requestToken !== contextToken) return suggestions.value
      const unwrapped = unwrapData(payload)
      const items = unwrapped?.items || []
      clearActionError()
      setSuggestions(items)
      await verifyRecoveredWritingPlan()
      return suggestions.value
    } finally {
      if (requestToken === contextToken) loading.value = false
    }
  }

  const loadSuggestionDetail = async (suggestionId) => {
    if (!featureEnabled.value || !suggestionId) return null
    const requestToken = contextToken
    const detail = normalizeSuggestion(await aiApi.getAISuggestion(String(suggestionId)))
    if (requestToken !== contextToken) return detail
    suggestionDetails.value = {
      ...suggestionDetails.value,
      [String(suggestionId)]: detail
    }
    upsertSuggestion(detail)
    return detail
  }

  const refreshCurrentSuggestions = async () => {
    if (!featureEnabled.value || !workId.value) return suggestions.value
    return loadSuggestions({ workId: workId.value, chapterId: chapterId.value })
  }

  const getSuggestionStatus = (item) => String(item?.status || '').toLowerCase()
  const getApplyConflictReason = (item) => String(
    applyConflictReasons.value[String(item?.suggestion_id || '')] || ''
  )
  const blockSuggestionApply = (suggestionId, reason) => {
    const id = String(suggestionId || '')
    if (!id) return
    applyConflictReasons.value = {
      ...applyConflictReasons.value,
      [id]: String(reason || 'conflict')
    }
  }
  const isPendingLifecycleSuggestion = (item) => ['pending', 'failed'].includes(getSuggestionStatus(item))
  const isTerminalSuggestion = (item) => DECISION_TERMINAL_STATUSES.has(getSuggestionStatus(item))
  const isAcceptedWritingTaskSuggestion = (item) => (
    String(item?.suggestion_type || '') === 'writing_task_suggestion' &&
    getSuggestionStatus(item) === 'accepted'
  )
  const isSelectionOnlySuggestion = (item) => {
    if (!['outline_polish', 'outline_expand'].includes(String(item?.suggestion_type || ''))) return false
    const payload = item?.payload ?? item?.payload_json ?? {}
    return String(payload?.target_kind || '').toLowerCase() === 'selection' &&
      !String(payload?.target_id || '').trim()
  }
  const isStaleSuggestion = (item) => (
    getSuggestionStatus(item) === 'stale' || getApplyConflictReason(item) === 'target_changed'
  )
  const canAcceptSuggestion = (item) => (
    String(item?.suggestion_type || '') !== 'writing_task_suggestion' &&
    RESULT_STATUSES.has(getSuggestionStatus(item))
  )
  const canResolveSuggestion = (item) => (
    RESULT_STATUSES.has(getSuggestionStatus(item)) ||
    (
      getSuggestionStatus(item) === 'accepted' &&
      String(item?.suggestion_type || '') !== 'writing_task_suggestion'
    )
  )
  const canConvertSuggestion = (item) => (
    String(item?.suggestion_type || '') === 'writing_task_suggestion' &&
    ['generated', 'shown', 'accepted'].includes(getSuggestionStatus(item))
  )
  const canApplySuggestion = (item) => (
    OUTLINE_APPLYABLE_SUGGESTION_TYPES.has(String(item?.suggestion_type || '')) &&
    getSuggestionStatus(item) === 'accepted' &&
    !isSelectionOnlySuggestion(item) &&
    !getApplyConflictReason(item)
  )

  const pollSuggestion = async (suggestionId, requestToken = contextToken) => {
    if (!suggestionId || requestToken !== contextToken) return null
    try {
      const suggestion = normalizeSuggestion(await aiApi.getAISuggestion(String(suggestionId)))
      if (requestToken !== contextToken) return suggestion
      upsertSuggestion(suggestion)
      const status = getSuggestionStatus(suggestion)
      if (POLL_TERMINAL_STATUSES.has(status)) {
        pollTimer = null
        activeSuggestionId.value = ''
        generating.value = false
        if (status === 'failed') {
          setActionError('这次没有整理成功，请稍后再试一次。')
        }
        return suggestion
      }
      pollTimer = setTimeout(() => {
        pollSuggestion(suggestionId, requestToken)
      }, POLL_INTERVAL_MS)
      return suggestion
    } catch (error) {
      if (requestToken === contextToken) {
        generating.value = false
        activeSuggestionId.value = ''
        setActionError(String(error?.userMessage || '暂时没能取得整理结果，请稍后重试。'))
      }
      return null
    }
  }

  const startGeneration = async (modeId = activeMode.value) => {
    const mode = String(modeId || DEFAULT_MODE)
    if (!featureEnabled.value || generating.value) return null
    if (!GENERATION_APIS[mode]) {
      setActionError('请选择一种整理方式。')
      return null
    }
    if (isModeDisabled(mode)) {
      setActionError('请先选定一个章节，再使用这个功能。')
      return null
    }
    if (!workId.value || (targetKind.value !== 'selection' && !targetId.value)) {
      setActionError('请先打开一部作品。')
      return null
    }
    if (targetKind.value !== 'selection' && !targetReady.value) {
      setActionError('大纲还没有读取完成，请重新读取后再试。')
      return null
    }
    if (targetKind.value === 'selection' && !String(sourceText.value || '').trim()) {
      setActionError('先写下想整理的文字。')
      return null
    }
    const apiMethod = aiApi[GENERATION_APIS[mode]]
    if (typeof apiMethod !== 'function') {
      setActionError('这个整理功能暂时不可用，请稍后重试。')
      return null
    }

    cancelPolling()
    const requestToken = contextToken
    activeMode.value = mode
    generating.value = true
    clearActionError()
    clearActionNotice()
    const generationScope = `generate_${mode}_${targetKind.value}_${targetId.value}_${baselineRevision.value}_${textFingerprint(sourceText.value)}`
    const protectedTargetPayload = {
      work_id: workId.value,
      target_kind: targetKind.value,
      target_id: targetKind.value === 'selection' ? null : targetId.value,
      target_revision: targetKind.value === 'selection' ? null : baselineRevision.value,
      selected_text: sourceText.value || null,
      caller_type: 'user_action',
      idempotency_key: operationKey(generationScope)
    }
    const payload = mode === 'writing_task_suggestion'
      ? {
          work_id: workId.value,
          chapter_id: chapterId.value,
          target_revision: baselineRevision.value,
          caller_type: 'user_action',
          idempotency_key: protectedTargetPayload.idempotency_key
        }
      : mode === 'chapter_outline_detail'
        ? {
            work_id: workId.value,
            target_kind: 'chapter_outline',
            target_id: targetId.value,
            target_revision: baselineRevision.value,
            chapter_goal: sourceText.value || null,
            caller_type: 'user_action',
            idempotency_key: protectedTargetPayload.idempotency_key
          }
      : protectedTargetPayload

    try {
      const launchResponse = await apiMethod(payload)
      idempotencyKeys.delete(generationScope)
      const launch = normalizeSuggestion(launchResponse)
      if (requestToken !== contextToken) return launch
      const suggestion = upsertSuggestion({
        ...launch,
        suggestion_type: launch?.suggestion_type || mode,
        status: launch?.status || 'pending',
        payload: {
          ...(launch?.payload ?? launch?.payload_json ?? {}),
          ...(mode === 'writing_task_suggestion'
            ? { chapter_id: chapterId.value, target_revision: baselineRevision.value }
            : {
                target_kind: targetKind.value,
                target_id: targetKind.value === 'selection' ? null : targetId.value,
                target_revision: targetKind.value === 'selection' ? null : baselineRevision.value
              })
        }
      })
      const suggestionId = String(suggestion?.suggestion_id || '')
      activeSuggestionId.value = suggestionId
      if (!suggestionId) {
        generating.value = false
        setActionError('没有拿到整理结果，请重新试一次。')
        return suggestion
      }
      if (POLL_TERMINAL_STATUSES.has(getSuggestionStatus(suggestion))) {
        generating.value = false
        activeSuggestionId.value = ''
        return suggestion
      }
      await pollSuggestion(suggestionId, requestToken)
      return suggestion
    } catch (error) {
      if (requestToken === contextToken) {
        generating.value = false
        activeSuggestionId.value = ''
        setActionError(String(error?.userMessage || '这次没有整理成功，请稍后再试一次。'))
      }
      throw error
    }
  }

  const runSuggestionAction = async (suggestionId, actionType, apiMethod, extraPayload = {}) => {
    const id = String(suggestionId || '')
    if (!featureEnabled.value || !id || submittingSuggestionId.value) return null
    clearActionError()
    clearActionNotice()
    const requestToken = contextToken
    submittingSuggestionId.value = id
    submittingActionType.value = actionType
    try {
      const result = normalizeSuggestion(await apiMethod(id, {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        idempotency_key: operationKey(`${actionType}_${id}`),
        ...extraPayload
      }))
      if (requestToken !== contextToken) return null
      upsertSuggestion(result)
      return result
    } finally {
      if (requestToken === contextToken) {
        submittingSuggestionId.value = ''
        submittingActionType.value = ''
      }
    }
  }

  const acceptSuggestion = async (suggestionId) => {
    const target = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (target && !canAcceptSuggestion(target)) {
      setActionError('这条建议现在不能保留。')
      return null
    }
    const accepted = await runSuggestionAction(suggestionId, 'accept', aiApi.acceptAISuggestion)
    if (accepted && workId.value) await refreshCurrentSuggestions()
    return accepted
  }

  const dismissSuggestion = async (suggestionId) => {
    const target = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (target && !canResolveSuggestion(target)) {
      setActionError('这条建议现在不能删除。')
      return null
    }
    const dismissed = await runSuggestionAction(
      suggestionId,
      'dismiss',
      aiApi.dismissAISuggestion,
      { decision_note: 'manual dismiss' }
    )
    if (dismissed && workId.value) await refreshCurrentSuggestions()
    return dismissed
  }

  const convertSuggestion = async (suggestionId) => {
    const target = suggestions.value.find((item) => String(item?.suggestion_id || '') === String(suggestionId || ''))
    if (target && !canConvertSuggestion(target)) {
      setActionError('只有“写作计划”建议可以这样使用。')
      return null
    }
    const converted = await runSuggestionAction(suggestionId, 'convert', aiApi.convertAISuggestion)
    if (!converted) return converted
    const actionRef = String(
      converted?.action?.action_payload_ref || converted?.result_ref || ''
    )
    pendingWritingTaskId.value = String(
      converted?.writing_task_id ||
      converted?.action?.writing_task_id ||
      (actionRef.startsWith('writing_task:') ? actionRef.slice('writing_task:'.length) : '')
    )
    actionNotice.value = '已整理成待确认的本章写作计划。还需要确认使用；在确认前，它不会写入正文。'
    if (workId.value) await refreshCurrentSuggestions()
    return converted
  }

  const confirmWritingPlan = async () => {
    const writingTaskId = String(pendingWritingTaskId.value || '')
    if (!writingTaskId || confirmingWritingTask.value) return null
    confirmingWritingTask.value = true
    clearActionError()
    try {
      const result = unwrapData(await aiApi.confirmWritingTask(writingTaskId, {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        decision_note: 'manual confirm outline writing plan',
        idempotency_key: operationKey(`confirm_writing_plan_${writingTaskId}`)
      }))
      pendingWritingTaskId.value = ''
      if (!confirmedWritingTaskIds.value.includes(writingTaskId)) {
        confirmedWritingTaskIds.value = [...confirmedWritingTaskIds.value, writingTaskId]
      }
      actionNotice.value = '已确认使用这份本章写作计划，之后续写时可以使用它；正文仍由你决定何时生成。'
      return result
    } catch (error) {
      setActionError(String(error?.userMessage || error?.message || '暂时没能确认这份写作计划，请稍后重试。'))
      throw error
    } finally {
      confirmingWritingTask.value = false
    }
  }

  const copySuggestionResult = async (suggestionId) => {
    const target = suggestions.value.find(
      (item) => String(item?.suggestion_id || '') === String(suggestionId || '')
    )
    const payload = target?.payload ?? target?.payload_json ?? {}
    if (String(payload?.target_kind || '') !== 'selection') return false
    const text = String(payload?.proposed_content_text || '')
    if (!text) {
      setActionError('这条整理结果暂时没有可复制的内容。')
      return false
    }
    try {
      if (!globalThis.navigator?.clipboard?.writeText) throw new Error('clipboard_unavailable')
      await globalThis.navigator.clipboard.writeText(text)
      clearActionError()
      actionNotice.value = '已复制整理结果，你可以粘贴到想放的位置。'
      return true
    } catch {
      setActionError('没能自动复制。请选中整理后的文字，手动复制一次。')
      return false
    }
  }

  const applySuggestion = async (suggestionId) => {
    const id = String(suggestionId || '')
    if (!featureEnabled.value || !id || applySubmittingSuggestionId.value) return null
    const target = suggestions.value.find((item) => String(item?.suggestion_id || '') === id)
    if (target && !canApplySuggestion(target)) {
      applyConfirmSuggestionId.value = ''
      setActionError(getApplyConflictReason(target)
        ? '这条旧建议不能再放进大纲。请重新读取大纲并重新生成建议。'
        : '请先选择“先留着”，再把这条建议放进大纲。')
      return null
    }
    const payload = target?.payload ?? target?.payload_json ?? {}
    const reviewedTargetVersion = normalizeRevision(
      payload?.target_revision ?? payload?.target_version ?? baselineRevision.value
    )
    const requestToken = contextToken
    clearActionError()
    clearActionNotice()
    applySubmittingSuggestionId.value = id
    try {
      const result = normalizeSuggestion(await aiApi.applyOutlineAssistSuggestion(id, {
        caller_type: 'user_action',
        user_action: true,
        user_id: 'ui-user',
        idempotency_key: operationKey(`apply_${id}`),
        confirm_apply: true,
        target_revision: reviewedTargetVersion
      }))
      if (requestToken !== contextToken) return null
      upsertSuggestion({ ...result, suggestion_id: result?.suggestion_id || id, status: 'converted' })
      const proposedText = String(payload?.proposed_content_text ?? '')
      if (proposedText) {
        baselineText.value = proposedText
        sourceText.value = proposedText
      }
      baselineRevision.value = normalizeRevision(result?.new_version ?? reviewedTargetVersion)
      applyConfirmSuggestionId.value = ''
      actionNotice.value = chapterId.value ? '已写入本章细纲。' : '已写入作品大纲。'
      if (workId.value) await refreshCurrentSuggestions()
      return result
    } catch (error) {
      if (requestToken === contextToken) {
        const errorCode = getApiErrorCode(error)
        if (errorCode === 'P2_OUTLINE_TARGET_CONFLICT') {
          applyConfirmSuggestionId.value = ''
          targetReady.value = false
          blockSuggestionApply(id, 'target_changed')
          clearConflictHandoff()
          setActionError('这份大纲刚刚有改动，请刷新后重新生成建议。')
        } else if (errorCode === 'P2_OUTLINE_CONFLICT_REVIEW_REQUIRED') {
          applyConfirmSuggestionId.value = ''
          targetReady.value = false
          blockSuggestionApply(id, 'review_required')
          const [recordRef] = getApiErrorRecordRefs(error)
          const conflictRef = recordRef && !recordRef.startsWith('conflict_guard:')
            ? `conflict_guard:${recordRef}`
            : recordRef
          setActionError('发现需要先处理的冲突，大纲没有改动。处理后请刷新并重新生成建议。')
          if (conflictRef) {
            try {
              await syncConflictHandoff(conflictRef, {
                workId: workId.value,
                chapterId: chapterId.value
              })
            } catch {
              // The original apply failure remains authoritative; keep its safe retry guidance.
            }
          } else {
            try {
              await loadBlockingConflictsForTarget({
                workId: workId.value,
                chapterId: chapterId.value
              })
            } catch {
              // The original apply failure remains authoritative; keep its safe retry guidance.
            }
          }
        } else {
          setActionError(String(error?.userMessage || error?.message || '暂时没能放进大纲，请稍后重试。'))
        }
      }
      throw error
    } finally {
      if (requestToken === contextToken) applySubmittingSuggestionId.value = ''
    }
  }

  const syncConflictHandoff = async (actionPayloadRef, {
    workId: targetWorkId = workId.value,
    chapterId: targetChapterId = chapterId.value
  } = {}) => {
    clearConflictHandoff()
    const actionRef = String(actionPayloadRef || '')
    if (!actionRef.startsWith('conflict_guard:')) return []
    const recordId = actionRef.split(':').slice(1).join(':')
    if (!recordId || !targetWorkId) return []
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
      const detail = unwrapData(detailPayload)
      const items = unwrapData(listPayload)?.items || []
      conflictDetails.value = { ...conflictDetails.value, [recordId]: detail }
      conflictItems.value = Array.isArray(items) ? items : []
      return conflictItems.value
    } finally {
      conflictLoading.value = false
    }
  }

  const loadBlockingConflictsForTarget = async ({
    workId: targetWorkId = workId.value,
    chapterId: targetChapterId = chapterId.value
  } = {}) => {
    clearConflictHandoff()
    if (!targetWorkId) return []
    conflictSectionVisible.value = true
    conflictLoading.value = true
    try {
      const payload = await aiApi.listConflicts({
        work_id: String(targetWorkId || ''),
        chapter_id: String(targetChapterId || '')
      })
      const items = unwrapData(payload)?.items || []
      conflictItems.value = (Array.isArray(items) ? items : []).filter((item) => (
        String(item?.severity || '').toLowerCase() === 'blocking' &&
        !['resolved', 'dismissed'].includes(String(item?.status || '').toLowerCase())
      ))
      return conflictItems.value
    } finally {
      conflictLoading.value = false
    }
  }

  const convertSuggestionWithConflictSync = async (suggestionId, {
    workId: targetWorkId = workId.value,
    chapterId: targetChapterId = chapterId.value
  } = {}) => {
    const converted = await convertSuggestion(suggestionId)
    if (!converted || !isCurrentSuggestionContext(targetWorkId, targetChapterId)) return converted
    await syncConflictHandoff(converted?.action?.action_payload_ref, {
      workId: targetWorkId,
      chapterId: targetChapterId
    })
    return converted
  }

  const setActiveMode = (modeId) => {
    const nextMode = modes.some((mode) => mode.id === modeId) ? modeId : DEFAULT_MODE
    if (isModeDisabled(nextMode)) {
      setActionError('请先选定一个章节，再使用这个功能。')
      return false
    }
    activeMode.value = nextMode
    clearActionError()
    clearActionNotice()
    return true
  }

  const openApplyConfirm = (suggestionId) => {
    clearActionError()
    const id = String(suggestionId || '')
    const target = suggestions.value.find((item) => String(item?.suggestion_id || '') === id)
    if (target && !canApplySuggestion(target)) {
      applyConfirmSuggestionId.value = ''
      setActionError(getApplyConflictReason(target)
        ? '这条旧建议不能再放进大纲。请重新读取大纲并重新生成建议。'
        : '这条建议现在不能放进大纲。')
      return false
    }
    applyConfirmSuggestionId.value = id
    return Boolean(id)
  }
  const closeApplyConfirm = () => {
    if (!applySubmittingSuggestionId.value) applyConfirmSuggestionId.value = ''
  }
  const startApplySubmitting = (suggestionId) => {
    clearActionError()
    applySubmittingSuggestionId.value = String(suggestionId || '')
  }
  const finishApplySubmitting = () => { applySubmittingSuggestionId.value = '' }

  return {
    workId,
    chapterId,
    targetKind,
    targetId,
    targetLabel,
    targetSelection,
    baselineText,
    baselineRevision,
    sourceText,
    targetLoading,
    targetReady,
    generating,
    activeSuggestionId,
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
    actionNotice,
    pendingWritingTaskId,
    confirmingWritingTask,
    loading,
    conflictSectionVisible,
    conflictLoading,
    conflictItems,
    conflictDetails,
    filteredSuggestions,
    initializeForWork,
    initializeForTarget,
    selectTarget,
    reloadTarget,
    resetState,
    setSourceText,
    setSuggestions,
    loadSuggestions,
    loadSuggestionDetail,
    refreshCurrentSuggestions,
    startGeneration,
    pollSuggestion,
    acceptSuggestion,
    dismissSuggestion,
    convertSuggestion,
    confirmWritingPlan,
    copySuggestionResult,
    applySuggestion,
    syncConflictHandoff,
    convertSuggestionWithConflictSync,
    setActiveMode,
    setActionError,
    clearActionError,
    clearActionNotice,
    openApplyConfirm,
    closeApplyConfirm,
    startApplySubmitting,
    finishApplySubmitting,
    clearConflictHandoff,
    clearChapterScopedUiState,
    cancelPolling,
    normalizeSuggestionMode,
    getSuggestionStatus,
    isPendingLifecycleSuggestion,
    isTerminalSuggestion,
    isAcceptedWritingTaskSuggestion,
    isSelectionOnlySuggestion,
    isStaleSuggestion,
    isModeDisabled,
    matchesCurrentTarget,
    canAcceptSuggestion,
    canResolveSuggestion,
    canConvertSuggestion,
    canApplySuggestion
  }
})
