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
})
