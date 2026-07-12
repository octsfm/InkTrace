import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import OutlineAssistPanel from '../OutlineAssistPanel.vue'

const baseProps = () => ({
  featureEnabled: true,
  modes: [
    { id: 'outline_polish', label: '润色' },
    { id: 'outline_expand', label: '扩写' }
  ],
  activeMode: 'outline_polish',
  suggestions: [],
  suggestionDetails: {},
  actionError: '',
  submittingSuggestionId: '',
  submittingActionType: '',
  loading: false,
  conflictSectionVisible: false,
  conflictLoading: false,
  conflictItems: [],
  conflictDetails: {},
  applyConfirmSuggestionId: '',
  applySubmittingSuggestionId: '',
  canAcceptSuggestion: vi.fn(() => false),
  canResolveSuggestion: vi.fn(() => false),
  canConvertSuggestion: vi.fn(() => false),
  canApplySuggestion: vi.fn(() => false),
  isAcceptedWritingTaskSuggestion: vi.fn(() => false),
  isSelectionOnlySuggestion: vi.fn(() => false),
  isStaleSuggestion: vi.fn(() => false),
  displaySuggestionType: vi.fn(() => '大纲扩写'),
  displaySeverity: vi.fn(() => '警告')
})

describe('OutlineAssistPanel', () => {
  it('uses chinese punctuation in empty and conflict helper copy', () => {
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        conflictSectionVisible: true
      }
    })

    expect(wrapper.text()).toContain('还没有整理结果。点击上面的按钮开始即可。')
    expect(wrapper.text()).toContain('暂时没有可查看的冲突，请重新读取大纲后再试。')
    expect(wrapper.text()).not.toContain('还没有整理结果,点击上面的按钮开始即可。')
    expect(wrapper.text()).not.toContain('暂时没有可查看的冲突,请重新读取大纲后再试。')
  })

  it('uses chinese punctuation in suggestion state hints and apply confirm copy', () => {
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        suggestions: [{
          suggestion_id: 'sg_1',
          title: '补全灯塔伏线',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          summary: '建议补足灯塔守夜人的出场。',
          status: 'pending'
        }, {
          suggestion_id: 'sg_2',
          title: '补全档案室目标',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          summary: '建议补足档案室目标。',
          status: 'accepted'
        }],
        applyConfirmSuggestionId: 'sg_2',
        isAcceptedWritingTaskSuggestion: vi.fn((item) => item.suggestion_id === 'sg_2'),
        isSelectionOnlySuggestion: vi.fn((item) => item.suggestion_id === 'sg_2'),
        canApplySuggestion: vi.fn((item) => item.suggestion_id === 'sg_2')
      }
    })

    expect(wrapper.text()).toContain('正在整理这条建议，请稍等。')
    expect(wrapper.text()).toContain('这份计划还需要你确认使用，确认前不会进入写作流程，也不会写入正文。')
    expect(wrapper.text()).toContain('这条建议只针对你选中的文字，不能直接改动整份大纲。')
    expect(wrapper.text()).toContain('确定把这条建议放进作品大纲吗？')
    expect(wrapper.text()).not.toContain('正在整理这条建议,请稍等。')
    expect(wrapper.text()).not.toContain('这份计划还需要你确认使用,确认前不会进入写作流程,也不会写入正文。')
    expect(wrapper.text()).not.toContain('这条建议只针对你选中的文字,不能直接改动整份大纲。')
    expect(wrapper.text()).not.toContain('确定把这条建议放进作品大纲吗?')
  })

  it('uses chinese punctuation in conflict summaries', () => {
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        conflictSectionVisible: true,
        conflictItems: [{
          record_id: 'conflict_1',
          title: '正式大纲节点冲突',
          severity: 'warning',
          summary: '目标节点已被其他操作修改,请先确认差异。'
        }]
      }
    })

    expect(wrapper.text()).toContain('目标节点已被其他操作修改，请先确认差异。')
    expect(wrapper.text()).not.toContain('目标节点已被其他操作修改,请先确认差异。')
  })

  it('uses chinese punctuation in suggestion summaries and detail summaries', () => {
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        suggestions: [{
          suggestion_id: 'sg_3',
          title: '补全档案室潜入步骤',
          suggestion_type: 'outline_expand',
          severity: 'warning',
          summary: '建议先补侦查,再进入档案室。',
          status: 'pending'
        }],
        suggestionDetails: {
          sg_3: {
            summary: '建议补足外墙侦查,再决定潜入时机。'
          }
        }
      }
    })

    expect(wrapper.text()).toContain('建议先补侦查，再进入档案室。')
    expect(wrapper.text()).toContain('建议补足外墙侦查，再决定潜入时机。')
    expect(wrapper.text()).not.toContain('建议先补侦查,再进入档案室。')
    expect(wrapper.text()).not.toContain('建议补足外墙侦查,再决定潜入时机。')
  })
})
