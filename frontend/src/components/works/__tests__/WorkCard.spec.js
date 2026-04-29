import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkCard from '../WorkCard.vue'

describe('WorkCard', () => {
  it('renders work summary', () => {
    const wrapper = mount(WorkCard, {
      props: {
        work: {
          id: 'work-1',
          title: '风暴将至',
          author: '测试作者',
          current_word_count: 32000,
          updated_at: '2026-04-09T10:00:00.000Z'
        }
      }
    })

    expect(wrapper.text()).toContain('风暴将至')
    expect(wrapper.text()).toContain('测试作者')
    expect(wrapper.text()).toContain('32,000')
    expect(wrapper.text()).toContain('进入写作页')
  })

  it('emits open when card is clicked', async () => {
    const wrapper = mount(WorkCard, {
      props: {
        work: {
          id: 'work-2',
          title: '第二作品',
          author: '',
          current_word_count: 0,
          updated_at: ''
        }
      }
    })

    await wrapper.trigger('click')

    expect(wrapper.emitted('open')).toEqual([['work-2']])
  })

  it('opens action menu without triggering open', async () => {
    const wrapper = mount(WorkCard, {
      props: {
        work: {
          id: 'work-3',
          title: '第三作品',
          author: '',
          current_word_count: 0,
          updated_at: ''
        }
      }
    })

    await wrapper.find('.more-button').trigger('click')

    expect(wrapper.find('.card-menu').exists()).toBe(true)
    expect(wrapper.emitted('open')).toBeUndefined()
  })

  it('requires confirmation before emitting delete', async () => {
    const wrapper = mount(WorkCard, {
      props: {
        work: {
          id: 'work-4',
          title: '第四作品',
          author: '',
          current_word_count: 0,
          updated_at: ''
        }
      }
    })

    await wrapper.find('.more-button').trigger('click')
    await wrapper.find('.menu-item.danger').trigger('click')

    expect(wrapper.find('.confirm-panel').exists()).toBe(true)
    expect(wrapper.emitted('delete')).toBeUndefined()

    await wrapper.find('.danger-button').trigger('click')

    expect(wrapper.emitted('delete')).toEqual([['work-4']])
    expect(wrapper.emitted('open')).toBeUndefined()
  })
})
