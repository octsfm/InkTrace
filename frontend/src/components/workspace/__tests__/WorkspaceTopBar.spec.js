import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkspaceTopBar from '../WorkspaceTopBar.vue'

describe('WorkspaceTopBar.vue', () => {
  it('renders parent-provided facts, status cards and object actions', async () => {
    const wrapper = mount(WorkspaceTopBar, {
      props: {
        novelTitle: '风暴将至',
        objectLabel: '第一章',
        viewTitle: '写作',
        viewDescription: '中央区域保持写作优先。',
        quickFacts: [
          { label: '当前章节', value: '第一章' }
        ],
        statusCards: [
          { label: '保存', value: '已保存', tone: 'success' }
        ],
        objectActions: [
          { label: '章节管理', action: { type: 'chapter-manager', chapterId: 'chapter-1' } }
        ],
        copilotOpen: true
      }
    })

    expect(wrapper.text()).toContain('当前章节')
    expect(wrapper.text()).toContain('已保存')
    expect(wrapper.text()).toContain('章节管理')
    expect(wrapper.text()).toContain('收起助手')

    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
    expect(wrapper.emitted('action')[0][0]).toEqual({ type: 'chapter-manager', chapterId: 'chapter-1' })
  })

  it('renders failed task shortcut from parent actions', async () => {
    const wrapper = mount(WorkspaceTopBar, {
      props: {
        novelTitle: '风暴将至',
        objectLabel: '第一章',
        viewTitle: '写作',
        viewDescription: '中央区域保持写作优先。',
        quickFacts: [],
        statusCards: [
          { label: '任务', value: '2 个失败任务', tone: 'warning', hint: '2 个失败任务' }
        ],
        objectActions: [
          { label: '失败任务 2', action: { type: 'task-filter', filter: 'failed' } }
        ],
        copilotOpen: true
      }
    })

    expect(wrapper.text()).toContain('失败任务 2')
    expect(wrapper.text()).toContain('收起助手')
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('action')[0][0]).toEqual({ type: 'task-filter', filter: 'failed' })
  })
})
