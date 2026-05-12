import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getAISettings = vi.fn()
const updateAISettings = vi.fn()
const testProvider = vi.fn()
const startInitialization = vi.fn()
const getAIJob = vi.fn()
const getLatestInitialization = vi.fn()
const buildContextPack = vi.fn()
const getContextPackReadiness = vi.fn()
const startContinuation = vi.fn()
const listCandidateDrafts = vi.fn()
const getCandidateDraft = vi.fn()
const acceptCandidateDraft = vi.fn()
const rejectCandidateDraft = vi.fn()
const applyCandidateDraft = vi.fn()
const runQuickTrial = vi.fn()
const reviewCandidateDraft = vi.fn()
const getAIReview = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    getAISettings,
    updateAISettings,
    testProvider,
    startInitialization,
    getAIJob,
    getLatestInitialization,
    buildContextPack,
    getContextPackReadiness,
    startContinuation,
    listCandidateDrafts,
    getCandidateDraft,
    acceptCandidateDraft,
    rejectCandidateDraft,
    applyCandidateDraft,
    runQuickTrial,
    reviewCandidateDraft,
    getAIReview
  }
}))

describe('AIPanel', () => {
  let AIPanel

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    AIPanel = (await import('../AIPanel.vue')).default

    getAISettings.mockResolvedValue({
      data: {
        provider_configs: [{ provider_name: 'fake', enabled: true, default_model: 'fake-chat' }],
        model_role_mappings: { writer: { provider_name: 'fake', model_name: 'fake-chat' } }
      }
    })
    getLatestInitialization.mockResolvedValue({ data: { status: 'completed', analyzed_chapter_count: 1, empty_chapter_count: 0, failed_chapter_count: 0 } })
    getContextPackReadiness.mockResolvedValue({ data: { status: 'ready', blocked_reason: '', degraded_reason: '', warnings: [] } })
    listCandidateDrafts.mockResolvedValue({ data: { items: [{ candidate_draft_id: 'cd_1', content_preview: '预览', validation_status: 'passed', source_context_pack_id: 'cp_1' }] } })
    getAIReview.mockResolvedValue({ data: { review_id: 'rv_1', summary: '审阅完成', issues: [], suggestions: [], risk_level: 'low' } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads ai settings without exposing plaintext api key and supports provider test', async () => {
    testProvider.mockResolvedValue({ data: { test_status: 'ok', message: 'ok' } })
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })

    await vi.runAllTimersAsync()
    expect(wrapper.text()).toContain('AI 设置')
    expect(wrapper.text()).not.toContain('fake-api-key')

    await wrapper.get('[data-test="ai-test-provider"]').trigger('click')
    expect(testProvider).toHaveBeenCalled()
  })

  it('polls job status and stops after terminal state', async () => {
    startInitialization.mockResolvedValue({ data: { initialization_id: 'init_1', job_id: 'job_1' } })
    getAIJob
      .mockResolvedValueOnce({ data: { job_id: 'job_1', status: 'running', steps: [] } })
      .mockResolvedValueOnce({ data: { job_id: 'job_1', status: 'completed', steps: [] } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })
    await vi.runAllTimersAsync()

    await wrapper.get('[data-test="ai-start-initialization"]').trigger('click')
    await vi.advanceTimersByTimeAsync(1200)
    await vi.advanceTimersByTimeAsync(1200)

    expect(getAIJob).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('completed')
  })

  it('lists candidate previews, loads detail on demand, and apply requires expected chapter version', async () => {
    startContinuation.mockResolvedValue({ data: { job_id: 'job_2', candidate_draft_id: 'cd_1', status: 'completed_with_candidate' } })
    getCandidateDraft.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', content: '完整候选稿内容', validation_status: 'passed' } })
    applyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5 }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('预览')
    expect(wrapper.text()).not.toContain('完整候选稿内容')

    await wrapper.get('[data-test="ai-start-continuation"]').trigger('click')
    await wrapper.get('[data-test="candidate-detail-cd_1"]').trigger('click')
    expect(getCandidateDraft).toHaveBeenCalledWith('cd_1')

    await wrapper.get('[data-test="candidate-apply-cd_1"]').trigger('click')
    expect(applyCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({ expected_chapter_version: 5 }))
  })

  it('runs quick trial and ai review without auto creating side effects in ui flow', async () => {
    runQuickTrial.mockResolvedValue({ data: { status: 'succeeded', output_text: '试跑输出', validation_status: 'passed' } })
    reviewCandidateDraft.mockResolvedValue({ data: { review_id: 'rv_1', status: 'succeeded', summary: '审阅完成' } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })
    await vi.runAllTimersAsync()

    await wrapper.get('[data-test="quick-trial-run"]').trigger('click')
    expect(runQuickTrial).toHaveBeenCalled()
    expect(wrapper.text()).toContain('试跑输出')

    await wrapper.get('[data-test="candidate-review-cd_1"]').trigger('click')
    expect(reviewCandidateDraft).toHaveBeenCalledWith('cd_1', { user_instruction: '' })
  })
})
