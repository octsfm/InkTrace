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

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      novel: { id: 'novel-1' },
      organizeProgress: { status: 'failed', progress: 60, error_message: '大纲写回失败' }
    },
    refreshStructure: vi.fn(),
    openSection: vi.fn()
  }))
}))

describe('WorkspaceTasksAudit.vue', () => {
  let wrapper
  let workspaceStore

  beforeEach(() => {
    mockScrollIntoView.mockClear()
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
      global: {
        plugins: [pinia],
        stubs: ['el-button', 'el-icon', 'el-progress', 'el-tag', 'el-empty']
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
    expect(mockScrollIntoView).toHaveBeenCalled()
  })
})
