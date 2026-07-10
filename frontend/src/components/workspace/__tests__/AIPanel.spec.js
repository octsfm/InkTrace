import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const routerPush = vi.fn()
const getAISettings = vi.fn()
const startInitialization = vi.fn()
const startVectorIndexReindex = vi.fn()
const upsertAutoQueueConfig = vi.fn()
const getAutoQueueConfig = vi.fn()
const startAutoQueue = vi.fn()
const getAutoQueueStatus = vi.fn()
const getAutoQueueHistory = vi.fn()
const pauseAutoQueue = vi.fn()
const resumeAutoQueue = vi.fn()
const stopAutoQueue = vi.fn()
const confirmAutoQueueContinue = vi.fn()
const startStyleDNAExtract = vi.fn()
const getStyleProfile = vi.fn()
const getActiveStyleProfile = vi.fn()
const getStyleProfileHistory = vi.fn()
const confirmStyleProfile = vi.fn()
const disableStyleProfile = vi.fn()
const deleteStyleProfile = vi.fn()
const getAIJob = vi.fn()
const getLatestInitialization = vi.fn()
const getContextPackReadiness = vi.fn()
const cancelAIJob = vi.fn()
const listAgentSessions = vi.fn()
const getAgentSession = vi.fn()
const pauseAgentSession = vi.fn()
const generateDirectionProposal = vi.fn()
const listDirectionProposals = vi.fn()
const selectDirection = vi.fn()
const generateChapterPlan = vi.fn()
const listChapterPlans = vi.fn()
const confirmChapterPlan = vi.fn()
const listWritingTasks = vi.fn()
const getWritingTask = vi.fn()
const confirmWritingTask = vi.fn()
const runQuickTrial = vi.fn()
const listPlotArcs = vi.fn()
const getPlotArc = vi.fn()
const getPlotArcStatus = vi.fn()
const listCandidateDrafts = vi.fn()
const listCandidateDraftVersions = vi.fn()
const listAISuggestions = vi.fn()
const getAISuggestion = vi.fn()
const acceptAISuggestion = vi.fn()
const dismissAISuggestion = vi.fn()
const convertAISuggestion = vi.fn()
const applyOutlineAssistSuggestion = vi.fn()
const elMessageSuccess = vi.fn()
const getOpeningAnalysis = vi.fn()
const getOpeningStatus = vi.fn()
const listConflicts = vi.fn()
const getConflict = vi.fn()
const listMemoryGates = vi.fn()
const listAgentTraces = vi.fn()
const getAgentTrace = vi.fn()
const getAgentTraceSteps = vi.fn()
const getAgentTraceDetailView = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: routerPush
  })
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: elMessageSuccess,
    error: vi.fn(),
    info: vi.fn()
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => ['enable_style_dna', 'enable_auto_queue', 'enable_outline_assist', 'enable_opening_agent'].includes(flagName)
}))

vi.mock('../ReviewTab.vue', () => ({
  default: {
    name: 'ReviewTab',
    props: ['workId', 'chapterId', 'chapterVersion', 'developerMode'],
    template: `
      <div data-test="review-tab-stub">
        ???????        <span data-test="review-tab-work">{{ workId }}</span>
        <span data-test="review-tab-chapter">{{ chapterId }}</span>
      </div>
    `
  }
}))

vi.mock('@/api', () => ({
  aiApi: {
    getAISettings,
    startInitialization,
    startVectorIndexReindex,
    upsertAutoQueueConfig,
    getAutoQueueConfig,
    startAutoQueue,
    getAutoQueueStatus,
    getAutoQueueHistory,
    pauseAutoQueue,
    resumeAutoQueue,
    stopAutoQueue,
    confirmAutoQueueContinue,
    startStyleDNAExtract,
    getStyleProfile,
    getActiveStyleProfile,
    getStyleProfileHistory,
    confirmStyleProfile,
    disableStyleProfile,
    deleteStyleProfile,
    getAIJob,
    getLatestInitialization,
    getContextPackReadiness,
    cancelAIJob,
    listAgentSessions,
    getAgentSession,
    pauseAgentSession,
    generateDirectionProposal,
    listDirectionProposals,
    selectDirection,
    generateChapterPlan,
    listChapterPlans,
    confirmChapterPlan,
    listWritingTasks,
    getWritingTask,
    confirmWritingTask,
    runQuickTrial,
    listPlotArcs,
    getPlotArc,
    getPlotArcStatus,
    listCandidateDrafts,
    listCandidateDraftVersions,
    listAISuggestions,
    getAISuggestion,
    acceptAISuggestion,
    dismissAISuggestion,
    convertAISuggestion,
    applyOutlineAssistSuggestion,
    getOpeningAnalysis,
    getOpeningStatus,
    listConflicts,
    getConflict,
    listMemoryGates,
    listAgentTraces,
    getAgentTrace,
    getAgentTraceSteps,
    getAgentTraceDetailView
  }
}))

describe('AIPanel', () => {
  let AIPanel

  beforeEach(async () => {
    vi.resetAllMocks()
    vi.useFakeTimers()
    setActivePinia(createPinia())
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

    getLatestInitialization.mockResolvedValue({
      data: {
        status: 'completed',
        analyzed_chapter_count: 1,
        empty_chapter_count: 0,
        failed_chapter_count: 0
      }
    })

    getContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        blocked_reason: '',
        degraded_reason: 'volume_arc_missing',
        warnings: ['volume_arc_missing'],
        plot_arc_statuses: {
          master_arc: { status: 'ready' },
          volume_arc: { status: 'pending' },
          sequence_arc: { status: 'ready' },
          immediate_window: { status: 'ready' }
        },
        plot_arc_summary: {
          master_arc: { arc_title: '????', current_stage: '?????', ultimate_goal: '??????' },
          volume_arc: { stage_goal: '?????????', stage_open_loops: ['????'] },
          sequence_arc: { sequence_goal: '???????', key_events: ['?????'] },
          immediate_window: { active_plot_threads: ['????'], recent_chapters_summary: ['??????'] }
        }
      }
    })

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

    listDirectionProposals.mockResolvedValue({
      data: {
        items: [{
          direction_proposal_id: 'dir_1',
          status: 'waiting_for_selection',
          warning_codes: [],
          options: [{
            option_id: 'opt_a',
            label: 'A',
            plot_summary: '??????????'
          }]
        }]
      }
    })

    listChapterPlans.mockResolvedValue({
      data: {
        items: [{
          chapter_plan_id: 'plan_1',
          status: 'waiting_for_confirmation',
          plan_summary: '????????????',
          plan_items: [{
            item_id: 'cpi_1',
            chapter_goal: '???????'
          }]
        }]
      }
    })

    listWritingTasks.mockResolvedValue({
      data: {
        items: [{
          writing_task_id: 'wt_1',
          status: 'ready',
          writing_goal: '??????????????',
          plan_summary: '????????????'
        }]
      }
    })

    getWritingTask.mockResolvedValue({
      data: {
        writing_task_id: 'wt_1',
        status: 'ready',
        writing_goal: '??????????????',
        must_include: ['????????'],
        must_not_include: ['????????'],
        plan_summary: '????????????',
        metadata: {}
      }
    })

    confirmWritingTask.mockResolvedValue({
      data: {
        writing_task_id: 'wt_1',
        status: 'ready',
        writing_goal: '??????????????',
        plan_summary: '????????????',
        metadata: {
          user_confirmed: true,
          confirmed_by: 'ui-user'
        }
      }
    })

    listPlotArcs.mockResolvedValue({
      data: {
        items: [
          { arc_id: 'arc_master_1', arc_level: 'master_arc', title: '????', status: 'ready', summary: '???????????' },
          { arc_id: 'arc_volume_1', arc_level: 'volume_arc', title: '????', status: 'pending', summary: '??????????' }
        ]
      }
    })

    getPlotArc.mockResolvedValue({
      data: {
        arc_id: 'arc_master_1',
        arc_level: 'master_arc',
        title: '????',
        status: 'ready',
        summary: '???????????',
        key_points: ['???', '????']
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
    listCandidateDrafts.mockResolvedValue({ data: { items: [] } })
    listCandidateDraftVersions.mockResolvedValue({ data: { items: [] } })
    listAISuggestions.mockResolvedValue({ data: { items: [] } })
    getOpeningAnalysis.mockResolvedValue({ data: {} })
    getOpeningStatus.mockResolvedValue({ data: {} })
    listConflicts.mockResolvedValue({ data: { items: [] } })
    getConflict.mockResolvedValue({ data: {} })
    listMemoryGates.mockResolvedValue({ data: { items: [] } })
    listAgentTraces.mockResolvedValue({ data: { items: [] } })

    startInitialization.mockResolvedValue({ data: { initialization_id: 'init_1', job_id: 'job_1' } })
    startVectorIndexReindex.mockResolvedValue({
      data: {
        job_id: 'job_reindex_1',
        status: 'queued',
        reused_existing_job: false,
        polling_hint: { next_poll_after_ms: 3000, max_poll_interval_ms: 10000, timeout_hint_ms: 300000 }
      }
    })
    cancelAIJob.mockResolvedValue({ data: { job_id: 'job_reindex_1', status: 'cancelled' } })
    upsertAutoQueueConfig.mockResolvedValue({
      data: {
        config: {
          config_id: 'aqc_001',
          work_id: 'work-1',
          queue_mode: 'safe',
          target_chapters: 5,
          target_word_count: 0,
          budget_limit_tokens: 0,
          stop_at_sequence_end: true,
          stop_on_blocking_review: true,
          stop_on_budget_exceeded: true,
          stop_on_foreshadow_premature: true
        }
      }
    })
    getAutoQueueConfig.mockResolvedValue({
      data: {
        config: {
          config_id: 'aqc_001',
          work_id: 'work-1',
          queue_mode: 'safe',
          target_chapters: 5,
          target_word_count: 0,
          budget_limit_tokens: 0,
          stop_at_sequence_end: true,
          stop_on_blocking_review: true,
          stop_on_budget_exceeded: true,
          stop_on_foreshadow_premature: true
        }
      }
    })
    getAutoQueueHistory.mockResolvedValue({ data: { runs: [] } })
    startAutoQueue.mockResolvedValue({
      data: {
        run_id: 'aqr_001',
        status: 'running',
        queue_mode: 'safe'
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_001',
          status: 'waiting_user_decision',
          queue_mode: 'safe',
          generated_count: 1
        }
      }
    })
    pauseAutoQueue.mockResolvedValue({ data: { run: { run_id: 'aqr_001', status: 'paused', queue_mode: 'safe', generated_count: 1 } } })
    resumeAutoQueue.mockResolvedValue({ data: { run: { run_id: 'aqr_001', status: 'running', queue_mode: 'safe', generated_count: 1 } } })
    stopAutoQueue.mockResolvedValue({ data: { run: { run_id: 'aqr_001', status: 'stopped', queue_mode: 'safe', generated_count: 1 } } })
    confirmAutoQueueContinue.mockResolvedValue({
      data: { run: { run_id: 'aqr_001', status: 'running', queue_mode: 'safe', generated_count: 2 } }
    })
    getActiveStyleProfile.mockResolvedValue({ data: { profile: null } })
    getStyleProfileHistory.mockResolvedValue({ data: { profiles: [] } })
    getStyleProfile.mockResolvedValue({ data: { profile: null } })
    startStyleDNAExtract.mockResolvedValue({
      data: {
        job_id: 'job_style_1',
        status: 'queued',
        polling_hint: { next_poll_after_ms: 3000, max_poll_interval_ms: 10000 }
      }
    })
    confirmStyleProfile.mockResolvedValue({ data: { profile: { profile_id: 'sp_1', status: 'active' } } })
    disableStyleProfile.mockResolvedValue({ data: { profile: { profile_id: 'sp_1', status: 'disabled' } } })
    deleteStyleProfile.mockResolvedValue({ data: { deleted: true, status: 'deleted' } })
    getAIJob
      .mockResolvedValueOnce({ data: { job_id: 'job_1', status: 'running', steps: [] } })
      .mockResolvedValueOnce({ data: { job_id: 'job_1', status: 'completed', steps: [] } })
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
    runQuickTrial.mockResolvedValue({ data: { status: 'succeeded', output_text: '璇曡窇杈撳嚭', validation_status: 'passed' } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows ai settings status and routes to settings page', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('?????')
    expect(wrapper.text()).toContain('?????????????????????')
    expect(listCandidateDrafts).not.toHaveBeenCalled()
    expect(listAISuggestions).not.toHaveBeenCalled()
    expect(listMemoryGates).not.toHaveBeenCalled()
    expect(listConflicts).not.toHaveBeenCalled()
    expect(listAgentTraces).not.toHaveBeenCalled()
    await wrapper.get('[data-test="go-settings-page"]').trigger('click')
    expect(routerPush).toHaveBeenCalledWith('/settings')
  })

  it('shows style dna config entry in ai workspace', async () => {
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai',
        chapterOptions: [
          { id: 'chapter-1', title: '??', content: '?????', status: 'published', order_index: 1 },
          { id: 'chapter-2', title: '??', content: '?????', status: 'published', order_index: 2 },
          { id: 'chapter-3', title: '??', content: '?????', status: 'draft', order_index: 3 }
        ],
        draftChapterIds: ['chapter-3']
      }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('风格画像')
    expect(wrapper.text()).toContain('从已有章节选择')
  })

  it('shows auto queue panel in ai workspace and starts safe queue from current chapter', async () => {
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.get('[data-test="ai-helper-nav"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="ai-helper-tab-auto_queue"]').classes())
      .toContain('ai-helper-tab--active')
    await wrapper.get('[data-test="auto-queue-start"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('AI 助手')
    expect(wrapper.text()).toContain('自动续写')
    expect(wrapper.text()).toContain('安全模式')
    expect(upsertAutoQueueConfig).toHaveBeenCalledWith({
      work_id: 'work-1',
      queue_mode: 'safe',
      target_chapters: 5,
      target_word_count: 0,
      budget_limit_tokens: 0,
      stop_at_sequence_end: true,
      stop_on_blocking_review: true,
      stop_on_budget_exceeded: true,
      stop_on_foreshadow_premature: true
    })
    expect(startAutoQueue).toHaveBeenCalledWith({
      work_id: 'work-1',
      start_chapter_id: 'chapter-1'
    })
  })

  it('shows outline assist tab and reuses ai suggestions actions', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_001',
          title: '强化灯塔章节细纲',
          suggestion_type: 'chapter_outline_suggestion',
          severity: 'warning',
          summary: '建议补足潜入前的侦查段落'
        }]
      }
    })
    getAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_001',
        summary: '建议先补侦查，再进入档案室。'
      }
    })
    acceptAISuggestion.mockResolvedValue({ data: { suggestion_id: 'sg_001', status: 'accepted' } })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-panel"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="outline-assist-view"]').text()).toContain('大纲辅助')
    expect(wrapper.text()).toContain('强化灯塔章节细纲')

    await wrapper.get('[data-test="suggestion-detail-sg_001"]').trigger('click')
    await flushPromises()
    expect(getAISuggestion).toHaveBeenCalledWith('sg_001')
    expect(wrapper.get('[data-test="outline-assist-view"]').text()).toContain('建议先补侦查，再进入档案室。')

    await wrapper.get('[data-test="suggestion-accept-sg_001"]').trigger('click')
    await flushPromises()
    expect(acceptAISuggestion).toHaveBeenCalled()
    expect(applyOutlineAssistSuggestion).not.toHaveBeenCalled()
  })

  it('shows loading state and disables accept button while accepting outline suggestion', async () => {
    let resolveAccept
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_accept_loading_001',
            title: '强化灯塔章节细纲',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '建议补足潜入前的侦查段落'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_accept_loading_001',
            title: '强化灯塔章节细纲',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: '采纳后回刷结果'
          }]
        }
      })
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-accept-sg_accept_loading_001"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-accept-sg_accept_loading_001"]').text()).toContain('采纳中...')
    expect(wrapper.get('[data-test="suggestion-accept-sg_accept_loading_001"]').attributes('disabled')).toBeDefined()

    resolveAccept({
      data: {
        suggestion_id: 'sg_accept_loading_001',
        status: 'accepted'
      }
    })
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-accept-sg_accept_loading_001"]').exists()).toBe(false)
  })

  it('disables sibling outline actions while accept is submitting', async () => {
    let resolveAccept
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_accept_guard_001',
            title: '寮哄寲鐏绔犺妭缁嗙翰',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑渚︽煡娈佃惤'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_accept_guard_001',
            title: '寮哄寲鐏绔犺妭缁嗙翰',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: '閲囩撼鍚庡洖鍒风粨鏋?'
          }]
        }
      })
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-accept-sg_accept_guard_001"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-accept-sg_accept_guard_001"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="suggestion-dismiss-sg_accept_guard_001"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="suggestion-convert-sg_accept_guard_001"]').attributes('disabled')).toBeDefined()

    resolveAccept({
      data: {
        suggestion_id: 'sg_accept_guard_001',
        status: 'accepted'
      }
    })
    await flushPromises()
  })

  it('shows loading state for dismiss and convert buttons while outline actions are submitting', async () => {
    let resolveDismiss
    let resolveConvert
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_action_loading_001',
            title: '寮哄寲鐏绔犺妭缁嗙翰',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑渚︽煡娈佃惤'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_action_loading_001',
            title: '寮哄寲鐏绔犺妭缁嗙翰',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'dismiss 鍚庡洖鍒风粨鏋?'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_action_loading_001',
            title: '寮哄寲鐏绔犺妭缁嗙翰',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'convert 鍚庡洖鍒风粨鏋?'
          }]
        }
      })
    dismissAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveDismiss = resolve
    }))
    convertAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveConvert = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-dismiss-sg_action_loading_001"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test="suggestion-dismiss-sg_action_loading_001"]').text()).toContain('忽略中...')
    expect(wrapper.get('[data-test="suggestion-dismiss-sg_action_loading_001"]').attributes('disabled')).toBeDefined()

    resolveDismiss({
      data: {
        suggestion_id: 'sg_action_loading_001',
        status: 'dismissed'
      }
    })
    await flushPromises()

    wrapper.vm.outlineAssistStore.setSuggestions([{
      suggestion_id: 'sg_action_loading_001',
      title: '寮哄寲鐏绔犺妭缁嗙翰',
      suggestion_type: 'outline_expand',
      severity: 'warning',
      status: 'pending',
      summary: '鍐嶆杩涘叆 convert'
    }])
    await flushPromises()

    await wrapper.get('[data-test="suggestion-convert-sg_action_loading_001"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test="suggestion-convert-sg_action_loading_001"]').text()).toContain('转换中...')
    expect(wrapper.get('[data-test="suggestion-convert-sg_action_loading_001"]').attributes('disabled')).toBeDefined()

    resolveConvert({
      data: {
        suggestion_id: 'sg_action_loading_001',
        status: 'converted',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })
    await flushPromises()
  })

  it('requires lightweight confirmation before applying an accepted outline suggestion', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_apply_001',
          title: '琛ュ叏妗ｆ瀹ゆ綔鍏ヨ妭鐐?',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'accepted',
          summary: '寤鸿灏嗕睛鏌ユ钀藉苟鍏ユ寮忓ぇ绾茶妭鐐广€?'
        }]
      }
    })
    applyOutlineAssistSuggestion.mockResolvedValue({
      data: {
        success: true
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-apply-sg_apply_001"]').exists()).toBe(true)

    await wrapper.get('[data-test="suggestion-apply-sg_apply_001"]').trigger('click')
    await flushPromises()

    expect(applyOutlineAssistSuggestion).not.toHaveBeenCalled()
    expect(wrapper.get('[data-test="suggestion-apply-confirm-sg_apply_001"]').text()).toContain('这会修改正式大纲内容')
    expect(wrapper.get('[data-test="suggestion-apply-confirm-sg_apply_001"]').text()).toContain('确定要将这条建议应用到正式大纲吗')

    await wrapper.get('[data-test="suggestion-apply-confirm-submit-sg_apply_001"]').trigger('click')
    await flushPromises()

    expect(applyOutlineAssistSuggestion).toHaveBeenCalledWith('sg_apply_001', expect.objectContaining({
      caller_type: 'user_action'
    }))
  })

  it('shows a 2-second success toast after applying an accepted outline suggestion', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_apply_success_001',
          title: '琛ュ叏闆ㄥ娼滃叆缁嗙翰',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'accepted',
          summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑鍦板舰瑙傚療銆?'
        }]
      }
    })
    applyOutlineAssistSuggestion.mockResolvedValue({
      data: {
        success: true
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-apply-sg_apply_success_001"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-apply-confirm-submit-sg_apply_success_001"]').trigger('click')
    await flushPromises()

    expect(elMessageSuccess).toHaveBeenCalledWith({
      message: '已应用 1 条建议',
      duration: 2000
    })
  })

  it('filters outline assist suggestions by selected mode', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'sg_polish_001',
            title: '润色灯塔入口描述',
            suggestion_type: 'outline_polish',
            severity: 'warning',
            status: 'accepted',
            summary: '收紧入口段落的语言节奏。'
          },
          {
            suggestion_id: 'sg_expand_001',
            title: '扩写外墙侦查节点',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: '补足潜入前的观察步骤。'
          },
          {
            suggestion_id: 'sg_detail_001',
            title: '补全潜入前的观察段落',
            suggestion_type: 'chapter_outline_detail',
            severity: 'warning',
            status: 'accepted',
            summary: '缁嗗寲鏈珷鍦烘櫙鑺傛媿銆?'
          },
          {
            suggestion_id: 'sg_task_001',
            title: '调整写作任务目标',
            suggestion_type: 'writing_task_suggestion',
            severity: 'warning',
            status: 'accepted',
            summary: '閲嶆柊鑱氱劍閽熷０鏉ユ簮鐨勮皟鏌ョ洰鏍囥€?'
          }
        ]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="outline-assist-mode-outline_polish"]').text()).toContain('润色')
    expect(wrapper.text()).toContain('润色灯塔入口描述')
    expect(wrapper.text()).not.toContain('扩写外墙侦查节点')

    await wrapper.get('[data-test="outline-assist-mode-writing_task_suggestion"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('调整写作任务目标')
    expect(wrapper.text()).not.toContain('润色灯塔入口描述')
    expect(wrapper.text()).not.toContain('鎵╁啓澶栧渚︽煡鑺傜偣')
    expect(wrapper.text()).not.toContain('补全潜入前的观察段落')
  })

  it('shows refresh button and loading state for outline assist suggestions', async () => {
    let resolveRefresh
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_ui_001',
            title: '初始建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'initial suggestion'
          }]
        }
      })
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveRefresh = resolve
      }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    const refreshButton = wrapper.get('[data-test="outline-assist-refresh"]')
    expect(refreshButton.text()).toContain('刷新建议')
    expect(refreshButton.attributes('disabled')).toBeUndefined()

    await refreshButton.trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="outline-assist-refresh"]').text()).toContain('刷新中...')
    expect(wrapper.get('[data-test="outline-assist-refresh"]').attributes('disabled')).toBeDefined()

    resolveRefresh({
      data: {
        items: [{
          suggestion_id: 'sg_refresh_ui_002',
          title: '刷新后建议',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'pending',
          summary: 'refreshed suggestion'
        }]
      }
    })
    await flushPromises()

    expect(wrapper.get('[data-test="outline-assist-refresh"]').text()).toContain('刷新建议')
    expect(wrapper.get('[data-test="outline-assist-refresh"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('刷新后建议')
  })

  it('shows loading hint while outline assist suggestions are loading', async () => {
    let resolveList
    listAISuggestions.mockImplementationOnce(() => new Promise((resolve) => {
      resolveList = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="outline-assist-refresh"]').text()).toContain('刷新中...')
    expect(wrapper.get('[data-test="outline-assist-loading"]').text()).toContain('正在加载建议')

    resolveList({
      data: {
        items: [{
          suggestion_id: 'sg_loading_ui_001',
          title: '加载完成建议',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'pending',
          summary: 'loaded'
        }]
      }
    })
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-loading"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('加载完成建议')
  })

  it('restores outline assist refresh button after refresh fails', async () => {
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_fail_001',
            title: '初始建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'initial suggestion'
          }]
        }
      })
      .mockRejectedValueOnce(new Error('network failed'))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="outline-assist-refresh"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="outline-assist-refresh"]').text()).toContain('刷新建议')
    expect(wrapper.get('[data-test="outline-assist-refresh"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('大纲建议加载失败，请稍后重试')
  })

  it('shows generating and failed lifecycle hints for outline suggestions', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'sg_generating_001',
            title: '正在生成章节细纲',
            suggestion_type: 'chapter_outline_detail',
            severity: 'warning',
            status: 'generating',
            summary: '系统正在生成本章细纲。'
          },
          {
            suggestion_id: 'sg_failed_001',
            title: '写作建议生成失败',
            suggestion_type: 'writing_task_suggestion',
            severity: 'error',
            status: 'failed',
            summary: '上一次生成未成功完成。'
          }
        ]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="outline-assist-mode-chapter_outline_detail"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-generating-hint-sg_generating_001"]').text()).toContain('建议生成中')
    expect(wrapper.find('[data-test="suggestion-accept-sg_generating_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_generating_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_generating_001"]').exists()).toBe(false)

    await wrapper.get('[data-test="outline-assist-mode-writing_task_suggestion"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-failed-hint-sg_failed_001"]').text()).toContain('建议生成失败')
    expect(wrapper.find('[data-test="suggestion-accept-sg_failed_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_failed_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_failed_001"]').exists()).toBe(false)
  })

  it('hides resolved actions for accepted and terminal outline suggestions', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'sg_accepted_001',
            title: '??????????',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: '寤鸿琛ヨ冻娼滃叆鍓嶄睛鏌ャ€?'
          },
          {
            suggestion_id: 'sg_applied_001',
            title: '宸插簲鐢ㄧ殑绔犺妭缁嗙翰',
            suggestion_type: 'chapter_outline_detail',
            severity: 'warning',
            status: 'applied',
            summary: '璇ュ缓璁凡缁忓啓鍏ユ寮忓ぇ绾层€?'
          },
          {
            suggestion_id: 'sg_dismissed_001',
            title: '宸插拷鐣ョ殑鎵╁啓寤鸿',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'dismissed',
            summary: '璇ュ缓璁凡琚拷鐣ャ€?'
          },
          {
            suggestion_id: 'sg_converted_001',
            title: '宸茶浆鎵ц鍔ㄤ綔鐨勫缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'converted',
            summary: '璇ュ缓璁凡杞负鎵ц鍔ㄤ綔銆?'
          }
        ]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="outline-assist-mode-outline_expand"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-accept-sg_accepted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_accepted_001"]').exists()).toBe(true)

    expect(wrapper.find('[data-test="suggestion-accept-sg_dismissed_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_dismissed_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_dismissed_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_dismissed_001"]').exists()).toBe(false)

    expect(wrapper.find('[data-test="suggestion-accept-sg_converted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_converted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_converted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_converted_001"]').exists()).toBe(false)

    await wrapper.get('[data-test="outline-assist-mode-chapter_outline_detail"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-accept-sg_applied_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_applied_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_applied_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_applied_001"]').exists()).toBe(false)
  })

  it('limits writing-task suggestion actions by suggestion type', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'sg_task_pending_001',
            title: '浼樺寲鍐欎綔浠诲姟鐩爣',
            suggestion_type: 'writing_task_suggestion',
            severity: 'warning',
            status: 'pending',
            summary: '寤鸿鎶婁换鍔￠噸鐐硅仛鐒﹀埌閽熷０鏉ユ簮銆?'
          },
          {
            suggestion_id: 'sg_task_accepted_001',
            title: '?????????',
            suggestion_type: 'writing_task_suggestion',
            severity: 'warning',
            status: 'accepted',
            summary: '璇ュ缓璁凡杩涘叆鍐欎綔浠诲姟纭閾俱€?'
          }
        ]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="outline-assist-mode-writing_task_suggestion"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-accept-sg_task_pending_001"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_task_pending_001"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="suggestion-convert-sg_task_pending_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_task_pending_001"]').exists()).toBe(false)

    expect(wrapper.find('[data-test="suggestion-accept-sg_task_accepted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-dismiss-sg_task_accepted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-convert-sg_task_accepted_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-apply-sg_task_accepted_001"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="suggestion-writing-task-hint-sg_task_accepted_001"]').text()).toContain('已进入写作任务确认链')
  })

  it('does not allow applying selection-only outline suggestions directly', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_selection_001',
          title: '润色自由文本片段',
          suggestion_type: 'outline_polish',
          severity: 'warning',
          status: 'accepted',
          summary: '建议先润色这一段，再决定是否并入正式大纲。',
          payload_json: {
            target_kind: 'selection',
            target_id: null
          }
        }]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="suggestion-apply-sg_selection_001"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="suggestion-apply-hint-sg_selection_001"]').text()).toContain('需要先选择目标大纲节点')
    expect(applyOutlineAssistSuggestion).not.toHaveBeenCalled()
  })

  it('shows stale warning when outline suggestion may no longer match the latest outline', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_stale_001',
          title: '??????????',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'stale',
          summary: '寤鸿琛ュ己涓昏鍦ㄨ繘鍏ユ。妗堝鍓嶇殑澶栭儴渚︽煡銆?'
        }]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-stale-hint-sg_stale_001"]').text()).toContain('大纲已被修改，当前建议可能已经过期。')
  })

  it('shows refresh action next to stale outline suggestion hint', async () => {
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_stale_refresh_001',
            title: '过期的大纲补全建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'stale',
            summary: '建议可能与当前大纲版本不一致。',
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_stale_refresh_002',
            title: '刷新后的最新建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '已重新获取最新建议。',
          }]
        }
      })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="suggestion-stale-hint-sg_stale_refresh_001"]').text()).toContain('大纲已被修改')

    await wrapper.get('[data-test="suggestion-stale-refresh-sg_stale_refresh_001"]').trigger('click')
    await flushPromises()

    expect(listAISuggestions).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('刷新后的最新建议')
  })

  it('shows outline assist conflict handoff when convert returns conflict guard ref', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_conflict_001',
          title: '琛ュ叏妗ｆ瀹よ妭鐐?',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'pending',
          summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑渚︽煡姝ラ銆?'
        }]
      }
    })
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_conflict_001',
        status: 'converted',
        action: {
          action_payload_ref: 'conflict_guard:cg_outline_001'
        }
      }
    })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_outline_001',
          title: '目标节点已发生冲突',
          severity: 'blocking',
          summary: '目标节点已被其他操作修改，请先确认差异。'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_outline_001',
        title: '目标节点已发生冲突',
        summary: '目标节点已被其他操作修改，请先确认差异。'
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-convert-sg_conflict_001"]').trigger('click')
    await flushPromises()

    expect(convertAISuggestion).toHaveBeenCalledWith('sg_conflict_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(getConflict).toHaveBeenCalledWith('cg_outline_001')
    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(wrapper.get('[data-test="outline-assist-conflicts"]').text()).toContain('目标节点已发生冲突')
    expect(wrapper.get('[data-test="outline-assist-conflicts"]').text()).toContain('目标节点已被其他操作修改，请先确认差异')
  })

  it('clears outline assist conflict handoff when chapter changes', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_conflict_002',
          title: '琛ュ叏娼滃叆鍓嶄睛鏌ヨ妭鐐?',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          status: 'pending',
          summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑渚︽煡姝ラ銆?'
        }]
      }
    })
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_conflict_002',
        status: 'converted',
        action: {
          action_payload_ref: 'conflict_guard:cg_outline_002'
        }
      }
    })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_outline_002',
          title: '澶х翰鑺傜偣瀛樺湪鍐茬獊',
          severity: 'blocking',
          summary: '褰撳墠绔犺妭鐨勫ぇ绾茶妭鐐瑰凡鍙戠敓鍙樺寲銆?'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_outline_002',
        summary: '褰撳墠绔犺妭鐨勫ぇ绾茶妭鐐瑰凡鍙戠敓鍙樺寲銆?'
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-convert-sg_conflict_002"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-conflicts"]').exists()).toBe(true)

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-conflicts"]').exists()).toBe(false)
  })

  it('clears previous outline assist conflict handoff when a later convert has no conflict guard', async () => {
    listAISuggestions.mockResolvedValue({
      data: {
        items: [
          {
            suggestion_id: 'sg_conflict_003',
            title: '??????????',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '寤鸿琛ヨ冻娼滃叆鍓嶇殑渚︽煡姝ラ銆?'
          },
          {
            suggestion_id: 'sg_convert_ok_001',
            title: '杞负鏅€氭墽琛屽姩浣?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '璇ュ缓璁彲鐩存帴杞负鏅€氬姩浣溿€?'
          }
        ]
      }
    })
    convertAISuggestion
      .mockResolvedValueOnce({
        data: {
          suggestion_id: 'sg_conflict_003',
          status: 'converted',
          action: {
            action_payload_ref: 'conflict_guard:cg_outline_003'
          }
        }
      })
      .mockResolvedValueOnce({
        data: {
          suggestion_id: 'sg_convert_ok_001',
          status: 'converted',
          action: {
            action_payload_ref: 'writing_task:wt_001'
          }
        }
      })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_outline_003',
          title: '???????',
          severity: 'blocking',
          summary: '鐩爣鑺傜偣宸茶鍏朵粬鎿嶄綔淇敼銆?'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_outline_003',
        summary: '鐩爣鑺傜偣宸茶鍏朵粬鎿嶄綔淇敼銆?'
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-convert-sg_conflict_003"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-conflicts"]').exists()).toBe(true)

    await wrapper.get('[data-test="suggestion-convert-sg_convert_ok_001"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="outline-assist-conflicts"]').exists()).toBe(false)
  })

  it('clears outline assist chapter-scoped ui state when chapter changes outside outline assist view', async () => {
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_apply_002',
            title: '补全潜入前的观察段落',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: '建议补全潜入前的侦查段落。'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_apply_003',
            title: '新章节建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: 'chapter-2 建议'
          }]
        }
      })
    getAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_apply_002',
        summary: '上一章详情'
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-detail-sg_apply_002"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-apply-sg_apply_002"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('上一章详情')
    expect(wrapper.find('[data-test="suggestion-apply-confirm-sg_apply_002"]').exists()).toBe(true)

    await wrapper.get('[data-test="ai-helper-tab-auto_queue"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).not.toContain('上一章详情')
    expect(wrapper.find('[data-test="suggestion-apply-confirm-sg_apply_002"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('chapter-2 建议')
  })

  it('does not keep previous suggestion submitting state after chapter changes', async () => {
    let resolveAccept
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_repeat_001',
            title: '上一章建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '上一章待采纳建议'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_repeat_001',
            title: '下一章建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '下一章建议已生成',
          }]
        }
      })
      .mockResolvedValue({
        data: {
          items: []
        }
      })
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-accept-sg_repeat_001"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test="suggestion-accept-sg_repeat_001"]').text()).toContain('采纳中...')

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    expect(wrapper.text()).toContain('下一章建议')
    expect(wrapper.get('[data-test="suggestion-accept-sg_repeat_001"]').text()).toContain('采纳建议')
    expect(wrapper.get('[data-test="suggestion-accept-sg_repeat_001"]').attributes('disabled')).toBeUndefined()

    resolveAccept({
      data: {
        suggestion_id: 'sg_repeat_001',
        status: 'accepted'
      }
    })
    await flushPromises()
  })

  it('ignores late accept result from previous chapter after chapter changes', async () => {
    let resolveAccept
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_repeat_late_001',
            title: '上一章建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '上一章待采纳建议'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_repeat_late_001',
            title: '下一章建议',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: '下一章仍应保持 pending'
          }]
        }
      })
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-accept-sg_repeat_late_001"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    resolveAccept({
      data: {
        suggestion_id: 'sg_repeat_late_001',
        status: 'accepted',
        summary: 'late accepted result'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('下一章建议')
    expect(wrapper.text()).toContain('下一章仍应保持')
    expect(wrapper.find('[data-test="suggestion-apply-sg_repeat_late_001"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="suggestion-accept-sg_repeat_late_001"]').exists()).toBe(true)
  })

  it('does not show stale conflict handoff after chapter changes', async () => {
    let resolveConvert
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_conflict_late_001',
            title: '涓婁竴绔犲啿绐佸缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-1 convert'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_conflict_late_001',
            title: '涓嬩竴绔犲缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-2 suggestion'
          }]
        }
      })
    convertAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveConvert = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="suggestion-convert-sg_conflict_late_001"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    resolveConvert({
      data: {
        suggestion_id: 'sg_conflict_late_001',
        status: 'converted',
        action: {
          action_payload_ref: 'conflict_guard:cg_late_001'
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('涓嬩竴绔犲缓璁?')
    expect(wrapper.find('[data-test="outline-assist-conflicts"]').exists()).toBe(false)
  })

  it('ignores late apply result from previous chapter after chapter changes', async () => {
    let resolveApply
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_apply_late_001',
            title: '涓婁竴绔犲簲鐢ㄥ缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: 'chapter-1 apply'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_apply_late_001',
            title: '涓嬩竴绔犲缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'accepted',
            summary: 'chapter-2 should stay accepted'
          }]
        }
      })
    applyOutlineAssistSuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveApply = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-apply-sg_apply_late_001"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-apply-confirm-submit-sg_apply_late_001"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    resolveApply({
      data: {
        suggestion_id: 'sg_apply_late_001',
        status: 'applied',
        summary: 'late applied result'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('涓嬩竴绔犲缓璁?')
    expect(wrapper.text()).toContain('chapter-2 should stay accepted')
    expect(wrapper.find('[data-test="suggestion-apply-sg_apply_late_001"]').exists()).toBe(true)
  })

  it('ignores late dismiss result from previous chapter after chapter changes', async () => {
    let resolveDismiss
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_dismiss_late_001',
            title: '涓婁竴绔犲拷鐣ュ缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-1 dismiss'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_dismiss_late_001',
            title: '涓嬩竴绔犲缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-2 should stay pending'
          }]
        }
      })
    dismissAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveDismiss = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-dismiss-sg_dismiss_late_001"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    resolveDismiss({
      data: {
        suggestion_id: 'sg_dismiss_late_001',
        status: 'dismissed',
        summary: 'late dismissed result'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('涓嬩竴绔犲缓璁?')
    expect(wrapper.text()).toContain('chapter-2 should stay pending')
    expect(wrapper.find('[data-test="suggestion-accept-sg_dismiss_late_001"]').exists()).toBe(true)
  })

  it('ignores late convert result from previous chapter after chapter changes', async () => {
    let resolveConvert
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_convert_late_001',
            title: '涓婁竴绔犺浆鎹㈠缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-1 convert'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_convert_late_001',
            title: '涓嬩竴绔犲缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-2 should stay pending'
          }]
        }
      })
    convertAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveConvert = resolve
    }))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="suggestion-convert-sg_convert_late_001"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    resolveConvert({
      data: {
        suggestion_id: 'sg_convert_late_001',
        status: 'converted',
        summary: 'late converted result',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('涓嬩竴绔犲缓璁?')
    expect(wrapper.text()).toContain('chapter-2 should stay pending')
    expect(wrapper.find('[data-test="suggestion-accept-sg_convert_late_001"]').exists()).toBe(true)
  })

  it('does not keep previous outline assist suggestions visible when chapter reload fails', async () => {
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_prev_002',
            title: '涓婁竴绔犲缓璁?',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-1 suggestion'
          }]
        }
      })
      .mockRejectedValueOnce(new Error('network failed'))

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('涓婁竴绔犲缓璁?')

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('涓婁竴绔犲缓璁?')
    expect(wrapper.text()).toContain('大纲建议加载失败，请稍后重试')
  })

  it('clears outline assist load error after a successful reload for the same chapter', async () => {
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_retry_001',
            title: '???????',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'chapter-1 suggestion'
          }]
        }
      })
      .mockRejectedValueOnce(new Error('network failed'))
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_retry_002',
            title: '????????',
            suggestion_type: 'outline_expand',
            severity: 'warning',
            status: 'pending',
            summary: 'reload succeeded'
          }]
        }
      })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('???????')

    await wrapper.setProps({
      chapterId: 'chapter-2',
      chapterVersion: 4
    })
    await flushPromises()

    expect(wrapper.text()).toContain('大纲建议加载失败，请稍后重试')

    await wrapper.get('[data-test="ai-helper-tab-auto_queue"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-outline_assist"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).not.toContain('大纲建议加载失败，请稍后重试')
    expect(wrapper.text()).toContain('????????')
  })

  it('shows opening agent tab and opens wizard shell', async () => {
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-view"]').text()).toContain('开篇助手')
    await wrapper.get('[data-test="opening-agent-open"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test="opening-agent-wizard"]').exists()).toBe(true)
  })

  it('shows opening preview summary in opening agent view', async () => {
    const { useOpeningStore } = await import('@/stores/useOpeningStore')
    const store = useOpeningStore()
    getOpeningAnalysis.mockRejectedValue(new Error('opening_snapshot_failed'))
    store.loadPreview({
      analysis: {
        analysis_summary: '通过海雾钟声建立开篇悬念。'
      },
      strategy: {
        target_audience: '悬疑向女性读者',
        genre_positioning: '都市悬疑',
        first_three_chapter_goal: '三章内建立主角与旧案的强关联',
        forbidden_similarity_notes: '避免直接复用现有作品中的具体表达',
        protagonist_entry: '第一章前半段以归乡视角登场',
        conflict_entry: '第一章结尾抛出旧案重启',
        selling_points: ['悬念强', '节奏快']
      },
      riskLevel: 'medium'
    })
    store.loadSnapshot({
      phase: 'generate',
      status: 'running',
      candidate_draft_ids: ['cd_1', 'cd_2']
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-summary"]').text()).toContain('通过海雾钟声建立开篇悬念')
    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('当前显示为本地预览')
    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('开篇助手实时结果读取失败')
    expect(wrapper.get('[data-test="opening-agent-strategy"]').text()).toContain('悬疑向女性读者')
    expect(wrapper.get('[data-test="opening-agent-strategy-details"]').text()).toContain('都市悬疑')
    expect(wrapper.get('[data-test="opening-agent-strategy-details"]').text()).toContain('三章内建立主角与旧案的强关联')
    expect(wrapper.get('[data-test="opening-agent-strategy-details"]').text()).toContain('避免直接复用现有作品中的具体表达')
    expect(wrapper.get('[data-test="opening-agent-strategy-structure"]').text()).toContain('第一章前半段以归乡视角登场')
    expect(wrapper.get('[data-test="opening-agent-strategy-structure"]').text()).toContain('第一章结尾抛出旧案重启')
    expect(wrapper.get('[data-test="opening-agent-strategy-structure"]').text()).toContain('悬念强')
    expect(wrapper.get('[data-test="opening-agent-strategy-structure"]').text()).toContain('节奏快')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('生成候选稿')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('进行中')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('2')
    expect(wrapper.get('[data-test="opening-agent-risk"]').text()).toContain('中风险')
  })

  it('loads opening snapshot during panel initialization', async () => {
    vi.setSystemTime(new Date('2026-07-02T10:47:00.000Z'))
    getOpeningAnalysis.mockResolvedValue({
      data: {
        analysis: {
          analysis_summary: '通过潮声和残页手记建立开篇悬念。'
        },
        strategy: {
          target_audience: '悬疑签约向读者'
        },
        risk_report: {
          risk_level: 'high'
        }
      }
    })
    getOpeningStatus.mockResolvedValue({
      data: {
        phase: 'generate',
        status: 'running',
        candidate_draft_ids: ['cd_1', 'cd_2', 'cd_3']
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    expect(getOpeningAnalysis).toHaveBeenCalledWith('work-1')
    expect(getOpeningStatus).toHaveBeenCalledWith('work-1')
    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('已读取开篇助手的实时结果')
    expect(wrapper.get('[data-test="opening-agent-last-result"]').text()).toContain('最近一次读取结果：读取成功。')
    expect(wrapper.get('[data-test="opening-agent-last-updated"]').text()).toContain('2026-07-02T10:47:00.000Z')
    expect(wrapper.get('[data-test="opening-agent-summary"]').text()).toContain('通过潮声和残页手记建立开篇悬念')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('生成候选稿')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('进行中')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('3')
    expect(wrapper.get('[data-test="opening-agent-risk"]').text()).toContain('高风险')
  })

  it('refreshes opening snapshot on demand after fallback preview', async () => {
    vi.setSystemTime(new Date('2026-07-02T10:48:00.000Z'))
    getOpeningAnalysis
      .mockRejectedValueOnce(new Error('opening_snapshot_failed'))
      .mockResolvedValueOnce({
        data: {
          analysis: {
            analysis_summary: '通过潮声和遗失手札更新开篇悬念。'
          },
          strategy: {
            target_audience: '悬疑签约向读者'
          },
          risk_report: {
            risk_level: 'high'
          }
        }
      })
    getOpeningStatus.mockResolvedValue({
      data: {
        phase: 'generate',
        status: 'running',
        candidate_draft_ids: ['cd_1', 'cd_2', 'cd_3']
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('开篇助手实时结果读取失败')
    expect(wrapper.get('[data-test="opening-agent-last-result"]').text()).toContain('最近一次读取结果：已回退到本地预览。')
    expect(wrapper.get('[data-test="opening-agent-last-updated"]').text()).toContain('2026-07-02T10:48:00.000Z')

    vi.setSystemTime(new Date('2026-07-02T10:49:00.000Z'))
    await wrapper.get('[data-test="opening-agent-refresh"]').trigger('click')
    await flushPromises()

    expect(getOpeningAnalysis).toHaveBeenCalledTimes(2)
    expect(getOpeningStatus).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('已读取开篇助手的实时结果')
    expect(wrapper.get('[data-test="opening-agent-last-result"]').text()).toContain('最近一次读取结果：读取成功。')
    expect(wrapper.get('[data-test="opening-agent-last-updated"]').text()).toContain('2026-07-02T10:49:00.000Z')
    expect(wrapper.get('[data-test="opening-agent-summary"]').text()).toContain('通过潮声和遗失手札更新开篇悬念')
    expect(wrapper.get('[data-test="opening-agent-runtime"]').text()).toContain('3')
  })

  it('shows loading state while refreshing opening snapshot on demand', async () => {
    let resolveRefresh
    const refreshPromise = new Promise((resolve) => {
      resolveRefresh = resolve
    })

    getOpeningAnalysis
      .mockRejectedValueOnce(new Error('opening_snapshot_failed'))
      .mockImplementationOnce(() => refreshPromise)
    getOpeningStatus.mockResolvedValue({
      data: {
        phase: 'generate',
        status: 'running',
        candidate_draft_ids: ['cd_1']
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    const refreshButton = wrapper.get('[data-test="opening-agent-refresh"]')
    expect(refreshButton.text()).toContain('刷新快照')

    const refreshTrigger = refreshButton.trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-refresh"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="opening-agent-refresh"]').text()).toContain('刷新中...')

    resolveRefresh({
      data: {
        analysis: {
          analysis_summary: '刷新中返回了新的开篇摘要。'
        },
        strategy: {
          target_audience: '悬疑签约向读者'
        },
        risk_report: {
          risk_level: 'medium'
        }
      }
    })

    await refreshTrigger
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-refresh"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-test="opening-agent-refresh"]').text()).toContain('刷新快照')
    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('已读取开篇助手的实时结果')
  })

  it('shows loading hint while initializing opening snapshot on mount', async () => {
    let resolveInitialLoad
    const initialLoadPromise = new Promise((resolve) => {
      resolveInitialLoad = resolve
    })

    getOpeningAnalysis.mockImplementationOnce(() => initialLoadPromise)
    getOpeningStatus.mockResolvedValue({
      data: {
        phase: 'analyze',
        status: 'running',
        candidate_draft_ids: []
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('正在读取开篇助手的实时结果')
    expect(wrapper.get('[data-test="opening-agent-refresh"]').attributes('disabled')).toBeDefined()

    resolveInitialLoad({
      data: {
        analysis: {
          analysis_summary: '初始化阶段返回了最新开篇摘要。'
        },
        strategy: {
          target_audience: '悬疑签约向读者'
        },
        risk_report: {
          risk_level: 'medium'
        }
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()

    expect(wrapper.get('[data-test="opening-agent-preview-status"]').text()).toContain('已读取开篇助手的实时结果')
    expect(wrapper.get('[data-test="opening-agent-refresh"]').attributes('disabled')).toBeUndefined()
  })

  it('passes opening preview data from store into wizard', async () => {
    const { useOpeningStore } = await import('@/stores/useOpeningStore')
    const store = useOpeningStore()
    store.hydratePreview({
      analysis: {
        analysis_summary: '通过灯塔钟声建立开篇悬念。'
      },
      strategy: {
        target_audience: '女性悬疑读者'
      },
      riskLevel: 'high'
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="ai-helper-tab-opening_agent"]').trigger('click')
    await wrapper.get('[data-test="opening-agent-open"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="opening-rights-confirm-step1"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    expect(wrapper.get('[data-test="opening-analysis-summary"]').text()).toContain('通过灯塔钟声建立开篇悬念')

    await wrapper.get('[data-test="opening-next"]').trigger('click')
    expect(wrapper.get('[data-test="opening-strategy-card"]').text()).toContain('女性悬疑读者')

    await wrapper.get('[data-test="opening-strategy-confirm"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    expect(wrapper.get('[data-test="opening-return-modify"]').exists()).toBe(true)
  })

  it('confirms before disabling auto queue budget check', async () => {
    upsertAutoQueueConfig.mockResolvedValue({
      data: {
        config: {
          config_id: 'aqc_001',
          work_id: 'work-1',
          queue_mode: 'safe',
          target_chapters: 5,
          stop_on_budget_exceeded: false
        }
      }
    })
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{
          run_id: 'aqr_001',
          status: 'stopped',
          queue_mode: 'safe',
          generated_count: 2,
          stop_record: {
            stop_reason: 'budget_exceeded',
            stop_severity: 'budget',
            suggested_action: 'adjust_budget'
          }
        }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_001',
          status: 'stopped',
          queue_mode: 'safe',
          generated_count: 2,
          stop_record: {
            stop_reason: 'budget_exceeded',
            stop_severity: 'budget',
            suggested_action: 'adjust_budget'
          }
        }
      }
    })

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="auto-queue-history-aqr_001"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="auto-queue-disable-budget-check"]').trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledWith('关闭预算检查后，AI 功能将不再受预算限制。确定要关闭吗？')
    expect(upsertAutoQueueConfig).toHaveBeenLastCalledWith({
      work_id: 'work-1',
      queue_mode: 'safe',
      target_chapters: 5,
      target_word_count: 0,
      budget_limit_tokens: 0,
      stop_at_sequence_end: true,
      stop_on_blocking_review: true,
      stop_on_budget_exceeded: false,
      stop_on_foreshadow_premature: true
    })
  })

  it('continues auto queue from stopped run', async () => {
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{
          run_id: 'aqr_031',
          status: 'stopped',
          queue_mode: 'safe',
          generated_count: 2,
          stop_record: {
            stop_reason: 'user_manual_stop',
            stop_severity: 'warning',
            suggested_action: 'resume_queue'
          }
        }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_031',
          status: 'stopped',
          queue_mode: 'safe',
          generated_count: 2,
          stop_record: {
            stop_reason: 'user_manual_stop',
            stop_severity: 'warning',
            suggested_action: 'resume_queue'
          }
        }
      }
    })
    resumeAutoQueue.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_031',
          status: 'running',
          queue_mode: 'safe',
          generated_count: 2
        }
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="auto-queue-history-aqr_031"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="auto-queue-continue"]').trigger('click')
    await flushPromises()

    expect(resumeAutoQueue).toHaveBeenCalledWith('aqr_031', expect.objectContaining({
      idempotency_key: expect.stringContaining('auto_queue_resume')
    }))
  })

  it('loads and shows blocking conflict details from auto queue action', async () => {
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{
          run_id: 'aqr_010',
          status: 'stopped',
          queue_mode: 'continuous',
          generated_count: 2,
          stop_record: {
            stop_reason: 'blocking_review_consecutive',
            stop_severity: 'blocking',
            suggested_action: 'resolve_conflict'
          }
        }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_010',
          status: 'stopped',
          queue_mode: 'continuous',
          generated_count: 2,
          stop_record: {
            stop_reason: 'blocking_review_consecutive',
            stop_severity: 'blocking',
            suggested_action: 'resolve_conflict'
          }
        }
      }
    })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'conf_001',
          title: '自动续写冲突详情',
          severity: 'blocking',
          summary: '主角设定与既有章节不一致'
        }]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="auto-queue-view-conflicts"]').trigger('click')
    await flushPromises()

    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(wrapper.get('[data-test="auto-queue-conflicts"]').text()).toContain('自动续写冲突详情')
    expect(wrapper.get('[data-test="auto-queue-conflicts"]').text()).toContain('主角设定与既有章节不一致')
  })

  it('shows auto queue progress overview and per chapter statuses from selected run', async () => {
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{
          run_id: 'aqr_020',
          status: 'completed',
          queue_mode: 'continuous',
          generated_count: 5,
          target_chapters: 10,
          total_word_count: 25000,
          target_word_count: 50000,
          consumed_tokens: 120000,
          per_chapter: [
            { chapter_title: '第1章', generated_word_count: 3200, status: 'review_passed' },
            { chapter_title: '第2章', generated_word_count: 2800, status: 'review_passed' },
            { chapter_title: '第3章', generated_word_count: 2600, status: 'candidate_generation' },
            { chapter_title: '第4章', generated_word_count: 0, status: 'waiting' }
          ]
        }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_020',
          status: 'completed',
          queue_mode: 'continuous',
          generated_count: 5,
          target_chapters: 10,
          total_word_count: 25000,
          target_word_count: 50000,
          consumed_tokens: 120000,
          per_chapter: [
            { chapter_title: '第1章', generated_word_count: 3200, status: 'review_passed' },
            { chapter_title: '第2章', generated_word_count: 2800, status: 'review_passed' },
            { chapter_title: '第3章', generated_word_count: 2600, status: 'candidate_generation' },
            { chapter_title: '第4章', generated_word_count: 0, status: 'waiting' }
          ]
        }
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.get('[data-test="auto-queue-progress"]').text()).toContain('5 / 10 章')
    expect(wrapper.text()).toContain('字数25,000 / 50,000')
    expect(wrapper.text()).toContain('令牌120K')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('第3章')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('生成中')
  })

  it('saves auto queue target word count from panel controls', async () => {
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="auto-queue-target-words"]').setValue('80000')
    await wrapper.get('[data-test="auto-queue-budget-limit"]').setValue('160000')
    await wrapper.get('[data-test="auto-queue-stop-sequence-end"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-blocking-review"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-budget"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-foreshadow"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-save-config"]').trigger('click')
    await flushPromises()

    expect(upsertAutoQueueConfig).toHaveBeenCalledWith({
      work_id: 'work-1',
      queue_mode: 'safe',
      target_chapters: 5,
      target_word_count: 80000,
      budget_limit_tokens: 160000,
      stop_at_sequence_end: false,
      stop_on_blocking_review: false,
      stop_on_budget_exceeded: false,
      stop_on_foreshadow_premature: false
    })
  })

  it('opens review workspace from auto queue candidate shortcut', async () => {
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{
          run_id: 'aqr_030',
          status: 'completed',
          queue_mode: 'safe',
          generated_count: 2
        }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_030',
          status: 'completed',
          queue_mode: 'safe',
          generated_count: 2
        }
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()
    await wrapper.get('[data-test="auto-queue-view-candidates"]').trigger('click')

    expect(wrapper.emitted('open-review-tab')).toEqual([[]])
  })

  it('blocks ai actions when key or critical role mappings are missing', async () => {
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

    expect(wrapper.get('[data-test="ai-settings-blocked"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="ai-generate-directions"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="ai-start-initialization"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="quick-trial-run"]').attributes('disabled')).toBeDefined()
  })

  it('polls initialization job to terminal state', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="ai-start-initialization"]').trigger('click')
    await vi.advanceTimersByTimeAsync(1200)
    await vi.advanceTimersByTimeAsync(1200)

    expect(getAIJob).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('已完成')
  })

  it('renders plot arc, session, planning, and quick-trial actions in ai mode', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('剧情轨道详情')
    expect(wrapper.text()).toContain('AI 写作任务')
    expect(wrapper.text()).toContain('方向推演')
    expect(wrapper.text()).toContain('章节计划')
    expect(wrapper.text()).toContain('写作任务')

    await wrapper.get('[data-test="agent-session-detail-session_1"]').trigger('click')
    expect(getAgentSession).toHaveBeenCalledWith('session_1')

    await wrapper.get('[data-test="agent-session-pause-session_1"]').trigger('click')
    expect(pauseAgentSession).toHaveBeenCalledWith('session_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="plot-arc-detail-arc_master_1"]').trigger('click')
    expect(getPlotArc).toHaveBeenCalledWith('arc_master_1')

    await wrapper.get('[data-test="ai-generate-directions"]').trigger('click')
    expect(generateDirectionProposal).toHaveBeenCalled()

    await wrapper.get('[data-test="select-direction-dir_1-opt_a"]').trigger('click')
    expect(selectDirection).toHaveBeenCalledWith('dir_1', expect.objectContaining({
      selected_option_id: 'opt_a',
      caller_type: 'user_action',
      user_action: true
    }))

    await wrapper.get('[data-test="generate-plan-dir_1"]').trigger('click')
    expect(generateChapterPlan).toHaveBeenCalled()

    await wrapper.get('[data-test="confirm-plan-plan_1"]').trigger('click')
    expect(confirmChapterPlan).toHaveBeenCalledWith('plan_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    await wrapper.get('[data-test="writing-task-detail-wt_1"]').trigger('click')
    expect(getWritingTask).toHaveBeenCalledWith('wt_1')
    expect(wrapper.text()).toContain('????????')

    await wrapper.get('[data-test="writing-task-confirm-wt_1"]').trigger('click')
    expect(confirmWritingTask).toHaveBeenCalledWith('wt_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user'
    }))


    await wrapper.get('[data-test="quick-trial-run"]').trigger('click')
    expect(runQuickTrial).toHaveBeenCalledWith(expect.objectContaining({
      model_role: expect.any(String),
      input_text: expect.any(String),
      caller_type: 'quick_trial',
      idempotency_key: expect.any(String)
    }))
    expect(wrapper.text()).toContain('????')
  })

  it('delegates review mode to ReviewTab and hides ai workspace sections', async () => {
    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-9',
        chapterVersion: 5,
        developerMode: true,
        mode: 'review'
      }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.get('[data-test="review-tab-stub"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="review-tab-work"]').text()).toBe('work-1')
    expect(wrapper.get('[data-test="review-tab-chapter"]').text()).toBe('chapter-9')
    expect(wrapper.text()).not.toContain('AI 设置状态')
    expect(wrapper.text()).not.toContain('快速试写')
    expect(wrapper.text()).not.toContain('AI 写作任务')
  })

  it('shows localized trace copy in developer mode', async () => {
    listAgentTraces.mockResolvedValue({
      data: {
        items: [{
          trace_id: 'trace_1',
          status: 'running',
          workflow_type: 'continuation',
          total_steps: 2,
          total_tokens: 321
        }]
      }
    })
    getAgentTrace.mockResolvedValue({ data: { trace_id: 'trace_1' } })
    getAgentTraceSteps.mockResolvedValue({
      data: {
        items: [
          { step_id: 'step_1', agent_type: 'planner', action: 'prepare', status: 'running' },
          { step_id: 'step_2', agent_type: 'writer', action: 'tool_call', status: 'completed' }
        ]
      }
    })
    getAgentTraceDetailView.mockResolvedValue({
      data: {
        tool_calls: [{ tool_name: 'vector_search', permission_result: 'allow' }],
        events: [{ event_type: 'tool_call_denied' }],
        metrics: [
          { metric_id: 'metric_1', metric_name: 'llm_token_count', metric_value: 321 },
          { metric_id: 'metric_2', metric_name: 'tool_call_latency_ms', metric_value: 180 }
        ]
      }
    })

    const wrapper = mount(AIPanel, {
      props: {
        workId: 'work-1',
        chapterId: 'chapter-1',
        chapterVersion: 3,
        developerMode: true,
        mode: 'ai'
      }
    })

    await vi.runAllTimersAsync()
    await flushPromises()

    expect(listAgentTraces).toHaveBeenCalledWith({ work_id: 'work-1', chapter_id: 'chapter-1' })
    expect(wrapper.text()).toContain('任务追踪')
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('令牌 321')
    })

    await wrapper.get('[data-test="trace-steps-trace_1"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('准备')
    expect(wrapper.text()).toContain('工具调用')
    expect(wrapper.text()).not.toContain('prepare')
    expect(wrapper.text()).not.toContain('tool_call')

    await wrapper.get('[data-test="trace-detail-trace_1"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('模型令牌用量')
    expect(wrapper.text()).toContain('工具调用耗时')
    expect(wrapper.text()).not.toContain('Token')
  })

  it('starts vector reindex from ai panel and polls progress after confirmation', async () => {
    getContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        degraded_reason: 'vector_index_stale_warning',
        warnings: ['vector_index_stale_warning']
      }
    })
    getAIJob.mockReset()
    getAIJob
      .mockResolvedValueOnce({
        data: {
          job_id: 'job_reindex_1',
          status: 'running',
          progress: { percent: 42, current_step_label: '????? 2/4 ?' }
        }
      })
      .mockResolvedValueOnce({
        data: {
          job_id: 'job_reindex_1',
          status: 'completed',
          progress: { percent: 100, current_step_label: '????' },
          result_summary: { index_status: 'ready' }
        }
      })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="vector-index-reindex-full-work"]').trigger('click')
    await vi.advanceTimersByTimeAsync(3100)

    expect(startVectorIndexReindex).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      index_scope: 'full_work',
      caller_type: 'user_action'
    }))
    expect(wrapper.text()).toContain('????')
    expect(wrapper.text()).toContain('??????????')
    expect(wrapper.text()).toContain('??????')
  })

  it('restores pending vector reindex job from sessionStorage on mount', async () => {
    window.sessionStorage.setItem(
      'inktrace.vector-reindex.pending:work-1',
      JSON.stringify({
        request: {
          work_id: 'work-1',
          index_scope: 'full_work',
          caller_type: 'user_action',
          idempotency_key: 'idem_restore_reindex'
        }
      })
    )
    startVectorIndexReindex.mockResolvedValueOnce({
      data: {
        job_id: 'job_restore_1',
        status: 'running',
        reused_existing_job: true,
        polling_hint: { next_poll_after_ms: 3000, max_poll_interval_ms: 10000, timeout_hint_ms: 300000 }
      }
    })
    getAIJob.mockReset()
    getAIJob.mockResolvedValue({
      data: {
        job_id: 'job_restore_1',
        status: 'running',
        progress: { percent: 20, current_step_label: '??????' }
      }
    })

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()

    expect(startVectorIndexReindex).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      idempotency_key: 'idem_restore_reindex'
    }))
    expect(wrapper.text()).toContain('任务 job_restore_1')
  })

  it('cancels active vector reindex job from ai panel', async () => {
    getAIJob.mockReset()
    getAIJob.mockResolvedValue({
      data: {
        job_id: 'job_reindex_1',
        status: 'running',
        progress: { percent: 35, current_step_label: '????? 1/3 ?' }
      }
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="vector-index-reindex-full-work"]').trigger('click')
    await wrapper.get('[data-test="vector-index-cancel"]').trigger('click')

    expect(cancelAIJob).toHaveBeenCalledWith('job_reindex_1', { reason: 'user_cancelled' })
  })

  it('shows partial success copy when vector reindex finishes with degraded result', async () => {
    getAIJob.mockReset()
    getAIJob
      .mockResolvedValueOnce({
        data: {
          job_id: 'job_reindex_partial_1',
          status: 'running',
          progress: { percent: 78, current_step_label: '??????' }
        }
      })
      .mockResolvedValueOnce({
        data: {
          job_id: 'job_reindex_partial_1',
          status: 'partial_success',
          progress: { percent: 100, current_step_label: '????' },
          result_summary: {
            completion_mode: 'partial_success',
            index_status: 'degraded'
          }
        }
      })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()
    await wrapper.get('[data-test="vector-index-reindex-full-work"]').trigger('click')
    await vi.advanceTimersByTimeAsync(6200)

    expect(wrapper.text()).toContain('???????????????????????????????????')
  })
})
