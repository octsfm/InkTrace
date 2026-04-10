import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '@/stores/workspace'
import WorkspaceStructureStudio from '../WorkspaceStructureStudio.vue'

const mockScrollIntoView = vi.fn()
const mockOpenSection = vi.fn()

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      structureLoading: false,
      refreshStructure: vi.fn(),
      memoryView: {
        main_plot_lines: ['主角发现异常', '调查逐渐升级'],
        current_progress: '主线正在向危机阶段推进。',
        current_state: '角色关系张力正在增强。'
      },
      activeArcs: [
        {
          arc_id: 'arc-1',
          title: '主线追踪',
          arc_type: 'main_arc',
          status: 'active',
          stage: 'escalation',
          priority: 'core',
          summary: '继续追踪主线线索。'
        },
        {
          arc_id: 'arc-2',
          title: '人物关系波动',
          arc_type: 'character_arc',
          status: 'active',
          stage: 'early_push',
          priority: 'major',
          summary: '人物之间开始出现冲突。'
        }
      ]
    },
    refreshStructure: vi.fn(),
    openSection: mockOpenSection
  }))
}))

describe('WorkspaceStructureStudio.vue', () => {
  let wrapper
  let workspaceStore

  beforeEach(() => {
    mockScrollIntoView.mockClear()
    mockOpenSection.mockClear()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: mockScrollIntoView
    })

    const pinia = createPinia()
    setActivePinia(pinia)
    workspaceStore = useWorkspaceStore()
    workspaceStore.currentView = 'structure'
    workspaceStore.currentStructureSection = 'plot_arc'
    workspaceStore.currentObject = {
      type: 'plot_arc',
      arcId: 'arc-2',
      title: '人物关系波动'
    }

    wrapper = mount(WorkspaceStructureStudio, {
      global: {
        plugins: [pinia],
        stubs: ['el-button', 'el-icon', 'el-tag', 'el-empty']
      }
    })
  })

  it('highlights and announces the focused arc', async () => {
    expect(wrapper.text()).toContain('当前聚焦：人物关系波动')
    expect(wrapper.text()).toContain('优先推进弧')
    expect(wrapper.text()).toContain('主线追踪')
    expect(wrapper.text()).toContain('Story Model')
    const focusedCard = wrapper.find('[data-arc-id="arc-2"]')
    expect(focusedCard.exists()).toBe(true)
    expect(focusedCard.classes()).toContain('focused')
  })

  it('scrolls the focused arc into view', () => {
    expect(mockScrollIntoView).toHaveBeenCalled()
  })

  it('switches structure view from quick chips', async () => {
    const chip = wrapper.findAll('.structure-switch-chip').find((node) => node.text().includes('风险点'))
    await chip.trigger('click')
    expect(workspaceStore.currentStructureSection).toBe('risk')
    expect(wrapper.text()).toContain('风险点视角')
  })

  it('provides cross-workspace actions', async () => {
    const overviewChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('回到概览'))
    await overviewChip.trigger('click')
    expect(mockOpenSection).toHaveBeenCalledWith('overview')
  })
})
