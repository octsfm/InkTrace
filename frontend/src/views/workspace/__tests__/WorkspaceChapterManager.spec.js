import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '@/stores/workspace'
import WorkspaceChapterManager from '../WorkspaceChapterManager.vue'

const mockScrollIntoView = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn()
  }))
}))

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      novel: { id: 'novel-1' },
      chapters: [
        { id: 'ch-1', chapter_number: 1, title: '序章', status: 'draft', updated_at: '2026-04-09T00:00:00Z', word_count: 1200 },
        { id: 'ch-2', chapter_number: 2, title: '风暴将至', status: 'draft', updated_at: '2026-04-10T00:00:00Z', word_count: 1800 }
      ]
    },
    createChapter: vi.fn(),
    openChapter: vi.fn()
  }))
}))

describe('WorkspaceChapterManager.vue', () => {
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
    workspaceStore.currentView = 'chapters'
    workspaceStore.currentChapterId = 'ch-2'
    workspaceStore.currentObject = {
      type: 'chapter',
      id: 'ch-2',
      title: '风暴将至'
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
})
