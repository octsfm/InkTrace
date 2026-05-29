import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const routerPush = vi.fn()
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
const listAgentSessions = vi.fn()
const getAgentSession = vi.fn()
const pauseAgentSession = vi.fn()
const resumeAgentSession = vi.fn()
const cancelAgentSession = vi.fn()
const generateDirectionProposal = vi.fn()
const listDirectionProposals = vi.fn()
const getDirectionProposal = vi.fn()
const selectDirection = vi.fn()
const generateChapterPlan = vi.fn()
const listChapterPlans = vi.fn()
const getChapterPlan = vi.fn()
const confirmChapterPlan = vi.fn()
const rejectChapterPlan = vi.fn()
const listWritingTasks = vi.fn()
const getWritingTask = vi.fn()
const listCandidateDraftVersions = vi.fn()
const getCandidateDraftVersion = vi.fn()
const getCandidateDraftVersionDiff = vi.fn()
const selectCandidateDraftVersion = vi.fn()
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
const listPlotArcs = vi.fn()
const getPlotArc = vi.fn()
const getPlotArcStatus = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: routerPush
  })
}))

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
    getAIReview,
    listAgentSessions,
    getAgentSession,
    pauseAgentSession,
    resumeAgentSession,
    cancelAgentSession,
    generateDirectionProposal,
    listDirectionProposals,
    getDirectionProposal,
    selectDirection,
    generateChapterPlan,
    listChapterPlans,
    getChapterPlan,
    confirmChapterPlan,
    rejectChapterPlan,
    listWritingTasks,
    getWritingTask,
    listCandidateDraftVersions,
    getCandidateDraftVersion,
    getCandidateDraftVersionDiff,
    selectCandidateDraftVersion,
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
    listPlotArcs,
    getPlotArc,
    getPlotArcStatus
  }
}))

describe('AIPanel', () => {
  let AIPanel

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    AIPanel = (await import('../AIPanel.vue')).default

    getAISettings.mockResolvedValue({
      data: {
        provider_configs: [{
          provider_name: 'fake',
          enabled: true,
          default_model: 'fake-chat',
          key_configured: true,
          api_key_masked: 'fak********90',
          last_test_status: 'not_tested'
        }],
        model_role_mappings: {
          analysis: { provider_name: 'fake', model_name: 'fake-analysis' },
          planning: { provider_name: 'fake', model_name: 'fake-plan' },
          writer: { provider_name: 'fake', model_name: 'fake-chat' },
          reviewer: { provider_name: 'fake', model_name: 'fake-review' },
          rewriter: { provider_name: 'fake', model_name: 'fake-rewrite' }
        }
      }
    })
    getLatestInitialization.mockResolvedValue({ data: { status: 'completed', analyzed_chapter_count: 1, empty_chapter_count: 0, failed_chapter_count: 0 } })
    getContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        blocked_reason: '',
        degraded_reason: 'volume_arc_missing',
        warnings: ['volume_arc_missing'],
        plot_arc_statuses: {
          master_arc: { status: 'ready', quality_level: 'minimal', warning_codes: [] },
          volume_arc: { status: 'pending', quality_level: 'placeholder', warning_codes: ['arc_placeholder_only'] },
          sequence_arc: { status: 'ready', quality_level: 'minimal', warning_codes: [] },
          immediate_window: { status: 'ready', quality_level: 'complete', warning_codes: [] }
        },
        plot_arc_summary: {
          master_arc: { arc_title: '灯塔迷局', current_stage: '追查旧地图', ultimate_goal: '揭开海雾秘密' },
          volume_arc: { stage_goal: '确认灯塔背后的势力', stage_open_loops: ['地图来源'] },
          sequence_arc: { sequence_goal: '完成第一轮追索', key_events: ['发现旧地图'] },
          immediate_window: { active_plot_threads: ['灯塔谜团'], recent_chapters_summary: ['顾迟进入灯塔'] }
        }
      }
    })
    listCandidateDrafts.mockResolvedValue({ data: { items: [{ candidate_draft_id: 'cd_1', content_preview: '预览', validation_status: 'passed', source_context_pack_id: 'cp_1', selected_version_id: 'ver_1', accepted_version_id: '', applied_version_id: '' }] } })
    listCandidateDraftVersions.mockResolvedValue({
      data: {
        items: [
          { candidate_version_id: 'ver_1', version_no: 1, status: 'review_completed', content_summary: 'v1 摘要', content: 'v1 内容' },
          { candidate_version_id: 'ver_2', version_no: 2, status: 'generated', content_summary: 'v2 摘要', content: 'v2 内容' }
        ]
      }
    })
    getCandidateDraftVersion.mockResolvedValue({ data: { candidate_version_id: 'ver_2', content: 'v2 修订稿完整内容', content_summary: 'v2 摘要', status: 'generated' } })
    getCandidateDraftVersionDiff.mockResolvedValue({ data: { from_version_id: 'ver_1', to_version_id: 'ver_2', summary: '新增父亲留下的地图线索。', diff_preview: ['+ 父亲留下地图'] } })
    getAIReview.mockResolvedValue({ data: { review_id: 'rv_1', summary: '审阅完成', issues: [], suggestions: [], risk_level: 'low' } })
    listAgentSessions.mockResolvedValue({
      data: {
        items: [{
          session_id: 'session_1',
          status: 'running',
          workflow_type: 'continuation',
          current_stage: 'candidate_generation',
          current_agent_type: 'writer',
          progress_percent: 48,
          polling_hint: { next_interval_ms: 2500, stop: false }
        }]
      }
    })
    getAgentSession.mockResolvedValue({
      data: {
        session_id: 'session_1',
        status: 'waiting_for_user',
        workflow_type: 'continuation',
        current_stage: 'human_review_gate',
        current_agent_type: 'reviewer',
        progress_percent: 72,
        polling_hint: { next_interval_ms: 5000, stop: true }
      }
    })
    pauseAgentSession.mockResolvedValue({ data: { session_id: 'session_1', status: 'paused' } })
    resumeAgentSession.mockResolvedValue({ data: { session_id: 'session_1', status: 'running' } })
    cancelAgentSession.mockResolvedValue({ data: { session_id: 'session_1', status: 'cancelled' } })
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'ais_1',
            suggestion_type: 'rewrite_suggestion',
            severity: 'high',
            title: '提前地图线索',
            summary: '建议把父亲留下的地图前置。',
            proposed_action: '转化为 RewriteInstruction',
            status: 'shown',
            action: { action_type: 'convert_to_rewrite_instruction', action_payload_ref: '' }
          },
          {
            suggestion_id: 'ais_2',
            suggestion_type: 'risk_warning',
            severity: 'high',
            title: '连续性风险',
            summary: '当前版本存在连续性风险。',
            proposed_action: '仅提示',
            status: 'shown',
            action: { action_type: 'dismiss_only', action_payload_ref: '' }
          },
          {
            suggestion_id: 'ais_3',
            suggestion_type: 'conflict_resolution_suggestion',
            severity: 'high',
            title: '存在资产冲突',
            summary: '建议先查看冲突处理卡片。',
            proposed_action: '打开冲突处理入口',
            status: 'shown',
            action: { action_type: 'open_conflict_resolution', action_payload_ref: '' }
          }
        ]
      }
    })
    getAISuggestion.mockResolvedValue({ data: { suggestion_id: 'ais_1', title: '提前地图线索', summary: '建议把父亲留下的地图前置。', severity: 'high', status: 'shown' } })
    listConflicts.mockResolvedValue({
      data: {
        items: [
          {
            record_id: 'cgr_warn_1',
            candidate_draft_id: 'cd_1',
            candidate_version_id: 'ver_1',
            conflict_type: 'candidate_version_conflict',
            severity: 'warning',
            status: 'shown',
            title: '检测结果可能不完整',
            summary: '当前版本依赖的上下文存在降级风险。',
            warning_codes: ['context_pack_degraded'],
            suggested_action_refs: ['review_context_before_apply']
          },
          {
            record_id: 'cgr_info_1',
            candidate_draft_id: 'cd_1',
            candidate_version_id: 'ver_1',
            conflict_type: 'candidate_version_conflict',
            severity: 'info',
            status: 'shown',
            title: '未发现阻断性冲突',
            summary: '当前版本未发现阻断性冲突，可继续人工判断。',
            warning_codes: [],
            suggested_action_refs: []
          },
          {
            record_id: 'cgr_failed_1',
            candidate_draft_id: 'cd_1',
            candidate_version_id: 'ver_1',
            conflict_type: 'candidate_version_conflict',
            severity: 'warning',
            status: 'failed',
            title: '检测失败',
            summary: '检测结果可能不完整',
            warning_codes: ['detection_timeout'],
            suggested_action_refs: []
          }
        ]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cgr_warn_1',
        conflict_type: 'candidate_version_conflict',
        severity: 'warning',
        summary: '当前版本依赖的上下文存在降级风险。',
        evidence_refs: ['warning_code:context_pack_degraded']
      }
    })
    decideConflict.mockResolvedValue({
      data: {
        record_id: 'cgr_warn_1',
        severity: 'warning',
        status: 'acknowledged',
        resolution_status: 'acknowledged'
      }
    })
    listDirectionProposals.mockResolvedValue({
      data: {
        items: [{
          direction_proposal_id: 'dir_1',
          status: 'waiting_for_selection',
          warning_codes: [],
          options: [{
            option_id: 'opt_a',
            label: 'A',
            plot_summary: '沿着钟声推进灯塔谜团',
            narrative_premise: '顾迟继续追索父亲线索'
          }]
        }]
      }
    })
    listChapterPlans.mockResolvedValue({
      data: {
        items: [{
          chapter_plan_id: 'plan_1',
          status: 'waiting_for_confirmation',
          plan_summary: '未来三章围绕灯塔调查展开',
          plan_items: [{
            item_id: 'cpi_1',
            chapter_goal: '潜入灯塔档案室',
            key_events: [],
            required_beats: ['取得航海图'],
            forbidden_items: ['不要提前揭示父亲真相'],
            foreshadow_arrangement: [],
            arc_alignment: []
          }]
        }]
      }
    })
    listWritingTasks.mockResolvedValue({
      data: {
        items: [{
          writing_task_id: 'wt_1',
          status: 'ready',
          writing_goal: '潜入灯塔档案室并锁定钟声来源',
          plan_summary: '未来三章围绕灯塔调查展开'
        }]
      }
    })
    listMemoryGates.mockResolvedValue({ data: { items: [] } })
    getMemoryRevision.mockResolvedValue({ data: { revision_id: 'memrev_1', status: 'applied', before_summary: 'A', after_summary: 'B' } })
    approveMemorySuggestion.mockResolvedValue({ data: { state: 'approved' } })
    editApproveMemorySuggestion.mockResolvedValue({ data: { state: 'approved' } })
    rejectMemorySuggestion.mockResolvedValue({ data: { state: 'waiting_for_user' } })
    deferMemorySuggestion.mockResolvedValue({ data: { state: 'waiting_for_user' } })
    applyMemoryGate.mockResolvedValue({ data: { gate: { state: 'applied' }, revision_ids: [] } })
    rollbackMemoryRevision.mockResolvedValue({ data: { revision_id: 'memrev_rb_1', status: 'applied' } })
    listAgentTraces.mockResolvedValue({
      data: {
        items: [{
          trace_id: 'trace_1',
          session_id: 'agent_session_1',
          status: 'running',
          workflow_type: 'continuation',
          total_steps: 2,
          total_tokens: 30
        }]
      }
    })
    getAgentTrace.mockResolvedValue({
      data: {
        trace_id: 'trace_1',
        status: 'running',
        workflow_type: 'continuation',
        result_summary: '',
        warning_codes: []
      }
    })
    getAgentTraceSteps.mockResolvedValue({
      data: {
        items: [{
          step_id: 'agent_step_1',
          agent_type: 'writer',
          action: 'run_writer',
          status: 'running'
        }]
      }
    })
    getAgentTraceDetailView.mockResolvedValue({
      data: {
        trace: { trace_id: 'trace_1', status: 'running' },
        events: [{ event_id: 'evt_1', event_type: 'tool_call_denied', summary: 'apply_candidate_to_draft:failed' }],
        steps: [{ step_id: 'agent_step_1', status: 'running' }],
        tool_calls: [{ tool_trace_id: 'tool_1', tool_name: 'apply_candidate_to_draft', permission_result: 'deny', call_status: 'failed' }],
        observations: [],
        llm_calls: [],
        user_decisions: [{ decision_trace_id: 'decision_1', decision_type: 'apply_memory', target_entity_type: 'memory_gate', target_entity_id: 'gate_1' }],
        metrics: [{ metric_id: 'metric_1', metric_name: 'tool_call_denied_total', metric_value: 1 }],
        alerts: [{ alert_id: 'alert_1', alert_type: 'audit_write_failed', status: 'open', summary: 'trace write failed' }]
      }
    })
    listPlotArcs.mockResolvedValue({
      data: {
        items: [
          { arc_id: 'arc_master_1', arc_level: 'master_arc', title: '灯塔迷局', status: 'ready', summary: '主线围绕灯塔真相展开。' },
          { arc_id: 'arc_volume_1', arc_level: 'volume_arc', title: '卷一目标', status: 'pending', summary: '确认灯塔背后的势力。' }
        ]
      }
    })
    getPlotArc.mockResolvedValue({
      data: {
        arc_id: 'arc_master_1',
        arc_level: 'master_arc',
        title: '灯塔迷局',
        status: 'ready',
        summary: '主线围绕灯塔真相展开。',
        key_points: ['旧地图', '钟声来源']
      }
    })
    getPlotArcStatus.mockResolvedValue({
      data: {
        items: [
          { arc_level: 'master_arc', status: 'ready' },
          { arc_level: 'volume_arc', status: 'pending' }
        ]
      }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('shows ai settings status in workspace and routes to settings page', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })

    await vi.runAllTimersAsync()
    expect(wrapper.text()).toContain('AI 设置状态')
    expect(wrapper.text()).toContain('配置与模型服务商管理已迁移到“设置”页面')
    expect(wrapper.text()).not.toContain('fake-api-key')

    await wrapper.get('[data-test="go-settings-page"]').trigger('click')
    expect(routerPush).toHaveBeenCalledWith('/settings')
  })

  it('removes settings-edit controls from ai workspace', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.find('[data-test="ai-settings-save"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="ai-test-provider"]').exists()).toBe(false)
    expect(wrapper.find('[data-test^="ai-settings-provider-key-"]').exists()).toBe(false)
    expect(wrapper.find('[data-test^="ai-settings-role-provider-"]').exists()).toBe(false)
  })


  it('blocks generation actions when key or critical role mappings are not ready', async () => {
    getAISettings.mockResolvedValue({
      data: {
        provider_configs: [{
          provider_name: 'fake',
          enabled: true,
          default_model: 'fake-chat',
          key_configured: false,
          api_key_masked: '',
          last_test_status: 'failed'
        }],
        model_role_mappings: {
          analysis: { provider_name: '', model_name: '' },
          planning: { provider_name: 'fake', model_name: 'fake-plan' },
          writer: { provider_name: '', model_name: '' },
          reviewer: { provider_name: 'fake', model_name: 'fake-review' },
          rewriter: { provider_name: 'fake', model_name: 'fake-rewrite' }
        }
      }
    })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('AI 设置未完成')
    expect(wrapper.text()).toContain('请先配置可用模型服务 Key，并完成分析任务模型/写作任务模型配置。')
    expect(wrapper.get('[data-test="ai-generate-directions"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="ai-start-initialization"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="quick-trial-run"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-test="ai-generate-directions"]').trigger('click')
    expect(generateDirectionProposal).not.toHaveBeenCalled()
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

  it('supports candidate draft version switching diff and rewrite actions through s6 apis', async () => {
    getCandidateDraft.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        content: '完整候选稿内容',
        selected_version_id: 'ver_2',
        accepted_version_id: 'ver_1',
        applied_version_id: '',
        validation_status: 'passed'
      }
    })
    selectCandidateDraftVersion.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', selected_version_id: 'ver_2', accepted_version_id: '', applied_version_id: '' } })
    rejectCandidateDraftVersion.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', status: 'revision_requested' } })
    rewriteCandidateDraft.mockResolvedValue({
      data: {
        rewrite_request: { rewrite_request_id: 'rw_1', trigger_type: 'review_based' },
        target_version: { candidate_version_id: 'ver_3', version_no: 3, status: 'generated' }
      }
    })
    applyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5 }
    })
    await vi.runAllTimersAsync()

    await wrapper.get('[data-test="candidate-detail-cd_1"]').trigger('click')
    expect(wrapper.text()).toContain('已接受版本 ver_1')

    await wrapper.get('[data-test="candidate-version-detail-cd_1-ver_2"]').trigger('click')
    expect(getCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_2')

    await wrapper.get('[data-test="candidate-version-select-cd_1-ver_2"]').trigger('click')
    expect(selectCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_2', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="candidate-version-diff-cd_1-ver_1-ver_2"]').trigger('click')
    expect(getCandidateDraftVersionDiff).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      from_version_id: 'ver_1',
      to_version_id: 'ver_2'
    }))
    expect(wrapper.text()).toContain('新增父亲留下的地图线索。')

    await wrapper.get('[data-test="candidate-version-rewrite-review-cd_1-ver_2"]').trigger('click')
    expect(rewriteCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      source_version_id: 'ver_2',
      trigger_type: 'review_based',
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="candidate-version-rewrite-user-cd_1-ver_2"]').trigger('click')
    expect(rewriteCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      source_version_id: 'ver_2',
      trigger_type: 'user_instruction',
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="candidate-version-reject-cd_1-ver_2"]').trigger('click')
    expect(rejectCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_2', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="candidate-apply-cd_1"]').trigger('click')
    expect(applyCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      candidate_version_id: 'ver_2',
      expected_chapter_version: 5
    }))
  })

  it('shows trace summary and only loads detail trace in developer mode', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5, developerMode: true }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('Agent Trace')
    expect(wrapper.text()).toContain('trace_1')

    await wrapper.get('[data-test="trace-steps-trace_1"]').trigger('click')
    expect(getAgentTraceSteps).toHaveBeenCalledWith('trace_1')

    await wrapper.get('[data-test="trace-detail-trace_1"]').trigger('click')
    expect(getAgentTraceDetailView).toHaveBeenCalledWith('trace_1', { detail: true, developer_mode: true })
    expect(wrapper.text()).toContain('apply_candidate_to_draft')
    expect(wrapper.text()).toContain('tool_call_denied_total')
    expect(wrapper.text()).toContain('audit_write_failed')
    expect(wrapper.text()).toContain('apply_memory')
  })

  it('renders ai suggestion cards and supports accept dismiss convert through s7 apis', async () => {
    acceptAISuggestion.mockResolvedValue({ data: { suggestion_id: 'ais_1', status: 'accepted' } })
    dismissAISuggestion.mockResolvedValue({ data: { suggestion_id: 'ais_2', status: 'dismissed' } })
    convertAISuggestion.mockResolvedValue({ data: { suggestion_id: 'ais_1', status: 'converted', action: { action_payload_ref: 'rewrite_request:rw_1' } } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('AI 建议')
    expect(wrapper.text()).toContain('提前地图线索')
    expect(wrapper.text()).toContain('连续性风险')

    await wrapper.get('[data-test="suggestion-detail-ais_1"]').trigger('click')
    expect(getAISuggestion).toHaveBeenCalledWith('ais_1')

    await wrapper.get('[data-test="suggestion-accept-ais_1"]').trigger('click')
    expect(acceptAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="suggestion-convert-ais_1"]').trigger('click')
    expect(convertAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="suggestion-dismiss-ais_2"]').trigger('click')
    expect(dismissAISuggestion).toHaveBeenCalledWith('ais_2', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))
  })

  it('renders conflict banner and requires warning confirmation before apply', async () => {
    getCandidateDraft.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', content: '完整候选稿内容', validation_status: 'passed', selected_version_id: 'ver_1' } })
    applyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5 }
    })
    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('资产风险需确认')
    expect(wrapper.text()).toContain('检测结果可能不完整')
    expect(wrapper.text()).toContain('警告 2')
    expect(wrapper.text()).toContain('提示 info 1')
    expect(wrapper.text()).toContain('当前版本未发现阻断性冲突，可继续人工判断。')

    await wrapper.get('[data-test="candidate-detail-cd_1"]').trigger('click')
    await wrapper.get('[data-test="conflict-detail-cgr_warn_1"]').trigger('click')
    expect(getConflict).toHaveBeenCalledWith('cgr_warn_1')

    await wrapper.get('[data-test="conflict-ack-cgr_warn_1"]').trigger('click')
    expect(decideConflict).toHaveBeenCalledWith('cgr_warn_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      decision: 'acknowledged'
    }))

    await wrapper.get('[data-test="candidate-apply-cd_1"]').trigger('click')
    expect(window.confirm).toHaveBeenCalled()
    expect(applyCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      candidate_version_id: 'ver_1',
      expected_chapter_version: 5
    }))
  })

  it('supports conflict quick actions and opens conflict resolution from suggestion convert', async () => {
    getCandidateDraft.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        content: '完整候选稿内容',
        validation_status: 'passed',
        selected_version_id: 'ver_1'
      }
    })
    rewriteCandidateDraft.mockResolvedValue({
      data: {
        rewrite_request: { rewrite_request_id: 'rw_conflict_1', trigger_type: 'review_based' },
        target_version: { candidate_version_id: 'ver_2', version_no: 2, status: 'generated' }
      }
    })
    rejectCandidateDraftVersion.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', status: 'revision_requested' } })
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'ais_3',
        status: 'converted',
        action: { action_payload_ref: 'conflict_guard:cgr_warn_1' }
      }
    })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 5 }
    })
    await vi.runAllTimersAsync()

    await wrapper.get('[data-test="candidate-detail-cd_1"]').trigger('click')

    await wrapper.get('[data-test="conflict-rewrite-cgr_warn_1"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(rewriteCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      source_version_id: 'ver_1',
      trigger_type: 'review_based',
      caller_type: 'user_action'
    }))
    expect(decideConflict).toHaveBeenCalledWith('cgr_warn_1', expect.objectContaining({
      decision: 'acknowledged',
      decision_note: 'revise_candidate'
    }))

    await wrapper.get('[data-test="conflict-reject-cgr_warn_1"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(rejectCandidateDraftVersion).toHaveBeenCalledWith('cd_1', 'ver_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(decideConflict).toHaveBeenCalledWith('cgr_warn_1', expect.objectContaining({
      decision: 'resolved',
      decision_note: 'reject_candidate'
    }))

    await wrapper.get('[data-test="suggestion-convert-ais_3"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(convertAISuggestion).toHaveBeenCalledWith('ais_3', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(getConflict).toHaveBeenCalledWith('cgr_warn_1')
  })


  it('renders plot arc readiness summary inside the ai workspace', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('剧情轨道')
    expect(wrapper.text()).toContain('灯塔迷局')
    expect(wrapper.text()).toContain('确认灯塔背后的势力')
    expect(wrapper.text()).toContain('完成第一轮追索')
    expect(wrapper.text()).toContain('顾迟进入灯塔')
    expect(wrapper.text()).toContain('master_arc')
    expect(wrapper.text()).toContain('volume_arc')
  })

  it('separates generation and review flows by mode while keeping ai tab session and plot arc entries', async () => {
    const aiWrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })
    await vi.runAllTimersAsync()

    expect(aiWrapper.text()).toContain('AI 设置')
    expect(aiWrapper.text()).toContain('AI 写作任务')
    expect(aiWrapper.text()).toContain('剧情轨道详情')
    expect(aiWrapper.text()).not.toContain('AI 建议')
    expect(aiWrapper.text()).not.toContain('记忆审批')

    await aiWrapper.get('[data-test="agent-session-detail-session_1"]').trigger('click')
    expect(getAgentSession).toHaveBeenCalledWith('session_1')

    await aiWrapper.get('[data-test="agent-session-pause-session_1"]').trigger('click')
    expect(pauseAgentSession).toHaveBeenCalledWith('session_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await aiWrapper.get('[data-test="plot-arc-detail-arc_master_1"]').trigger('click')
    expect(getPlotArc).toHaveBeenCalledWith('arc_master_1')

    const reviewWrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'review' }
    })
    await vi.runAllTimersAsync()

    expect(reviewWrapper.text()).toContain('续写与候选稿')
    expect(reviewWrapper.text()).toContain('AI 建议')
    expect(reviewWrapper.text()).toContain('记忆审批')
    expect(reviewWrapper.text()).not.toContain('AI 设置')
    expect(reviewWrapper.text()).not.toContain('AgentSession')
  })


  it('renders direction and plan workspace and supports planning actions through p1-s5 apis', async () => {
    generateDirectionProposal.mockResolvedValue({ data: { direction_proposal_id: 'dir_2', status: 'waiting_for_selection', options: [] } })
    selectDirection.mockResolvedValue({ data: { selection: { selection_type: 'direct_select' }, proposal: { status: 'selected' } } })
    generateChapterPlan.mockResolvedValue({ data: { chapter_plan_id: 'plan_2', status: 'waiting_for_confirmation', plan_items: [] } })
    confirmChapterPlan.mockResolvedValue({
      data: {
        confirmation: { confirmation_type: 'direct_confirm' },
        plan: { status: 'confirmed' },
        writing_task: { writing_task_id: 'wt_2', status: 'ready' }
      }
    })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3 }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('方向推演')
    expect(wrapper.text()).toContain('沿着钟声推进灯塔谜团')
    expect(wrapper.text()).toContain('章节计划')
    expect(wrapper.text()).toContain('潜入灯塔档案室')
    expect(wrapper.text()).toContain('写作任务')
    expect(wrapper.text()).toContain('潜入灯塔档案室并锁定钟声来源')

    await wrapper.get('[data-test="ai-generate-directions"]').trigger('click')
    expect(generateDirectionProposal).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="select-direction-dir_1-opt_a"]').trigger('click')
    expect(selectDirection).toHaveBeenCalledWith('dir_1', expect.objectContaining({
      selected_option_id: 'opt_a',
      user_action: true,
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="generate-plan-dir_1"]').trigger('click')
    expect(generateChapterPlan).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      direction_proposal_id: 'dir_1',
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="confirm-plan-plan_1"]').trigger('click')
    expect(confirmChapterPlan).toHaveBeenCalledWith('plan_1', expect.objectContaining({
      user_action: true,
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))
  })
})
