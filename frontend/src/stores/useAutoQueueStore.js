import { computed, ref, unref, watch } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'
import { useAIJobPolling } from '@/composables/useAIJobPolling'

const TERMINAL_RUN_STATUSES = new Set(['stopped', 'completed', 'failed', 'cancelled'])

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const isRunSnapshot = (value) => Boolean(
  value &&
  typeof value === 'object' &&
  (
    'run_id' in value ||
    'status' in value ||
    'generated_count' in value
  )
)
const normalizeRunSnapshot = (value) => {
  const directValue = unref(value)
  if (isRunSnapshot(directValue)) {
    return directValue
  }
  const nestedRun = unref(directValue?.run)
  if (isRunSnapshot(nestedRun)) {
    return nestedRun
  }
  return null
}
const mergeRunSnapshots = (baseRun, preferredRun) => {
  if (!baseRun && !preferredRun) return null
  return {
    ...(baseRun || {}),
    ...(preferredRun || {})
  }
}

export const useAutoQueueStore = defineStore('workbenchAutoQueue', () => {
  const workId = ref('')
  const loading = ref(false)
  const savingConfig = ref(false)
  const actionLoading = ref(false)
  const config = ref(null)
  const currentRun = ref(null)
  const historyRuns = ref([])
  const errorMessage = ref('')
  const noteMessage = ref('')
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_auto_queue'))
  const statusPolling = useAIJobPolling({
    intervalMs: 2500,
    maxIntervalMs: 5000,
    fetchJob: async (runId) => {
      const payload = unwrapData(await aiApi.getAutoQueueStatus(runId))
      return {
        data: normalizeRunSnapshot(payload),
        polling_hint: payload?.polling_hint || payload?.run?.polling_hint || {}
      }
    },
    terminalStatuses: TERMINAL_RUN_STATUSES
  })

  const waitingUserDecision = computed(() => String(currentRun.value?.status || '') === 'waiting_user_decision')
  const runActive = computed(() => Boolean(currentRun.value?.run_id) && !TERMINAL_RUN_STATUSES.has(String(currentRun.value?.status || '')))

  const updateNoteMessage = (run) => {
    const status = String(run?.status || '')
    const stopReason = String(run?.stop_record?.stop_reason || '')
    if (status === 'waiting_user_decision') {
      noteMessage.value = '等待你确认后继续下一章。'
      return
    }
    if (stopReason === 'budget_exceeded') {
      noteMessage.value = '已到达你设置的用量上限，这次续写已停下。'
      return
    }
    if (stopReason === 'blocking_review_consecutive') {
      noteMessage.value = '连续发现需要你处理的矛盾，这次续写已停下。'
      return
    }
    if (stopReason === 'user_manual_stop' || status === 'stopped') {
      noteMessage.value = '这次续写已停下，已经写好的新稿会保留。'
      return
    }
    noteMessage.value = ''
  }

  const resetState = () => {
    loading.value = false
    savingConfig.value = false
    actionLoading.value = false
    config.value = null
    currentRun.value = null
    historyRuns.value = []
    errorMessage.value = ''
    noteMessage.value = ''
    statusPolling.stop()
    statusPolling.job.value = null
    statusPolling.jobId.value = ''
    statusPolling.pollingHint.value = {}
  }

  const syncCurrentRun = (run) => {
    currentRun.value = normalizeRunSnapshot(run)
    updateNoteMessage(currentRun.value)
  }

  const loadConfig = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) {
      config.value = null
      return null
    }
    const payload = unwrapData(await aiApi.getAutoQueueConfig(targetWorkId))
    config.value = payload?.config || null
    return config.value
  }

  const loadHistory = async (targetWorkId = workId.value, options = {}) => {
    if (!featureEnabled.value || !targetWorkId) {
      historyRuns.value = []
      syncCurrentRun(null)
      return []
    }
    const payload = unwrapData(await aiApi.getAutoQueueHistory(targetWorkId))
    historyRuns.value = Array.isArray(payload?.runs) ? payload.runs : []
    const preferredRun = options?.preferredRun || null
    const currentSnapshot = preferredRun || currentRun.value
    const currentRunId = String(currentSnapshot?.run_id || '')
    const historyMatch = historyRuns.value.find((item) => String(item?.run_id || '') === currentRunId)
    const nextCurrent = historyMatch
      ? mergeRunSnapshots(historyMatch, currentSnapshot)
      : currentSnapshot ||
      historyRuns.value.find((item) => !TERMINAL_RUN_STATUSES.has(String(item?.status || ''))) ||
        historyRuns.value[0] ||
        null
    syncCurrentRun(nextCurrent)
    return historyRuns.value
  }

  const refreshAll = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) {
      resetState()
      return
    }
    loading.value = true
    errorMessage.value = ''
    try {
      await Promise.all([
        loadConfig(targetWorkId),
        loadHistory(targetWorkId)
      ])
      const activeRunId = String(currentRun.value?.run_id || '')
      if (activeRunId && !TERMINAL_RUN_STATUSES.has(String(currentRun.value?.status || ''))) {
        await statusPolling.start(activeRunId)
      }
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '暂时没能看到这次续写的状态')
    } finally {
      loading.value = false
    }
  }

  const initializeForWork = async (targetWorkId) => {
    workId.value = String(targetWorkId || '')
    resetState()
    if (!featureEnabled.value || !workId.value) return
    await refreshAll(workId.value)
  }

  const saveConfig = async (payload = {}) => {
    if (!featureEnabled.value || !workId.value) return null
    savingConfig.value = true
    errorMessage.value = ''
    try {
      const response = unwrapData(await aiApi.upsertAutoQueueConfig({
        work_id: workId.value,
        ...payload
      }))
      config.value = response?.config || null
      return config.value
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '保护设置暂时没能保存')
      throw error
    } finally {
      savingConfig.value = false
    }
  }

  const startQueue = async ({ startChapterId, userInstruction = '' } = {}) => {
    if (!featureEnabled.value || !workId.value) return null
    actionLoading.value = true
    errorMessage.value = ''
    try {
      const response = unwrapData(await aiApi.startAutoQueue({
        work_id: workId.value,
        start_chapter_id: String(startChapterId || ''),
        user_instruction: String(userInstruction || '').trim()
      }))
      const runId = String(response?.run_id || '')
      if (!runId) {
        throw new Error('auto_queue_run_missing')
      }
      const provisionalRun = {
        run_id: runId,
        status: String(response?.status || 'pending'),
        generated_count: 0
      }
      syncCurrentRun(provisionalRun)
      await statusPolling.start(runId)
      const startedRun = mergeRunSnapshots(
        provisionalRun,
        normalizeRunSnapshot(statusPolling.job.value)
      )
      syncCurrentRun(startedRun)
      await loadHistory(workId.value, { preferredRun: startedRun })
      return currentRun.value
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '这次没能开始写，请稍后再试')
      throw error
    } finally {
      actionLoading.value = false
    }
  }

  const buildActionPayload = (prefix) => ({
    caller_type: 'user_action',
    user_action: true,
    idempotency_key: buildIdempotencyKey(prefix)
  })

  const runControlAction = async (executor, runId, prefix) => {
    if (!featureEnabled.value || !runId) return null
    actionLoading.value = true
    errorMessage.value = ''
    try {
      const payload = unwrapData(await executor(runId, buildActionPayload(prefix)))
      syncCurrentRun(payload?.run || currentRun.value)
      if (currentRun.value?.run_id && !TERMINAL_RUN_STATUSES.has(String(currentRun.value?.status || ''))) {
        await statusPolling.start(currentRun.value.run_id)
      } else {
        statusPolling.stop()
      }
      await loadHistory(workId.value, { preferredRun: currentRun.value })
      return currentRun.value
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '这次操作没有完成，请稍后再试')
      throw error
    } finally {
      actionLoading.value = false
    }
  }

  const pauseQueue = async (runId) => runControlAction(aiApi.pauseAutoQueue, runId, 'auto_queue_pause')
  const resumeQueue = async (runId) => runControlAction(aiApi.resumeAutoQueue, runId, 'auto_queue_resume')
  const stopQueue = async (runId) => runControlAction(aiApi.stopAutoQueue, runId, 'auto_queue_stop')
  const cancelQueue = async (runId) => runControlAction(aiApi.cancelAutoQueue, runId, 'auto_queue_cancel')
  const confirmContinue = async (runId) => runControlAction(aiApi.confirmAutoQueueContinue, runId, 'auto_queue_confirm_continue')

  const selectRun = async (runId) => {
    if (!featureEnabled.value || !runId) return null
    loading.value = true
    errorMessage.value = ''
    try {
      const payload = unwrapData(await aiApi.getAutoQueueStatus(runId))
      syncCurrentRun(payload?.run || null)
      if (currentRun.value?.run_id && !TERMINAL_RUN_STATUSES.has(String(currentRun.value?.status || ''))) {
        await statusPolling.start(currentRun.value.run_id)
      } else {
        statusPolling.stop()
      }
      return currentRun.value
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '暂时没能看到以前写过的新稿')
      throw error
    } finally {
      loading.value = false
    }
  }

  watch(() => statusPolling.job.value, async (job) => {
    const nextRun = normalizeRunSnapshot(job)
    if (!nextRun) return
    syncCurrentRun(nextRun)
    if (TERMINAL_RUN_STATUSES.has(String(nextRun.status || '')) && workId.value) {
      await loadHistory(workId.value)
    }
  }, { deep: true })

  return {
    workId,
    featureEnabled,
    loading,
    savingConfig,
    actionLoading,
    config,
    currentRun,
    historyRuns,
    errorMessage,
    noteMessage,
    waitingUserDecision,
    runActive,
    statusPolling,
    initializeForWork,
    refreshAll,
    loadConfig,
    loadHistory,
    saveConfig,
    startQueue,
    pauseQueue,
    resumeQueue,
    stopQueue,
    cancelQueue,
    confirmContinue,
    selectRun
  }
})
