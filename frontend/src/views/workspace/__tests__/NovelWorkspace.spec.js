import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/stores/workspace'
import NovelWorkspace from '../NovelWorkspace.vue'
import {
  buildWorkspaceTaskActionPayload,
  buildWorkspaceTaskStatusLabel,
  normalizeWorkspaceTaskStatus
} from '../workspaceTaskModel'

const mockRoute = { params: { id: '1' }, query: {} }

const mockMemoryViewV2 = vi.fn(async () => ({ current_state: '真实上下文：角色冲突升级', main_plot_lines: ['主线必须继续升级'] }))
const mockContinuationContextV2 = vi.fn(async () => ({ last_chapter_tail: '上一章结尾停在冲突升级前夕。', relevant_foreshadowing: ['神秘来信'] }))
const mockBranchesV2 = vi.fn(async () => ({
  branches: [
    {
      id: 'branch-1',
      title: '冲突升级线',
      summary: '主角提前与反派正面碰撞。',
      core_conflict: '信息暴露过早',
      key_progressions: ['冲突升级'],
      related_characters: ['主角'],
      consistency_note: '注意前文铺垫',
      risk_note: '节奏可能过快'
    }
  ]
}))
const mockChapterPlanV2 = vi.fn(async () => ({
  plans: [
    {
      id: 'plan-1',
      title: '第一章推进方案',
      goal: '让主角被迫提前行动',
      ending_hook: '反派留下反向线索',
      chapter_task_seed: {
        chapter_function: '冲突升级',
        must_continue_points: ['必须承接门后异响']
      }
    }
  ]
}))

vi.mock('@/api', () => ({
  novelApi: {
    get: vi.fn(),
    listChapters: vi.fn()
  },
  projectApi: {
    memoryViewV2: (...args) => mockMemoryViewV2(...args),
    continuationContextV2: (...args) => mockContinuationContextV2(...args),
    branchesV2: (...args) => mockBranchesV2(...args),
    chapterPlanV2: (...args) => mockChapterPlanV2(...args)
  }
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => mockRoute),
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() }))
}))

// Mock child components
vi.mock('../WorkspaceOverview.vue', () => ({ default: { name: 'WorkspaceOverview', template: '<div class="workspace-overview-mock">概览</div>' } }))
vi.mock('../WorkspaceWritingStudio.vue', () => ({ default: { name: 'WorkspaceWritingStudio', template: '<div class="workspace-writing-mock">写作</div>' } }))
vi.mock('../WorkspaceStructureStudio.vue', () => ({ default: { name: 'WorkspaceStructureStudio', template: '<div class="workspace-structure-mock">结构</div>' } }))
vi.mock('../WorkspaceChapterManager.vue', () => ({ default: { name: 'WorkspaceChapterManager', template: '<div class="workspace-chapter-mock">章节</div>' } }))
vi.mock('../WorkspaceTasksAudit.vue', () => ({ default: { name: 'WorkspaceTasksAudit', template: '<div class="workspace-tasks-mock">任务</div>' } }))
vi.mock('../WorkspaceSettingsPanel.vue', () => ({ default: { name: 'WorkspaceSettingsPanel', template: '<div class="workspace-settings-mock">设置</div>' } }))
vi.mock('@/components/workspace/WorkspaceSidebar.vue', () => ({ default: { name: 'WorkspaceSidebar', template: '<div class="workspace-sidebar-mock">侧栏</div>' } }))
vi.mock('@/components/workspace/WorkspaceCopilotPanel.vue', () => ({ default: { name: 'WorkspaceCopilotPanel', template: '<div class="workspace-copilot-mock">助手</div>' } }))
vi.mock('@/components/workspace/WorkspaceTopBar.vue', () => ({ default: { name: 'WorkspaceTopBar', template: '<div class="workspace-topbar-mock">顶栏</div>' } }))
vi.mock('@/components/workspace/WorkspaceCommandPalette.vue', () => ({ default: { name: 'WorkspaceCommandPalette', props: ['visible'], template: '<div v-if="visible" class="workspace-command-palette-mock">命令面板</div>' } }))
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
    mockBranchesV2.mockClear()
    mockChapterPlanV2.mockClear()
    mountComponent()
  })

  it('normalizes workspace task status and action payload through shared task model', () => {
    expect(normalizeWorkspaceTaskStatus('error')).toBe('failed')
    expect(buildWorkspaceTaskStatusLabel('done')).toBe('已完成')
    expect(buildWorkspaceTaskActionPayload({
      task_type: 'audit',
      status: 'error'
    })).toEqual({
      type: 'task-filter',
      filter: 'failed'
    })
  })

  it('renders the workspace layout with overview section when requested', async () => {
    mockRoute.query = { section: 'overview' }
    mountComponent()
    await wrapper.vm.$nextTick()

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

  it('switches to settings view when store activeView changes', async () => {
    store.currentView = 'settings'
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.workspace-settings-mock').exists()).toBe(true)
    expect(wrapper.find('.workspace-overview-mock').exists()).toBe(false)
    expect(wrapper.vm.sidebarOverviewCards[0].label).toBe('项目编号')
  })

  it('builds actionable overview sidebar cards and topbar actions', async () => {
    store.currentView = 'overview'
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.sidebarOverviewCards.some((item) => item.key === 'overview-recent-chapter' && item.action?.type === 'chapter')).toBe(true)
    expect(wrapper.vm.sidebarOverviewCards.some((item) => item.key === 'overview-current-task' && item.action?.section === 'tasks')).toBe(true)
    expect(wrapper.vm.resolvedTopbarObjectActions.some((item) => item.label === '继续写作')).toBe(true)
    expect(wrapper.vm.resolvedTopbarObjectActions.some((item) => item.label === '看结构')).toBe(true)
  })

  it('builds actionable settings sidebar cards and recovery action in topbar', async () => {
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 1,
      runningCount: 0,
      completedCount: 0,
      auditCount: 1
    }
    store.currentContextSnapshot = {
      chapterId: 'chapter-1',
      chapterTitle: '第一章',
      contextMeta: { issueCount: 1 }
    }
    store.currentView = 'settings'
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.sidebarOverviewCards.some((item) => item.key === 'settings-failed-tasks' && item.action?.filter === 'failed')).toBe(true)
    expect(wrapper.vm.sidebarOverviewCards.some((item) => item.key === 'settings-issues' && item.action?.type === 'chapter')).toBe(true)
    expect(wrapper.vm.resolvedTopbarObjectActions.some((item) => item.label === '回到写作')).toBe(true)
    expect(wrapper.vm.resolvedTopbarObjectActions.some((item) => item.label === '恢复失败链路')).toBe(true)
  })

  it('uses workspace snapshots for overview quick facts and settings sidebar cards', async () => {
    store.resourceSnapshot = {
      novelId: 'novel-1',
      novelTitle: '风暴将至',
      projectId: 'project-1',
      chapterCount: 3,
      activeChapterId: 'chapter-1',
      hasStructure: true
    }
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 2,
      runningCount: 1,
      completedCount: 3,
      auditCount: 1
    }
    store.currentContextSnapshot = {
      chapterId: 'chapter-1',
      chapterTitle: '第一章',
      contextMeta: { issueCount: 5 }
    }

    store.currentView = 'overview'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.resolvedTopbarQuickFacts.some((item) => item.label === '项目状态' && item.value === '已绑定')).toBe(true)
    expect(wrapper.vm.resolvedTopbarQuickFacts.some((item) => item.label === '失败任务' && item.value === '2')).toBe(true)

    store.currentView = 'settings'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.sidebarOverviewCards.find((item) => item.key === 'settings-project-id')?.value).toBe('project-1')
    expect(wrapper.vm.sidebarOverviewCards.find((item) => item.key === 'settings-failed-tasks')?.value).toBe('2 个')
    expect(wrapper.vm.sidebarOverviewCards.find((item) => item.key === 'settings-issues')?.value).toBe('5 个')
  })

  it('prefers task center snapshot for task quick facts and task status text', async () => {
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 3,
      runningCount: 1,
      completedCount: 0,
      auditCount: 1
    }
    store.currentView = 'tasks'
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.resolvedTopbarQuickFacts.some((item) => item.label === '失败任务' && item.value === '3')).toBe(true)
    expect(wrapper.vm.taskStatusText).toBe('3 个失败任务')
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
      title: '打开结构',
      subtitle: '查看结构摘要和剧情弧',
      group: '视图',
      hint: '',
      action: { type: 'section', section: 'structure', object: { type: 'plot_arc' } }
    }

    await wrapper.vm.handleCommandExecute(item)
    expect(store.recentCommandItems[0]).toMatchObject({
      id: 'view-structure',
      title: '打开结构'
    })
  })

  it('includes settings command in command palette items', () => {
    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('view-settings')
  })

  it('includes expanded object commands in command palette items', () => {
    store.openDocuments = [
      { type: 'chapter', id: 'chapter-1', title: '第一章', lastOpenedAt: Date.now() - 60 * 1000 }
    ]
    store.currentObject = { type: 'chapter', id: 'chapter-1', title: '第一章' }
    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('story-model')
    expect(itemIds).toContain('structure-character')
    expect(itemIds).toContain('structure-worldview')
    expect(itemIds).toContain('structure-risk')
    expect(itemIds).toContain('copilot-chat')
    expect(itemIds).toContain('current-object-chapter-chapter-1')
    expect(itemIds.some((id) => id.startsWith('recent-doc-chapter-chapter-1'))).toBe(false)
    expect(itemIds).toContain('issue-0')
  })

  it('promotes current plot arc object over duplicated recent entry', async () => {
    store.setCurrentObject({ type: 'plot_arc', arcId: 'arc-1', title: '主线追踪' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.commandPaletteItems.some((item) => item.id === 'current-object-arc-arc-1')).toBe(true)
    expect(wrapper.vm.commandPaletteItems.some((item) => item.id.startsWith('recent-doc-plot_arc-arc-1'))).toBe(false)
  })

  it('builds restore commands for recent issue and task objects', async () => {
    store.openDocuments = [
      { type: 'risk', id: 'risk', title: '风险点', lastOpenedAt: Date.now() - 3000 },
      { type: 'issue', id: 'chapter-1::issue-0', title: '连续性风险', chapterId: 'chapter-1', index: 0, code: 'continuity', lastOpenedAt: Date.now() - 2000 },
      { type: 'task', id: 'task-1', title: '章节审查', chapterId: 'chapter-1', status: 'failed', lastOpenedAt: Date.now() - 1000 },
      { type: 'writing-result', id: 'chapter-1::issues', title: '问题结果', chapterId: 'chapter-1', resultType: 'issues', taskId: 'task-1', lastOpenedAt: Date.now() - 500 }
    ]
    await wrapper.vm.$nextTick()

    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds.some((id) => id.startsWith('recent-doc-risk-risk'))).toBe(true)
    expect(itemIds.some((id) => id.startsWith('recent-doc-issue-chapter-1::issue-0'))).toBe(true)
    expect(itemIds.some((id) => id.startsWith('recent-doc-task-task-1'))).toBe(true)
    expect(itemIds.some((id) => id.startsWith('recent-doc-writing-result-chapter-1::issues'))).toBe(true)
  })

  it('adds richer subtitle and hint for recent failed task objects', async () => {
    store.openDocuments = [
      { type: 'task', id: 'task-1', title: '章节审查', chapterId: 'chapter-1', status: 'failed', lastOpenedAt: Date.now() - 1000 }
    ]
    await wrapper.vm.$nextTick()

    const taskItem = wrapper.vm.commandPaletteItems.find((item) => item.id.startsWith('recent-doc-task-task-1'))
    expect(taskItem.subtitle).toContain('恢复该任务对象')
    expect(taskItem.subtitle).toContain('第一章')
    expect(taskItem.hint).toBe('失败')
  })

  it('builds restore commands for current writing result object', async () => {
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::issues',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1',
      title: '问题结果'
    }
    await wrapper.vm.$nextTick()

    const currentItem = wrapper.vm.commandPaletteItems.find((item) => item.id.startsWith('current-object-writing-result-'))
    expect(currentItem).toBeTruthy()
    expect(currentItem.action).toMatchObject({
      type: 'writing-result',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1'
    })
  })

  it('treats writing result as a first-class current object in shell labels and copilot action', async () => {
    store.currentView = 'writing'
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::issues',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1',
      title: '问题结果'
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.currentObjectLabel).toContain('问题结果')
    expect(wrapper.vm.copilotCurrentObjectAction).toMatchObject({
      type: 'writing-result',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1'
    })
    expect(wrapper.vm.currentCopilotSessionMeta.key).toContain('writing-result:chapter-1:issues')
  })

  it('adds topbar object action for current writing result object', async () => {
    store.currentView = 'writing'
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::issues',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1',
      title: '问题结果'
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.resolvedTopbarObjectActions.some((item) => item.label === '查看问题结果' && item.action?.type === 'writing-result')).toBe(true)
  })

  it('adapts copilot prompts for issue result objects', async () => {
    store.currentView = 'writing'
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::issues',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1',
      title: '问题结果'
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.copilotChatPrompts[0]).toContain('问题单')
    expect(wrapper.vm.copilotObjectPromptCards[0].title).toBe('排序问题优先级')
  })

  it('adapts copilot prompts for candidate result objects', async () => {
    store.currentView = 'writing'
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::candidate',
      chapterId: 'chapter-1',
      resultType: 'candidate',
      taskId: 'task-2',
      title: '候选稿'
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.copilotChatPrompts[0]).toContain('候选稿')
    expect(wrapper.vm.copilotObjectPromptCards[0].title).toBe('评估候选稿可用性')
  })

  it('builds dedicated inspire items for writing result objects', async () => {
    store.currentView = 'writing'
    store.currentObject = {
      type: 'writing-result',
      id: 'chapter-1::issues',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1',
      title: '问题结果'
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.copilotInspireItems[0].title).toContain('修复顺序')
    expect(wrapper.vm.copilotInspireItems[0].action).toMatchObject({
      type: 'writing-result',
      chapterId: 'chapter-1',
      resultType: 'issues'
    })
  })

  it('adds failed task recovery into dedicated inspire items', async () => {
    store.currentView = 'overview'
    store.currentObject = null
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 2,
      runningCount: 0,
      completedCount: 0,
      auditCount: 1
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.copilotInspireItems.some((item) => item.key === 'inspire-failed-task-recovery')).toBe(true)
  })

  it('applies inspire feedback to ranking scores', async () => {
    store.currentView = 'overview'
    store.currentObject = null
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 1,
      runningCount: 0,
      completedCount: 0,
      auditCount: 0
    }
    await wrapper.vm.$nextTick()

    const before = wrapper.vm.copilotInspireItems.find((item) => item.key === 'inspire-failed-task-recovery')
    expect(before).toBeTruthy()

    wrapper.vm.handleInspireFeedback({ key: 'inspire-failed-task-recovery', signal: 'accept' })
    await wrapper.vm.$nextTick()

    const after = wrapper.vm.copilotInspireItems.find((item) => item.key === 'inspire-failed-task-recovery')
    expect(Number(after.score)).toBeGreaterThan(Number(before.score))
  })

  it('loads remote branch inspire items when inspire tab becomes active', async () => {
    store.currentCopilotTab = 'inspire'
    await wrapper.vm.$nextTick()
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(mockBranchesV2).toHaveBeenCalled()
    expect(mockChapterPlanV2).toHaveBeenCalled()
    expect(wrapper.vm.copilotInspireItems.some((item) => String(item.key).startsWith('remote-branch-'))).toBe(true)
    expect(wrapper.vm.copilotInspireItems.some((item) => String(item.key).startsWith('remote-plan-'))).toBe(true)
  })

  it('builds current object command for structure section objects', async () => {
    store.currentObject = { type: 'story_model' }
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.commandPaletteItems.some((item) => item.id === 'current-object-structure-story_model')).toBe(true)
  })

  it('builds restore commands for worldview recent object and current structure view', async () => {
    store.currentObject = { type: 'worldview' }
    store.openDocuments = [
      { type: 'worldview', id: 'worldview', title: '世界观', lastOpenedAt: Date.now() - 1000 }
    ]
    await wrapper.vm.$nextTick()

    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('current-object-structure-worldview')
    expect(itemIds.some((id) => id.startsWith('recent-doc-worldview-worldview'))).toBe(false)
  })

  it('deduplicates current object and recent object commands for the same chapter', async () => {
    store.currentObject = { type: 'chapter', id: 'chapter-1', title: '第一章' }
    store.openDocuments = [
      { type: 'chapter', id: 'chapter-1', title: '第一章', lastOpenedAt: Date.now() - 1000 }
    ]
    await wrapper.vm.$nextTick()

    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('current-object-chapter-chapter-1')
    expect(itemIds.some((id) => id.startsWith('recent-doc-chapter-chapter-1'))).toBe(false)
  })

  it('prioritizes current object command when query is empty', async () => {
    store.currentObject = { type: 'chapter', id: 'chapter-1', title: '第一章' }
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.filteredCommandPaletteItems[0].id).toBe('current-object-chapter-chapter-1')
  })

  it('prioritizes failed task recent objects over lower-priority structure restores when query is empty', async () => {
    store.currentObject = null
    store.openDocuments = [
      { type: 'risk', id: 'risk', title: '风险点', lastOpenedAt: Date.now() - 3000 },
      { type: 'task', id: 'task-1', title: '章节审查', chapterId: 'chapter-1', status: 'failed', lastOpenedAt: Date.now() - 1000 }
    ]
    await wrapper.vm.$nextTick()

    const riskIndex = wrapper.vm.filteredCommandPaletteItems.findIndex((item) => item.id.startsWith('recent-doc-risk-risk'))
    const taskIndex = wrapper.vm.filteredCommandPaletteItems.findIndex((item) => item.id.startsWith('recent-doc-task-task-1'))
    expect(taskIndex).toBeGreaterThanOrEqual(0)
    expect(riskIndex).toBeGreaterThanOrEqual(0)
    expect(taskIndex).toBeLessThan(riskIndex)
  })

  it('deduplicates current task entry when the same task is already the current object', async () => {
    store.currentTask = { id: 'task-1', label: '章节审查', chapterId: 'chapter-1', status: 'failed' }
    store.currentObject = { type: 'task', id: 'task-1', title: '章节审查', chapterId: 'chapter-1', status: 'failed' }
    await wrapper.vm.$nextTick()

    const itemIds = wrapper.vm.commandPaletteItems.map((item) => item.id)
    expect(itemIds).toContain('current-object-task-task-1')
    expect(itemIds).not.toContain('current-task-task-1')
  })

  it('builds richer current task entry when task is not the current object', async () => {
    store.currentObject = null
    store.currentTask = { id: 'task-2', label: '结构整理', chapterId: 'chapter-1', status: 'running' }
    await wrapper.vm.$nextTick()

    const item = wrapper.vm.commandPaletteItems.find((entry) => entry.id === 'current-task-task-2')
    expect(item.subtitle).toContain('恢复当前任务上下文')
    expect(item.subtitle).toContain('第一章')
    expect(item.hint).toBe('运行中')
    expect(item.action).toMatchObject({
      type: 'task',
      taskId: 'task-2',
      chapterId: 'chapter-1',
      status: 'running'
    })
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
      type: 'writing-result',
      chapterId: 'chapter-1',
      resultType: 'issues',
      taskId: 'task-1'
    })
  })

  it('builds task recommendations and grouped task sections', () => {
    expect(wrapper.vm.taskRecommendationItems[0].key).toBeTruthy()
    expect(wrapper.vm.groupedTaskSections.some((item) => item.key === 'failed')).toBe(true)
  })

  it('builds richer structure navigation metadata for sidebar', () => {
    expect(wrapper.vm.sidebarStructureItems.find((item) => item.key === 'plot_arc')?.count).toBeDefined()
    expect(wrapper.vm.sidebarStructureItems.find((item) => item.key === 'plot_arc')?.hint).toBeTruthy()
    expect(wrapper.vm.sidebarStructureItems.find((item) => item.key === 'risk')?.count).toBe(1)
  })

  it('adds task counts to filters and exposes failed task shortcut in top bar actions', () => {
    store.taskCenterSnapshot = {
      tasks: [],
      failedCount: 1,
      runningCount: 0,
      completedCount: 0,
      auditCount: 1
    }
    store.currentView = 'tasks'
    expect(wrapper.vm.taskFilterOptions.find((item) => item.key === 'failed')?.label).toBe('失败任务')
    expect(wrapper.vm.taskFilterOptions.find((item) => item.key === 'failed')?.count).toBe(1)
    expect(wrapper.vm.taskFilterOptions.find((item) => item.key === 'failed')?.hint).toContain('优先恢复')
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
      group: '助手会话',
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
    expect(store.currentObject).toMatchObject({
      type: 'issue',
      index: 0
    })
  })

  it('restores task object when executing task command', async () => {
    await wrapper.vm.handleCommandExecute({
      id: 'recent-doc-task-task-1',
      title: '章节审查',
      subtitle: '恢复该任务对象',
      group: '最近对象',
      hint: '最近',
      action: { type: 'task', taskId: 'task-1', title: '章节审查', chapterId: 'chapter-1', status: 'failed' }
    })

    expect(store.currentView).toBe('tasks')
    expect(store.currentObject).toMatchObject({
      type: 'task',
      taskId: 'task-1',
      chapterId: 'chapter-1'
    })
  })

  it('keeps chapter manager view when entering with chapters section and chapter id', async () => {
    mockRoute.query = {
      section: 'chapters',
      chapterId: 'chapter-1'
    }
    mountComponent()
    await wrapper.vm.$nextTick()

    expect(store.currentView).toBe('chapters')
    expect(store.currentObject).toMatchObject({
      type: 'chapter',
      id: 'chapter-1',
      title: '第一章'
    })
  })

})
