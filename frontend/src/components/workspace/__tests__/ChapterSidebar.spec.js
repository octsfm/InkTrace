import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ChapterSidebar from '../ChapterSidebar.vue'

describe('ChapterSidebar', () => {
  it('renders chapter list and active state', () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [
          { id: 'ch-1', title: '第一章', word_count: 1200 },
          { id: 'ch-2', title: '第二章', word_count: 1600 }
        ],
        activeChapterId: 'ch-2'
      }
    })

    expect(wrapper.text()).toContain('第一章')
    expect(wrapper.text()).toContain('第二章')
    expect(wrapper.text()).toContain('1,600')
    expect(wrapper.findAll('.chapter-item.active')).toHaveLength(1)
  })

  it('emits select and create actions', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [{ id: 'ch-1', title: '第一章', word_count: 1200 }],
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.find('.chapter-item').trigger('click')
    await wrapper.find('.add-button').trigger('click')

    expect(wrapper.emitted('select')).toEqual([['ch-1']])
    expect(wrapper.emitted('create')).toEqual([[]])
  })
})
