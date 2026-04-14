import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/stores/workspace'
import WorkspaceWritingStudio from '../WorkspaceWritingStudio.vue'
import IssuePanelCard from '@/components/story/IssuePanelCard.vue'

const mockSetContent = vi.fn()
const mockFocus = vi.fn()
const mockSetTextSelection = vi.fn()
const mockDispatch = vi.fn()
const mockSetMeta = vi.fn()
const mockTransaction = { meta: {} }
const mockScrollIntoView = vi.fn()
let lastEditorOptions = null
const mockEditorInstance = {
  commands: {
    setContent: mockSetContent,
    focus: mockFocus,
    setTextSelection: mockSetTextSelection
  },
  getText: vi.fn(() => 'test content'),
  state: {
    selection: {
      empty: true,
      from: 0,
      to: 0
    },
    tr: {
      setMeta: mockSetMeta
    },
    doc: {
      textBetween: vi.fn(() => ''),
      descendants: (callback) => {
        callback({ isText: true, text: 'test content' }, 0)
      }
    }
  },
  view: {
    dispatch: mockDispatch
  },
  destroy: vi.fn()
}
const mockWorkspaceContext = {
  state: {
    editor: {
      chapter: { id: '1', title: 'Chapter 1', content: 'test content' },
      loading: false,
      saving: false,
      aiRunning: false,
      dirty: false,
      chapterTask: { chapter_function: 'advance_investigation', goals: ['追踪线索'] },
      chapterArcs: [{ arc_id: 'arc-1', title: '主线追踪', binding_role: 'primary', arc_type: 'main_arc', current_stage: 'escalation', status: 'active' }],
      contextMeta: {},
      integrityCheck: {
        issue_list: [
          { code: 'continuity', severity: 'high', title: 'test', detail: '连续性不足' }
        ]
      },
      structuralDraft: null,
      detemplatedDraft: null,
      activeDraftTab: 'structural',
      resultState: {
        latestTaskId: '',
        latestAction: '',
        latestResultType: 'none',
        latestDraftType: '',
        lastDecision: 'idle',
        lastUpdatedAt: '',
        latestIssueCount: 1,
        lastError: ''
      }
    },
    projectId: 'proj-1',
    markEditorDirty: vi.fn()
  },
  currentChapterId: { value: '1' },
  loadEditorChapter: vi.fn(),
  saveEditorChapter: vi.fn(),
  runEditorAiAction: vi.fn(),
  openSection: vi.fn()
}

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ query: { chapterId: '1' } })),
  useRouter: vi.fn(() => ({ push: vi.fn() }))
}))

// Mock TipTap
vi.mock('@tiptap/vue-3', () => ({
  EditorContent: { template: '<div class="mock-editor-content"></div>' },
  useEditor: vi.fn((options) => {
    lastEditorOptions = options
    return { value: mockEditorInstance }
  })
}))

vi.mock('@tiptap/vue-3/menus', () => ({
  BubbleMenu: {
    template: '<div class="mock-bubble-menu"><slot /></div>'
  }
}))

// Mock composable
vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => mockWorkspaceContext)
}))

describe('WorkspaceWritingStudio.vue', () => {
  let wrapper

  beforeEach(() => {
    mockSetContent.mockClear()
    mockFocus.mockClear()
    mockSetTextSelection.mockClear()
    mockDispatch.mockClear()
    mockSetMeta.mockClear()
    mockScrollIntoView.mockClear()
    lastEditorOptions = null
    mockEditorInstance.state.selection = { empty: true, from: 0, to: 0 }
    mockEditorInstance.state.doc.textBetween.mockReset()
    mockEditorInstance.state.doc.textBetween.mockReturnValue('')
    mockSetMeta.mockImplementation((key, payload) => {
      mockTransaction.meta = { key, payload }
      return mockTransaction
    })
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: mockScrollIntoView
    })
    mockWorkspaceContext.runEditorAiAction.mockClear()
    const pinia = createPinia()
    setActivePinia(pinia)
    const workspaceStore = useWorkspaceStore()
    workspaceStore.currentView = 'writing'
    workspaceStore.isZenMode = false

    wrapper = mount(WorkspaceWritingStudio, {
      global: {
        plugins: [pinia],
        stubs: [
          'el-button',
          'el-skeleton',
          'el-empty',
          'el-icon',
          'el-tooltip',
          'el-card',
          'el-tag',
          'el-alert',
          'el-tabs',
          'el-tab-pane',
          'el-descriptions',
          'el-descriptions-item',
          'el-collapse',
          'el-collapse-item'
        ],
        directives: {
          loading: () => {}
        },
        mocks: {
          $route: { query: { chapterId: '1' } },
          $router: { push: vi.fn() }
        }
      }
    })
  })

  it('renders the editor surface without side context cards', () => {
    expect(wrapper.find('.editor-surface').exists()).toBe(true)
    expect(wrapper.find('.writing-inspector').exists()).toBe(true)
    
    // According to the new UI spec, side cards like context-column should be removed from the center area
    expect(wrapper.find('.context-column').exists()).toBe(false)
  })

  it('renders a clean top bar and title input', () => {
    expect(wrapper.find('.chapter-title-input').exists()).toBe(true)
  })

  it('renders the writing inspector with task and arc summaries', () => {
    const text = wrapper.text()
    expect(text).toContain('写作状态')
    expect(text).toContain('本章剧情弧')
    expect(text).toContain('回到概览')
    expect(text).toContain('章节状态')
  })

  it('renders top-level writing object actions', () => {
    expect(wrapper.text()).toContain('章节管理')
    expect(wrapper.text()).toContain('查看目标弧')
    expect(wrapper.text()).toContain('重新审查')
  })

  it('shows issue panel with rendered issue items', async () => {
    expect(wrapper.text()).toContain('问题单')
    const issuePanel = wrapper.findComponent(IssuePanelCard)
    expect(issuePanel.exists()).toBe(true)
    expect(wrapper.find('.issue-item').exists()).toBe(true)
    const objectActions = issuePanel.props('objectActions')
    expect(Array.isArray(objectActions)).toBe(true)
    expect(objectActions.map((item) => item.label)).toContain('章节管理')
    expect(objectActions.map((item) => item.label)).toContain('查看目标弧')
  })

  it('renders unified result state banner for pending drafts', async () => {
    mockWorkspaceContext.state.editor.structuralDraft = {
      title: 'Chapter 1',
      content: '候选稿内容'
    }
    mockWorkspaceContext.state.editor.resultState = {
      latestTaskId: 'task-1',
      latestAction: 'continue',
      latestResultType: 'candidate',
      latestDraftType: 'structural',
      lastDecision: 'pending',
      lastUpdatedAt: new Date().toISOString(),
      latestIssueCount: 0,
      lastError: ''
    }

    wrapper = mount(WorkspaceWritingStudio, {
      global: {
        plugins: [createPinia()],
        stubs: [
          'el-button', 'el-skeleton', 'el-empty', 'el-icon', 'el-tooltip',
          'el-card', 'el-tag', 'el-alert', 'el-tabs', 'el-tab-pane',
          'el-descriptions', 'el-descriptions-item', 'el-collapse', 'el-collapse-item'
        ],
        directives: { loading: () => {} },
        mocks: {
          $route: { query: { chapterId: '1' } },
          $router: { push: vi.fn() }
        }
      }
    })

    expect(wrapper.text()).toContain('最近回流：候选稿')
    expect(wrapper.text()).toContain('结果状态')
    expect(wrapper.text()).toContain('候选稿 · 待处理')
  })

  it('shows a real selection bubble and seeds copilot draft from selected text', async () => {
    const workspaceStore = useWorkspaceStore()
    mockEditorInstance.state.selection = {
      empty: false,
      from: 1,
      to: 6
    }
    mockEditorInstance.state.doc.textBetween.mockReturnValue('这是一段选中的正文')

    lastEditorOptions.onSelectionUpdate({ editor: mockEditorInstance })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('解释片段')
    expect(wrapper.text()).toContain('改写片段')
    expect(wrapper.text()).toContain('审查片段')

    const rewriteButton = wrapper.findAll('button').find((node) => node.text().includes('改写片段'))
    await rewriteButton.trigger('click')

    expect(workspaceStore.isCopilotOpen).toBe(true)
    expect(workspaceStore.currentCopilotTab).toBe('chat')
    expect(workspaceStore.copilotChatDraft).toContain('这是一段选中的正文')
    expect(workspaceStore.copilotChatDraft).toContain('改写方案')
  })

  it('renders an inline candidate block inside the editor area', async () => {
    mockWorkspaceContext.state.editor.chapter.content = '原始正文第一段。'
    mockWorkspaceContext.state.editor.structuralDraft = {
      title: 'Chapter 1',
      content: '这是新增续写内容。',
      full_content: '原始正文第一段。\n这是新增续写内容。',
      preview_mode: 'delta'
    }
    mockWorkspaceContext.state.editor.resultState = {
      latestTaskId: 'task-2',
      latestAction: 'continue',
      latestResultType: 'candidate',
      latestDraftType: 'structural',
      lastDecision: 'pending',
      lastUpdatedAt: new Date().toISOString(),
      latestIssueCount: 0,
      lastError: ''
    }

    wrapper = mount(WorkspaceWritingStudio, {
      global: {
        plugins: [createPinia()],
        stubs: [
          'el-button', 'el-skeleton', 'el-empty', 'el-icon', 'el-tooltip',
          'el-card', 'el-tag', 'el-alert', 'el-tabs', 'el-tab-pane',
          'el-descriptions', 'el-descriptions-item', 'el-collapse', 'el-collapse-item'
        ],
        directives: { loading: () => {} },
        mocks: {
          $route: { query: { chapterId: '1' } },
          $router: { push: vi.fn() }
        }
      }
    })

    expect(wrapper.text()).toContain('行内候选块')
    expect(wrapper.text()).toContain('这是新增续写内容。')
    expect(wrapper.text()).toContain('插入正文末尾')
  })

  it('renders an inline diff block for detemplated drafts', async () => {
    mockWorkspaceContext.state.editor.chapter.content = '原始正文第一段。\n原始正文第二段。'
    mockWorkspaceContext.state.editor.detemplatedDraft = {
      title: 'Chapter 1',
      content: '改写后第一段。\n改写后第二段。',
      full_content: '改写后第一段。\n改写后第二段。',
      preview_mode: 'full',
      display_fallback_to_structural: false
    }
    mockWorkspaceContext.state.editor.resultState = {
      latestTaskId: 'task-3',
      latestAction: 'rewrite',
      latestResultType: 'diff',
      latestDraftType: 'detemplated',
      lastDecision: 'pending',
      lastUpdatedAt: new Date().toISOString(),
      latestIssueCount: 0,
      lastError: ''
    }

    wrapper = mount(WorkspaceWritingStudio, {
      global: {
        plugins: [createPinia()],
        stubs: [
          'el-button', 'el-skeleton', 'el-empty', 'el-icon', 'el-tooltip',
          'el-card', 'el-tag', 'el-alert', 'el-tabs', 'el-tab-pane',
          'el-descriptions', 'el-descriptions-item', 'el-collapse', 'el-collapse-item'
        ],
        directives: { loading: () => {} },
        mocks: {
          $route: { query: { chapterId: '1' } },
          $router: { push: vi.fn() }
        }
      }
    })

    expect(wrapper.text()).toContain('行内改写对照')
    expect(wrapper.text()).toContain('原正文')
    expect(wrapper.text()).toContain('改写结果')
    expect(wrapper.text()).toContain('改写后第一段。')
  })

  it('switches into draft result focus when workspace focuses a writing result object', async () => {
    const workspaceStore = useWorkspaceStore()
    mockWorkspaceContext.state.editor.structuralDraft = {
      title: 'Chapter 1',
      content: '候选稿内容'
    }
    workspaceStore.focusWritingResult({
      chapterId: '1',
      resultType: 'candidate',
      taskId: 'task-1'
    }, { openView: false })
    await wrapper.vm.$nextTick()

    expect(mockWorkspaceContext.state.editor.activeDraftTab).toBe('structural')
    expect(workspaceStore.currentObject).toMatchObject({
      type: 'writing-result',
      chapterId: '1',
      resultType: 'candidate'
    })
  })

  it('dispatches temporary highlight when locating an issue', async () => {
    const issuePanel = wrapper.findComponent(IssuePanelCard)
    await issuePanel.vm.$emit('locate', {
      issue: { code: 'continuity', severity: 'high', title: 'test', detail: '连续性不足' },
      index: 0
    })
    expect(mockSetMeta).toHaveBeenCalled()
    expect(mockDispatch).toHaveBeenCalled()
    expect(mockSetTextSelection).toHaveBeenCalled()
    const workspaceStore = useWorkspaceStore()
    expect(workspaceStore.currentObject).toMatchObject({
      type: 'issue',
      index: 0,
      code: 'continuity',
      title: 'test',
      chapterId: '1'
    })
  })

  it('prefers explicit issue range when provided', async () => {
    const issuePanel = wrapper.findComponent(IssuePanelCard)
    await issuePanel.vm.$emit('locate', {
      issue: { code: 'continuity', severity: 'high', title: 'test', detail: '连续性不足', from: 3, to: 8 },
      index: 0
    })

    expect(mockSetTextSelection).toHaveBeenCalledWith({ from: 3, to: 8 })
  })

  it('previews issue highlight on hover and restores persistent highlight on leave', async () => {
    const issuePanel = wrapper.findComponent(IssuePanelCard)
    const initialCalls = mockSetMeta.mock.calls.length

    await issuePanel.vm.$emit('preview', {
      issue: { code: 'continuity', severity: 'high', title: 'test', detail: '连续性不足' },
      index: 0
    })
    expect(mockSetMeta.mock.calls.length).toBeGreaterThan(initialCalls)

    const workspaceStore = useWorkspaceStore()
    workspaceStore.setCurrentObject({ type: 'issue', index: 0, code: 'continuity', title: 'test' })
    await wrapper.vm.$nextTick()

    const afterPersistent = mockSetMeta.mock.calls.length
    await issuePanel.vm.$emit('preview-leave', {
      issue: { code: 'continuity', severity: 'high', title: 'test', detail: '连续性不足' },
      index: 0
    })
    expect(mockSetMeta.mock.calls.length).toBeGreaterThanOrEqual(afterPersistent)
  })

  it('routes to structure when issue object action emits arc payload', async () => {
    const workspaceStore = useWorkspaceStore()
    const issuePanel = wrapper.findComponent(IssuePanelCard)
    await issuePanel.vm.$emit('action', {
      type: 'arc',
      arcId: 'arc-1',
      title: '主线追踪'
    })

    expect(workspaceStore.currentView).toBe('structure')
    expect(workspaceStore.currentObject).toEqual({
      type: 'plot_arc',
      arcId: 'arc-1',
      title: '主线追踪'
    })
  })

  it('re-runs analyze action from writing object action strip', async () => {
    const analyzeButton = wrapper.findAll('button').find((node) => node.text().includes('重新审查'))
    expect(analyzeButton).toBeTruthy()
    await analyzeButton.trigger('click')
    expect(mockWorkspaceContext.runEditorAiAction).toHaveBeenCalledWith('analyze')
  })

  it('provides workspace-level action chips', async () => {
    const tasksChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('打开任务台'))
    await tasksChip.trigger('click')
    expect(mockWorkspaceContext.openSection).toHaveBeenCalledWith('tasks')
  })
})
