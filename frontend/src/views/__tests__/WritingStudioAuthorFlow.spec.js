import { webcrypto } from 'node:crypto'
import { defineComponent, h, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const routerPush = vi.fn()

const mockV1WorksGet = vi.fn()
const mockV1WorksUpdate = vi.fn()
const mockV1ChaptersList = vi.fn()
const mockV1ChaptersUpdate = vi.fn()
const mockV1ChaptersCreate = vi.fn()
const mockV1ChaptersDelete = vi.fn()
const mockV1ChaptersReorder = vi.fn()
const mockV1ChaptersForceOverride = vi.fn()
const mockV1SessionsGet = vi.fn()
const mockV1SessionsSave = vi.fn()

const mockAIGetSettings = vi.fn()
const mockAIGetLatestInitialization = vi.fn()
const mockAIBuildContextPack = vi.fn()
const mockAIGetLatestContextPack = vi.fn()
const mockAIGetContextPackReadiness = vi.fn()
const mockAIStartInitialization = vi.fn()
const mockAIGetJob = vi.fn()
const mockAIListAgentSessions = vi.fn()
const mockAIGetAgentSession = vi.fn()
const mockAIPauseAgentSession = vi.fn()
const mockAIResumeAgentSession = vi.fn()
const mockAICancelAgentSession = vi.fn()
const mockAIListPlotArcs = vi.fn()
const mockAIGetPlotArc = vi.fn()
const mockAIGetPlotArcStatus = vi.fn()
const mockAIGenerateDirectionProposal = vi.fn()
const mockAIListDirectionProposals = vi.fn()
const mockAISelectDirection = vi.fn()
const mockAIGenerateChapterPlan = vi.fn()
const mockAIListChapterPlans = vi.fn()
const mockAIGetChapterPlan = vi.fn()
const mockAIConfirmChapterPlan = vi.fn()
const mockAIRejectChapterPlan = vi.fn()
const mockAIListWritingTasks = vi.fn()
const mockAIGetWritingTask = vi.fn()
const mockAIConfirmWritingTask = vi.fn()
const mockAIStartContinuation = vi.fn()
const mockAIListCandidateDrafts = vi.fn()
const mockAIGetCandidateDraft = vi.fn()
const mockAIListCandidateDraftVersions = vi.fn()
const mockAIGetCandidateDraftVersion = vi.fn()
const mockAIGetCandidateDraftVersionDiff = vi.fn()
const mockAISelectCandidateDraftVersion = vi.fn()
const mockAIAcceptCandidateDraft = vi.fn()
const mockAIRejectCandidateDraft = vi.fn()
const mockAIApplyCandidateDraft = vi.fn()
const mockAIReviewCandidateDraft = vi.fn()
const mockAIGetAIReview = vi.fn()
const mockAIRewriteCandidateDraft = vi.fn()
const mockAIRejectCandidateDraftVersion = vi.fn()
const mockAIListAISuggestions = vi.fn()
const mockAIGetAISuggestion = vi.fn()
const mockAIAcceptAISuggestion = vi.fn()
const mockAIDismissAISuggestion = vi.fn()
const mockAIConvertAISuggestion = vi.fn()
const mockAIListConflicts = vi.fn()
const mockAIGetConflict = vi.fn()
const mockAIDecideConflict = vi.fn()
const mockAIListMemoryGates = vi.fn()
const mockAIGetMemoryRevision = vi.fn()
const mockAIApproveMemorySuggestion = vi.fn()
const mockAIEditApproveMemorySuggestion = vi.fn()
const mockAIRejectMemorySuggestion = vi.fn()
const mockAIDeferMemorySuggestion = vi.fn()
const mockAIApplyMemoryGate = vi.fn()
const mockAIRollbackMemoryRevision = vi.fn()
const mockAIListAgentTraces = vi.fn()
const mockAIGetAgentTrace = vi.fn()
const mockAIGetAgentTraceSteps = vi.fn()
const mockAIGetAgentTraceDetailView = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'work-1' }
  }),
  useRouter: () => ({
    push: routerPush
  })
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: () => false
}))

vi.mock('@/api', () => ({
  v1WorksApi: {
    get: mockV1WorksGet,
    update: mockV1WorksUpdate
  },
  v1ChaptersApi: {
    list: mockV1ChaptersList,
    update: mockV1ChaptersUpdate,
    create: mockV1ChaptersCreate,
    delete: mockV1ChaptersDelete,
    reorder: mockV1ChaptersReorder,
    forceOverride: mockV1ChaptersForceOverride
  },
  v1SessionsApi: {
    get: mockV1SessionsGet,
    save: mockV1SessionsSave
  },
  aiApi: {
    getAISettings: mockAIGetSettings,
    getLatestInitialization: mockAIGetLatestInitialization,
    buildContextPack: mockAIBuildContextPack,
    getLatestContextPack: mockAIGetLatestContextPack,
    getContextPackReadiness: mockAIGetContextPackReadiness,
    startInitialization: mockAIStartInitialization,
    getAIJob: mockAIGetJob,
    listAgentSessions: mockAIListAgentSessions,
    getAgentSession: mockAIGetAgentSession,
    pauseAgentSession: mockAIPauseAgentSession,
    resumeAgentSession: mockAIResumeAgentSession,
    cancelAgentSession: mockAICancelAgentSession,
    listPlotArcs: mockAIListPlotArcs,
    getPlotArc: mockAIGetPlotArc,
    getPlotArcStatus: mockAIGetPlotArcStatus,
    generateDirectionProposal: mockAIGenerateDirectionProposal,
    listDirectionProposals: mockAIListDirectionProposals,
    getDirectionProposal: vi.fn(),
    selectDirection: mockAISelectDirection,
    generateChapterPlan: mockAIGenerateChapterPlan,
    listChapterPlans: mockAIListChapterPlans,
    getChapterPlan: mockAIGetChapterPlan,
    confirmChapterPlan: mockAIConfirmChapterPlan,
    rejectChapterPlan: mockAIRejectChapterPlan,
    listWritingTasks: mockAIListWritingTasks,
    getWritingTask: mockAIGetWritingTask,
    confirmWritingTask: mockAIConfirmWritingTask,
    startContinuation: mockAIStartContinuation,
    listCandidateDrafts: mockAIListCandidateDrafts,
    getCandidateDraft: mockAIGetCandidateDraft,
    listCandidateDraftVersions: mockAIListCandidateDraftVersions,
    getCandidateDraftVersion: mockAIGetCandidateDraftVersion,
    getCandidateDraftVersionDiff: mockAIGetCandidateDraftVersionDiff,
    selectCandidateDraftVersion: mockAISelectCandidateDraftVersion,
    acceptCandidateDraft: mockAIAcceptCandidateDraft,
    rejectCandidateDraft: mockAIRejectCandidateDraft,
    applyCandidateDraft: mockAIApplyCandidateDraft,
    reviewCandidateDraft: mockAIReviewCandidateDraft,
    getAIReview: mockAIGetAIReview,
    rewriteCandidateDraft: mockAIRewriteCandidateDraft,
    rejectCandidateDraftVersion: mockAIRejectCandidateDraftVersion,
    listAISuggestions: mockAIListAISuggestions,
    getAISuggestion: mockAIGetAISuggestion,
    acceptAISuggestion: mockAIAcceptAISuggestion,
    dismissAISuggestion: mockAIDismissAISuggestion,
    convertAISuggestion: mockAIConvertAISuggestion,
    listConflicts: mockAIListConflicts,
    getConflict: mockAIGetConflict,
    decideConflict: mockAIDecideConflict,
    listMemoryGates: mockAIListMemoryGates,
    getMemoryRevision: mockAIGetMemoryRevision,
    approveMemorySuggestion: mockAIApproveMemorySuggestion,
    editApproveMemorySuggestion: mockAIEditApproveMemorySuggestion,
    rejectMemorySuggestion: mockAIRejectMemorySuggestion,
    deferMemorySuggestion: mockAIDeferMemorySuggestion,
    applyMemoryGate: mockAIApplyMemoryGate,
    rollbackMemoryRevision: mockAIRollbackMemoryRevision,
    listAgentTraces: mockAIListAgentTraces,
    getAgentTrace: mockAIGetAgentTrace,
    getAgentTraceSteps: mockAIGetAgentTraceSteps,
    getAgentTraceDetailView: mockAIGetAgentTraceDetailView
  }
}))

const ChapterSidebarStub = defineComponent({
  name: 'ChapterSidebarStub',
  emits: ['select'],
  setup(_, { emit }) {
    return () => h('button', {
      type: 'button',
      class: 'chapter-sidebar-stub',
      onClick: () => emit('select', 'chapter-1')
    }, '????')
  }
})

const ChapterTitleInputStub = defineComponent({
  name: 'ChapterTitleInputStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  setup(props) {
    return () => h('input', {
      class: 'chapter-title-input-stub',
      value: props.modelValue
    })
  }
})

const PureTextEditorStub = defineComponent({
  name: 'PureTextEditorStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit, expose }) {
    expose({
      getViewport: () => ({ cursorPosition: 0, scrollTop: 0 }),
      restoreViewport: vi.fn(),
      focusEditor: vi.fn(),
      insertPlainTextAtSelection: vi.fn()
    })
    return () => h('textarea', {
      class: 'pure-text-editor-stub',
      value: props.modelValue,
      onInput: (event) => emit('update:modelValue', event.target.value)
    })
  }
})

const AssetPanelStub = (name) => defineComponent({
  name,
  setup(_, { expose }) {
    expose({
      saveFocusedDraft: vi.fn(async () => {}),
      discardFocusedDraft: vi.fn()
    })
    return () => h('div', { class: `${name}-stub` }, name)
  }
})

const StatusBarStub = defineComponent({
  name: 'StatusBarStub',
  setup() {
    return () => h('div', { class: 'status-bar-stub' }, '???')
  }
})

const EmptyStub = (name) => defineComponent({
  name,
  setup() {
    return () => h('div', { class: `${name}-stub` }, name)
  }
})

const flushStudio = async () => {
  await flushPromises()
  await nextTick()
  await flushPromises()
  await nextTick()
}

describe('WritingStudio author flow integration', () => {
  let WritingStudio
  let candidateDrafts
  let writingTasks

  beforeEach(async () => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    window.localStorage.clear()
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: webcrypto
    })
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(window, 'prompt').mockReturnValue('??????')
    globalThis.requestAnimationFrame = vi.fn((callback) => {
      callback()
      return 1
    })

    candidateDrafts = []
    writingTasks = [{
      writing_task_id: 'wt_1',
      status: 'ready',
      writing_goal: '??????????????',
      plan_summary: '????????',
      metadata: {}
    }]

    mockV1WorksGet.mockResolvedValue({
      id: 'work-1',
      title: '????',
      author: '????'
    })
    mockV1WorksUpdate.mockResolvedValue({
      id: 'work-1',
      title: '????',
      author: '????'
    })
    mockV1ChaptersList.mockResolvedValue([{
      id: 'chapter-1',
      title: '??? ????',
      content: '??????????????????????????',
      order_index: 1,
      version: 9,
      updated_at: '2026-07-08T09:00:00.000Z'
    }])
    mockV1ChaptersUpdate.mockResolvedValue({})
    mockV1ChaptersCreate.mockResolvedValue({})
    mockV1ChaptersDelete.mockResolvedValue({})
    mockV1ChaptersReorder.mockResolvedValue({ items: [] })
    mockV1ChaptersForceOverride.mockResolvedValue({})
    mockV1SessionsGet.mockResolvedValue({
      last_open_chapter_id: 'chapter-1',
      cursor_position: 0,
      scroll_top: 0,
      updated_at: '2026-07-08T09:00:00.000Z'
    })
    mockV1SessionsSave.mockResolvedValue({
      last_open_chapter_id: 'chapter-1',
      cursor_position: 0,
      scroll_top: 0,
      updated_at: '2026-07-08T09:00:00.000Z'
    })

    mockAIGetSettings.mockResolvedValue({
      data: {
        provider_configs: [{
          provider_name: 'deepseek',
          enabled: true,
          default_model: 'deepseek-chat',
          key_configured: true,
          api_key_masked: 'dee********123',
          last_test_status: 'ok'
        }],
        model_role_mappings: {
          analysis: { provider_name: 'deepseek', model_name: 'deepseek-analysis' },
          planning: { provider_name: 'deepseek', model_name: 'deepseek-plan' },
          writer: { provider_name: 'deepseek', model_name: 'deepseek-writer' },
          reviewer: { provider_name: 'deepseek', model_name: 'deepseek-reviewer' },
          rewriter: { provider_name: 'deepseek', model_name: 'deepseek-rewriter' }
        }
      }
    })
    mockAIGetLatestInitialization.mockResolvedValue({
      data: {
        status: 'completed',
        analyzed_chapter_count: 1,
        empty_chapter_count: 0,
        failed_chapter_count: 0
      }
    })
    mockAIBuildContextPack.mockResolvedValue({
      data: { context_pack_id: 'cp_1', status: 'ready' }
    })
    mockAIGetLatestContextPack.mockResolvedValue({
      data: {
        context_pack_id: 'cp_1',
        context_items: [{ item_id: 'ctx_1', source_type: 'master_arc', summary: '????' }]
      }
    })
    mockAIGetContextPackReadiness.mockResolvedValue({
      data: {
        status: 'ready',
        blocked_reason: '',
        degraded_reason: '',
        warnings: [],
        plot_arc_statuses: {
          master_arc: { status: 'ready' },
          volume_arc: { status: 'ready' },
          sequence_arc: { status: 'ready' },
          immediate_window: { status: 'ready' }
        },
        plot_arc_summary: {
          master_arc: { arc_title: '????', current_stage: '?????', ultimate_goal: '??????' },
          volume_arc: { stage_goal: '?????????', stage_open_loops: ['?????'] },
          sequence_arc: { sequence_goal: '???????', key_events: ['?????'] },
          immediate_window: { active_plot_threads: ['????'], recent_chapters_summary: ['??????'] }
        }
      }
    })
    mockAIStartInitialization.mockResolvedValue({ data: { initialization_id: 'init_1', job_id: 'job_1' } })
    mockAIGetJob.mockResolvedValue({ data: { job_id: 'job_1', status: 'completed', steps: [] } })
    mockAIListAgentSessions.mockResolvedValue({ data: { items: [] } })
    mockAIGetAgentSession.mockResolvedValue({ data: { session_id: 'session_1', status: 'waiting_for_user' } })
    mockAIPauseAgentSession.mockResolvedValue({ data: { status: 'paused' } })
    mockAIResumeAgentSession.mockResolvedValue({ data: { status: 'running' } })
    mockAICancelAgentSession.mockResolvedValue({ data: { status: 'cancelled' } })
    mockAIListPlotArcs.mockResolvedValue({
      data: {
        items: [{ arc_id: 'arc_1', arc_level: 'master_arc', title: '????', status: 'ready', summary: '??????????' }]
      }
    })
    mockAIGetPlotArc.mockResolvedValue({
      data: { arc_id: 'arc_1', arc_level: 'master_arc', title: '????', status: 'ready', key_points: ['???', '??'] }
    })
    mockAIGetPlotArcStatus.mockResolvedValue({
      data: { items: [{ arc_level: 'master_arc', status: 'ready' }] }
    })

    mockAIGenerateDirectionProposal.mockResolvedValue({
      data: { direction_proposal_id: 'dir_2', status: 'waiting_for_selection' }
    })
    mockAIListDirectionProposals.mockResolvedValue({
      data: {
        items: [{
          direction_proposal_id: 'dir_1',
          status: 'waiting_for_selection',
          options: [{
            option_id: 'opt_a',
            label: '?? A',
            plot_summary: '??????????'
          }]
        }]
      }
    })
    mockAISelectDirection.mockResolvedValue({
      data: { selection: { selection_type: 'direct_select' }, proposal: { status: 'selected' } }
    })
    mockAIGenerateChapterPlan.mockResolvedValue({
      data: { chapter_plan_id: 'plan_2', status: 'waiting_for_confirmation' }
    })
    mockAIListChapterPlans.mockResolvedValue({
      data: {
        items: [{
          chapter_plan_id: 'plan_1',
          status: 'waiting_for_confirmation',
          plan_summary: '????????',
          plan_items: [{ item_id: 'pi_1', chapter_goal: '???????' }]
        }]
      }
    })
    mockAIGetChapterPlan.mockResolvedValue({
      data: {
        chapter_plan_id: 'plan_1',
        status: 'waiting_for_confirmation',
        plan_items: [{ item_id: 'pi_1', chapter_goal: '???????' }]
      }
    })
    mockAIConfirmChapterPlan.mockImplementation(async () => ({
      data: {
        confirmation: { confirmation_type: 'direct_confirm' },
        plan: { status: 'confirmed' },
        writing_task: writingTasks[0]
      }
    }))
    mockAIRejectChapterPlan.mockResolvedValue({ data: { status: 'rejected' } })
    mockAIListWritingTasks.mockImplementation(async () => ({
      data: { items: writingTasks }
    }))
    mockAIGetWritingTask.mockResolvedValue({
      data: {
        writing_task_id: 'wt_1',
        status: 'ready',
        writing_goal: '??????????????',
        must_include: ['????'],
        must_not_include: ['????????'],
        plan_summary: '????????',
        metadata: {}
      }
    })
    mockAIConfirmWritingTask.mockImplementation(async () => {
      writingTasks = [{
        ...writingTasks[0],
        metadata: {
          user_confirmed: true,
          confirmed_by: 'ui-user'
        }
      }]
      return {
        data: {
          writing_task_id: 'wt_1',
          status: 'ready',
          metadata: writingTasks[0].metadata
        }
      }
    })

    mockAIStartContinuation.mockImplementation(async () => {
      candidateDrafts = [{
        candidate_draft_id: 'cd_1',
        content_preview: '?????',
        validation_status: 'passed',
        selected_version_id: 'ver_1',
        accepted_version_id: '',
        applied_version_id: '',
        source_context_pack_id: 'cp_1'
      }]
      return {
        data: {
          job_id: 'job_candidate_1',
          candidate_draft_id: 'cd_1',
          status: 'completed_with_candidate'
        }
      }
    })
    mockAIListCandidateDrafts.mockImplementation(async () => ({
      data: { items: candidateDrafts }
    }))
    mockAIGetCandidateDraft.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        content: '???????',
        selected_version_id: 'ver_1',
        accepted_version_id: 'ver_1',
        applied_version_id: ''
      }
    })
    mockAIListCandidateDraftVersions.mockResolvedValue({
      data: {
        items: [{ candidate_version_id: 'ver_1', version_no: 1, status: 'review_completed', content_summary: '??' }]
      }
    })
    mockAIGetCandidateDraftVersion.mockResolvedValue({
      data: {
        candidate_version_id: 'ver_1',
        content: '???????',
        content_summary: '??',
        status: 'review_completed'
      }
    })
    mockAIGetCandidateDraftVersionDiff.mockResolvedValue({
      data: {
        summary: '??????',
        diff_preview: ['+ ????']
      }
    })
    mockAISelectCandidateDraftVersion.mockResolvedValue({
      data: {
        candidate_draft_id: 'cd_1',
        selected_version_id: 'ver_1',
        accepted_version_id: 'ver_1',
        applied_version_id: ''
      }
    })
    mockAIAcceptCandidateDraft.mockResolvedValue({ data: { status: 'accepted' } })
    mockAIRejectCandidateDraft.mockResolvedValue({ data: { status: 'rejected' } })
    mockAIApplyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })
    mockAIReviewCandidateDraft.mockResolvedValue({ data: { review_id: 'rv_1', summary: '????' } })
    mockAIGetAIReview.mockResolvedValue({ data: { review_id: 'rv_1', summary: '????', issues: [] } })
    mockAIRewriteCandidateDraft.mockResolvedValue({ data: { target_version: { candidate_version_id: 'ver_2' } } })
    mockAIRejectCandidateDraftVersion.mockResolvedValue({ data: { status: 'rejected' } })

    mockAIListAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'ais_1',
          suggestion_type: 'rewrite_suggestion',
          severity: 'warning',
          title: '??????',
          summary: '???????????????',
          status: 'shown'
        }]
      }
    })
    mockAIGetAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'ais_1',
        summary: '??????????????????????'
      }
    })
    mockAIAcceptAISuggestion.mockResolvedValue({ data: { status: 'accepted' } })
    mockAIDismissAISuggestion.mockResolvedValue({ data: { status: 'dismissed' } })
    mockAIConvertAISuggestion.mockResolvedValue({ data: { status: 'converted' } })
    mockAIListConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cgr_1',
          candidate_draft_id: 'cd_1',
          candidate_version_id: 'ver_1',
          conflict_type: 'continuity_conflict',
          severity: 'warning',
          title: '????????',
          summary: '??????????????????????'
        }]
      }
    })
    mockAIGetConflict.mockResolvedValue({ data: { record_id: 'cgr_1', summary: '??????????' } })
    mockAIDecideConflict.mockResolvedValue({ data: { status: 'acknowledged' } })
    mockAIListMemoryGates.mockResolvedValue({
      data: {
        items: [{
          gate_id: 'mg_1',
          state: 'waiting_for_user',
          suggestions: [{
            id: 'mus_1',
            target_memory_type: 'story_memory',
            revision_type: 'foreshadow_update',
            status: 'shown',
            current_value_summary: '????????',
            proposed_value_summary: '?????????????'
          }],
          revision_ids: ['mr_1']
        }]
      }
    })
    mockAIGetMemoryRevision.mockResolvedValue({ data: { revision_id: 'mr_1', status: 'applied', summary: '???????' } })
    mockAIApproveMemorySuggestion.mockResolvedValue({ data: { status: 'approved' } })
    mockAIEditApproveMemorySuggestion.mockResolvedValue({ data: { status: 'approved' } })
    mockAIRejectMemorySuggestion.mockResolvedValue({ data: { status: 'rejected' } })
    mockAIDeferMemorySuggestion.mockResolvedValue({ data: { status: 'shown' } })
    mockAIApplyMemoryGate.mockResolvedValue({ data: { revision_ids: ['mr_1'] } })
    mockAIRollbackMemoryRevision.mockResolvedValue({ data: { status: 'superseded' } })
    mockAIListAgentTraces.mockResolvedValue({
      data: {
        items: [{
          trace_id: 'trace_1',
          workflow_type: 'continuation',
          status: 'waiting_for_user',
          total_steps: 5,
          total_tokens: 1800
        }]
      }
    })
    mockAIGetAgentTrace.mockResolvedValue({ data: { trace_id: 'trace_1', status: 'waiting_for_user' } })
    mockAIGetAgentTraceSteps.mockResolvedValue({
      data: {
        items: [{
          step_id: 'step_1',
          agent_type: 'reviewer',
          action: 'review_candidate',
          status: 'completed'
        }]
      }
    })
    mockAIGetAgentTraceDetailView.mockResolvedValue({ data: { items: [] } })

    WritingStudio = (await import('../WritingStudio.vue')).default
  })

  it('runs the author path from planning to suggestion, memory, trace, and candidate apply through the real workspace tabs', async () => {
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          PureTextEditor: PureTextEditorStub,
          OutlinePanel: AssetPanelStub('OutlinePanel'),
          TimelinePanel: AssetPanelStub('TimelinePanel'),
          ForeshadowPanel: AssetPanelStub('ForeshadowPanel'),
          CharacterPanel: AssetPanelStub('CharacterPanel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: EmptyStub('VersionConflictModal'),
          SelectionRewriteDiffModal: EmptyStub('SelectionRewriteDiffModal'),
          SelectionRewriteToolbar: EmptyStub('SelectionRewriteToolbar'),
          MentionPopup: EmptyStub('MentionPopup'),
          WritingPreferencePanel: EmptyStub('WritingPreferencePanel'),
          FocusModeToggle: EmptyStub('FocusModeToggle'),
          ManualSyncButton: EmptyStub('ManualSyncButton'),
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()

    wrapper.findComponent({ name: 'RightWorkspacePanel' }).vm.$emit('update:model-value', 'ai')
    await flushStudio()
    expect(wrapper.text()).toContain('方向推演')
    expect(wrapper.text()).toContain('章节计划')
    expect(wrapper.text()).toContain('写作任务')

    await wrapper.get('[data-test="ai-generate-directions"]').trigger('click')
    expect(mockAIGenerateDirectionProposal).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="select-direction-dir_1-opt_a"]').trigger('click')
    expect(mockAISelectDirection).toHaveBeenCalledWith('dir_1', expect.objectContaining({
      selected_option_id: 'opt_a',
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="generate-plan-dir_1"]').trigger('click')
    expect(mockAIGenerateChapterPlan).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      direction_proposal_id: 'dir_1',
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="confirm-plan-plan_1"]').trigger('click')
    expect(mockAIConfirmChapterPlan).toHaveBeenCalledWith('plan_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="writing-task-detail-wt_1"]').trigger('click')
    expect(mockAIGetWritingTask).toHaveBeenCalledWith('wt_1')

    await wrapper.get('[data-test="writing-task-confirm-wt_1"]').trigger('click')
    expect(mockAIConfirmWritingTask).toHaveBeenCalledWith('wt_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await flushStudio()
    await wrapper.get('[data-test="ai-start-continuation"]').trigger('click')
    expect(mockAIStartContinuation).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await flushStudio()
    wrapper.findComponent({ name: 'RightWorkspacePanel' }).vm.$emit('update:model-value', 'review')
    await flushStudio()
    expect(wrapper.text()).toContain('候选稿与人工确认门')
    expect(wrapper.text()).toContain('AI 建议')
    expect(wrapper.text()).toContain('记忆审批')
    expect(wrapper.text()).toContain('任务追踪')

    await wrapper.get('[data-test="candidate-detail-cd_1"]').trigger('click')
    expect(mockAIGetCandidateDraft).toHaveBeenCalledWith('cd_1')

    await wrapper.get('[data-test="candidate-review-cd_1"]').trigger('click')
    expect(mockAIReviewCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="suggestion-detail-ais_1"]').trigger('click')
    expect(mockAIGetAISuggestion).toHaveBeenCalledWith('ais_1')

    await wrapper.get('[data-test="suggestion-accept-ais_1"]').trigger('click')
    expect(mockAIAcceptAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="suggestion-convert-ais_1"]').trigger('click')
    expect(mockAIConvertAISuggestion).toHaveBeenCalledWith('ais_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="conflict-detail-cgr_1"]').trigger('click')
    expect(mockAIGetConflict).toHaveBeenCalledWith('cgr_1')

    await wrapper.get('[data-test="conflict-ack-cgr_1"]').trigger('click')
    expect(mockAIDecideConflict).toHaveBeenCalledWith('cgr_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      decision: 'acknowledged',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="memory-approve-mg_1-mus_1"]').trigger('click')
    expect(mockAIApproveMemorySuggestion).toHaveBeenCalledWith('mg_1', 'mus_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="memory-edit-approve-mg_1-mus_1"]').trigger('click')
    expect(mockAIEditApproveMemorySuggestion).toHaveBeenCalledWith('mg_1', 'mus_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      proposed_value_summary: '??????',
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="memory-apply-mg_1"]').trigger('click')
    expect(mockAIApplyMemoryGate).toHaveBeenCalledWith('mg_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="memory-revision-detail-mr_1"]').trigger('click')
    expect(mockAIGetMemoryRevision).toHaveBeenCalledWith('mr_1')

    await wrapper.get('[data-test="trace-steps-trace_1"]').trigger('click')
    expect(mockAIGetAgentTraceSteps).toHaveBeenCalledWith('trace_1')

    await wrapper.get('[data-test="candidate-accept-cd_1"]').trigger('click')
    expect(mockAIAcceptCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))

    await wrapper.get('[data-test="candidate-apply-cd_1"]').trigger('click')
    expect(mockAIApplyCandidateDraft).toHaveBeenCalledWith('cd_1', expect.objectContaining({
      expected_chapter_version: 9,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))
  })
})
