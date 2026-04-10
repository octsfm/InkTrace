import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/stores/workspace'
import NovelWorkspace from '../NovelWorkspace.vue'

const mockRoute = { params: { id: '1' }, query: {} }

const mockMemoryViewV2 = vi.fn(async () => ({ current_state: '真实上下文：角色冲突升级', main_plot_lines: ['主线必须继续升级'] }))
const mockContinuationContextV2 = vi.fn(async () => ({ last_chapter_tail: '上一章结尾停在冲突升级前夕。', relevant_foreshadowing: ['神秘来信'] }))

vi.mock('@/api', () => ({
  novelApi: {
    get: vi.fn(),
    listChapters: vi.fn()
  },
  projectApi: {
    memoryViewV2: (...args) => mockMemoryViewV2(...args),
    continuationContextV2: (...args) => mockContinuationContextV2(...args)
  }
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => mockRoute),
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() }))
}))

// Mock child components
vi.mock('../WorkspaceOverview.vue', () => ({ default: { name: 'WorkspaceOverview', template: '<div class="workspace-overview-mock">Overview</div>' } }))
vi.mock('../WorkspaceWritingStudio.vue', () => ({ default: { name: 'WorkspaceWritingStudio', template: '<div class="workspace-writing-mock">Writing</div>' } }))
vi.mock('../WorkspaceStructureStudio.vue', () => ({ default: { name: 'WorkspaceStructureStudio', template: '<div class="workspace-structure-mock">Structure</div>' } }))
vi.mock('../WorkspaceChapterManager.vue', () => ({ default: { name: 'WorkspaceChapterManager', template: '<div class="workspace-chapter-mock">Chapters</div>' } }))
vi.mock('../WorkspaceTasksAudit.vue', () => ({ default: { name: 'WorkspaceTasksAudit', template: '<div class="workspace-tasks-mock">Tasks</div>' } }))
vi.mock('@/components/workspace/WorkspaceSidebar.vue', () => ({ default: { name: 'WorkspaceSidebar', template: '<div class="workspace-sidebar-mock">Sidebar</div>' } }))
vi.mock('@/components/workspace/WorkspaceCopilotPanel.vue', () => ({ default: { name: 'WorkspaceCopilotPanel', template: '<div class="workspace-copilot-mock">Copilot</div>' } }))
vi.mock('@/components/workspace/WorkspaceTopBar.vue', () => ({ default: { name: 'WorkspaceTopBar', template: '<div class="workspace-topbar-mock">TopBar</div>' } }))
vi.mock('@/components/workspace/WorkspaceCommandPalette.vue', () => ({ default: { name: 'WorkspaceCommandPalette', props: ['visible'], template: '<div v-if="visible" class="workspace-command-palette-mock">CommandPalette</div>' } }))
vi.mock('@/stores/novelWorkspace', () => ({
  useNovelWorkspaceStore: vi.fn(() => ({
    novel: { title: '测试小说' },
    chapters: [{ id: 'chapter-1', chapter_number: 1, title: '第一章', updated_at: '2026-04-09T00:00:00Z' }],
    activeArcs: [],
    memoryView: {},
    projectId: 'project-1',
    project: { id: 'project-1' },
    chapterTasks: [
      {
        id: 'task-1',
        task_type: 'audit',
        title: '章节审查',
        status: 'failed',
        chapter_id: 'chapter-1',
        error_message: '审查失败'
      }
    ],
    organizeProgress: {},
    loading: false,
    editor: {
      chapter: { id: 'chapter-1', title: '第一章', content: 'test content' },
      saving: false,
      dirty: false,
      aiRunning: false,
      contextMeta: {},
      integrityCheck: {
        issue_list: [
          { title: '连续性风险', detail: '角色动机需要补强', severity: 'high' }
        ]
      }
    },
    loadBase: vi.fn(),
    loadStructure: vi.fn(),
    syncChapterSnapshot: vi.fn(),
    loadEditorChapter: vi.fn(),
    saveEditorChapter: vi.fn(),
    runEditorAiAction: vi.fn(),
    applyDraftToEditor: vi.fn(),
    saveDraftResult: vi.fn(),
    discardDraft: vi.fn()
  }))
}))

describe('NovelWorkspace.vue', () => {
  let wrapper
  let store

  const mountComponent = () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    store = useWorkspaceStore()
    store.currentView = 'overview'
    store.isZenMode = false
    store.isCopilotOpen = true
    store.currentCopilotTab = 'context'

    wrapper = mount(NovelWorkspace, {
      global: {
        plugins: [pinia],
        stubs: ['el-icon', 'el-tooltip', 'el-button', 'el-alert'],
        mocks: {
          $route: {
            params: { id: '1' }
          },
          $router: {
            push: vi.fn(),
            replace: vi.fn()
          }
        }
      }
    })
  }

  beforeEach(() => {
    mockRoute.params = { id: '1' }
    mockRoute.query = {}
    mockMemoryViewV2.mockClear()
    mockContinuationContextV2.mockClear()
    mountComponent()
  })

  it('renders the workspace layout with default overview view', () => {
    // Should have left nav
    expect(wrapper.find('.workspace-nav-bar').exists()).toBe(true)
    expect(wrapper.find('.workspace-topbar-mock').exists()).toBe(true)
    
    // Should render Overview mock based on activeView
    expect(wrapper.find('.workspace-overview-mock').exists()).toBe(true)
    expect(wrapper.find('.workspace-writing-mock').exists()).toBe(false)
  })

  it('switches to writing view when store activeView changes', async () => {
    store.currentView = 'writing'
    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('.workspace-writing-mock').exists()).toBe(true)
    expect(wrapper.find('.workspace-overview-mock').exists()).toBe(false)
  })

  it('hides left nav when zen mode is enabled', async () => {
    store.currentView = 'writing'
    store.isZenMode = true
    await wrapper.vm.$nextTick()
    
    // In Vue Test Utils, elements with v-show=false still exist but are not visible
    expect(wrapper.find('.workspace-nav-bar').classes()).toContain('hidden-in-zen')
    expect(wrapper.find('.workspace-copilot-mock').isVisible()).toBe(false)
  })

  it('opens command palette with ctrl+k shortcut', async () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.workspace-command-palette-mock').exists()).toBe(true)
  })

  it('records recent command when command palette executes an item', async () => {
    const item = {
      id: 'view-structure',
      title: '打开 Structure',
      subtitle: '查看结构摘要和剧情弧',
      group: '视图',
      hint: '',
      action: { type: 'section', section: 'structure', object: { type: 'plot_arc' } }
    }

    await wrapper.vm.handleCommandExecute(item)
    expect(store.recentCommandItems[0]).toMatchObject({
      id: 'view-structure',
      title: '打开 Structure'
    })
  })

  it('includes expanded object commands in command palette items', () => {
    store.openDocuments = [
      { type: 'chapter', id: 'chapter-1', title: '第一章', lastOpenedAt: Date.now() - 60 * 1000 }
    ]
    store.currentObject = { type: 'chapter', id: 'chapter-1', title: '第一章' }
    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('story-model')
    expect(itemIds).toContain('copilot-chat')
    expect(itemIds.some((id) => id.startsWith('recent-doc-chapter-chapter-1'))).toBe(true)
    expect(itemIds).toContain('issue-0')
  })

  it('records recent plot arc objects into recent open commands', async () => {
    store.setCurrentObject({ type: 'plot_arc', arcId: 'arc-1', title: '主线追踪' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.commandPaletteItems.some((item) => item.id.startsWith('recent-doc-plot_arc-arc-1'))).toBe(true)
  })

  it('prioritizes current object command when query is empty', async () => {
    store.currentObject = { type: 'chapter', id: 'chapter-1', title: '第一章' }
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.filteredCommandPaletteItems[0].id).toBe('current-object-chapter-chapter-1')
  })

  it('prioritizes stronger title matches when searching command palette', async () => {
    wrapper.vm.commandPaletteQuery = 'story'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.filteredCommandPaletteItems[0].id).toBe('story-model')
  })

  it('builds copilot chat reply with remote context when available', async () => {
    store.currentChapterId = 'chapter-1'
    await wrapper.vm.handleCopilotChatSubmit('下一步应该怎么继续？')
    expect(mockMemoryViewV2).toHaveBeenCalled()
    expect(mockContinuationContextV2).toHaveBeenCalled()
    expect(store.copilotChatMessages.some((item) => item.role === 'assistant' && item.content.includes('主线必须继续升级'))).toBe(true)
  })

  it('builds overview decision cards from workspace context state', () => {
    expect(wrapper.vm.overviewDecisionCards[0].key).toBe('issue-review')
    expect(wrapper.vm.overviewDecisionCards.some((item) => item.key === 'structure-focus')).toBe(true)
  })

  it('builds unified task cards from organize progress and chapter tasks', () => {
    expect(wrapper.vm.unifiedTaskCards.some((item) => item.id === 'organize-task')).toBe(true)
    expect(wrapper.vm.unifiedTaskCards.some((item) => item.id === 'task-1' && item.type === 'audit')).toBe(true)
    expect(wrapper.vm.taskStatusCards[2].label).toBe('失败任务')
    expect(wrapper.vm.unifiedTaskCards.find((item) => item.id === 'task-1')?.action).toEqual({
      type: 'chapter',
      chapterId: 'chapter-1'
    })
  })

  it('builds task recommendations and grouped task sections', () => {
    expect(wrapper.vm.taskRecommendationItems[0].key).toBeTruthy()
    expect(wrapper.vm.groupedTaskSections.some((item) => item.key === 'failed')).toBe(true)
  })

  it('adds task counts to filters and exposes failed task shortcut in top bar actions', () => {
    expect(wrapper.vm.taskFilterOptions.find((item) => item.key === 'failed')?.label).toContain('(1)')
    expect(wrapper.vm.topbarObjectActions.some((item) => item.label.includes('失败任务'))).toBe(true)
    expect(wrapper.vm.topbarQuickFacts.some((item) => item.label === '失败任务')).toBe(true)
  })

  it('adds failed-task and audit shortcuts into command palette items', () => {
    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('task-failed-shortcut')
    expect(itemIds).toContain('task-audit-shortcut')
  })

  it('switches to target chat session from command execution', async () => {
    store.copilotChatSessions = [
      { key: 'writing::chapter:chapter-1', label: '第一章', draft: '', messages: [], updatedAt: Date.now() }
    ]
    await wrapper.vm.handleCommandExecute({
      id: 'chat-session-writing::chapter:chapter-1',
      title: '第一章',
      subtitle: '切到该对象的聊天会话',
      group: 'Copilot 会话',
      hint: '会话',
      action: { type: 'chat-session', sessionKey: 'writing::chapter:chapter-1' }
    })

    expect(store.currentCopilotTab).toBe('chat')
    expect(store.currentCopilotChatSessionKey).toBe('writing::chapter:chapter-1')
  })

  it('returns to writing when executing issue command', async () => {
    store.currentChapterId = 'chapter-1'
    await wrapper.vm.handleCommandExecute({
      id: 'issue-0',
      title: '连续性风险',
      subtitle: '在写作页中定位该问题',
      group: '问题单',
      hint: '高优先级',
      action: { type: 'issue', issueIndex: 0 }
    })

    expect(store.currentView).toBe('writing')
  })

})
