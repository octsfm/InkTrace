import { mount } from '@vue/test-utils'
import { computed } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import WorkspaceOverview from '../WorkspaceOverview.vue'

const mockWorkspaceContext = {
  state: {
    novel: { title: '风暴将至' },
    chapters: [
      { id: 'chapter-1', chapter_number: 1, title: '第一章', updated_at: '2026-04-09T10:00:00.000Z' }
    ],
    activeArcs: [{ arc_id: 'arc-1', title: '主线追踪' }],
    memoryView: { current_progress: '主线进入冲突升级阶段。' },
    organizeProgress: { status: 'running', progress: 50 },
    editor: {
      integrityCheck: {
        issue_list: [{ title: '连续性风险' }]
      }
    }
  },
  currentChapterId: computed(() => 'chapter-1'),
  suggestedActions: computed(() => [
    { key: 'writing', title: '继续写作', description: '进入当前章节。', cta: '打开写作' }
  ]),
  overviewDecisionCards: computed(() => [
    {
      key: 'issue-review',
      tag: '问题单',
      cta: '处理',
      title: '先处理当前问题单',
      description: '当前章节已有待处理问题。',
      meta: '1 个问题待处理',
      onClick: () => mockWorkspaceContext.openSection('writing', { chapterId: 'chapter-1' })
    },
    {
      key: 'structure-focus',
      tag: '结构',
      cta: '查看',
      title: '检查活跃剧情弧',
      description: '先确认主线和当前推进阶段。',
      meta: '主线追踪',
      onClick: () => mockWorkspaceContext.openSection('structure')
    }
  ]),
  overviewTaskSnapshot: computed(() => ({
    failed: 1,
    running: 0,
    audit: 1,
    recommendation: {
      tag: '优先',
      meta: '章节 ch-1',
      title: '先恢复：AI 审查',
      description: '一致性校验失败',
      actionLabel: '打开章节',
      action: { type: 'chapter', chapterId: 'chapter-1' }
    }
  })),
  executeWorkspaceAction: vi.fn(),
  setTaskFilter: vi.fn(),
  openSection: vi.fn(),
  openChapter: vi.fn()
}

vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: () => mockWorkspaceContext
}))

describe('WorkspaceOverview.vue', () => {
  it('renders next-step cards and routes issue review to writing', async () => {
    const wrapper = mount(WorkspaceOverview, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          'el-empty': true
        }
      }
    })

    expect(wrapper.text()).toContain('下一步入口')
    expect(wrapper.text()).toContain('先处理当前问题单')
    expect(wrapper.text()).toContain('检查活跃剧情弧')
    expect(wrapper.text()).toContain('任务快照')
    expect(wrapper.text()).toContain('先恢复：AI 审查')
    expect(wrapper.text()).toContain('打开任务台')

    const firstDecision = wrapper.find('.decision-card')
    await firstDecision.trigger('click')
    expect(mockWorkspaceContext.openSection).toHaveBeenCalledWith('writing', { chapterId: 'chapter-1' })

    const taskButton = wrapper.findAll('button').find((node) => node.text().includes('打开章节'))
    await taskButton.trigger('click')
    expect(mockWorkspaceContext.executeWorkspaceAction).toHaveBeenCalledWith({ type: 'chapter', chapterId: 'chapter-1' })

    const tasksChip = wrapper.findAll('.workspace-action-chip').find((node) => node.text().includes('打开任务台'))
    await tasksChip.trigger('click')
    expect(mockWorkspaceContext.openSection).toHaveBeenCalledWith('tasks')
  })
})
