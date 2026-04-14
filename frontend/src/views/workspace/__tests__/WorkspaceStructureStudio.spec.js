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
    workspaceStore.taskCenterSnapshot = {
      tasks: [
        {
          id: 'task-arc-1',
          label: '结构审查',
          status: 'failed',
          targetArcId: 'arc-1',
          resultType: 'issues'
        }
      ],
      failedCount: 1,
      runningCount: 0,
      completedCount: 0,
      auditCount: 1
    }

    wrapper = mount(WorkspaceStructureStudio, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          'el-icon': { template: '<span><slot /></span>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-empty': { template: '<div><slot /></div>' }
        }
      }
    })
  })

  it('highlights and announces the focused arc', async () => {
    expect(wrapper.text()).toContain('当前聚焦：人物关系波动')
    expect(wrapper.text()).toContain('优先推进弧')
    expect(wrapper.text()).toContain('主线追踪')
    expect(wrapper.text()).toContain('故事模型')
    expect(wrapper.text()).toContain('切到风险点视角')
    expect(wrapper.text()).toContain('风险切换')
    const focusedCard = wrapper.find('[data-arc-id="arc-2"]')
    expect(focusedCard.exists()).toBe(true)
    expect(focusedCard.classes()).toContain('focused')
  })

  it('scrolls the focused arc into view', () => {
    expect(mockScrollIntoView).toHaveBeenCalled()
  })

  it('switches structure view from quick chips', async () => {
    const chip = wrapper.findAll('.workspace-selectable-chip').find((node) => node.text().includes('风险点'))
    await chip.trigger('click')
    expect(workspaceStore.currentStructureSection).toBe('risk')
    expect(wrapper.text()).toContain('风险点视角')
    expect(wrapper.text()).toContain('结构风险扫描')
    expect(wrapper.text()).toContain('风险视角')
    expect(wrapper.text()).toContain('当前主要风险')
    expect(wrapper.text()).toContain('回到剧情弧主视角')
    expect(wrapper.text()).toContain('当前处于结构风险扫描视角')
    expect(wrapper.text()).toContain('查看任务台')
    expect(wrapper.text()).not.toContain('当前聚焦：人物关系波动')
  })

  it('provides cross-workspace actions', async () => {
    const overviewChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('回到概览'))
    await overviewChip.trigger('click')
    expect(mockOpenSection).toHaveBeenCalledWith('overview')
  })

  it('surfaces failed task recovery for structure decisions', async () => {
    const focusTaskFilterSpy = vi.spyOn(workspaceStore, 'focusTaskFilter')
    expect(wrapper.text()).toContain('当前有 1 个失败任务影响结构推进')
    expect(wrapper.text()).toContain('结构审查 · 问题结果')

    const recoveryButton = wrapper.findAll('button').find((node) => node.text().includes('看失败任务'))
    await recoveryButton.trigger('click')

    expect(focusTaskFilterSpy).toHaveBeenCalledWith('failed', { openView: false })
    expect(mockOpenSection).toHaveBeenCalledWith('tasks')
  })
})
