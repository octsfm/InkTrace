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
    await api.aiApi.getLatestInitialization('work-1')
    await api.aiApi.buildContextPack({ work_id: 'work-1', chapter_id: 'chapter-1' })
    await api.aiApi.getLatestContextPack('work-1', 'chapter-1')
    await api.aiApi.getContextPackReadiness('work-1', 'chapter-1')
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

    expect(mockGet).toHaveBeenCalledWith('/v2/ai/settings')
    expect(mockPut).toHaveBeenCalledWith('/v2/ai/settings', { provider_configs: [], model_role_mappings: {} })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/settings/providers/fake/test', { model_name: 'fake-chat' })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/initializations', { work_id: 'work-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/jobs/job-1')
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/jobs', { params: { work_id: 'work-1', status: 'running' } })
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/jobs/job-1/cancel', { reason: 'user_cancelled' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/works/work-1/initialization/latest')
    expect(mockPost).toHaveBeenCalledWith('/v2/ai/context-packs', { work_id: 'work-1', chapter_id: 'chapter-1' })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/context-packs/works/work-1/latest', { params: { chapter_id: 'chapter-1' } })
    expect(mockGet).toHaveBeenCalledWith('/v2/ai/context-packs/works/work-1/readiness', { params: { chapter_id: 'chapter-1' } })
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
  })
})
