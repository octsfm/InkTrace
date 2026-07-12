import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AutoQueuePanel from '../AutoQueuePanel.vue'

describe('AutoQueuePanel', () => {
  it('renders per-chapter confirmation, waiting review copy, and history list', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 5,
        currentRun: {
          run_id: 'aqr_001',
          status: 'waiting_user_decision',
          generated_count: 2,
          stop_record: null
        },
        historyRuns: [
          { run_id: 'aqr_001', status: 'waiting_user_decision', generated_count: 2 },
          { run_id: 'aqr_000', status: 'stopped', generated_count: 1 }
        ]
      }
    })

    expect(wrapper.text()).toContain('接着写')
    expect(wrapper.text()).toContain('说想法 → 写一章 → 你来看 → 再决定')
    expect(wrapper.text()).toContain('每次只写一章')
    expect(wrapper.text()).toContain('写完先停下来，等你看过再决定要不要继续。')
    expect(wrapper.text()).toContain('第 2 章已生成，需要你确认')
    expect(wrapper.text()).toContain('历史记录')
    expect(wrapper.text()).toContain('已生成 2 章候选稿')
  })

  it('emits config and control actions', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        targetWordCount: 50000,
        budgetLimitTokens: 120000,
        stopAtSequenceEnd: true,
        stopOnBlockingReview: true,
        stopOnBudgetExceeded: true,
        stopOnForeshadowPremature: true,
        currentRun: null,
        historyRuns: []
      }
    })

    await wrapper.get('[data-test="auto-queue-target-chapters"]').setValue('6')
    await wrapper.get('[data-test="auto-queue-target-words"]').setValue('80000')
    await wrapper.get('[data-test="auto-queue-budget-limit"]').setValue('150000')
    await wrapper.get('[data-test="auto-queue-stop-sequence-end"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-blocking-review"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-budget"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-stop-foreshadow"]').setValue(false)
    await wrapper.get('[data-test="auto-queue-save-config"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-start"]').trigger('click')
    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_002',
        status: 'waiting_user_decision',
        generated_count: 1,
        stop_record: null
      },
      historyRuns: [
        { run_id: 'aqr_002', status: 'waiting_user_decision', generated_count: 1 }
      ]
    })
    await wrapper.get('[data-test="auto-queue-view-candidates"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-confirm-continue"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-stop"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-history-aqr_002"]').trigger('click')

    expect(wrapper.find('[data-test="auto-queue-mode-continuous"]').exists()).toBe(false)
    expect(wrapper.emitted('update:target-chapters')).toEqual([[6]])
    expect(wrapper.emitted('update:target-word-count')).toEqual([[80000]])
    expect(wrapper.emitted('update:budget-limit-tokens')).toEqual([[150000]])
    expect(wrapper.emitted('update:stop-at-sequence-end')).toEqual([[false]])
    expect(wrapper.emitted('update:stop-on-blocking-review')).toEqual([[false]])
    expect(wrapper.emitted('update:stop-on-budget-exceeded')).toEqual([[false]])
    expect(wrapper.emitted('update:stop-on-foreshadow-premature')).toEqual([[false]])
    expect(wrapper.emitted('save-config')).toHaveLength(1)
    expect(wrapper.emitted('start')).toHaveLength(1)
    expect(wrapper.emitted('view-candidates')).toHaveLength(1)
    expect(wrapper.emitted('confirm-continue')).toHaveLength(1)
    expect(wrapper.emitted('stop')).toHaveLength(1)
    expect(wrapper.emitted('select-run')).toEqual([['aqr_002']])
  })

  it('shows stop summary and pause resume actions for non-terminal runs', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 8,
        currentRun: {
          run_id: 'aqr_003',
          status: 'running',
          generated_count: 4,
          stop_record: {
            stop_reason: 'budget_exceeded',
            stop_severity: 'budget',
            suggested_action: 'adjust_budget'
          }
        },
        historyRuns: []
      }
    })

    expect(wrapper.text()).toContain('每次只写一章')
    expect(wrapper.find('[data-test="auto-queue-pause"]').exists()).toBe(true)

    await wrapper.get('[data-test="auto-queue-pause"]').trigger('click')
    expect(wrapper.emitted('pause')).toHaveLength(1)

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_003',
        status: 'paused',
        generated_count: 4,
        stop_record: {
          stop_reason: 'budget_exceeded',
          stop_severity: 'budget',
          suggested_action: 'adjust_budget'
        }
      }
    })

    expect(wrapper.text()).toContain('预算已超出')
    await wrapper.get('[data-test="auto-queue-resume"]').trigger('click')
    expect(wrapper.emitted('resume')).toHaveLength(1)
  })

  it('highlights confirm continue and exposes disable budget check action', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_004',
          status: 'waiting_user_decision',
          generated_count: 2,
          stop_record: null
        },
        historyRuns: [],
        noteMessage: '等待你确认后继续下一章。'
      }
    })

    expect(wrapper.get('[data-test="auto-queue-confirm-continue"]').classes())
      .toContain('auto-queue-panel__primary')

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_004',
        status: 'stopped',
        generated_count: 2,
        stop_record: {
          stop_reason: 'budget_exceeded',
          stop_severity: 'budget',
          suggested_action: 'adjust_budget'
        }
      },
      noteMessage: ''
    })

    await wrapper.get('[data-test="auto-queue-disable-budget-check"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-continue"]').trigger('click')
    expect(wrapper.emitted('disable-budget-check')).toHaveLength(1)
    expect(wrapper.emitted('resume')).toHaveLength(1)
  })

  it('exposes view conflicts action for blocking stop reason', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 4,
        currentRun: {
          run_id: 'aqr_005',
          status: 'stopped',
          generated_count: 2,
          stop_record: {
            stop_reason: 'blocking_review_consecutive',
            stop_severity: 'blocking',
            suggested_action: 'resolve_conflict'
          }
        },
        historyRuns: []
      }
    })

    await wrapper.get('[data-test="auto-queue-view-conflicts"]').trigger('click')
    expect(wrapper.emitted('view-conflicts')).toHaveLength(1)
  })

  it('renders severity banner styles and budget usage detail', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_006',
          status: 'waiting_user_decision',
          generated_count: 2,
          stop_record: null
        },
        historyRuns: [],
        noteMessage: '等待你确认后继续下一章。'
      }
    })

    expect(wrapper.get('[data-test="auto-queue-banner"]').classes()).toContain('auto-queue-panel__banner--info')

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_006',
        status: 'stopped',
        generated_count: 2,
        consumed_tokens: 128000,
        stop_record: {
          stop_reason: 'budget_exceeded',
          stop_severity: 'budget',
          suggested_action: 'adjust_budget'
        }
      },
      noteMessage: ''
    })

    expect(wrapper.get('[data-test="auto-queue-banner"]').classes()).toContain('auto-queue-panel__banner--error')
    expect(wrapper.text()).toContain('已使用约 128000 AI 用量')
    expect(wrapper.get('[data-test="auto-queue-stop-record"]').text()).toContain('停止原因：预算已超出')
    expect(wrapper.get('[data-test="auto-queue-stop-record"]').text()).toContain('建议操作：提高预算或关闭预算检查')
  })

  it('renders queue progress, word and token overview, and per chapter status list', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 10,
        currentRun: {
          run_id: 'aqr_007',
          status: 'running',
          generated_count: 5,
          target_chapters: 10,
          total_word_count: 25000,
          target_word_count: 50000,
          consumed_tokens: 120000,
          per_chapter: [
            { chapter_title: '第1章', generated_word_count: 3200, status: 'review_passed' },
            { chapter_title: '第2章', generated_word_count: 2800, status: 'review_passed' },
            { chapter_title: '第3章', generated_word_count: 2600, status: 'candidate_generation' },
            { chapter_title: '第4章', generated_word_count: 0, status: 'waiting' }
          ]
        },
        historyRuns: []
      }
    })

    expect(wrapper.get('[data-test="auto-queue-progress"]').text()).toContain('5 / 10 章')
    expect(wrapper.text()).toContain('字数25,000 / 50,000')
    expect(wrapper.text()).toContain('AI 用量120K')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('第1章')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('审阅通过')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('生成中')
    expect(wrapper.get('[data-test="auto-queue-per-chapter"]').text()).toContain('等待中')
  })

  it('shows stop reason and suggested action inside history items', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_010',
          status: 'stopped',
          generated_count: 2,
          stop_record: {
            stop_reason: 'user_manual_stop',
            suggested_action: 'resume_queue'
          }
        },
        historyRuns: [{
          run_id: 'aqr_009',
          status: 'stopped',
          generated_count: 2,
          stop_record: {
            stop_reason: 'blocking_review_consecutive',
            suggested_action: 'resolve_conflict'
          }
        }]
      }
    })

    const historyText = wrapper.get('[data-test="auto-queue-history-aqr_009"]').text()
    expect(historyText).toContain('连续发现需要你处理的矛盾')
    expect(historyText).toContain('先查看并处理冲突详情')
  })

  it('uses chinese punctuation in per-chapter hint and stop summaries', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_015',
          status: 'stopped',
          generated_count: 2,
          stop_record: {
            stop_reason: 'blocking_review_consecutive',
            suggested_action: 'resolve_conflict'
          }
        },
        historyRuns: []
      }
    })

    expect(wrapper.text()).toContain('写完先停下来，等你看过再决定要不要继续。')
    expect(wrapper.get('[data-test="auto-queue-banner"]').text()).toContain('连续发现需要你处理的矛盾，这次续写已停下。')
    expect(wrapper.text()).not.toContain('连续模式')
    expect(wrapper.text()).not.toContain('连续发现需要你处理的矛盾,这次续写已停下。')
  })

  it('shows target word count field for queue stop conditions', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 10,
        targetWordCount: 50000,
        historyRuns: []
      }
    })

    expect(wrapper.get('[data-test="auto-queue-target-words"]').element.value).toBe('50000')
    expect(wrapper.text()).toContain('目标字数')
  })

  it('shows budget and stop toggles from queue config', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 0,
        targetWordCount: 50000,
        budgetLimitTokens: 120000,
        stopAtSequenceEnd: true,
        stopOnBlockingReview: true,
        stopOnBudgetExceeded: false,
        stopOnForeshadowPremature: true,
        historyRuns: []
      }
    })

    expect(wrapper.get('[data-test="auto-queue-budget-limit"]').element.value).toBe('120000')
    expect(wrapper.get('[data-test="auto-queue-stop-sequence-end"]').element.checked).toBe(true)
    expect(wrapper.get('[data-test="auto-queue-stop-blocking-review"]').element.checked).toBe(true)
    expect(wrapper.get('[data-test="auto-queue-stop-budget"]').element.checked).toBe(false)
    expect(wrapper.get('[data-test="auto-queue-stop-foreshadow"]').element.checked).toBe(true)
  })

  it('allows safe mode to save and start with only target word count enabled', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 0,
        targetWordCount: 80000,
        historyRuns: []
      }
    })

    expect(wrapper.get('[data-test="auto-queue-save-config"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-test="auto-queue-start"]').attributes('disabled')).toBeUndefined()
  })

  it('allows target words as the stop condition without a mode switch', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 0,
        targetWordCount: 80000,
        historyRuns: []
      }
    })

    expect(wrapper.find('[data-test="auto-queue-mode-continuous"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="auto-queue-save-config"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-test="auto-queue-start"]').attributes('disabled')).toBeUndefined()
  })

  it('shows running and completed banner copy from current run status', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_009',
          status: 'running',
          generated_count: 2
        },
        historyRuns: []
      }
    })

    expect(wrapper.text()).toContain('正在生成第 3 章')

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_009',
        status: 'completed',
        generated_count: 3
      }
    })

    expect(wrapper.text()).toContain('全部章节已生成')
    expect(wrapper.get('[data-test="auto-queue-view-candidates"]').exists()).toBe(true)
  })

  it('renders precise summary copy for completed failed and cancelled terminal states', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_011',
          status: 'completed',
          generated_count: 3
        },
        historyRuns: []
      }
    })

    expect(wrapper.get('.auto-queue-panel__summary').text()).toBe('这次新稿写完了，共有 3 章。')

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_011',
        status: 'failed',
        generated_count: 2
      }
    })
    expect(wrapper.get('.auto-queue-panel__summary').text()).toBe('这次没有写完，请看看原因或稍后重试。')

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_011',
        status: 'cancelled',
        generated_count: 2
      }
    })
    expect(wrapper.get('.auto-queue-panel__summary').text()).toBe('这次续写已结束，已经写好的新稿会保留。')
  })

  it('localizes stopping status and shows budget limit in budget exceeded banner', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 4,
        budgetLimitTokens: 500000,
        currentRun: {
          run_id: 'aqr_012',
          status: 'stopping',
          generated_count: 4,
          consumed_tokens: 520000,
          stop_record: {
            stop_reason: 'budget_exceeded',
            stop_severity: 'budget',
            suggested_action: 'adjust_budget'
          }
        },
        historyRuns: []
      }
    })

    expect(wrapper.text()).toContain('状态 正在停止')
    expect(wrapper.get('[data-test="auto-queue-banner"]').text()).toContain('已使用约 520000 / 上限 500000 AI 用量')
    expect(wrapper.get('.auto-queue-panel__summary').text()).toBe('正在停下来，写完手上这一章就结束。')
  })

  it('shows raise budget action and focuses budget input when clicked', async () => {
    const wrapper = mount(AutoQueuePanel, {
      attachTo: document.body,
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 3,
        budgetLimitTokens: 500000,
        currentRun: {
          run_id: 'aqr_013',
          status: 'stopped',
          generated_count: 2,
          stop_record: {
            stop_reason: 'budget_exceeded',
            stop_severity: 'budget',
            suggested_action: 'adjust_budget'
          }
        },
        historyRuns: []
      }
    })

    await wrapper.get('[data-test="auto-queue-raise-budget"]').trigger('click')

    expect(document.activeElement).toBe(wrapper.get('[data-test="auto-queue-budget-limit"]').element)
    wrapper.unmount()
  })

  it('falls back to configured target word count when current run snapshot omits it', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        targetChapters: 5,
        targetWordCount: 80000,
        currentRun: {
          run_id: 'aqr_014',
          status: 'running',
          generated_count: 2,
          total_word_count: 16000
        },
        historyRuns: []
      }
    })

    expect(wrapper.text()).toContain('字数16,000 / 80,000')
  })
})
