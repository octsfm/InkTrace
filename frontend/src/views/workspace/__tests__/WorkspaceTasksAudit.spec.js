import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '@/stores/workspace'
import WorkspaceTasksAudit from '../WorkspaceTasksAudit.vue'

const mockScrollIntoView = vi.fn()

vi.mock('@/api', () => ({
  contentApi: {
    organizeProgress: vi.fn(async () => ({ status: 'failed', progress: 60, error_message: '大纲写回失败' })),
    retryOrganize: vi.fn(async () => ({})),
    pauseOrganize: vi.fn(async () => ({})),
    resumeOrganize: vi.fn(async () => ({})),
    cancelOrganize: vi.fn(async () => ({}))
  }
}))

const mockOpenSection = vi.fn()
const mockOpenChapter = vi.fn()

vi.mock('@/composables/useWorkspaceContext', async () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      novel: { id: 'novel-1' },
      organizeProgress: { status: 'failed', progress: 60, error_message: '大纲写回失败' }
    },
    refreshStructure: vi.fn(),
    openSection: mockOpenSection,
    openChapter: mockOpenChapter
  }))
}))

describe('WorkspaceTasksAudit.vue', () => {
  let wrapper
  let workspaceStore

  beforeEach(() => {
    mockScrollIntoView.mockClear()
    mockOpenSection.mockClear()
    mockOpenChapter.mockClear()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: mockScrollIntoView
    })

    const pinia = createPinia()
    setActivePinia(pinia)
    workspaceStore = useWorkspaceStore()
    workspaceStore.currentView = 'tasks'
    workspaceStore.currentTaskFilter = 'failed'
    workspaceStore.currentTask = {
      id: 'editor-analyze-1',
      type: 'audit',
      label: 'AI 审查',
      status: 'failed',
      chapterId: 'ch-2',
      error: '一致性校验失败'
    }
    workspaceStore.currentObject = {
      type: 'task',
      taskId: 'organize-task',
      title: '全书整理任务',
      status: 'failed'
    }

    wrapper = mount(WorkspaceTasksAudit, {
      props: {
        filterOptions: [
          { key: 'all', label: '全部任务' },
          { key: 'running', label: '运行中' },
          { key: 'failed', label: '失败任务' }
        ],
        statusText: '失败',
        progressText: '60%',
        statusHint: '大纲写回失败',
        statusCards: [
          { label: '当前状态', value: '失败', hint: '大纲写回失败' },
          { label: '最近进度', value: '60%', hint: '项目任务 2 个' }
        ],
        summaryChips: [
          { label: '全部', value: '2' },
          { label: '失败', value: '2' }
        ],
        taskCards: [
          {
            id: 'organize-task',
            type: 'organize',
            status: 'failed',
            statusLabel: '失败',
            title: '全书整理任务',
            subtitle: '当前进度 60%',
            description: '大纲写回失败',
            hint: '建议先查看失败原因，再重试整理。',
            actionLabel: '重新整理'
          },
          {
            id: 'editor-analyze-1',
            type: 'audit',
            status: 'failed',
            statusLabel: '失败',
            title: 'AI 审查',
            subtitle: '章节 ch-2',
            description: '一致性校验失败',
            hint: '如需恢复，可回到写作页重新发起。',
            actionLabel: '打开章节',
            action: { type: 'chapter', chapterId: 'ch-2' },
            chapterId: 'ch-2'
          }
        ],
        filteredTaskCards: [
          {
            id: 'organize-task',
            type: 'organize',
            status: 'failed',
            statusLabel: '失败',
            title: '全书整理任务',
            subtitle: '当前进度 60%',
            description: '大纲写回失败',
            hint: '建议先查看失败原因，再重试整理。',
            actionLabel: '重新整理'
          },
          {
            id: 'editor-analyze-1',
            type: 'audit',
            status: 'failed',
            statusLabel: '失败',
            title: 'AI 审查',
            subtitle: '章节 ch-2',
            description: '一致性校验失败',
            hint: '如需恢复，可回到写作页重新发起。',
            actionLabel: '打开章节',
            action: { type: 'chapter', chapterId: 'ch-2' },
            chapterId: 'ch-2'
          }
        ],
        groupedTaskSections: [
          {
            key: 'failed',
            title: '优先恢复',
            description: '这些任务当前失败或异常。',
            items: [
              {
                id: 'organize-task',
                type: 'organize',
                status: 'failed',
                statusLabel: '失败',
                title: '全书整理任务',
                subtitle: '当前进度 60%',
                description: '大纲写回失败',
                hint: '建议先查看失败原因，再重试整理。',
                actionLabel: '重新整理',
                action: { type: 'retry-organize' }
              },
              {
                id: 'editor-analyze-1',
                type: 'audit',
                status: 'failed',
                statusLabel: '失败',
                title: 'AI 审查',
                subtitle: '章节 ch-2',
                description: '一致性校验失败',
                hint: '如需恢复，可回到写作页重新发起。',
                actionLabel: '打开章节',
                action: { type: 'chapter', chapterId: 'ch-2' },
                chapterId: 'ch-2'
              }
            ]
          }
        ],
        recommendationItems: [
          {
            key: 'failed-task',
            tag: '优先',
            title: '先恢复：AI 审查',
            description: '一致性校验失败',
            meta: '章节 ch-2',
            actionLabel: '打开章节',
            action: { type: 'chapter', chapterId: 'ch-2' }
          }
        ],
        focusBannerText: '当前聚焦：全书整理任务',
        historyEmptyText: '更完整的任务历史和 trace 将在后续接入。'
      },
      global: {
        plugins: [pinia],
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\', $event)"><slot /></button>' },
          'el-icon': true,
          'el-progress': true,
          'el-tag': true,
          'el-empty': true
        }
      }
    })
  })

  it('shows the active filter banner', () => {
    expect(wrapper.text()).toContain('当前聚焦：全书整理任务')
    expect(wrapper.text()).toContain('失败任务')
  })

  it('highlights and scrolls to the focused task card', () => {
    const focusedCard = wrapper.find('[data-task-id="organize-task"]')
    expect(focusedCard.exists()).toBe(true)
    expect(focusedCard.classes()).toContain('focused')
    expect(focusedCard.classes()).toContain('is-failed')
    expect(mockScrollIntoView).toHaveBeenCalled()
  })

  it('runs chapter action from parent-provided task payload', async () => {
    const actionButtons = wrapper.findAll('button').filter((node) => node.text().includes('打开章节'))
    await actionButtons[0].trigger('click')
    expect(mockOpenChapter).toHaveBeenCalledWith('ch-2', 'writing')
  })

  it('renders recommendation and grouped task sections', () => {
    expect(wrapper.text()).toContain('优先处理建议')
    expect(wrapper.text()).toContain('先恢复：AI 审查')
    expect(wrapper.text()).toContain('优先恢复')
    expect(wrapper.text()).toContain('优先恢复 2')
    expect(wrapper.text()).toContain('回到概览')
  })

  it('provides workspace-level action chips', async () => {
    const overviewChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('回到概览'))
    await overviewChip.trigger('click')
    expect(mockOpenSection).toHaveBeenCalledWith('overview')
  })

  it('syncs focused task back into workspace store', async () => {
    const taskCard = wrapper.find('[data-task-id="editor-analyze-1"]')
    await taskCard.trigger('click')
    expect(workspaceStore.currentTask).toMatchObject({
      id: 'editor-analyze-1',
      label: 'AI 审查',
      chapterId: 'ch-2'
    })
    expect(workspaceStore.currentObject).toMatchObject({
      type: 'task',
      taskId: 'editor-analyze-1'
    })
  })
})
