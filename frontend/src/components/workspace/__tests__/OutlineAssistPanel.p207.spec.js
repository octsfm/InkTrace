import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import OutlineAssistPanel from '../OutlineAssistPanel.vue'

const baseProps = () => ({
  featureEnabled: true,
  modes: [
    { id: 'outline_polish', label: '把这段写顺' },
    { id: 'outline_expand', label: '把这段补完整' },
    { id: 'chapter_outline_detail', label: '生成本章细纲' },
    { id: 'writing_task_suggestion', label: '整理本章写作要点' }
  ],
  activeMode: 'outline_polish',
  targetKind: 'work_outline',
  targetLabel: '作品大纲',
  targetSelection: 'work',
  chapterOptions: [
    { id: 'chapter-1', order_index: 1, title: '雨夜来信' },
    { id: 'chapter-2', order_index: 2, title: '旧城档案馆' }
  ],
  sourceText: '主角在雨夜抵达旧城。',
  suggestions: [],
  suggestionDetails: {},
  actionError: '',
  actionNotice: '',
  submittingSuggestionId: '',
  submittingActionType: '',
  loading: false,
  targetLoading: false,
  generating: false,
  conflictSectionVisible: false,
  conflictLoading: false,
  conflictItems: [],
  conflictDetails: {},
  applyConfirmSuggestionId: '',
  applySubmittingSuggestionId: '',
  isModeDisabled: vi.fn((mode) => ['chapter_outline_detail', 'writing_task_suggestion'].includes(mode)),
  canAcceptSuggestion: vi.fn(() => false),
  canResolveSuggestion: vi.fn(() => false),
  canConvertSuggestion: vi.fn(() => false),
  canApplySuggestion: vi.fn(() => false),
  isAcceptedWritingTaskSuggestion: vi.fn(() => false),
  isSelectionOnlySuggestion: vi.fn(() => false),
  isStaleSuggestion: vi.fn(() => false),
  displaySuggestionType: vi.fn(() => '补充情节细节'),
  displaySeverity: vi.fn(() => '')
})

describe('OutlineAssistPanel P2-07 author-facing flow', () => {
  it('presents four plain-language tabs and disables chapter actions without a chapter', () => {
    const wrapper = mount(OutlineAssistPanel, { props: baseProps() })

    const tabList = wrapper.get('[role="tablist"]')
    expect(tabList.attributes('aria-label')).toBe('选择大纲整理方式')
    expect(wrapper.get('[data-test="outline-assist-mode-outline_polish"]').text()).toBe('把这段写顺')
    expect(wrapper.get('[data-test="outline-assist-mode-outline_expand"]').text()).toBe('把这段补完整')
    expect(wrapper.get('[data-test="outline-assist-mode-chapter_outline_detail"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="outline-assist-mode-writing_task_suggestion"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="outline-assist-mode-outline_polish"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('[data-test="outline-chapter-mode-hint"]').text())
      .toContain('先选一章')
  })

  it('lets the author explicitly choose the whole story, a chapter, or temporary text', async () => {
    const wrapper = mount(OutlineAssistPanel, { props: baseProps() })
    const select = wrapper.get('[data-test="outline-assist-target-select"]')

    expect(wrapper.text()).toContain('要整理哪里？')
    expect(select.findAll('option').map((option) => option.text())).toEqual([
      '整本故事大纲',
      '第1章 雨夜来信',
      '第2章 旧城档案馆',
      '一段临时文字'
    ])

    await select.setValue('chapter:chapter-2')
    expect(wrapper.emitted('target-change')?.[0]).toEqual(['chapter:chapter-2'])
    await select.setValue('selection')
    expect(wrapper.emitted('target-change')?.[1]).toEqual(['selection'])
  })

  it('shows the current outline above the AI result and uses human action labels', () => {
    const suggestion = {
      suggestion_id: 'sg-outline',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      title: '补足雨夜进城的动机',
      summary: '补上主角冒雨进城的原因。',
      payload: {
        target_content_text: '主角在雨夜抵达旧城。',
        proposed_content_text: '主角收到失踪姐姐的密信后，冒雨赶到旧城。',
        diff_summary: ['补充进城动机']
      }
    }
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        suggestions: [suggestion],
        canApplySuggestion: vi.fn(() => true),
        canResolveSuggestion: vi.fn(() => true)
      }
    })

    const comparison = wrapper.get('[data-test="outline-comparison-sg-outline"]')
    expect(comparison.text()).toContain('现在的大纲')
    expect(comparison.text()).toContain('AI 整理后')
    expect(comparison.text()).toContain('主角在雨夜抵达旧城。')
    expect(comparison.text()).toContain('主角收到失踪姐姐的密信后')
    expect(wrapper.get('[data-test="suggestion-apply-sg-outline"]').text()).toBe('放进大纲')
    expect(wrapper.get('[data-test="suggestion-dismiss-sg-outline"]').text()).toBe('不要这条')
  })

  it('offers copy instead of apply for temporary text and explains an empty input', () => {
    const suggestion = {
      suggestion_id: 'sg-selection',
      suggestion_type: 'outline_polish',
      status: 'shown',
      payload: {
        target_kind: 'selection',
        target_id: null,
        target_revision: null,
        target_content_text: '他走进雨里',
        proposed_content_text: '他推开门，独自走进沉沉雨幕。'
      }
    }
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        targetKind: 'selection',
        targetLabel: '一段临时文字',
        targetSelection: 'selection',
        sourceText: '',
        suggestions: [suggestion],
        isSelectionOnlySuggestion: vi.fn(() => true),
        canAcceptSuggestion: vi.fn(() => true),
        canResolveSuggestion: vi.fn(() => true)
      }
    })

    expect(wrapper.get('[data-test="outline-assist-source"]').attributes('placeholder')).toBe('先写下想整理的文字。')
    expect(wrapper.get('[data-test="outline-assist-generate"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="outline-selection-empty-hint"]').text()).toBe('先写下想整理的文字。')
    expect(wrapper.get('[data-test="suggestion-copy-sg-selection"]').text()).toBe('复制整理结果')
    expect(wrapper.find('[data-test="suggestion-apply-sg-selection"]').exists()).toBe(false)
  })

  it('announces progress and offers writing-plan conversion without an accept step', () => {
    const suggestion = {
      suggestion_id: 'sg-task',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      title: '本章写作计划',
      payload: { writing_goal: '查清密信来源' }
    }
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        activeMode: 'writing_task_suggestion',
        targetKind: 'chapter_outline',
        targetLabel: '本章细纲',
        generating: true,
        pendingWritingTaskId: 'task-1',
        suggestions: [suggestion],
        isModeDisabled: vi.fn(() => false),
        canConvertSuggestion: vi.fn(() => true)
      }
    })

    expect(wrapper.get('[data-test="outline-assist-status"]').attributes('aria-live')).toBe('polite')
    expect(wrapper.get('[data-test="outline-assist-status"]').text()).toContain('正在整理')
    expect(wrapper.find('[data-test="suggestion-accept-sg-task"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="suggestion-convert-sg-task"]').text()).toBe('设为本章写作计划')
    expect(wrapper.text()).toContain('不会替你写正文')
    expect(wrapper.get('[data-test="outline-writing-plan-confirm-submit"]').text()).toBe('确认使用')
  })

  it('offers a retry button on a failed suggestion card', async () => {
    const wrapper = mount(OutlineAssistPanel, {
      props: {
        ...baseProps(),
        suggestions: [{
          suggestion_id: 'sg-failed',
          suggestion_type: 'outline_expand',
          status: 'failed'
        }]
      }
    })

    const retry = wrapper.get('[data-test="suggestion-retry-sg-failed"]')
    expect(retry.text()).toBe('再试一次')
    await retry.trigger('click')
    expect(wrapper.emitted('generate')?.[0]).toEqual(['outline_expand'])
  })

  it('shows the conflict recovery loop and never offers apply for the old suggestion', async () => {
    const wrapper = mount(OutlineAssistPanel, {
      attachTo: document.body,
      props: {
        ...baseProps(),
        targetReady: false,
        suggestions: [{
          suggestion_id: 'sg-stale',
          suggestion_type: 'outline_expand',
          status: 'accepted'
        }],
        conflictSectionVisible: true,
        conflictItems: [{
          record_id: 'cg-1',
          severity: 'blocking',
          summary: '章节安排和已确认计划冲突。'
        }],
        isStaleSuggestion: vi.fn(() => true),
        canApplySuggestion: vi.fn(() => false)
      }
    })

    expect(wrapper.find('[data-test="suggestion-apply-sg-stale"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="suggestion-stale-refresh-sg-stale"]').text()).toBe('重新读取大纲')
    const regenerate = wrapper.get('[data-test="suggestion-stale-regenerate-sg-stale"]')
    expect(regenerate.text()).toBe('重新生成')
    expect(regenerate.attributes('disabled')).toBeDefined()

    await wrapper.setProps({ targetReady: true })
    await regenerate.trigger('click')
    expect(wrapper.emitted('generate')?.[0]).toEqual(['outline_expand'])

    const reviewButton = wrapper.get('[data-test="outline-conflict-review"]')
    expect(reviewButton.text()).toBe('查看怎么处理')
    await reviewButton.trigger('click')
    expect(document.activeElement).toBe(wrapper.get('[data-test="outline-assist-conflicts"]').element)
    wrapper.unmount()
  })

  it('focuses the confirmation, closes it with Escape, and restores focus to the apply button', async () => {
    const suggestion = {
      suggestion_id: 'sg-keyboard',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload: { proposed_content_text: '整理后的大纲' }
    }
    const wrapper = mount(OutlineAssistPanel, {
      attachTo: document.body,
      props: {
        ...baseProps(),
        suggestions: [suggestion],
        canApplySuggestion: vi.fn(() => true)
      }
    })
    const applyButton = wrapper.get('[data-test="suggestion-apply-sg-keyboard"]')
    applyButton.element.focus()
    await applyButton.trigger('click')
    await wrapper.setProps({ applyConfirmSuggestionId: 'sg-keyboard' })
    await nextTick()

    const dialog = wrapper.get('[data-test="suggestion-apply-confirm-sg-keyboard"]')
    const cancel = wrapper.get('[data-test="suggestion-apply-cancel-sg-keyboard"]')
    expect(dialog.attributes('aria-describedby')).toBe('outline-apply-description-sg-keyboard')
    expect(wrapper.get('#outline-apply-description-sg-keyboard').text()).toContain('当前大纲会被修改')
    expect(document.activeElement).toBe(cancel.element)

    await dialog.trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('suggestion-apply-cancel')).toHaveLength(1)
    await wrapper.setProps({ applyConfirmSuggestionId: '' })
    await nextTick()
    expect(document.activeElement).toBe(applyButton.element)
    wrapper.unmount()
  })
})
