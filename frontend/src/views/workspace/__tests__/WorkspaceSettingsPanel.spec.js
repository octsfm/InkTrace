import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import WorkspaceSettingsPanel from '../WorkspaceSettingsPanel.vue'

describe('WorkspaceSettingsPanel.vue', () => {
  it('renders diagnostics and triggers suggested actions', async () => {
    const openWriting = vi.fn()
    const openTasks = vi.fn()
    const openStructure = vi.fn()
    const openChapters = vi.fn()

    const wrapper = mount(WorkspaceSettingsPanel, {
      props: {
        novelTitle: '风暴将至',
        projectId: 'project-1',
        resourceSnapshot: {
          projectId: 'project-1',
          chapterCount: 12
        },
        taskCenterSnapshot: {
          failedCount: 2,
          runningCount: 1,
          auditCount: 1
        },
        contextSnapshot: {
          chapterTitle: '风暴前夜',
          contextMeta: { issueCount: 3 }
        },
        chapterCount: 12,
        currentView: 'settings',
        currentChapterTitle: '风暴前夜',
        saveStatusText: '已保存',
        taskStatusText: '2 个失败任务',
        failedTaskCount: 2,
        runningTaskCount: 1,
        auditTaskCount: 1,
        issueCount: 3,
        copilotOpen: true,
        recentPromptCount: 4,
        sessionCount: 2,
        zenMode: false,
        currentObjectTitle: '世界观',
        actionItems: [
          { key: 'settings-open-writing', label: '回到写作', onClick: openWriting },
          { key: 'settings-open-tasks', label: '查看任务', onClick: openTasks },
          { key: 'settings-open-structure', label: '查看结构', onClick: openStructure },
          { key: 'settings-open-chapters', label: '查看章节', onClick: openChapters }
        ]
      },
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })

    expect(wrapper.text()).toContain('工作区诊断')
    expect(wrapper.text()).toContain('建议动作')
    expect(wrapper.text()).toContain('有 2 个失败任务待处理')
    expect(wrapper.text()).toContain('当前有 2 个失败任务待恢复')
    expect(wrapper.text()).toContain('先恢复失败任务')
    expect(wrapper.text()).toContain('先处理当前问题单')
    expect(wrapper.text()).toContain('检查当前结构焦点')

    const buttons = wrapper.findAll('button')
    await buttons.find((node) => node.text().includes('查看任务')).trigger('click')
    await buttons.find((node) => node.text().includes('回到写作')).trigger('click')
    await buttons.find((node) => node.text().includes('查看结构')).trigger('click')

    expect(openTasks).toHaveBeenCalled()
    expect(openWriting).toHaveBeenCalled()
    expect(openStructure).toHaveBeenCalled()
  })

  it('surfaces context recovery when chapter context snapshot is missing', async () => {
    const openWriting = vi.fn()
    const openChapters = vi.fn()

    const wrapper = mount(WorkspaceSettingsPanel, {
      props: {
        novelTitle: '风暴将至',
        projectId: 'project-1',
        resourceSnapshot: {
          projectId: 'project-1',
          chapterCount: 12
        },
        taskCenterSnapshot: {
          failedCount: 0,
          runningCount: 0,
          auditCount: 0
        },
        contextSnapshot: {},
        currentView: 'settings',
        taskStatusText: '未运行',
        actionItems: [
          { key: 'settings-open-writing', label: '回到写作', onClick: openWriting },
          { key: 'settings-open-chapters', label: '查看章节', onClick: openChapters }
        ]
      },
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })

    expect(wrapper.text()).toContain('当前没有稳定的章节上下文快照')
    expect(wrapper.text()).toContain('先补足当前章节上下文')

    const chapterButton = wrapper.findAll('button').find((node) => node.text().includes('查看章节'))
    await chapterButton.trigger('click')
    expect(openChapters).toHaveBeenCalled()
  })
})
