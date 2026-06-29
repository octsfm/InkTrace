import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AutoQueuePanel from '../AutoQueuePanel.vue'

describe('AutoQueuePanel', () => {
  it('renders safe mode configuration, waiting state, and history list', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        savingConfig: false,
        actionLoading: false,
        chapterId: 'chapter-1',
        queueMode: 'safe',
        targetChapters: 5,
        currentRun: {
          run_id: 'aqr_001',
          status: 'waiting_user_decision',
          queue_mode: 'safe',
          generated_count: 2,
          stop_record: null
        },
        historyRuns: [
          { run_id: 'aqr_001', status: 'waiting_user_decision', queue_mode: 'safe', generated_count: 2 },
          { run_id: 'aqr_000', status: 'stopped', queue_mode: 'safe', generated_count: 1 }
        ],
        noteMessage: '等待你确认后继续下一章。'
      }
    })

    expect(wrapper.text()).toContain('自动续写')
    expect(wrapper.text()).toContain('安全模式')
    expect(wrapper.text()).toContain('等待你确认后继续下一章。')
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
        queueMode: 'safe',
        targetChapters: 3,
        currentRun: {
          run_id: 'aqr_002',
          status: 'waiting_user_decision',
          queue_mode: 'safe',
          generated_count: 1,
          stop_record: null
        },
        historyRuns: [
          { run_id: 'aqr_002', status: 'waiting_user_decision', queue_mode: 'safe', generated_count: 1 }
        ]
      }
    })

    await wrapper.get('[data-test="auto-queue-mode-continuous"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-target-chapters"]').setValue('6')
    await wrapper.get('[data-test="auto-queue-save-config"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-start"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-confirm-continue"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-stop"]').trigger('click')
    await wrapper.get('[data-test="auto-queue-history-aqr_002"]').trigger('click')

    expect(wrapper.emitted('update:queue-mode')).toEqual([['continuous']])
    expect(wrapper.emitted('update:target-chapters')).toEqual([[6]])
    expect(wrapper.emitted('save-config')).toHaveLength(1)
    expect(wrapper.emitted('start')).toHaveLength(1)
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
        queueMode: 'continuous',
        targetChapters: 8,
        currentRun: {
          run_id: 'aqr_003',
          status: 'running',
          queue_mode: 'continuous',
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

    expect(wrapper.text()).toContain('连续模式')
    expect(wrapper.find('[data-test="auto-queue-pause"]').exists()).toBe(true)

    await wrapper.get('[data-test="auto-queue-pause"]').trigger('click')
    expect(wrapper.emitted('pause')).toHaveLength(1)

    await wrapper.setProps({
      currentRun: {
        run_id: 'aqr_003',
        status: 'paused',
        queue_mode: 'continuous',
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
})
