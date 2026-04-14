import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '@/stores/workspace'
import WorkspaceChapterManager from '../WorkspaceChapterManager.vue'

const {
  mockUpdateChapter,
  mockMessageSuccess,
  mockMessageError
} = vi.hoisted(() => ({
  mockUpdateChapter: vi.fn(() => Promise.resolve({})),
  mockMessageSuccess: vi.fn(),
  mockMessageError: vi.fn()
}))

const mockScrollIntoView = vi.fn()
const mockOpenSection = vi.fn()
const mockOpenChapter = vi.fn()
const mockRouterPush = vi.fn()
const mockExecuteWorkspaceAction = vi.fn()

vi.mock('element-plus', () => ({
  ElMessage: {
    success: mockMessageSuccess,
    error: mockMessageError
  }
}))

vi.mock('@/api', () => ({
  novelApi: {
    updateChapter: mockUpdateChapter
  }
}))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: mockRouterPush
  }))
}))

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      novel: { id: 'novel-1' },
      chapters: [
        { id: 'ch-1', chapter_number: 1, title: '序章', status: 'draft', updated_at: '2026-04-09T00:00:00Z', word_count: 1200 },
        { id: 'ch-2', chapter_number: 2, title: '风暴将至', status: 'reviewed', updated_at: '2026-04-10T00:00:00Z', word_count: 1800 }
      ]
    },
    createChapter: vi.fn(),
    openChapter: mockOpenChapter,
    openSection: mockOpenSection,
    executeWorkspaceAction: mockExecuteWorkspaceAction
  }))
}))

describe('WorkspaceChapterManager.vue', () => {
  let wrapper
  let workspaceStore

  beforeEach(() => {
    mockScrollIntoView.mockClear()
    mockOpenSection.mockClear()
    mockOpenChapter.mockClear()
    mockRouterPush.mockClear()
    mockExecuteWorkspaceAction.mockClear()
    mockUpdateChapter.mockClear()
    mockMessageSuccess.mockClear()
    mockMessageError.mockClear()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: mockScrollIntoView
    })

    const pinia = createPinia()
    setActivePinia(pinia)
    workspaceStore = useWorkspaceStore()
    workspaceStore.currentView = 'chapters'
    workspaceStore.currentChapterId = 'ch-2'
    workspaceStore.currentObject = {
      type: 'chapter',
      id: 'ch-2',
      title: '风暴将至'
    }
    workspaceStore.taskCenterSnapshot = {
      tasks: [
        {
          id: 'task-ch-2',
          label: 'AI 审查',
          status: 'completed',
          chapterId: 'ch-2',
          resultType: 'issues'
        }
      ],
      failedCount: 0
    }

    wrapper = mount(WorkspaceChapterManager, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-icon': { template: '<span><slot /></span>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-table': { template: '<div class="table-stub"><slot /></div>' },
          'el-table-column': { template: '<div class="table-column-stub"></div>' },
          'el-radio-group': { template: '<div><slot /></div>' },
          'el-radio-button': { template: '<button><slot /></button>' }
        }
      }
    })
  })

  it('shows the focused chapter banner', () => {
    expect(wrapper.text()).toContain('当前聚焦：风暴将至')
    expect(wrapper.text()).toContain('当前筛选：全部 (2)')
    expect(wrapper.text()).toContain('最近更新')
    expect(wrapper.text()).toContain('风暴将至')
    expect(wrapper.text()).toContain('已校验 (1)')
    expect(wrapper.text()).toContain('下一步建议')
    expect(wrapper.text()).toContain('处理审查结果')
    expect(wrapper.text()).toContain('当前章节最近回流：问题结果')
    expect(wrapper.text()).toContain('查看问题结果')
  })

  it('highlights the focused chapter in kanban mode and scrolls into view', async () => {
    wrapper.vm.viewMode = 'kanban'
    await nextTick()
    await nextTick()

    const focusedCard = wrapper.find('[data-chapter-id="ch-2"]')
    expect(focusedCard.exists()).toBe(true)
    expect(focusedCard.classes()).toContain('focused')
    expect(mockScrollIntoView).toHaveBeenCalled()
  })

  it('applies status filter to the unified chapter collection', async () => {
    wrapper.vm.selectedStatusFilter = 'reviewed'
    await nextTick()
    expect(wrapper.vm.filteredChapters).toHaveLength(1)
    expect(wrapper.vm.filteredChapters[0].id).toBe('ch-2')
  })

  it('normalizes chapter status into unified lifecycle labels', () => {
    expect(wrapper.vm.filteredChapters.find((item) => item.id === 'ch-1')?.normalizedStatus).toBe('draft')
    expect(wrapper.vm.filteredChapters.find((item) => item.id === 'ch-2')?.normalizedStatus).toBe('reviewed')
  })

  it('switches section copy when entering kanban mode', async () => {
    wrapper.vm.viewMode = 'kanban'
    await nextTick()

    expect(wrapper.text()).toContain('章节看板管理')
    expect(wrapper.vm.modeBannerText).toContain('看板视图更适合按状态巡视章节流转')
  })

  it('provides cross-workspace actions', async () => {
    const structureChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('查看结构'))
    await structureChip.trigger('click')
    expect(mockOpenSection).toHaveBeenCalledWith('structure')
  })

  it('routes chapter edit action back into workspace writing view', () => {
    wrapper.vm.openChapterWorkspace('ch-2')
    expect(mockRouterPush).toHaveBeenCalledWith({
      path: '/novel/novel-1',
      query: {
        section: 'writing',
        chapterId: 'ch-2'
      }
    })
  })

  it('routes focused chapter result back into writing-result flow', async () => {
    const resultButton = wrapper.findAll('button').find((node) => node.text().includes('查看问题结果'))
    await resultButton.trigger('click')

    expect(mockExecuteWorkspaceAction).toHaveBeenCalledWith({
      type: 'writing-result',
      chapterId: 'ch-2',
      resultType: 'issues',
      taskId: 'task-ch-2',
      title: 'AI 审查'
    })
  })

  it('supports real kanban drag drop status transition', async () => {
    wrapper.vm.viewMode = 'kanban'
    await nextTick()

    wrapper.vm.handleDragStart({ id: 'ch-1' })
    wrapper.vm.handleDragOver('reviewed')
    await wrapper.vm.handleDrop('reviewed')

    expect(wrapper.vm.draggingChapterId).toBe('')
    expect(wrapper.vm.dragOverStatus).toBe('')
    expect(mockUpdateChapter).toHaveBeenCalledWith('novel-1', 'ch-1', { status: 'reviewed' })
    expect(mockMessageSuccess).toHaveBeenCalled()
  })
})
