import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const startContinuation = vi.fn()
const listCandidateDrafts = vi.fn()
const getCandidateDraft = vi.fn()
const listCandidateDraftVersions = vi.fn()
const getCandidateDraftVersion = vi.fn()
const getCandidateDraftVersionDiff = vi.fn()
const selectCandidateDraftVersion = vi.fn()
const acceptCandidateDraft = vi.fn()
const rejectCandidateDraft = vi.fn()
const applyCandidateDraft = vi.fn()
const reviewCandidateDraft = vi.fn()
const rewriteCandidateDraft = vi.fn()
const rejectCandidateDraftVersion = vi.fn()
const listAISuggestions = vi.fn()
const getAISuggestion = vi.fn()
const acceptAISuggestion = vi.fn()
const dismissAISuggestion = vi.fn()
const convertAISuggestion = vi.fn()
const listConflicts = vi.fn()
const getConflict = vi.fn()
const decideConflict = vi.fn()
const listMemoryGates = vi.fn()
const getMemoryRevision = vi.fn()
const approveMemorySuggestion = vi.fn()
const editApproveMemorySuggestion = vi.fn()
const rejectMemorySuggestion = vi.fn()
const deferMemorySuggestion = vi.fn()
const applyMemoryGate = vi.fn()
const rollbackMemoryRevision = vi.fn()
const listAgentTraces = vi.fn()
const getAgentTrace = vi.fn()
const getAgentTraceSteps = vi.fn()
const getAgentTraceDetailView = vi.fn()

const getAISettings = vi.fn()
const getLatestInitialization = vi.fn()
const getContextPackReadiness = vi.fn()
const listAgentSessions = vi.fn()
const listPlotArcs = vi.fn()
const getPlotArcStatus = vi.fn()
const getAIReview = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    startContinuation,
    listCandidateDrafts,
    getCandidateDraft,
    listCandidateDraftVersions,
    getCandidateDraftVersion,
    getCandidateDraftVersionDiff,
    selectCandidateDraftVersion,
    acceptCandidateDraft,
    rejectCandidateDraft,
    applyCandidateDraft,
    reviewCandidateDraft,
    rewriteCandidateDraft,
    rejectCandidateDraftVersion,
    listAISuggestions,
    getAISuggestion,
    acceptAISuggestion,
    dismissAISuggestion,
    convertAISuggestion,
    listConflicts,
    getConflict,
    decideConflict,
    listMemoryGates,
    getMemoryRevision,
    approveMemorySuggestion,
    editApproveMemorySuggestion,
    rejectMemorySuggestion,
    deferMemorySuggestion,
    applyMemoryGate,
    rollbackMemoryRevision,
    listAgentTraces,
    getAgentTrace,
    getAgentTraceSteps,
    getAgentTraceDetailView,
    getAIReview,

    getAISettings,
    getLatestInitialization,
    getContextPackReadiness,
    listAgentSessions,
    listPlotArcs,
    getPlotArcStatus
  }
}))

describe('ReviewTab', () => {
  let ReviewTab

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(window, 'prompt').mockReturnValue('已人工修改的记忆摘要')

    ReviewTab = (await import('../ReviewTab.vue')).default

    listCandidateDrafts.mockResolvedValue({
      data: {
        items: [{
          candidate_draft_id: 'cd_1',
          content_preview: '候选稿预览',
          validation_status: 'passed',
          selected_version_id: 'ver_1',
          accepted_version_id: '',
          applied_version_id: ''
        }]
      }
    })
    getCandidateDraft.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        content: '完整候选稿',
        selected_version_id: 'ver_1',
        accepted_version_id: 'ver_1',
        applied_version_id: ''
      }
    })
    listCandidateDraftVersions.mockResolvedValue({
      data: {
        items: [
          { candidate_version_id: 'ver_1', version_no: 1, status: 'review_completed', content_summary: '初稿' },
          { candidate_version_id: 'ver_2', version_no: 2, status: 'generated', content_summary: '修订稿' }
        ]
      }
    })
    getCandidateDraftVersion.mockResolvedValue({
      data: {
        candidate_version_id: 'ver_2',
        content: '修订稿完整内容',
        content_summary: '修订稿',
        status: 'generated'
      }
    })
    getCandidateDraftVersionDiff.mockResolvedValue({
      data: {
        summary: '新增地图线索',
        diff_preview: ['+ 地图线索']
      }
    })
    startContinuation.mockResolvedValue({ data: { candidate_draft_id: 'cd_2', status: 'completed_with_candidate' } })
    acceptCandidateDraft.mockResolvedValue({ data: { status: 'accepted' } })
    rejectCandidateDraft.mockResolvedValue({ data: { status: 'rejected' } })
    applyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })
    reviewCandidateDraft.mockResolvedValue({ data: { review_id: 'rv_1', summary: '审阅完成' } })
    getAIReview.mockResolvedValue({ data: { review_id: 'rv_1', summary: '审阅完成' } })
    rewriteCandidateDraft.mockResolvedValue({ data: { target_version: { candidate_version_id: 'ver_3' } } })
    rejectCandidateDraftVersion.mockResolvedValue({ data: { status: 'rejected' } })
    selectCandidateDraftVersion.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        selected_version_id: 'ver_2',
        accepted_version_id: 'ver_1',
        applied_version_id: ''
      }
    })

    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'ais_1',
          suggestion_type: 'rewrite_suggestion',
          severity: 'high',
          title: '强化线索',
          summary: '建议提前铺垫地图',
          status: 'shown'
        }]
      }
    })
    getAISuggestion.mockResolvedValue({ data: { suggestion_id: 'ais_1', summary: '详细建议说明' } })
    acceptAISuggestion.mockResolvedValue({ data: { status: 'accepted' } })
    dismissAISuggestion.mockResolvedValue({ data: { status: 'dismissed' } })
    convertAISuggestion.mockResolvedValue({ data: { status: 'converted', action: { action_payload_ref: '' } } })

    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cgr_1',
          candidate_draft_id: 'cd_1',
          candidate_version_id: 'ver_1',
          conflict_type: 'candidate_version_conflict',
          severity: 'warning',
          title: '上下文存在风险',
          summary: '当前版本存在上下文降级风险'
        }]
      }
    })
    getConflict.mockResolvedValue({ data: { record_id: 'cgr_1', summary: '冲突详情摘要' } })
    decideConflict.mockResolvedValue({ data: { status: 'acknowledged' } })

    listMemoryGates.mockResolvedValue({
      data: {
        items: [{
          gate_id: 'mg_1',
          state: 'waiting_for_user',
          suggestions: [{
            id: 'mus_1',
            target_memory_type: 'character',
            revision_type: 'character_update',
            status: 'shown',
            current_value_summary: '旧设定',
            proposed_value_summary: '新设定'
          }],
          revision_ids: ['mr_1']
        }]
      }
    })
    approveMemorySuggestion.mockResolvedValue({ data: { status: 'approved' } })
    editApproveMemorySuggestion.mockResolvedValue({ data: { status: 'approved' } })
    rejectMemorySuggestion.mockResolvedValue({ data: { status: 'rejected' } })
    deferMemorySuggestion.mockResolvedValue({ data: { status: 'shown' } })
    applyMemoryGate.mockResolvedValue({ data: { revision_ids: ['mr_1'] } })
    getMemoryRevision.mockResolvedValue({ data: { revision_id: 'mr_1', status: 'applied' } })
    rollbackMemoryRevision.mockResolvedValue({ data: { revision_id: 'mr_1', status: 'superseded' } })

    listAgentTraces.mockResolvedValue({
      data: {
        items: [{
          trace_id: 'trace_1',
          status: 'waiting_for_user',
          workflow_type: 'continuation',
          total_steps: 4,
          total_tokens: 1200
        }]
      }
    })
    getAgentTrace.mockResolvedValue({ data: { trace_id: 'trace_1', status: 'waiting_for_user' } })
    getAgentTraceSteps.mockResolvedValue({
      data: { items: [{ step_id: 'step_1', agent_type: 'reviewer', action: 'review', status: 'completed' }] }
    })
    getAgentTraceDetailView.mockResolvedValue({
      data: { trace_id: 'trace_1', summary: 'detail', metrics: [{ metric_name: 'tool_call_denied_total', metric_value: 1 }] }
    })
  })

  it('loads only review-domain APIs on mount and does not pull ai-workspace setup data', async () => {
    const wrapper = mount(ReviewTab, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5 }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('候选稿与人工确认门')
    expect(wrapper.text()).toContain('AI 建议')
    expect(wrapper.text()).toContain('记忆审批')
    expect(wrapper.text()).toContain('任务追踪')

    expect(listCandidateDrafts).toHaveBeenCalled()
    expect(listAISuggestions).toHaveBeenCalled()
    expect(listMemoryGates).toHaveBeenCalled()
    expect(listConflicts).toHaveBeenCalled()
    expect(listAgentTraces).toHaveBeenCalled()

    expect(getAISettings).not.toHaveBeenCalled()
    expect(getLatestInitialization).not.toHaveBeenCalled()
    expect(getContextPackReadiness).not.toHaveBeenCalled()
    expect(listAgentSessions).not.toHaveBeenCalled()
    expect(listPlotArcs).not.toHaveBeenCalled()
    expect(getPlotArcStatus).not.toHaveBeenCalled()
  })

  it('supports candidate review actions and apply passes expected chapter version', async () => {
    const wrapper = mount(ReviewTab, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 9 }
    })

    await flushPromises()
    await wrapper.get('[data-test=\"candidate-start-continuation\"]').trigger('click')
    await wrapper.get('[data-test=\"candidate-detail-cd_1\"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test=\"candidate-accept-cd_1\"]').trigger('click')
    expect(acceptCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      candidate_version_id: 'ver_1',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test=\"candidate-version-detail-cd_1-ver_2\"]').trigger('click')
    expect(getCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_2')

    await wrapper.get('[data-test=\"candidate-version-select-cd_1-ver_2\"]').trigger('click')
    expect(selectCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_2', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test=\"candidate-version-diff-cd_1-ver_1-ver_2\"]').trigger('click')
    expect(getCandidateDraftVersionDiff).toHaveBeenCalledWith('cd_1', {
      from_version_id: 'ver_1',
      to_version_id: 'ver_2'
    })

    await wrapper.get('[data-test=\"candidate-version-rewrite-review-cd_1-ver_2\"]').trigger('click')
    expect(rewriteCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      source_version_id: 'ver_2',
      trigger_type: 'review_based'
    }))

    await wrapper.get('[data-test=\"candidate-apply-cd_1\"]').trigger('click')
    expect(applyCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      expected_chapter_version: 9,
      caller_type: 'user_action',
      user_action: true
    }))
  })

  it('supports suggestion, memory gate, and trace actions within review workspace', async () => {
    const wrapper = mount(ReviewTab, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, developerMode: true }
    })

    await flushPromises()

    await wrapper.get('[data-test=\"suggestion-detail-ais_1\"]').trigger('click')
    expect(getAISuggestion).toHaveBeenCalledWith('ais_1')

    await wrapper.get('[data-test=\"suggestion-accept-ais_1\"]').trigger('click')
    expect(acceptAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test=\"suggestion-convert-ais_1\"]').trigger('click')
    expect(convertAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test=\"memory-approve-mg_1-mus_1\"]').trigger('click')
    expect(approveMemorySuggestion).toHaveBeenCalledWith('mg_1', 'mus_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test=\"memory-apply-mg_1\"]').trigger('click')
    expect(applyMemoryGate).toHaveBeenCalledWith('mg_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test=\"trace-steps-trace_1\"]').trigger('click')
    expect(getAgentTraceSteps).toHaveBeenCalledWith('trace_1')

    await wrapper.get('[data-test=\"trace-detail-trace_1\"]').trigger('click')
    expect(getAgentTraceDetailView).toHaveBeenCalledWith('trace_1', {
      detail: true,
      developer_mode: true
    })
  })
})
