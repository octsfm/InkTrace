import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import OpeningAgentWizard from '../OpeningAgentWizard.vue'

describe('OpeningAgentWizard', () => {
  it('requires copyright confirmation on step 1 before continuing', async () => {
    const wrapper = mount(OpeningAgentWizard, {
      props: { visible: true }
    })

    expect(wrapper.get('[data-test="opening-next"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-test="opening-rights-confirm-step1"]').setValue(true)

    expect(wrapper.get('[data-test="opening-next"]').attributes('disabled')).toBeUndefined()
  })

  it('blocks generation on high risk and only allows return to modify', async () => {
    const wrapper = mount(OpeningAgentWizard, {
      props: { visible: true, riskLevel: 'high' }
    })

    await wrapper.get('[data-test="opening-rights-confirm-step1"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    await wrapper.get('[data-test="opening-strategy-confirm"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')

    expect(wrapper.text()).toContain('存在较高的模仿风险')
    expect(wrapper.find('[data-test="opening-generate"]').exists()).toBe(false)

    await wrapper.get('[data-test="opening-return-modify"]').trigger('click')

    expect(wrapper.get('[data-test="opening-step"]').text()).toContain('选择策略')
  })

  it('renders analysis and strategy shells, and gates warning generation by second rights confirmation', async () => {
    const wrapper = mount(OpeningAgentWizard, {
      props: {
        visible: true,
        riskLevel: 'warning',
        analysis: {
          analysis_summary: '参考作在前三章通过钟声与旧地图快速建立悬念。',
          hook_patterns: ['前 500 字抛出异常钟声'],
          conflict_patterns: ['主角被迫卷入灯塔旧案'],
          satisfaction_points: ['线索密集且推进快'],
          chapter_end_hooks: ['章尾留下地图来源疑点']
        },
        strategy: {
          target_audience: '悬疑向女频读者',
          genre_positioning: '都市悬疑',
          opening_hook: '用异常钟声切入谜案',
          first_three_chapter_goal: '三章内建立主角与灯塔旧案的强关联',
          protagonist_entry: '第一章前半段登场',
          conflict_entry: '第一章结尾抛出旧案反转',
          selling_points: ['节奏快', '悬念强'],
          forbidden_similarity_notes: '避免直接复用旧地图设定'
        }
      }
    })

    await wrapper.get('[data-test="opening-rights-confirm-step1"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')

    expect(wrapper.get('[data-test="opening-analysis-summary"]').text()).toContain('参考作在前三章通过钟声与旧地图快速建立悬念。')
    expect(wrapper.get('[data-test="opening-analysis-hooks"]').text()).toContain('前 500 字抛出异常钟声')

    await wrapper.get('[data-test="opening-next"]').trigger('click')

    expect(wrapper.get('[data-test="opening-strategy-card"]').text()).toContain('悬疑向女频读者')
    expect(wrapper.get('[data-test="opening-strategy-card"]').text()).toContain('避免直接复用旧地图设定')

    await wrapper.get('[data-test="opening-strategy-confirm"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')

    expect(wrapper.get('[data-test="opening-generate"]').text()).toContain('了解风险，继续生成')
    expect(wrapper.get('[data-test="opening-generate"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-test="opening-rights-confirm-step4"]').setValue(true)

    expect(wrapper.get('[data-test="opening-generate"]').attributes('disabled')).toBeUndefined()
  })

  it('uses warning-style generate label for low risk before final confirmation', async () => {
    const wrapper = mount(OpeningAgentWizard, {
      props: { visible: true, riskLevel: 'low' }
    })

    await wrapper.get('[data-test="opening-rights-confirm-step1"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    await wrapper.get('[data-test="opening-next"]').trigger('click')
    await wrapper.get('[data-test="opening-strategy-confirm"]').setValue(true)
    await wrapper.get('[data-test="opening-next"]').trigger('click')

    expect(wrapper.get('[data-test="opening-generate"]').text()).toContain('了解风险，继续生成')
    expect(wrapper.get('[data-test="opening-generate"]').attributes('disabled')).toBeDefined()
  })
})
