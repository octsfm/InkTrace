import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ChapterSidebar from '../ChapterSidebar.vue'

describe('ChapterSidebar', () => {
  it('renders chapter list and active state', () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [
          { id: 'ch-1', title: '起点', word_count: 1200, order_index: 1 },
          { id: 'ch-2', title: '', word_count: 1600, order_index: 2 }
        ],
        activeChapterId: 'ch-2'
      }
    })

    expect(wrapper.text()).toContain('第1章 起点')
    expect(wrapper.text()).toContain('第2章')
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

    await wrapper.find('.chapter-select-button').trigger('click')
    await wrapper.find('.add-button').trigger('click')

    expect(wrapper.emitted('select')).toEqual([['ch-1']])
    expect(wrapper.emitted('create')).toEqual([[]])
  })

  it('emits rename when inline editing is submitted', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [{ id: 'ch-1', title: '第一章', word_count: 1200 }],
        activeChapterId: 'ch-1'
      },
      attachTo: document.body
    })

    await wrapper.find('.chapter-action-button').trigger('click')
    const input = wrapper.find('.chapter-rename-input')
    await input.setValue('第一章·修订')
    await input.trigger('blur')

    expect(wrapper.emitted('rename')).toEqual([[{ chapterId: 'ch-1', title: '第一章·修订' }]])
  })

  it('emits delete for the target chapter', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [{ id: 'ch-1', title: '第一章', word_count: 1200 }],
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.find('.chapter-action-button.danger').trigger('click')

    expect(wrapper.emitted('delete')).toEqual([['ch-1']])
  })

  it('emits reordered chapter ids after drag and drop', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: [
          { id: 'ch-1', title: '第一章', word_count: 1200 },
          { id: 'ch-2', title: '第二章', word_count: 1600 },
          { id: 'ch-3', title: '第三章', word_count: 1800 }
        ],
        activeChapterId: 'ch-2'
      }
    })

    const items = wrapper.findAll('.chapter-item')
    const dataTransfer = {
      setData: () => {},
      effectAllowed: 'move'
    }

    await items[2].trigger('dragstart', { dataTransfer })
    await items[0].trigger('dragover', {
      preventDefault: () => {}
    })
    await items[0].trigger('drop')

    expect(wrapper.emitted('reorder')).toEqual([[['ch-3', 'ch-1', 'ch-2']]])
  })
})
