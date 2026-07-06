import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockPut = vi.fn()
const mockDelete = vi.fn()
const responseUse = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: responseUse }
      }
    }))
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn() }
}))

describe('P0 AI API client', () => {
  let api

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()
    api = await import('../index.js')
  })

  it('wraps all P0 AI endpoints with expected request paths', async () => {
    mockGet.mockResolvedValue({})
    mockPost.mockResolvedValue({})
    mockPut.mockResolvedValue({})

    await api.aiApi.getAISettings()
    await api.aiApi.updateAISettings({ provider_configs: [], model_role_mappings: {} })
    await api.aiApi.testProvider('fake', { model_name: 'fake-chat' })
    await api.aiApi.startInitialization({ work_id: 'work-1' })
    await api.aiApi.getAIJob('job-1')
    await api.aiApi.listAIJobs({ work_id: 'work-1', status: 'running' })
    await api.aiApi.cancelAIJob('job-1', { reason: 'user_cancelled' })
    await api.aiApi.startVectorIndexReindex({
      work_id: 'work-1',
      index_scope: 'full_work',
      caller_type: 'user_action',
      idempotency_key: 'idem-reindex-1'
    })
    await api.aiApi.startStyleDNAExtract({
      work_id: 'work-1',
      source_text: '这是标杆文本',
      source_type: 'user_upload',
      caller_type: 'user_action',
      idempotency_key: 'idem-style-1'
    })
    await api.aiApi.importOpeningReference({
      work_id: 'work-1',
      title: '标杆开篇',
      chapters_text: ['第一章文本'],
      rights_confirmed: true,
      rights_confirmation_text_version: 'v1'
    })
    await api.aiApi.analyzeOpening({
      work_id: 'work-1',
      analysis_id: 'oa-1',
      job_id: 'job-opening-1'
    })
    await api.aiApi.getOpeningStrategy('work-1')
    await api.aiApi.confirmOpeningStrategy('st-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'opening-confirm-1'
    })
    await api.aiApi.rejectOpeningStrategy('st-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'opening-reject-1',
      reason: '请降低相似度'
    })
    await api.aiApi.generateOpeningDrafts({
      work_id: 'work-1',
      analysis_id: 'oa-1',
      strategy_id: 'st-1',
      job_id: 'job-opening-1'
    })
    await api.aiApi.getOpeningStatus('work-1')
    await api.aiApi.getOpeningAnalysis('work-1')
    await api.aiApi.getOpeningDrafts('work-1')
    await api.aiApi.getStyleProfile('sp-1')
    await api.aiApi.getActiveStyleProfile('work-1')
    await api.aiApi.getStyleProfileHistory('work-1')
    await api.aiApi.confirmStyleProfile('sp-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'style-confirm-1'
    })
    await api.aiApi.disableStyleProfile('sp-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'style-disable-1'
    })
    await api.aiApi.deleteStyleProfile('sp-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'style-delete-1'
    })
    await api.aiApi.upsertAutoQueueConfig({
      work_id: 'work-1',
      queue_mode: 'safe',
      target_chapters: 5
    })
    await api.aiApi.getAutoQueueConfig('work-1')
    await api.aiApi.startAutoQueue({
      work_id: 'work-1',
      start_chapter_id: 'chapter-1'
    })
    await api.aiApi.getAutoQueueStatus('aqr-1')
    await api.aiApi.pauseAutoQueue('aqr-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-pause-1'
    })
    await api.aiApi.resumeAutoQueue('aqr-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-resume-1'
    })
    await api.aiApi.stopAutoQueue('aqr-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-stop-1'
    })
    await api.aiApi.confirmAutoQueueContinue('aqr-1', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-confirm-1'
    })
    await api.aiApi.getAutoQueueHistory('work-1')
    await api.aiApi.getLatestInitialization('work-1')
    await api.aiApi.buildContextPack({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.getLatestContextPack('work-1', 'chapter-1')
    await api.aiApi.getContextPackReadiness('work-1', 'chapter-1')
    await api.aiApi.listAgentSessions({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.getAgentSession('session-1')
    await api.aiApi.pauseAgentSession('session-1', { caller_type: 'user_action', user_action: true, idempotency_key: 'pause-1' })
    await api.aiApi.resumeAgentSession('session-1', { caller_type: 'user_action', user_action: true, idempotency_key: 'resume-1' })
    await api.aiApi.cancelAgentSession('session-1', { caller_type: 'user_action', user_action: true, idempotency_key: 'cancel-1' })
    await api.aiApi.listPlotArcs({ work_id: 'work-1' })
    await api.aiApi.getPlotArc('arc-1')
    await api.aiApi.getPlotArcStatus({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.startContinuation({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.listCandidateDrafts({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.getCandidateDraft('cd-1')
    await api.aiApi.acceptCandidateDraft('cd-1', { user_action: true, user_id: 'u1' })
    await api.aiApi.rejectCandidateDraft('cd-1', { user_action: true, user_id: 'u1', reason: 'bad' })
    await api.aiApi.applyCandidateDraft('cd-1', { user_action: true, user_id: 'u1', expected_chapter_version: 3 })
    await api.aiApi.runQuickTrial({ model_role: 'quick_trial_writer', input_text: '试试' })
    await api.aiApi.reviewCandidateDraft('cd-1', { user_instruction: '关注逻辑' })
    await api.aiApi.getAIReview('rv-1')
    await api.aiApi.listAIReviews({ work_id: 'work-1', candidate_draft_id: 'cd-1' })
    await api.aiApi.listAgentTraces({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.getAgentTrace('trace-1')
    await api.aiApi.getAgentTraceSteps('trace-1')
    await api.aiApi.getAgentTraceDetailView('trace-1', { detail: true, developer_mode: true })

    expect(mockGet).toHaveBeenCalledWith('/v2/ai/settings')
    expect(mockPut).toHaveBeenCalledWith('/v2/ai/settings', { provider_configs: [], model_role_mappings: {} })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/settings/providers/fake/test', { model_name: 'fake-chat' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/initializations', { work_id: 'work-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/jobs/job-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/jobs', { params: { work_id: 'work-1', status: 'running' } })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/jobs/job-1/cancel', { reason: 'user_cancelled' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/vector-index/reindex', {
      work_id: 'work-1',
      index_scope: 'full_work',
      caller_type: 'user_action',
      idempotency_key: 'idem-reindex-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/style-dna/extract', {
      work_id: 'work-1',
      source_text: '这是标杆文本',
      source_type: 'user_upload',
      caller_type: 'user_action',
      idempotency_key: 'idem-style-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/opening/import-reference', {
      work_id: 'work-1',
      title: '标杆开篇',
      chapters_text: ['第一章文本'],
      rights_confirmed: true,
      rights_confirmation_text_version: 'v1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/opening/analyze', {
      work_id: 'work-1',
      analysis_id: 'oa-1',
      job_id: 'job-opening-1'
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/opening/work-1/strategy')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/opening/strategies/st-1/confirm', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'opening-confirm-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/opening/strategies/st-1/reject', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'opening-reject-1',
      reason: '请降低相似度'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/opening/generate', {
      work_id: 'work-1',
      analysis_id: 'oa-1',
      strategy_id: 'st-1',
      job_id: 'job-opening-1'
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/opening/work-1/status')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/opening/work-1/analysis')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/opening/work-1/drafts')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/style-dna/profiles/sp-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/style-dna/work-1/active')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/style-dna/work-1/history')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/style-dna/profiles/sp-1/confirm', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'style-confirm-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/style-dna/profiles/sp-1/disable', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'style-disable-1'
    })
    expect(mockDelete).toHaveBeenCalledWith('/v2/ai/style-dna/profiles/sp-1', {
      data: {
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: 'style-delete-1'
      }
    })
    expect(mockPut).toHaveBeenCalledWith('/v2/ai/auto-queues/config', {
      work_id: 'work-1',
      queue_mode: 'safe',
      target_chapters: 5
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/auto-queues/config/work-1')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/auto-queues/start', {
      work_id: 'work-1',
      start_chapter_id: 'chapter-1'
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/auto-queues/aqr-1/status')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/auto-queues/aqr-1/pause', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-pause-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/auto-queues/aqr-1/resume', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-resume-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/auto-queues/aqr-1/stop', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-stop-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/auto-queues/aqr-1/confirm-continue', {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'aq-confirm-1'
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/auto-queues/work-1/history')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/works/work-1/initialization/latest')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/context-packs', { work_id: 'work-1', chapter_id: 'chapter-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/context-packs/works/work-1/latest', { params: { chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/context-packs/works/work-1/readiness', { params: { chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/sessions', { params: { work_id: 'work-1', chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/sessions/session-1')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/sessions/session-1/pause', { caller_type: 'user_action', user_action: true, idempotency_key: 'pause-1' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/sessions/session-1/resume', { caller_type: 'user_action', user_action: true, idempotency_key: 'resume-1' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/sessions/session-1/cancel', { caller_type: 'user_action', user_action: true, idempotency_key: 'cancel-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/plot-arcs', { params: { work_id: 'work-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/plot-arcs/arc-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/plot-arcs/status', { params: { work_id: 'work-1', chapter_id: 'chapter-1' } })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/continuations', { work_id: 'work-1', chapter_id: 'chapter-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/candidate-drafts', { params: { work_id: 'work-1', chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/candidate-drafts/cd-1')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/candidate-drafts/cd-1/accept', { user_action: true, user_id: 'u1' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/candidate-drafts/cd-1/reject', { user_action: true, user_id: 'u1', reason: 'bad' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/candidate-drafts/cd-1/apply', { user_action: true, user_id: 'u1', expected_chapter_version: 3 })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/quick-trials', { model_role: 'quick_trial_writer', input_text: '试试' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/reviews/candidate-drafts/cd-1', { user_instruction: '关注逻辑' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/reviews/rv-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/reviews', { params: { work_id: 'work-1', candidate_draft_id: 'cd-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/traces', { params: { work_id: 'work-1', chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/traces/trace-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/traces/trace-1/steps')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/traces/trace-1/detail-view', { params: { detail: true, developer_mode: true } })
  })

  it('uses v2 safe_message for conflict responses without triggering global toast', async () => {
    const { ElMessage } = await import('element-plus')
    const errorHandler = responseUse.mock.calls[0][1]
    const error = {
      message: 'Request failed with status code 409',
      response: {
        status: 409,
        data: {
          status: 'error',
          error: {
            error_code: 'P2_VECTOR_INDEXING_IN_PROGRESS',
            safe_message: '这个作品已有索引任务正在运行，请等待完成后再试。',
            retryable: true
          }
        },
        headers: {
          'x-request-id': 'req_conflict_1'
        }
      },
      config: {
        metadata: {
          requestId: 'req_conflict_1'
        }
      }
    }

    await expect(errorHandler(error)).rejects.toMatchObject({
      userMessage: '这个作品已有索引任务正在运行，请等待完成后再试。'
    })
    expect(ElMessage.error).not.toHaveBeenCalled()
  })

  it('uses v2 safe_message for service unavailable responses', async () => {
    const { ElMessage } = await import('element-plus')
    const errorHandler = responseUse.mock.calls[0][1]
    const error = {
      message: 'Request failed with status code 503',
      response: {
        status: 503,
        data: {
          status: 'error',
          error: {
            error_code: 'P2_VECTOR_EMBEDDING_UNAVAILABLE',
            safe_message: 'AI 嵌入服务暂时不可用，请稍后重试或检查 AI 设置。',
            retryable: true
          }
        },
        headers: {
          'x-request-id': 'req_service_unavailable_1'
        }
      },
      config: {
        metadata: {
          requestId: 'req_service_unavailable_1'
        }
      }
    }

    await expect(errorHandler(error)).rejects.toBe(error)
    expect(ElMessage.error).toHaveBeenCalledWith('AI 嵌入服务暂时不可用，请稍后重试或检查 AI 设置。')
  })

  it('maps P2 feature disabled errors to a unified chinese message', async () => {
    const { ElMessage } = await import('element-plus')
    const errorHandler = responseUse.mock.calls[0][1]
    const error = {
      message: 'Request failed with status code 403',
      response: {
        status: 403,
        data: {
          status: 'error',
          error: {
            error_code: 'P2_FEATURE_DISABLED',
            message: 'feature disabled'
          }
        },
        headers: {
          'x-request-id': 'req_feature_disabled_1'
        }
      },
      config: {
        metadata: {
          requestId: 'req_feature_disabled_1'
        }
      }
    }

    await expect(errorHandler(error)).rejects.toBe(error)
    expect(ElMessage.error).toHaveBeenCalledWith('这个功能暂未开启')
  })

  it('wraps selection rewrite endpoints with expected request paths', async () => {
    mockGet.mockResolvedValue({})
    mockPost.mockResolvedValue({})
    mockDelete.mockResolvedValue({})

    await api.aiApi.createSelectionRewrite({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      chapter_revision: 7,
      draft_revision: 12,
      source_text: '月光落在窗台上',
      source_hash: 'sha256-source',
      start_pos: 4,
      end_pos: 12,
      context_before: '前文片段',
      context_after: '后文片段',
      mode: 'polish'
    })
    await api.aiApi.getSelectionRewrite('srw_001')
    await api.aiApi.listSelectionRewriteHistory('chapter-1')
    await api.aiApi.applySelectionRewrite('srw_001', {
      final_text: '月光静静落在旧窗台上',
      chapter_revision: 7,
      draft_revision: 12,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'selection-apply-1'
    })
    await api.aiApi.rejectSelectionRewrite('srw_001')
    await api.aiApi.clearSelectionRewriteHistory('chapter-1')

    expect(mockPost).toHaveBeenCalledWith('/v2/ai/selection-rewrite', {
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      chapter_revision: 7,
      draft_revision: 12,
      source_text: '月光落在窗台上',
      source_hash: 'sha256-source',
      start_pos: 4,
      end_pos: 12,
      context_before: '前文片段',
      context_after: '后文片段',
      mode: 'polish'
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/selection-rewrite/srw_001')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/selection-rewrite/chapters/chapter-1/history')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/selection-rewrite/srw_001/apply', {
      final_text: '月光静静落在旧窗台上',
      chapter_revision: 7,
      draft_revision: 12,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: 'selection-apply-1'
    })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/selection-rewrite/srw_001/reject')
    expect(mockDelete).toHaveBeenCalledWith('/v2/ai/selection-rewrite/chapters/chapter-1/history')
  })

  it('wraps mention endpoints with expected request paths', async () => {
    mockGet.mockResolvedValue({})
    mockPut.mockResolvedValue({})

    await api.aiApi.suggestMentions({
      work_id: 'work-1',
      q: '张',
      types: 'character,event',
      limit: 10
    })
    await api.aiApi.getChapterMentions('chapter-1')
    await api.aiApi.replaceChapterMentions('chapter-1', {
      chapter_revision: 3,
      mentions: [{
        mention_id: 'm_001',
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name_snapshot: '张三',
        start_pos: 2,
        end_pos: 5,
        source: 'user_input',
        ai_suggestion_id: ''
      }]
    })
    await api.aiApi.getMentionSummary('m_001')

    expect(mockGet).toHaveBeenCalledWith('/v2/mentions/suggest', {
      params: {
        work_id: 'work-1',
        q: '张',
        types: 'character,event',
        limit: 10
      }
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/chapters/chapter-1/mentions')
    expect(mockPut).toHaveBeenCalledWith('/v2/chapters/chapter-1/mentions', {
      chapter_revision: 3,
      mentions: [{
        mention_id: 'm_001',
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name_snapshot: '张三',
        start_pos: 2,
        end_pos: 5,
        source: 'user_input',
        ai_suggestion_id: ''
      }]
    })
    expect(mockGet).toHaveBeenCalledWith('/v2/mentions/m_001/summary')
  })
})
