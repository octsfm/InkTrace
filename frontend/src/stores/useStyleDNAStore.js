import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'
import { useAIJobPolling } from '@/composables/useAIJobPolling'

const STYLE_DNA_PENDING_KEY_PREFIX = 'inktrace.style-dna.pending'
const TERMINAL_JOB_STATUSES = new Set(['completed', 'failed', 'cancelled'])

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const normalizeChapterText = (chapter) => String(chapter?.content || '').trim()
const isPublishedChapter = (chapter) => String(chapter?.status || '') === 'published'

export const useStyleDNAStore = defineStore('workbenchStyleDNA', () => {
  const workId = ref('')
  const loading = ref(false)
  const activeProfile = ref(null)
  const currentProfile = ref(null)
  const historyProfiles = ref([])
  const errorMessage = ref('')
  const warningMessage = ref('')
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_style_dna'))
  const extractPolling = useAIJobPolling({ intervalMs: 3000, maxIntervalMs: 10000 })
  const extracting = computed(() => Boolean(extractPolling.jobId.value) && !extractPolling.isTerminal.value)
  const extractJobActive = computed(() => extracting.value)

  const buildStorageKey = (targetWorkId = workId.value) => `${STYLE_DNA_PENDING_KEY_PREFIX}:${String(targetWorkId || 'unknown')}`

  const savePendingExtract = (jobId) => {
    if (typeof window === 'undefined' || !window.sessionStorage || !workId.value || !jobId) return
    window.sessionStorage.setItem(buildStorageKey(), JSON.stringify({ job_id: String(jobId) }))
  }

  const clearPendingExtract = (targetWorkId = workId.value) => {
    if (typeof window === 'undefined' || !window.sessionStorage || !targetWorkId) return
    window.sessionStorage.removeItem(buildStorageKey(targetWorkId))
  }

  const loadPendingExtract = (targetWorkId = workId.value) => {
    if (typeof window === 'undefined' || !window.sessionStorage || !targetWorkId) return null
    try {
      return JSON.parse(window.sessionStorage.getItem(buildStorageKey(targetWorkId)) || 'null')
    } catch {
      return null
    }
  }

  const resetState = () => {
    activeProfile.value = null
    currentProfile.value = null
    historyProfiles.value = []
    errorMessage.value = ''
    warningMessage.value = ''
    extractPolling.stop()
    extractPolling.jobId.value = ''
    extractPolling.job.value = null
    extractPolling.pollingHint.value = {}
  }

  const loadActiveProfile = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) {
      activeProfile.value = null
      return null
    }
    const payload = unwrapData(await aiApi.getActiveStyleProfile(targetWorkId))
    activeProfile.value = payload?.profile || null
    return activeProfile.value
  }

  const loadHistoryProfiles = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) {
      historyProfiles.value = []
      return []
    }
    const payload = unwrapData(await aiApi.getStyleProfileHistory(targetWorkId))
    historyProfiles.value = Array.isArray(payload?.profiles) ? payload.profiles : []
    return historyProfiles.value
  }

  const loadProfile = async (profileId) => {
    if (!featureEnabled.value || !profileId) {
      currentProfile.value = null
      return null
    }
    const payload = unwrapData(await aiApi.getStyleProfile(profileId))
    currentProfile.value = payload?.profile || null
    return currentProfile.value
  }

  const refreshProfiles = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) {
      activeProfile.value = null
      historyProfiles.value = []
      currentProfile.value = null
      return
    }
    loading.value = true
    errorMessage.value = ''
    try {
      await Promise.all([
        loadActiveProfile(targetWorkId),
        loadHistoryProfiles(targetWorkId)
      ])
      if (!currentProfile.value?.profile_id) {
        currentProfile.value = activeProfile.value || historyProfiles.value[0] || null
      } else {
        const latestCurrent = historyProfiles.value.find((item) => item?.profile_id === currentProfile.value?.profile_id)
        currentProfile.value = latestCurrent || activeProfile.value || historyProfiles.value[0] || currentProfile.value
      }
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '风格画像加载失败')
    } finally {
      loading.value = false
    }
  }

  const restorePendingExtract = async (targetWorkId = workId.value) => {
    const pending = loadPendingExtract(targetWorkId)
    const jobId = String(pending?.job_id || '')
    if (!jobId) return
    try {
      await extractPolling.start(jobId)
    } catch (error) {
      clearPendingExtract(targetWorkId)
      errorMessage.value = String(error?.userMessage || error?.message || '风格画像任务恢复失败')
    }
  }

  const initializeForWork = async (targetWorkId) => {
    const nextWorkId = String(targetWorkId || '')
    if (workId.value && workId.value !== nextWorkId) {
      clearPendingExtract(workId.value)
    }
    workId.value = nextWorkId
    resetState()
    if (!featureEnabled.value || !workId.value) return
    await refreshProfiles(workId.value)
    await restorePendingExtract(workId.value)
  }

  const startExtract = async ({
    sourceText,
    sourceType = 'user_upload',
    sourceRef = '',
    sourceChapterIds = [],
    availableChapters = [],
    draftChapterIds = []
  } = {}) => {
    if (!featureEnabled.value || !workId.value) return null
    errorMessage.value = ''
    warningMessage.value = ''
    let normalizedSourceText = String(sourceText || '')
    let normalizedSourceRef = String(sourceRef || '')
    if (String(sourceType || '') === 'chapter_reference') {
      const normalizedChapterIds = Array.isArray(sourceChapterIds) ? sourceChapterIds.map((item) => String(item || '')) : []
      const normalizedAvailableChapters = Array.isArray(availableChapters) ? availableChapters : []
      const draftChapterIdSet = new Set(Array.isArray(draftChapterIds) ? draftChapterIds.map((item) => String(item || '')) : [])
      const selectedChapters = normalizedChapterIds
        .slice(0, 3)
        .map((chapterId) => normalizedAvailableChapters.find((item) => String(item?.id || '') === chapterId))
        .filter((chapter) => chapter && isPublishedChapter(chapter) && !draftChapterIdSet.has(String(chapter.id || '')))
      normalizedSourceRef = selectedChapters.map((chapter) => String(chapter.id || '')).join(',')
      normalizedSourceText = selectedChapters
        .map((chapter) => normalizeChapterText(chapter))
        .filter(Boolean)
        .join('\n\n')
    }
    const payload = unwrapData(await aiApi.startStyleDNAExtract({
      work_id: workId.value,
      source_text: normalizedSourceText,
      source_type: String(sourceType || 'user_upload'),
      source_ref: normalizedSourceRef,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('style_dna_extract')
    }))
    const jobId = String(payload?.job_id || '')
    if (!jobId) {
      throw new Error('style_dna_job_missing')
    }
    savePendingExtract(jobId)
    await extractPolling.start(jobId)
    return payload
  }

  const runProfileAction = async (action, profileId, successMessage) => {
    if (!featureEnabled.value || !workId.value || !profileId) return null
    errorMessage.value = ''
    warningMessage.value = ''
    try {
      const payload = unwrapData(await action(profileId, {
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: buildIdempotencyKey(`style_dna_${successMessage}`)
      }))
      currentProfile.value = payload?.profile || null
      await refreshProfiles(workId.value)
      return payload
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '风格画像操作失败')
      throw error
    }
  }

  const confirmProfile = async (profileId) => runProfileAction(aiApi.confirmStyleProfile, profileId, 'confirm')
  const disableProfile = async (profileId) => runProfileAction(aiApi.disableStyleProfile, profileId, 'disable')
  const deleteProfile = async (profileId) => {
    if (!featureEnabled.value || !workId.value || !profileId) return null
    errorMessage.value = ''
    warningMessage.value = ''
    try {
      await aiApi.deleteStyleProfile(profileId, {
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: buildIdempotencyKey('style_dna_delete')
      })
      if (currentProfile.value?.profile_id === profileId) {
        currentProfile.value = null
      }
      await refreshProfiles(workId.value)
      return true
    } catch (error) {
      errorMessage.value = String(error?.userMessage || error?.message || '风格画像删除失败')
      throw error
    }
  }

  watch(() => String(extractPolling.job.value?.status || ''), async (status) => {
    if (!status || !TERMINAL_JOB_STATUSES.has(status)) return
    clearPendingExtract()
    if (status === 'completed') {
      const resultSummary = extractPolling.job.value?.result_summary || {}
      const profileId = String(resultSummary.profile_id || '')
      if (profileId) {
        await loadProfile(profileId)
      }
      await refreshProfiles(workId.value)
      if (resultSummary.warning_code === 'P2_STYLE_LOW_CONFIDENCE' || currentProfile.value?.confidence < 0.5) {
        warningMessage.value = '风格画像置信度较低，建议补充更长的标杆文本。'
      }
      return
    }
    if (status === 'failed') {
      errorMessage.value = '风格画像提取失败，请稍后重试。'
      return
    }
    if (status === 'cancelled') {
      errorMessage.value = '风格画像提取已取消。'
    }
  })

  return {
    workId,
    featureEnabled,
    loading,
    activeProfile,
    currentProfile,
    historyProfiles,
    errorMessage,
    warningMessage,
    extractPolling,
    extracting,
    extractJobActive,
    initializeForWork,
    refreshProfiles,
    loadProfile,
    startExtract,
    confirmProfile,
    disableProfile,
    deleteProfile
  }
})
