import { mount } from '@vue/test-utils'
import { computed } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import WorkspaceSidebar from '../WorkspaceSidebar.vue'

vi.mock('@/stores/workspace', () => ({
  useWorkspaceStore: () => ({
    currentView: 'structure',
    currentStructureSection: 'plot_arc',
    currentTaskFilter: 'all'
  })
}))

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: () => ({
    state: {
      chapters: [
        { id: 'chapter-1', chapter_number: 1, title: '第一章', updated_at: '2026-04-09T10:00:00.000Z' }
      ],
      novel: { title: '风暴将至' },
      organizeProgress: {}
    },
    currentChapterId: computed(() => 'chapter-1')
  })
}))

describe('WorkspaceSidebar.vue', () => {
  it('renders parent-provided overview cards and emits navigation events', async () => {
    const wrapper = mount(WorkspaceSidebar, {
      props: {
        currentView: 'overview',
        overviewCards: [
          { label: '当前小说', value: '风暴将至' },
          { label: '最近章节', value: '第一章', actionLabel: '去写作', action: { type: 'chapter', chapterId: 'chapter-1' } }
        ]
      },
      global: {
        stubs: ['el-input', 'el-icon']
      }
    })

    expect(wrapper.text()).toContain('风暴将至')
    expect(wrapper.text()).toContain('第一章')
    expect(wrapper.text()).toContain('去写作')

    await wrapper.findAll('.overview-card')[1].trigger('click')
    expect(wrapper.emitted('run-action')[0][0]).toEqual({ type: 'chapter', chapterId: 'chapter-1' })
  })

  it('emits structure change for parent-owned navigation', async () => {
    const wrapper = mount(WorkspaceSidebar, {
      props: {
        currentView: 'structure',
        currentStructureSection: 'plot_arc',
        structureItems: [
          { key: 'story_model', label: '故事模型' },
          { key: 'plot_arc', label: '剧情弧' }
        ]
      },
      global: {
        stubs: ['el-input', 'el-icon']
      }
    })

    await wrapper.findAll('.nav-item')[0].trigger('click')
    expect(wrapper.emitted('change-structure')).toBeTruthy()
    expect(wrapper.emitted('change-structure')[0][0]).toBe('story_model')
  })

  it('renders task filters with parent-provided counts', () => {
    const wrapper = mount(WorkspaceSidebar, {
      props: {
        currentView: 'tasks',
        currentTaskFilter: 'failed',
        taskFilters: [
          { key: 'all', label: '全部任务', count: 5, hint: '查看全部任务动态' },
          { key: 'failed', label: '失败任务', count: 2, hint: '优先恢复失败链路' }
        ]
      },
      global: {
        stubs: ['el-input', 'el-icon']
      }
    })

    expect(wrapper.text()).toContain('失败任务')
    expect(wrapper.text()).toContain('优先恢复失败链路')
    expect(wrapper.text()).toContain('2')
  })

  it('renders settings summary cards when settings view is active', () => {
    const wrapper = mount(WorkspaceSidebar, {
      props: {
        currentView: 'settings',
        overviewCards: [
          { label: '项目 ID', value: 'proj-1' },
          { label: '失败任务', value: '2 个' }
        ]
      },
      global: {
        stubs: ['el-input', 'el-icon']
      }
    })

    expect(wrapper.text()).toContain('设置摘要')
    expect(wrapper.text()).toContain('proj-1')
    expect(wrapper.text()).toContain('2 个')
  })
})
