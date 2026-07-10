import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const key = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`

export const useOpeningStore = defineStore('workbenchOpening', () => {
  const workId = ref('')
  const brief = ref(null)
  const directionBatch = ref(null)
  const selectedDirection = ref(null)
  const draftBatch = ref(null)
  const previewAnalysis = ref(null)
  const previewStrategy = ref(null)
  const previewRiskLevel = ref('low')
  const loading = ref(false)
  const actionError = ref('')
  const snapshotLoaded = ref(false)
  const snapshotLoadFailed = ref(false)
  const lastSnapshotOutcome = ref('idle')
  const lastSnapshotAt = ref('')
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_opening_agent'))

  // Compatibility summaries for the existing AI panel while it migrates to the v2 cards.
  const analysis = computed(() => previewAnalysis.value || ({
    analysis_summary: brief.value
      ? `故事：${brief.value.story_premise || ''}`
      : '先说说你的故事，开篇助手会帮你整理三个开篇方向。'
  }))
  const strategy = computed(() => previewStrategy.value || ({
    target_audience: selectedDirection.value?.name || '尚未选择开篇方向',
    opening_hook: selectedDirection.value?.summary || '',
    genre_positioning: '原创开篇',
    first_three_chapter_goal: (selectedDirection.value?.chapter_goals || []).join(' / '),
    forbidden_similarity_notes: (selectedDirection.value?.risks || []).join(' / '),
    protagonist_entry: '',
    conflict_entry: '',
    selling_points: selectedDirection.value?.advantages || []
  }))
  const riskLevel = computed(() => previewRiskLevel.value)
  const phase = computed(() => directionBatch.value?.status || brief.value?.status || '')
  const status = computed(() => draftBatch.value?.status || directionBatch.value?.status || brief.value?.status || '')
  const candidateDraftIds = computed(() => (draftBatch.value?.chapter_results || [])
    .map((item) => item.candidate_draft_id)
    .filter(Boolean))

  const reset = () => {
    brief.value = null
    directionBatch.value = null
    selectedDirection.value = null
    draftBatch.value = null
    previewAnalysis.value = null
    previewStrategy.value = null
    previewRiskLevel.value = 'low'
    actionError.value = ''
    snapshotLoaded.value = false
    snapshotLoadFailed.value = false
    lastSnapshotOutcome.value = 'idle'
    lastSnapshotAt.value = ''
  }

  const initializeForWork = async (targetWorkId) => {
    const next = String(targetWorkId || '')
    if (workId.value && workId.value !== next) reset()
    workId.value = next
  }

  const createBrief = async (form) => {
    loading.value = true
    actionError.value = ''
    try {
      brief.value = unwrapData(await aiApi.createOpeningBrief({
        work_id: workId.value,
        story_premise: form.storyPremise,
        protagonist_desire: form.protagonistDesire,
        third_chapter_expectation: form.thirdChapterExpectation,
        idempotency_key: key('opening-brief')
      }))
      return brief.value
    } catch (error) {
      actionError.value = String(error?.userMessage || '故事信息没有保存成功，请重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const generateDirections = async () => {
    if (!brief.value?.brief_id) throw new Error('opening_brief_missing')
    loading.value = true
    actionError.value = ''
    try {
      directionBatch.value = unwrapData(await aiApi.generateOpeningDirections(brief.value.brief_id, {
        idempotency_key: key('opening-directions')
      }))
      return directionBatch.value
    } catch (error) {
      actionError.value = String(error?.userMessage || '开篇方向没有生成成功，请重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const addReferences = async (references, rightsConfirmed) => {
    if (!brief.value?.brief_id) throw new Error('opening_brief_missing')
    if (!Array.isArray(references) || references.length === 0) return null
    loading.value = true
    actionError.value = ''
    try {
      return unwrapData(await aiApi.addOpeningReferences(brief.value.brief_id, {
        references: references.map((item) => ({ title: item.title, chapters_text: item.chaptersText })),
        rights_confirmed: Boolean(rightsConfirmed),
        rights_text_version: 'opening-reference-rights-v1',
        idempotency_key: key('opening-references')
      }))
    } catch (error) {
      actionError.value = String(error?.userMessage || '灵感参考没有分析成功，请检查内容后重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const confirmDirection = async (directionId) => {
    loading.value = true
    actionError.value = ''
    try {
      selectedDirection.value = unwrapData(await aiApi.confirmOpeningDirection(directionId, {
        caller_type: 'user_action', user_action: true, user_id: 'ui-user',
        idempotency_key: key('opening-confirm-direction')
      }))
      return selectedDirection.value
    } catch (error) {
      actionError.value = String(error?.userMessage || '开篇方向没有确认成功，请重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const reviseDirection = async (directionId, form) => {
    loading.value = true
    actionError.value = ''
    try {
      const revised = unwrapData(await aiApi.reviseOpeningDirection(directionId, {
        name: form.name,
        summary: form.summary,
        chapter_goals: form.chapterGoals,
        advantages: form.advantages || [],
        risks: form.risks || [],
        idempotency_key: key('opening-revise-direction')
      }))
      if (directionBatch.value) {
        directionBatch.value = {
          ...directionBatch.value,
          directions: [...(directionBatch.value.directions || []).filter((item) => item.direction_id !== revised.direction_id), revised]
        }
      }
      selectedDirection.value = null
      return revised
    } catch (error) {
      actionError.value = String(error?.userMessage || '方向没有保存成功，请重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const generateDrafts = async () => {
    if (!selectedDirection.value?.direction_id) throw new Error('opening_direction_missing')
    loading.value = true
    actionError.value = ''
    try {
      draftBatch.value = unwrapData(await aiApi.generateOpeningDrafts(selectedDirection.value.direction_id, {
        idempotency_key: key('opening-drafts')
      }))
      return draftBatch.value
    } catch (error) {
      actionError.value = String(error?.userMessage || '候选稿没有生成成功，请重试。')
      throw error
    } finally {
      loading.value = false
    }
  }

  const loadOpeningSnapshot = async (targetWorkId = workId.value) => {
    if (!featureEnabled.value || !targetWorkId) return false
    try {
      let payload
      if (typeof aiApi.getLatestOpening === 'function') {
        payload = unwrapData(await aiApi.getLatestOpening(targetWorkId))
      } else {
        const analysisPayload = unwrapData(await aiApi.getOpeningAnalysis(targetWorkId))
        const statusPayload = unwrapData(await aiApi.getOpeningStatus(targetWorkId))
        previewAnalysis.value = analysisPayload.analysis || previewAnalysis.value
        previewStrategy.value = analysisPayload.strategy || previewStrategy.value
        previewRiskLevel.value = analysisPayload.risk_report?.risk_level || previewRiskLevel.value
        payload = {
          draft_batch: {
            ...statusPayload,
            chapter_results: (statusPayload.candidate_draft_ids || []).map((candidate_draft_id, index) => ({
              chapter_no: index + 1, status: 'waiting_review', candidate_draft_id
            }))
          }
        }
      }
      brief.value = payload.brief || brief.value
      directionBatch.value = payload.direction_batch || directionBatch.value
      draftBatch.value = payload.draft_batch || draftBatch.value
      const confirmedId = directionBatch.value?.confirmed_direction_id
      selectedDirection.value = (directionBatch.value?.directions || []).find((item) => item.direction_id === confirmedId) || selectedDirection.value
      snapshotLoaded.value = true
      snapshotLoadFailed.value = false
      lastSnapshotOutcome.value = 'succeeded'
      lastSnapshotAt.value = new Date().toISOString()
      return true
    } catch {
      snapshotLoaded.value = false
      snapshotLoadFailed.value = true
      lastSnapshotOutcome.value = 'failed'
      lastSnapshotAt.value = new Date().toISOString()
      return false
    }
  }

  const loadPreview = ({ analysis: nextAnalysis, strategy: nextStrategy, riskLevel: nextRisk } = {}) => {
    if (nextAnalysis) previewAnalysis.value = { ...(previewAnalysis.value || {}), ...nextAnalysis }
    if (nextStrategy) previewStrategy.value = { ...(previewStrategy.value || {}), ...nextStrategy }
    if (nextRisk) previewRiskLevel.value = String(nextRisk).toLowerCase()
  }

  const loadSnapshot = (payload = {}) => {
    loadPreview({ analysis: payload.analysis, strategy: payload.strategy, riskLevel: payload.risk_report?.risk_level })
    if (payload.phase || payload.status || payload.candidate_draft_ids) {
      draftBatch.value = {
        ...(draftBatch.value || {}), phase: payload.phase, status: payload.status,
        chapter_results: (payload.candidate_draft_ids || []).map((candidate_draft_id, index) => ({ chapter_no: index + 1, status: 'waiting_review', candidate_draft_id }))
      }
    }
  }

  return {
    workId, brief, directionBatch, selectedDirection, draftBatch, loading, actionError,
    featureEnabled, analysis, strategy, riskLevel, phase, status, candidateDraftIds,
    snapshotLoaded, snapshotLoadFailed, lastSnapshotOutcome, lastSnapshotAt,
    initializeForWork, createBrief, addReferences, generateDirections, reviseDirection, confirmDirection, generateDrafts,
    loadOpeningSnapshot, loadPreview, loadSnapshot, hydratePreview: loadPreview, resetPreview: reset
  }
})
