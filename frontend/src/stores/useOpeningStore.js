import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const buildDefaultAnalysis = () => ({
  analysis_summary: '前三章快速建立悬念,并持续抛出新的未解问题。',
  hook_patterns: ['前 500 字引入异常事件'],
  conflict_patterns: ['主角被迫卷入核心冲突'],
  satisfaction_points: ['节奏快、线索密集'],
  chapter_end_hooks: ['章尾抛出新的关键疑点']
})

const buildDefaultStrategy = () => ({
  target_audience: '签约向悬疑读者',
  genre_positioning: '都市悬疑',
  opening_hook: '用异常事件快速抓住读者',
  first_three_chapter_goal: '三章内建立主角、主冲突与核心悬念',
  protagonist_entry: '第一章前半段完成登场',
  conflict_entry: '第一章结尾抛出不可回避的主冲突',
  selling_points: ['节奏快', '悬念强'],
  forbidden_similarity_notes: '避免直接复用参考作的关键设定与场景编排'
})

const normalizeRiskLevel = (value) => {
  const normalizedValue = String(value || 'warning').toLowerCase()
  return ['low', 'medium', 'warning', 'high', 'blocking'].includes(normalizedValue)
    ? normalizedValue
    : 'warning'
}

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const nowIso = () => new Date().toISOString()

export const useOpeningStore = defineStore('workbenchOpening', () => {
  const workId = ref('')
  const analysis = ref(buildDefaultAnalysis())
  const strategy = ref(buildDefaultStrategy())
  const riskLevel = ref('warning')
  const phase = ref('')
  const status = ref('')
  const candidateDraftIds = ref([])
  const snapshotLoaded = ref(false)
  const snapshotLoadFailed = ref(false)
  const lastSnapshotOutcome = ref('idle')
  const lastSnapshotAt = ref('')
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_opening_agent'))

  const resetPreview = () => {
    analysis.value = buildDefaultAnalysis()
    strategy.value = buildDefaultStrategy()
    riskLevel.value = 'warning'
    phase.value = ''
    status.value = ''
    candidateDraftIds.value = []
    snapshotLoaded.value = false
    snapshotLoadFailed.value = false
    lastSnapshotOutcome.value = 'idle'
    lastSnapshotAt.value = ''
  }

  const setAnalysis = (nextAnalysis = {}) => {
    analysis.value = {
      ...buildDefaultAnalysis(),
      ...(analysis.value || {}),
      ...(nextAnalysis || {})
    }
  }

  const setStrategy = (nextStrategy = {}) => {
    strategy.value = {
      ...buildDefaultStrategy(),
      ...(strategy.value || {}),
      ...(nextStrategy || {})
    }
  }

  const setRiskLevel = (nextRiskLevel) => {
    riskLevel.value = normalizeRiskLevel(nextRiskLevel)
  }

  const loadPreview = ({ analysis: nextAnalysis, strategy: nextStrategy, riskLevel: nextRiskLevel } = {}) => {
    analysis.value = {
      ...buildDefaultAnalysis(),
      ...(nextAnalysis || {})
    }
    strategy.value = {
      ...buildDefaultStrategy(),
      ...(nextStrategy || {})
    }
    setRiskLevel(nextRiskLevel)
  }

  const hydratePreview = (payload = {}) => {
    loadPreview(payload)
  }

  const loadSnapshot = (payload = {}) => {
    if (payload.analysis) setAnalysis(payload.analysis)
    if (payload.strategy) setStrategy(payload.strategy)
    if (payload.risk_report) setRiskLevel(payload.risk_report.risk_level)
    if (Object.prototype.hasOwnProperty.call(payload, 'phase')) phase.value = String(payload.phase || '')
    if (Object.prototype.hasOwnProperty.call(payload, 'status')) status.value = String(payload.status || '')
    if (Array.isArray(payload.candidate_draft_ids)) candidateDraftIds.value = [...payload.candidate_draft_ids]
  }

  const loadOpeningSnapshot = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) return false
    try {
      const analysisPayload = unwrapData(await aiApi.getOpeningAnalysis(targetWorkId))
      const statusPayload = unwrapData(await aiApi.getOpeningStatus(targetWorkId))
      loadSnapshot(analysisPayload)
      loadSnapshot(statusPayload)
      snapshotLoaded.value = true
      snapshotLoadFailed.value = false
      lastSnapshotOutcome.value = 'succeeded'
      lastSnapshotAt.value = nowIso()
      return true
    } catch {
      snapshotLoaded.value = false
      snapshotLoadFailed.value = true
      lastSnapshotOutcome.value = 'failed'
      lastSnapshotAt.value = nowIso()
      return false
    }
  }

  const initializeForWork = async (targetWorkId) => {
    const nextWorkId = String(targetWorkId || '')
    if (!featureEnabled.value) {
      workId.value = nextWorkId
      resetPreview()
      return
    }
    if (workId.value && workId.value !== nextWorkId) resetPreview()
    workId.value = nextWorkId
  }

  return {
    workId,
    analysis,
    strategy,
    riskLevel,
    phase,
    status,
    candidateDraftIds,
    snapshotLoaded,
    snapshotLoadFailed,
    lastSnapshotOutcome,
    lastSnapshotAt,
    featureEnabled,
    initializeForWork,
    loadPreview,
    loadSnapshot,
    loadOpeningSnapshot,
    setAnalysis,
    setStrategy,
    setRiskLevel,
    hydratePreview,
    resetPreview
  }
})
