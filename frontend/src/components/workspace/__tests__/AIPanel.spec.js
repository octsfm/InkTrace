import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const routerPush = vi.fn()
const getAISettings = vi.fn()
const startInitialization = vi.fn()
const getAIJob = vi.fn()
const getLatestInitialization = vi.fn()
const getContextPackReadiness = vi.fn()
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
const runQuickTrial = vi.fn()
const listPlotArcs = vi.fn()
const getPlotArc = vi.fn()
const getPlotArcStatus = vi.fn()
const listCandidateDrafts = vi.fn()
const listCandidateDraftVersions = vi.fn()
const listAISuggestions = vi.fn()
const listConflicts = vi.fn()
const listMemoryGates = vi.fn()
const listAgentTraces = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: routerPush
  })
}))

vi.mock('../ReviewTab.vue', () => ({
  default: {
    name: 'ReviewTab',
    props: ['workId', 'chapterId', 'chapterVersion', 'developerMode'],
    template: `
      <div data-test="review-tab-stub">
        审阅工作区占位
        <span data-test="review-tab-work">{{ workId }}</span>
        <span data-test="review-tab-chapter">{{ chapterId }}</span>
      </div>
    `
  }
}))

vi.mock('@/api', () => ({
  aiApi: {
    getAISettings,
    startInitialization,
    getAIJob,
    getLatestInitialization,
    getContextPackReadiness,
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
    runQuickTrial,
    listPlotArcs,
    getPlotArc,
    getPlotArcStatus,
    listCandidateDrafts,
    listCandidateDraftVersions,
    listAISuggestions,
    listConflicts,
    listMemoryGates,
    listAgentTraces
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
          master_arc: { arc_title: '灯塔迷局', current_stage: '追查旧地图', ultimate_goal: '揭开海雾秘密' },
          volume_arc: { stage_goal: '确认灯塔背后的势力', stage_open_loops: ['地图来源'] },
          sequence_arc: { sequence_goal: '完成第一轮追索', key_events: ['发现旧地图'] },
          immediate_window: { active_plot_threads: ['灯塔谜团'], recent_chapters_summary: ['顾迟进入灯塔'] }
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
            plot_summary: '沿着钟声推进灯塔谜团'
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
            chapter_goal: '潜入灯塔档案室'
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
    listCandidateDrafts.mockResolvedValue({ data: { items: [] } })
    listCandidateDraftVersions.mockResolvedValue({ data: { items: [] } })
    listAISuggestions.mockResolvedValue({ data: { items: [] } })
    listConflicts.mockResolvedValue({ data: { items: [] } })
    listMemoryGates.mockResolvedValue({ data: { items: [] } })
    listAgentTraces.mockResolvedValue({ data: { items: [] } })

    startInitialization.mockResolvedValue({ data: { initialization_id: 'init_1', job_id: 'job_1' } })
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
    runQuickTrial.mockResolvedValue({ data: { status: 'succeeded', output_text: '试跑输出', validation_status: 'passed' } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows ai settings status and routes to settings page', async () => {
    const wrapper = mount(AIPanel, {
      props: { workId: 'work-1', chapterId: 'chapter-1', chapterVersion: 3, mode: 'ai' }
    })

    await vi.runAllTimersAsync()

    expect(wrapper.text()).toContain('AI 设置状态')
    expect(wrapper.text()).toContain('配置与模型服务商管理已迁移到“设置”页面')
    expect(listCandidateDrafts).not.toHaveBeenCalled()
    expect(listAISuggestions).not.toHaveBeenCalled()
    expect(listMemoryGates).not.toHaveBeenCalled()
    expect(listConflicts).not.toHaveBeenCalled()
    expect(listAgentTraces).not.toHaveBeenCalled()
    await wrapper.get('[data-test="go-settings-page"]').trigger('click')
    expect(routerPush).toHaveBeenCalledWith('/settings')
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
    expect(wrapper.text()).toContain('已完成（completed）')
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

    await wrapper.get('[data-test="quick-trial-run"]').trigger('click')
    expect(runQuickTrial).toHaveBeenCalled()
    expect(wrapper.text()).toContain('试跑输出')
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
})
