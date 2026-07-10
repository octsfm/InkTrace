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

    expect(wrapper.text()).toContain('当前模式下暂时没有建议，生成后会在这里展示。')
    expect(wrapper.text()).toContain('当前没有可展示的冲突，请刷新后重试。')
    expect(wrapper.text()).not.toContain('当前模式下暂时没有建议,生成后会在这里展示。')
    expect(wrapper.text()).not.toContain('当前没有可展示的冲突,请刷新后重试。')
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
          status: 'generating'
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

    expect(wrapper.text()).toContain('建议生成中，请稍后刷新查看结果。')
    expect(wrapper.text()).toContain('已进入写作任务确认链，待二次确认后才会进入"写作任务已确认"状态。')
    expect(wrapper.text()).toContain('当前建议针对自由文本片段，需要先选择目标大纲节点后才能应用。')
    expect(wrapper.text()).toContain('确定要将这条建议应用到正式大纲吗？')
    expect(wrapper.text()).not.toContain('建议生成中,请稍后刷新查看结果。')
    expect(wrapper.text()).not.toContain('已进入写作任务确认链,待二次确认后才会进入"写作任务已确认"状态。')
    expect(wrapper.text()).not.toContain('当前建议针对自由文本片段,需要先选择目标大纲节点后才能应用。')
    expect(wrapper.text()).not.toContain('确定要将这条建议应用到正式大纲吗?')
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
