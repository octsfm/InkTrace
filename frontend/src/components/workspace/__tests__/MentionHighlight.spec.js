import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import MentionHighlight from '../MentionHighlight.vue'

describe('MentionHighlight', () => {
  it('renders user and AI mentions without changing plain content', () => {
    const wrapper = mount(MentionHighlight, {
      props: {
        content: '@张三遇见李四',
        mentions: [
          { mention_id: 'm1', start_pos: 0, end_pos: 3, source: 'user_input', status: 'active' },
          { mention_id: 'm2', start_pos: 5, end_pos: 7, source: 'ai_suggestion', status: 'active' }
        ]
      }
    })
    expect(wrapper.text()).toContain('@张三遇见李四')
    expect(wrapper.get('[data-mention-id="m1"]').classes()).toContain('mention-highlight__item--user')
    expect(wrapper.get('[data-mention-id="m2"]').classes()).toContain('mention-highlight__item--ai')
  })

  it('does not highlight broken mentions and loads a summary after hover delay', async () => {
    vi.useFakeTimers()
    const wrapper = mount(MentionHighlight, {
      props: {
        content: '@张三',
        mentions: [
          { mention_id: 'broken', start_pos: 0, end_pos: 3, source: 'user_input', status: 'broken' },
          { mention_id: 'm1', start_pos: 0, end_pos: 3, source: 'user_input', status: 'active' }
        ]
      }
    })
    expect(wrapper.find('[data-mention-id="broken"]').exists()).toBe(false)
    await wrapper.get('[data-mention-id="m1"]').trigger('mouseenter')
    vi.advanceTimersByTime(500)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('mention-hover')?.[0]?.[0]?.mention_id).toBe('m1')
    expect(wrapper.find('[data-test="mention-tooltip"]').exists()).toBe(true)
    vi.useRealTimers()
  })
})
